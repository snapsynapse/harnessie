#!/bin/bash
# Harbor verifier, in-sandbox form. Runs inside the task environment after
# the agent and writes the reward under /logs/verifier/.
#
# Reward mapping, shared with ../../harnessie_reward.py:
#   harnessie verify exit 0 (verified)       -> reward.txt = 1
#   harnessie verify exit 1 (failed)         -> reward.txt = 0
#   anything else (2 = cannot verify, crash) -> no reward file; the trial is
#                                               unscorable, never a zero
#
# Every path below can be overridden by environment variable so the script
# is testable outside Harbor with a stub in place of the real verifier.
set -u

LOGS="${HARBOR_VERIFIER_DIR:-/logs/verifier}"
WORKSPACE="${HARBOR_WORKSPACE:-/app}"
CLAIMS="${HARBOR_CLAIMS:-/tests/claims.md}"
HARNESSIE_VERSION="${HARNESSIE_VERSION:-1.4.1}"
mkdir -p "$LOGS"

if [ -n "${HARNESSIE_VERIFY_CMD:-}" ]; then
  VERIFY="$HARNESSIE_VERIFY_CMD"
else
  # Fresh install of the pinned release through uv; harnessie needs an OS
  # sandbox backend (bubblewrap is in the image) or every check reports
  # cannot-verify and the trial stays unscorable, which is the honest result.
  if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    # shellcheck disable=SC1091
    [ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
  fi
  VERIFY="uvx --from harnessie==${HARNESSIE_VERSION} harnessie verify"
fi

$VERIFY \
  --workspace "$WORKSPACE" \
  --criteria "$CLAIMS" \
  --no-verifier \
  --report-dir "$LOGS/harnessie" \
  --check "python3 -c 'import calc; assert calc.add(2, 3) == 5'" \
  --check "python3 -c \"import calc
raised = False
try:
    calc.mean([])
except ValueError:
    raised = True
assert raised\"" \
  > "$LOGS/harnessie-verify.log" 2>&1
code=$?

case "$code" in
  0) outcome=verified;      echo 1 > "$LOGS/reward.txt" ;;
  1) outcome=failed;        echo 0 > "$LOGS/reward.txt" ;;
  *) outcome=cannot_verify; code=2 ;;
esac
scored=true; [ "$outcome" = cannot_verify ] && scored=false
printf '{"verifier": "harnessie", "exit_code": %s, "outcome": "%s", "scored": %s, "report": "%s"}\n' \
  "$code" "$outcome" "$scored" "$LOGS/harnessie/report.md" > "$LOGS/harnessie-verify.json"
exit 0
