"""Pilot-only Claude Code subscription transport.

This adapter deliberately lives in ``scripts/``: it is not a registered
provider, configuration schema option, or package export.  It converts the
neutral Harnessie request/response shapes to one short-lived Claude Code CLI
process. Operational native tools are disabled. Claude Code's built-in
``StructuredOutput`` formatter is the sole observed CLI formatting mechanism;
it is bound to the terminal envelope and is never dispatched by Harnessie.
Returned neutral tool requests are validated against the tools that Harnessie
offered, and Harnessie performs all operational tool dispatch.

``PilotLimits.max_output_tokens`` is supplied as
``CLAUDE_CODE_MAX_OUTPUT_TOKENS`` because the tested Claude Code CLI does not
provide a stable command-line output-token flag. The adapter also refuses a
completed response whose aggregate reported output across all models exceeds
that limit, retaining its capture and usage first. This cannot prevent already
generated provider usage. The independent byte limit is always enforced while
draining stdout.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time
from typing import Any, Mapping

import jsonschema
from jsonschema.exceptions import SchemaError

from harness.models.base import AssistantTurn, Message, ModelInterface, ModelSpec, ToolCall

from scripts.pilot_contract import CLAUDE_MODEL, CallAllowance, PilotLimits, PilotRefusal
from scripts.pilot_policy import EXACT_MODEL_ONLY, PilotPolicy, PolicyDecision
from scripts.pilot_request_metrics import PreparedPilotRequest
from scripts.pilot_stream import parse_stream_json, unknown_usage
from scripts.pilot_capture import ResponseCaptureStore


AUTH_CONTRACT_ID = "claude-code-first-party-oauth-plus-billing/v2"
AUTH_CLASS = "claude.ai:oauth:firstParty"
LEGACY_MAX_AUTH_CLASS = "claude.ai:max:firstParty"
ELIGIBLE_AUTH_CLASSES = frozenset({AUTH_CLASS, LEGACY_MAX_AUTH_CLASS})
CLI_STDIN_PROMPT = (
    "Process the neutral Harnessie request JSON supplied on stdin and return the "
    "requested structured response; never execute tools."
)
_SAFE_ENV = frozenset({"PATH", "HOME", "USER", "LANG", "LC_ALL", "TMPDIR", "TERM", "TZ", "NO_COLOR"})


@dataclass(frozen=True)
class PilotReceipt:
    """Non-secret record of one completed or refused pilot request."""

    requested_model: str
    reported_model: str | None
    answer_model: str | None
    observed_candidate_model: str | None
    auth_class: str | None
    usage: dict[str, int | None]
    model_usage: dict[str, dict[str, int | None]]
    reported_model_usages: tuple[dict[str, Any], ...]
    policy_id: str
    policy_disposition: str
    policy_bounds: dict[str, int]
    dollar_cost: None
    attempt: int | None
    inference_started: bool
    status: str
    failure: str | None = None
    response_capture: dict[str, Any] | None = None
    parser_diagnostic: dict[str, str | int] | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def dollar_cost_usd(self) -> None:
        """Subscription execution has no per-request dollar receipt."""
        return None


@dataclass(frozen=True)
class _RunResult:
    output: bytes | None
    returncode: int | None
    failure: str | None


class ClaudeCodePilot(ModelInterface):
    """Bounded, fail-closed transport for an already-authenticated Max CLI."""

    def __init__(
        self,
        spec: ModelSpec,
        executable: Path,
        cwd: Path,
        allowance: CallAllowance | None = None,
        env: Mapping[str, str] | None = None,
        policy: PilotPolicy = EXACT_MODEL_ONLY,
        capture_store: ResponseCaptureStore | None = None,
        expected_auth_class: str | None = None,
    ) -> None:
        super().__init__(spec)
        if spec.model_id != CLAUDE_MODEL:
            raise PilotRefusal("unsupported_pilot_model")
        if not isinstance(executable, Path) or not executable.is_file() or not os.access(executable, os.X_OK):
            raise PilotRefusal("invalid_executable")
        if not isinstance(cwd, Path) or not cwd.is_dir():
            raise PilotRefusal("invalid_cwd")
        if env is not None and not isinstance(env, Mapping):
            raise PilotRefusal("invalid_environment")
        if type(policy) is not PilotPolicy:
            raise PilotRefusal("invalid_pilot_policy")
        if expected_auth_class is not None and expected_auth_class not in ELIGIBLE_AUTH_CLASSES:
            raise PilotRefusal("invalid_auth_contract")
        self.executable = executable.resolve()
        self.cwd = cwd.resolve()
        self.allowance = allowance or CallAllowance()
        if capture_store is not None and (type(capture_store) is not ResponseCaptureStore
                or capture_store.max_bytes != self.allowance.limits.max_output_bytes):
            raise PilotRefusal("invalid_response_capture_store")
        self.capture_store = capture_store
        self.expected_auth_class = expected_auth_class
        self._response_capture = None
        self._parser_diagnostic = None
        self._requested_env = dict(env or {})
        self.policy = policy
        self.receipts: list[PilotReceipt] = []
        # AgentLoop calls once more after an error.  A pilot failure must not
        # silently turn into a fresh provider attempt in that loop.
        self._failed = False

    def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        effort: str = "medium",
    ) -> AssistantTurn:
        self._response_capture = None
        self._parser_diagnostic = None
        if self._failed:
            return self._refuse("transport_latched", None)
        offered_tools = tools or []
        try:
            prepared = self.prepare_request(messages, offered_tools, effort)
        except (AttributeError, TypeError, ValueError, PilotRefusal, SchemaError, UnicodeError):
            return self._refuse("invalid_request", None)
        if len(prepared.request) > self.allowance.limits.max_input_bytes:
            return self._refuse("input_limit_exceeded", None)
        evidence_bytes = sum(len(message.content.encode("utf-8")) for message in messages
                             if message.role == "tool")
        if evidence_bytes > self.allowance.limits.max_evidence_bytes:
            return self._refuse("evidence_limit_exceeded", None)
        return self.complete_prepared(prepared, offered_tools, effort)

    @classmethod
    def prepare_request(
        cls,
        messages: list[Message],
        tools: list[dict] | None = None,
        effort: str = "medium",
    ) -> PreparedPilotRequest:
        """Encode the exact neutral request bytes without launching anything."""
        request = cls._request_prompt(messages, tools or []).encode("utf-8")
        return PreparedPilotRequest(
            request=request,
            transport="claude-code-max-pilot",
            encoding="claude_code_stdin_neutral_json",
            inner_prompt_bytes=None,
        )

    def complete_prepared(
        self,
        prepared: PreparedPilotRequest,
        offered_tools: list[dict],
        effort: str = "medium",
    ) -> AssistantTurn:
        """Run one already measured request without re-encoding its bytes."""
        self._response_capture = None
        self._parser_diagnostic = None
        if self._failed:
            return self._refuse("transport_latched", None)
        if (type(prepared) is not PreparedPilotRequest
                or prepared.transport != "claude-code-max-pilot"
                or prepared.encoding != "claude_code_stdin_neutral_json"
                or prepared.inner_prompt_bytes is not None
                or not isinstance(prepared.request, bytes)
                or type(offered_tools) is not list):
            return self._refuse("invalid_request", None)
        if len(prepared.request) > self.allowance.limits.max_input_bytes:
            return self._refuse("input_limit_exceeded", None)

        # Authentication is a subprocess too.  Reserve before it, so a zero
        # allowance means no executable is ever launched.
        try:
            auth_attempt = self.allowance.reserve()
        except PilotRefusal as exc:
            return self._refuse(exc.code, None)
        auth_result = self._run([str(self.executable), "auth", "status", "--json"], b"")
        auth_data = self._json_object(auth_result.output)
        auth_class = self._auth_class(auth_data)
        if auth_result.failure is not None:
            return self._refuse(auth_result.failure, auth_attempt)
        if auth_result.returncode != 0:
            return self._refuse("auth_status_failed", auth_attempt)
        if auth_class is None:
            return self._refuse("auth_ineligible", auth_attempt)
        if self.expected_auth_class is not None and auth_class != self.expected_auth_class:
            return self._refuse("auth_identity_drift", auth_attempt)

        attempt = auth_attempt
        reservation = None
        if self.capture_store is not None:
            try:
                reservation = self.capture_store.reserve(attempt)
            except (PilotRefusal, OSError):
                self._response_capture = {"status": "failed", "phase": "before_inference"}
                return self._refuse("response_capture_failed", attempt, auth_class=auth_class)
        config_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as config:
                config.write('{"mcpServers":{}}')
                config_path = Path(config.name)
            result = self._run(self._inference_argv(effort, config_path), prepared.request)
        finally:
            if config_path is not None:
                try:
                    config_path.unlink(missing_ok=True)
                except OSError:
                    pass

        capture_failed = False
        if reservation is not None:
            try:
                self._response_capture = reservation.save(result.output, returncode=result.returncode,
                                                           process_failure=result.failure)
            except (PilotRefusal, OSError):
                capture_failed = True
                self._response_capture = {"status": "failed", "phase": "after_inference",
                                          "directory": str(reservation.directory)}
        # Save bytes before interpretation. Even if persistence failed, parse
        # the in-memory bytes for accounting only; never accept or retry them.
        capture = parse_stream_json(result.output or b"")
        self._parser_diagnostic = capture.diagnostic
        usage = capture.usage_totals
        observed_candidate_model = capture.answer_model
        # A candidate model becomes an answer only after the entire stream has
        # linked it to one successful StructuredOutput terminal result.
        reported_model = observed_candidate_model if capture.failure is None else None
        model_usage = capture.model_usage
        reported_model_usages = capture.reported_model_usages
        decision = PolicyDecision("not_evaluated", None)
        if capture_failed:
            return self._refuse("response_capture_failed", attempt, None, auth_class, usage, True,
                                model_usage, reported_model_usages, observed_candidate_model)
        if result.failure is not None:
            return self._refuse(result.failure, attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model)
        if result.returncode != 0:
            return self._refuse("process_failed", attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model)
        if capture.failure is not None:
            return self._refuse(capture.failure, attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model)
        if reported_model is None:
            return self._refuse("model_identity_unknown", attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model)
        if reported_model != self.spec.model_id:
            return self._refuse("model_identity_mismatch", attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model)
        if self.spec.model_id not in model_usage:
            return self._refuse("model_identity_unknown", attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model)
        if len(reported_model_usages) != 1:
            return self._refuse("model_usage_ambiguous", attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model)
        decision = self.policy.evaluate(self.spec.model_id, reported_model_usages[0], model_usage)
        if decision.failure is not None:
            return self._refuse(decision.failure, attempt, reported_model, auth_class, usage, True, model_usage,
                                reported_model_usages, observed_candidate_model, decision)
        data = {"structured_output": capture.structured_output}
        try:
            turn = self._turn(data, offered_tools)
        except PilotRefusal as exc:
            return self._refuse(exc.code, attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model, decision)
        except (TypeError, ValueError, json.JSONDecodeError):
            return self._refuse("malformed_response", attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model, decision)
        if usage["input_tokens"] is None or usage["output_tokens"] is None:
            # A subscription has no dollar receipt, so primary token counts
            # are the minimum evidence needed for a successful pilot turn.
            return self._refuse("usage_unknown", attempt, reported_model, auth_class, usage, True, model_usage, reported_model_usages, observed_candidate_model, decision)
        if usage["output_tokens"] > self.allowance.limits.max_output_tokens:
            return self._refuse("output_token_limit_exceeded", attempt, reported_model, auth_class,
                                usage, True, model_usage, reported_model_usages,
                                observed_candidate_model, decision)

        receipt = PilotReceipt(
            requested_model=self.spec.model_id,
            reported_model=reported_model,
            answer_model=reported_model,
            observed_candidate_model=observed_candidate_model,
            auth_class=auth_class,
            usage=usage,
            model_usage=model_usage,
            reported_model_usages=reported_model_usages,
            policy_id=self.policy.id,
            policy_disposition=decision.disposition,
            policy_bounds=self.policy.bounds,
            dollar_cost=None,
            attempt=attempt,
            inference_started=True,
            status="completed",
            response_capture=self._response_capture,
            parser_diagnostic=self._parser_diagnostic,
        )
        self.receipts.append(receipt)
        return AssistantTurn(
            content=turn[0], tool_calls=turn[1], stop_reason=turn[2],
            input_tokens=usage["input_tokens"] or 0,
            output_tokens=usage["output_tokens"] or 0,
        )

    def _refuse(
        self,
        code: str,
        attempt: int | None,
        reported_model: str | None = None,
        auth_class: str | None = None,
        usage: dict[str, int | None] | None = None,
        inference_started: bool = False,
        model_usage: dict[str, dict[str, int | None]] | None = None,
        reported_model_usages: tuple[dict[str, Any], ...] = (),
        observed_candidate_model: str | None = None,
        decision: PolicyDecision | None = None,
    ) -> AssistantTurn:
        self._failed = True
        self.receipts.append(PilotReceipt(
            requested_model=self.spec.model_id,
            reported_model=reported_model,
            answer_model=reported_model,
            observed_candidate_model=observed_candidate_model,
            auth_class=auth_class,
            usage=usage or unknown_usage(),
            model_usage=model_usage or {},
            reported_model_usages=reported_model_usages,
            policy_id=self.policy.id,
            policy_disposition=(decision.disposition if decision else "not_evaluated"),
            policy_bounds=self.policy.bounds,
            dollar_cost=None,
            attempt=attempt,
            inference_started=inference_started,
            status="refused",
            failure=code,
            response_capture=self._response_capture,
            parser_diagnostic=self._parser_diagnostic,
        ))
        return AssistantTurn(content=f"pilot_refusal: {code}", stop_reason="error")

    def _sanitized_env(self) -> dict[str, str]:
        # Do not inherit arbitrary process settings.  In particular, credentials
        # and cloud/provider endpoint overrides never cross this process boundary.
        env = {key: os.environ[key] for key in _SAFE_ENV if key in os.environ}
        env.update({key: value for key, value in self._requested_env.items()
                    if key in _SAFE_ENV and isinstance(value, str)})
        env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(self.allowance.limits.max_output_tokens)
        return env

    def _run(self, argv: list[str], stdin: bytes) -> _RunResult:
        limits = self.allowance.limits
        if len(stdin) > limits.max_input_bytes:
            return _RunResult(None, None, "input_limit_exceeded")
        try:
            with tempfile.TemporaryFile() as input_file:
                input_file.write(stdin)
                input_file.seek(0)
                process = subprocess.Popen(
                    argv, cwd=self.cwd, stdin=input_file, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, env=self._sanitized_env(),
                    start_new_session=True,
                )
                return self._drain(process)
        except (OSError, ValueError):
            return _RunResult(None, None, "process_start_failed")

    def _drain(self, process: subprocess.Popen[bytes]) -> _RunResult:
        assert process.stdout is not None
        output = bytearray()
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + self.allowance.limits.timeout_s
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._kill_group(process)
                    return _RunResult(bytes(output), None, "process_timeout")
                events = selector.select(remaining)
                if not events:
                    continue
                for key, _ in events:
                    chunk = os.read(key.fd, min(8192, self.allowance.limits.max_output_bytes + 1 - len(output)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    output.extend(chunk)
                    if len(output) > self.allowance.limits.max_output_bytes:
                        self._kill_group(process)
                        return _RunResult(bytes(output), None, "output_limit_exceeded")
            try:
                return _RunResult(bytes(output), process.wait(timeout=0.2), None)
            except subprocess.TimeoutExpired:
                self._kill_group(process)
                return _RunResult(bytes(output), None, "process_timeout")
        except BaseException:
            self._kill_group(process)
            raise
        finally:
            selector.close()

    @staticmethod
    def _kill_group(process: subprocess.Popen[bytes]) -> None:
        # A leader can exit while a child inherited its stdout.  Kill by PGID
        # even then, otherwise the child keeps draining blocked indefinitely.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (AttributeError, OSError):
            if process.poll() is None:
                process.kill()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass

    def _inference_argv(self, effort: str, config_path: Path) -> list[str]:
        schema = json.dumps(self._output_schema(), separators=(",", ":"))
        return [
            str(self.executable), "--safe-mode", "--tools", "", "--strict-mcp-config",
            "--mcp-config", str(config_path), "--setting-sources", "",
            "--no-session-persistence", "--output-format", "stream-json", "--verbose", "--json-schema", schema,
            "--model", self.spec.model_id, "--effort", effort, "--print", CLI_STDIN_PROMPT,
        ]

    @staticmethod
    def _output_schema() -> dict[str, object]:
        return {
            "type": "object", "additionalProperties": False,
            "required": ["content", "tool_calls", "stop_reason"],
            "properties": {
                "content": {"type": "string"},
                "tool_calls": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["id", "name", "arguments"],
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"},
                                   "arguments": {"type": "object"}},
                }},
                "stop_reason": {"enum": ["end_turn", "tool_use", "max_tokens", "refusal"]},
            },
        }

    @staticmethod
    def _request_prompt(messages: list[Message], tools: list[dict]) -> str:
        wire_messages = []
        for message in messages:
            if (type(message) is not Message
                    or message.role not in {"system", "user", "assistant", "tool"}
                    or not isinstance(message.content, str)):
                raise ValueError("invalid message")
            calls = []
            for call in message.tool_calls:
                if not isinstance(call.id, str) or not isinstance(call.name, str) or not isinstance(call.arguments, dict):
                    raise ValueError("invalid tool call")
                calls.append({"id": call.id, "name": call.name, "arguments": call.arguments})
            wire_messages.append({"role": message.role, "content": message.content,
                                  "tool_calls": calls, "tool_call_id": message.tool_call_id,
                                  "name": message.name})
        if any(not isinstance(tool, dict) or not isinstance(tool.get("name"), str) or not tool["name"]
               or not isinstance(tool.get("parameters"), dict) for tool in tools):
            raise ValueError("invalid tools")
        if len({tool["name"] for tool in tools}) != len(tools):
            raise ValueError("duplicate tool names")
        for tool in tools:
            jsonschema.Draft202012Validator.check_schema(tool["parameters"])
        return json.dumps({"messages": wire_messages, "tools": tools,
                           "instruction": "Return only the requested structured response. Never execute tools."},
                          separators=(",", ":"), ensure_ascii=False, allow_nan=False)

    @staticmethod
    def _json_object(output: bytes | None) -> dict[str, Any] | None:
        if output is None:
            return None
        try:
            data = json.loads(output.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _auth_class(data: dict[str, Any] | None) -> str | None:
        if not isinstance(data, dict):
            return None
        if data.get("loggedIn") is not True or data.get("apiProvider") != "firstParty":
            return None
        if data.get("authMethod") == "oauth_token":
            return AUTH_CLASS
        if data.get("authMethod") == "claude.ai" and data.get("subscriptionType") == "max":
            return LEGACY_MAX_AUTH_CLASS
        return None

    @staticmethod
    def _result_failure(data: dict[str, Any]) -> str | None:
        if data.get("is_error") is True:
            return "provider_result_error"
        subtype = data.get("subtype")
        if subtype == "error":
            return "provider_result_error"
        if subtype in {"max_turns", "max-turns"}:
            return "provider_result_max_turns"
        return None

    @staticmethod
    def _unknown_usage() -> dict[str, int | None]:
        return {
            "input_tokens": None,
            "output_tokens": None,
            "cache_creation_input_tokens": None,
            "cache_read_input_tokens": None,
        }

    @classmethod
    def _usage(cls, data: dict[str, Any] | None) -> dict[str, int | None]:
        sources: list[dict[str, Any]] = []
        if isinstance(data, dict):
            model_usage = data.get("modelUsage")
            if isinstance(model_usage, dict) and len(model_usage) == 1:
                candidate = next(iter(model_usage.values()))
                if isinstance(candidate, dict):
                    sources.append(candidate)
            top_level = data.get("usage")
            if isinstance(top_level, dict):
                sources.append(top_level)
        def count(*names: str) -> int | None:
            for source in sources:
                for name in names:
                    value = source.get(name)
                    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                        return value
            return None
        return {
            "input_tokens": count("input_tokens", "inputTokens"),
            "output_tokens": count("output_tokens", "outputTokens"),
            "cache_creation_input_tokens": count(
                "cache_creation_input_tokens", "cacheCreationInputTokens"),
            "cache_read_input_tokens": count(
                "cache_read_input_tokens", "cacheReadInputTokens"),
        }

    def _reported_model(self, data: dict[str, Any] | None) -> tuple[str | None, str | None]:
        if not isinstance(data, dict) or not isinstance(data.get("modelUsage"), dict):
            return None, "model_identity_unknown"
        models = data["modelUsage"]
        if len(models) != 1:
            return None, "model_identity_mismatch"
        reported = next(iter(models))
        if not isinstance(reported, str) or not reported:
            return None, "model_identity_unknown"
        if reported != self.spec.model_id:
            return reported, "model_identity_mismatch"
        return reported, None

    @staticmethod
    def _turn(data: dict[str, Any], offered_tools: list[dict]) -> tuple[str, list[ToolCall], str]:
        envelope = data.get("structured_output")
        if not isinstance(envelope, dict) or set(envelope) != {"content", "tool_calls", "stop_reason"}:
            raise ValueError("invalid structured output")
        content, raw_calls, stop_reason = (envelope["content"], envelope["tool_calls"], envelope["stop_reason"])
        if not isinstance(content, str) or not isinstance(raw_calls, list):
            raise TypeError("invalid structured output values")
        offered = {tool["name"] for tool in offered_tools}
        calls: list[ToolCall] = []
        call_ids: set[str] = set()
        for raw_call in raw_calls:
            if not isinstance(raw_call, dict) or set(raw_call) != {"id", "name", "arguments"}:
                raise TypeError("invalid tool call")
            call_id, name, arguments = raw_call["id"], raw_call["name"], raw_call["arguments"]
            if not isinstance(call_id, str) or not call_id or not isinstance(name, str) or name not in offered:
                raise PilotRefusal("tool_not_offered")
            if call_id in call_ids:
                raise PilotRefusal("duplicate_tool_call_id")
            call_ids.add(call_id)
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as exc:
                    raise PilotRefusal("malformed_tool_arguments") from exc
            if not isinstance(arguments, dict):
                raise PilotRefusal("malformed_tool_arguments")
            schema = next(tool["parameters"] for tool in offered_tools if tool["name"] == name)
            try:
                jsonschema.Draft202012Validator(schema).validate(arguments)
            except jsonschema.ValidationError as exc:
                raise PilotRefusal("tool_arguments_invalid") from exc
            calls.append(ToolCall(id=call_id, name=name, arguments=arguments))
        if not isinstance(stop_reason, str) or stop_reason not in {"end_turn", "tool_use", "max_tokens", "refusal"}:
            raise ValueError("invalid stop reason")
        if calls and stop_reason != "tool_use":
            raise PilotRefusal("tool_calls_with_terminal_stop")
        return content, calls, stop_reason
