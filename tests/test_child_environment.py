"""Child-process environment isolation for checks and model shell tools."""

import os
import subprocess

from harness.tools.builtin import scrubbed_env


def test_scrubbed_env_disables_operator_git_configuration(monkeypatch):
    monkeypatch.setenv("HOME", "/operator/home")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/operator/global.gitconfig")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "0")

    env = scrubbed_env()

    assert env["HOME"] == "/operator/home"
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"


def test_scrubbed_env_drops_credentials_and_git_override_vectors(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "commit.gpgsign")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")

    env = scrubbed_env()

    assert "OPENAI_API_KEY" not in env
    assert "GIT_CONFIG_COUNT" not in env
    assert "GIT_CONFIG_KEY_0" not in env
    assert "GIT_CONFIG_VALUE_0" not in env


def test_scrubbed_env_prevents_global_commit_signing_from_breaking_fixtures(
        tmp_path, monkeypatch):
    global_config = tmp_path / "operator.gitconfig"
    global_config.write_text(
        "[commit]\n\tgpgsign = true\n[user]\n"
        "\tname = Operator\n\temail = operator@example.invalid\n",
        encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    repo = tmp_path / "repo"
    repo.mkdir()
    env = scrubbed_env()

    subprocess.run(["git", "init", "-q"], cwd=repo, env=env, check=True)
    (repo / "proof.txt").write_text("proof\n", encoding="utf-8")
    subprocess.run(["git", "add", "proof.txt"], cwd=repo, env=env, check=True)
    committed = subprocess.run(
        ["git", "-c", "user.name=Harnessie", "-c",
         "user.email=harnessie@example.invalid", "commit", "-qm", "proof"],
        cwd=repo, env=env, capture_output=True, text=True)

    assert committed.returncode == 0, committed.stderr
