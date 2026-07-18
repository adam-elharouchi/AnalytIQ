"""
tests/unit/test_sandbox_container.py — the container execution backend.

Student code (playground "Run" + deterministic grading) can execute inside a
locked-down container instead of a host subprocess, gated behind
config.SANDBOX_USE_CONTAINER (default off). Docker cannot run in CI/this
environment, so these tests exercise the seam without a daemon:

  * default OFF  -> host backend is used (container_runner is never called)
  * flag ON      -> code_runner dispatches to container_runner, the docker argv
                    carries every hardening flag, and harness output round-trips
  * fail-closed  -> flag ON with no docker CLI never falls back to the host
  * timeout      -> the container is killed by name so it can't outlive the run
  * build_argv   -> pure-function assertions on the isolation flags

The actual container execution is validated on real infra (see
docs/SANDBOX_CONTAINER.md); here we prove the wiring and the command we build.
"""
import json
import subprocess
import types

import pytest

import config
from services import code_runner
from services import container_runner


# ---------------------------------------------------------------------------
# Helpers: fake a present docker CLI + a fake `docker run` returning harness JSON
# ---------------------------------------------------------------------------


def _fake_completed(stdout="", stderr="", returncode=0):
    return types.SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


class _RunRecorder:
    """Stand-in for subprocess.run that records argv and returns canned output."""

    def __init__(self, stdout="", stderr="", raise_timeout=False):
        self.stdout = stdout
        self.stderr = stderr
        self.raise_timeout = raise_timeout
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        # The kill-on-timeout path is a second call: [cli, "kill", name]
        if self.raise_timeout and argv[:2] == [config.SANDBOX_CONTAINER_CLI, "run"]:
            raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout"))
        return _fake_completed(self.stdout, self.stderr)


@pytest.fixture
def fake_docker(monkeypatch):
    """Pretend the docker CLI exists on PATH."""
    monkeypatch.setattr(container_runner, "_cli_path", lambda: "/usr/bin/docker")


# ---------------------------------------------------------------------------
# Default OFF: host backend, container_runner never touched
# ---------------------------------------------------------------------------


class TestFlagDefaultOff:
    def test_flag_defaults_off(self):
        assert config.SANDBOX_USE_CONTAINER is False

    def test_run_code_uses_host_when_off(self, monkeypatch):
        monkeypatch.setattr(config, "SANDBOX_USE_CONTAINER", False)

        def _boom(*a, **k):
            raise AssertionError("container_runner must not be called when flag is off")

        monkeypatch.setattr(container_runner, "run_in_container", _boom)
        r = code_runner.run_code("print(6*7)", language="python", timeout=10)
        assert r["stdout"].strip() == "42"
        assert r["timed_out"] is False

    def test_run_test_cases_uses_host_when_off(self, monkeypatch):
        monkeypatch.setattr(config, "SANDBOX_USE_CONTAINER", False)
        monkeypatch.setattr(
            container_runner,
            "run_in_container",
            lambda **k: (_ for _ in ()).throw(AssertionError("should not run")),
        )
        tcs = [{"description": "add", "input": [2, 3], "expected_output": 5, "weight": 1}]
        g = code_runner.run_test_cases("def add(a, b):\n    return a + b", "Python", "add", tcs)
        assert g["tests_passed"] == 1


# ---------------------------------------------------------------------------
# Flag ON with a (faked) docker: dispatch + output round-trip + argv hardening
# ---------------------------------------------------------------------------


class TestContainerDispatch:
    def test_run_code_dispatches_and_roundtrips(self, monkeypatch, fake_docker):
        monkeypatch.setattr(config, "SANDBOX_USE_CONTAINER", True)
        rec = _RunRecorder(stdout=json.dumps({"stdout": "hello\n", "stderr": ""}))
        monkeypatch.setattr(container_runner.subprocess, "run", rec)

        r = code_runner.run_code("print('hello')", language="python", timeout=7)
        assert r["stdout"] == "hello\n"
        assert r["timed_out"] is False

        argv = rec.calls[0][0]
        assert argv[:2] == ["docker", "run"]
        assert argv[-3:] == ["python", "/opt/run/harness.py", "/opt/run/code.py"]

    def test_grading_dispatches_and_grades(self, monkeypatch, fake_docker):
        monkeypatch.setattr(config, "SANDBOX_USE_CONTAINER", True)
        rec = _RunRecorder(stdout=json.dumps({"result": 5, "printed": None, "error": None}))
        monkeypatch.setattr(container_runner.subprocess, "run", rec)

        tcs = [{"description": "add", "input": [2, 3], "expected_output": 5, "weight": 1}]
        g = code_runner.run_test_cases("def add(a, b):\n    return a + b", "Python", "add", tcs)
        assert g["tests_passed"] == 1

        # Grading uses the deterministic (network=none) path.
        argv = rec.calls[0][0]
        assert argv[argv.index("--network") + 1] == "none"
        # harness command tail: python <harness> <input-json> <fn-name> <code-path>
        assert argv[-5:] == [
            "python",
            "/opt/run/harness.py",
            "[2, 3]",
            "add",
            "/opt/run/code.py",
        ]

    def test_docker_argv_has_all_hardening_flags(self, monkeypatch, fake_docker):
        monkeypatch.setattr(config, "SANDBOX_USE_CONTAINER", True)
        rec = _RunRecorder(stdout=json.dumps({"stdout": "", "stderr": ""}))
        monkeypatch.setattr(container_runner.subprocess, "run", rec)

        code_runner.run_code("pass", language="python", timeout=5)
        argv = rec.calls[0][0]
        joined = " ".join(argv)

        assert "--rm" in argv
        assert "--read-only" in argv
        assert "--cap-drop" in argv and argv[argv.index("--cap-drop") + 1] == "ALL"
        assert "--security-opt" in argv and "no-new-privileges" in argv
        assert "--pids-limit" in argv
        assert "--memory" in argv
        assert "--cpus" in argv
        assert "--user" in argv and argv[argv.index("--user") + 1] == "10001:10001"
        assert "--tmpfs" in argv
        assert ":/opt/run:ro" in joined  # code mounted read-only
        # no-swap: memory == memory-swap
        assert argv[argv.index("--memory-swap") + 1] == argv[argv.index("--memory") + 1]


# ---------------------------------------------------------------------------
# Fail-closed: flag ON but no docker -> never runs on the host
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_run_code_fails_closed(self, monkeypatch):
        monkeypatch.setattr(config, "SANDBOX_USE_CONTAINER", True)
        monkeypatch.setattr(container_runner, "_cli_path", lambda: None)
        r = code_runner.run_code("print('should not run on host')", language="python", timeout=5)
        assert r["stdout"] == ""
        assert "unavailable" in r["stderr"].lower()

    def test_grading_fails_closed(self, monkeypatch):
        monkeypatch.setattr(config, "SANDBOX_USE_CONTAINER", True)
        monkeypatch.setattr(container_runner, "_cli_path", lambda: None)
        tcs = [{"description": "add", "input": [2, 3], "expected_output": 5, "weight": 1}]
        g = code_runner.run_test_cases("def add(a, b):\n    return a + b", "Python", "add", tcs)
        # No execution-based credit: tests can't pass and correctness is 0. (The
        # quality score is pure static analysis of the source — no code ran — so
        # it may be non-zero; that does not indicate host execution.)
        assert g["tests_passed"] == 0
        assert g["correctness_score"] == 0
        assert "unavailable" in g["results"][0]["error"].lower()


# ---------------------------------------------------------------------------
# Timeout: container is killed by name so untrusted code can't outlive the run
# ---------------------------------------------------------------------------


class TestTimeoutKill:
    def test_timeout_kills_container(self, monkeypatch, fake_docker):
        monkeypatch.setattr(config, "SANDBOX_USE_CONTAINER", True)
        rec = _RunRecorder(raise_timeout=True)
        monkeypatch.setattr(container_runner.subprocess, "run", rec)

        r = code_runner.run_code("while True: pass", language="python", timeout=3)
        assert r["timed_out"] is True

        # First call = docker run (raised timeout); a follow-up docker kill fired.
        kill_calls = [c for c in rec.calls if c[0][:2] == ["docker", "kill"]]
        assert len(kill_calls) == 1
        # kill targets the exact container name from the run argv.
        run_argv = rec.calls[0][0]
        name = run_argv[run_argv.index("--name") + 1]
        assert kill_calls[0][0] == ["docker", "kill", name]


# ---------------------------------------------------------------------------
# build_argv pure-function behaviour
# ---------------------------------------------------------------------------


class TestBuildArgv:
    def test_network_passthrough(self):
        argv = container_runner.build_argv("/d", "h.py", ["/opt/run/code.py"], "my-egress-net", "n")
        assert argv[argv.index("--network") + 1] == "my-egress-net"

    def test_image_and_command_tail(self, monkeypatch):
        monkeypatch.setattr(config, "SANDBOX_CONTAINER_IMAGE", "analytiq-sandbox:pinned")
        argv = container_runner.build_argv("/d", "h.py", ["A", "B"], "none", "n")
        assert argv[-5:] == ["analytiq-sandbox:pinned", "python", "/opt/run/h.py", "A", "B"]

    def test_runtime_flag_absent_by_default(self, monkeypatch):
        monkeypatch.setattr(config, "SANDBOX_CONTAINER_RUNTIME", "")
        argv = container_runner.build_argv("/d", "h.py", [], "none", "n")
        assert "--runtime" not in argv

    def test_gvisor_runtime_when_set(self, monkeypatch):
        monkeypatch.setattr(config, "SANDBOX_CONTAINER_RUNTIME", "runsc")
        argv = container_runner.build_argv("/d", "h.py", [], "none", "n")
        assert "--runtime" in argv and argv[argv.index("--runtime") + 1] == "runsc"

    def test_name_used_for_cleanup(self):
        argv = container_runner.build_argv("/d", "h.py", [], "none", "aq-sbx-abc")
        assert argv[argv.index("--name") + 1] == "aq-sbx-abc"


# ---------------------------------------------------------------------------
# _write_inputs: perms + traversal guard
# ---------------------------------------------------------------------------


class TestWriteInputs:
    def test_writes_world_readable(self, tmp_path):
        import os

        d = str(tmp_path)
        container_runner._write_inputs(d, {"harness.py": "x = 1", "code.py": "y = 2"})
        assert (os.stat(d).st_mode & 0o755) == 0o755
        for name in ("harness.py", "code.py"):
            p = tmp_path / name
            assert p.read_text()  # written
            assert (os.stat(p).st_mode & 0o644) == 0o644

    def test_rejects_path_traversal(self, tmp_path):
        with pytest.raises(ValueError):
            container_runner._write_inputs(str(tmp_path), {"../evil.py": "boom"})
        with pytest.raises(ValueError):
            container_runner._write_inputs(str(tmp_path), {"sub/dir.py": "boom"})
