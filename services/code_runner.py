"""
Sandboxed multi-language code executor for exercise grading.

Grading is purely output-based: student code is run against pre-generated
test cases; the actual return value (or printed output) is compared to the
expected output.  There is NO string-similarity or Levenshtein comparison.

Supported languages
───────────────────
Python     subprocess + RLIMIT_FSIZE/AS/NPROC (Linux) + import block
R          Rscript subprocess, timeout enforced
JavaScript Node.js subprocess, --disallow-code-generation-from-strings
SQL        SQLite in-process (inherently sandboxed, no subprocess needed)
Java       javac + java subprocess, timeout enforced
Others     runtime_missing error returned to caller

Grading schema (0-100)
──────────────────────
Correctness  0-80   (tests_passed / tests_total) * 80, weighted
Quality      0-20   10 runs-cleanly + 5 no-hardcode + 5 basic-style
Total        0-100

Security model
──────────────
- All non-SQL code runs in a child subprocess (process isolation).
- Per-test timeout via subprocess.run(timeout=...).
- Python: dangerous imports blocked + RLIMIT_* on Linux + read-only open().
- JavaScript: --disallow-code-generation-from-strings flag.
- SQL: sqlite3 in-process + SIGALRM timeout on Unix.
- R / Java: timeout only.

Execution backend (SANDBOX_USE_CONTAINER)
─────────────────────────────────────────
The Python paths (grading + live "Run") can execute inside a locked-down,
ephemeral container instead of a host subprocess — kernel-enforced isolation
(no network, read-only rootfs, cgroup memory/cpu/pid caps, dropped caps,
non-root) in place of the in-process import/open shims, which are bypassable
(os.system, os.open, ctypes …). Gated behind config.SANDBOX_USE_CONTAINER
(default off); see services/container_runner.py + docs/SANDBOX_CONTAINER.md.
The container backend currently covers Python; JS/R/Java grading still uses the
host subprocess (the sandbox image ships only a Python runtime).
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Any

import config
from services import container_runner

logger = logging.getLogger(__name__)

MAX_CODE_BYTES = 50_000


# ---------------------------------------------------------------------------
# Sandbox environment isolation
# ---------------------------------------------------------------------------
# Student code runs in a child process of the web/Celery worker. Without an
# explicit env, that child inherits the parent's entire environment —
# DATABASE_URL, JWT_SECRET_KEY/SECRET_KEY, GEMINI_API_KEY, SUPABASE_KEY,
# RESEND_API_KEY, etc. — which untrusted code could read via os.environ and
# exfiltrate. We pass an allowlisted, secret-free environment instead and run
# from a neutral working directory so relative paths cannot reach app source.
#
# NOTE: this closes the secret-exposure vector for the host backend. True
# isolation (separate locked-down container / microVM, network namespace,
# seccomp, non-priv uid) is now available behind config.SANDBOX_USE_CONTAINER
# (services/container_runner.py); this env allowlist still applies to the host
# backend and to non-Python languages, which the container backend does not yet
# cover.


def _sandbox_env() -> dict:
    """Return a minimal, secret-free environment for student subprocesses."""
    allow = (
        "PATH",
        "HOME",  # needed for interpreter/user-site & library config discovery
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        "TEMP",
        "TMP",
        "SYSTEMROOT",
        "VIRTUAL_ENV",
        "PYTHONPATH",
        "JAVA_HOME",
    )
    env = {k: os.environ[k] for k in allow if k in os.environ}
    env.setdefault("PATH", "/usr/bin:/bin")
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


# Computed once at import — the relevant vars are stable for the process life.
_SANDBOX_ENV = _sandbox_env()
_SANDBOX_CWD = tempfile.gettempdir()

BLOCKED_PY_MODULES: frozenset = frozenset(
    {
        "subprocess",
        "socket",
        "ssl",
        "shutil",
        "multiprocessing",
        "threading",
        "concurrent",
        "asyncio",
        "_thread",
        "ctypes",
        "signal",
        "mmap",
        "resource",
        "pty",
        "termios",
        "fcntl",
    }
)

# For the live "run" sandbox, network is intentionally allowed so that
# pd.read_csv(url), requests.get(url), etc. work like in a Colab cell.
# socket and ssl are removed; everything else stays blocked.
_RUN_BLOCKED_PY_MODULES: frozenset = BLOCKED_PY_MODULES - {"socket", "ssl"}


# ---------------------------------------------------------------------------
# Language normalisation
# ---------------------------------------------------------------------------


def _normalise_language(lang: str) -> str:
    lang = (lang or "python").lower().strip()
    return {
        "py": "python",
        "python3": "python",
        "js": "javascript",
        "node": "javascript",
        "nodejs": "javascript",
        "ts": "javascript",
        "r": "r",
        "sql": "sql",
        "sqlite": "sql",
        "mysql": "sql",
        "postgresql": "sql",
        "java": "java",
    }.get(lang, lang)


# ---------------------------------------------------------------------------
# Python harness (written to a temp .py file, run by child subprocess)
# ---------------------------------------------------------------------------

_PY_HARNESS = r"""
import sys, json, builtins, io

# Resource limits — Linux only, silently skipped elsewhere.
# 512 MB virtual memory ceiling (pandas + numpy need headroom beyond the old 256 MB).
try:
    import resource as _res
    _MB = 1024 * 1024
    _res.setrlimit(_res.RLIMIT_FSIZE, (0, 0))
    _res.setrlimit(_res.RLIMIT_AS,    (512 * _MB, 512 * _MB))
    _res.setrlimit(_res.RLIMIT_NPROC, (0, 0))
except Exception:
    pass

# Block dangerous imports
_BLOCKED = {blocked_set}

class _BlockImporter:
    def find_module(self, name, path=None):
        return self if name.split(".")[0] in _BLOCKED else None
    def load_module(self, name):
        raise ImportError(f"Import of {{name!r}} is not permitted in exercises.")

sys.meta_path.insert(0, _BlockImporter())

# Restrict open() to read-only
_ro = builtins.open
def _safe_open(file, mode="r", *args, **kwargs):
    if any(c in mode for c in "wax"):
        raise PermissionError("File writing is not allowed in exercises.")
    return _ro(file, mode, *args, **kwargs)
builtins.open = _safe_open

# Parse CLI args: argv[1]=JSON input, argv[2]=function name, argv[3]=path to student code file
_params    = json.loads(sys.argv[1])
_fn_name   = sys.argv[2]
_code_path = sys.argv[3]
_globs     = {{"__builtins__": builtins, "__name__": "__student__"}}

# Read student code from the dedicated temp file
try:
    _student_src = _ro(_code_path, encoding="utf-8").read()
except Exception as e:
    print(json.dumps({{"error": "compile_error", "message": f"Could not read student code: {{e}}"}})); sys.exit(0)

# ── Capture ALL stdout produced during exec (top-level prints = script output) ──
_exec_buf = io.StringIO()
sys.stdout = _exec_buf
try:
    exec(compile(_student_src, "<student>", "exec"), _globs)
except SyntaxError as e:
    sys.stdout = sys.__stdout__
    print(json.dumps({{"error": "compile_error", "message": f"SyntaxError: {{e}}"}})); sys.exit(0)
except Exception as e:
    sys.stdout = sys.__stdout__
    print(json.dumps({{"error": "compile_error", "message": str(e)}})); sys.exit(0)
finally:
    sys.stdout = sys.__stdout__

_exec_printed = _exec_buf.getvalue().strip()

# ── Locate the target function ───────────────────────────────────────────────
_func = _globs.get(_fn_name)
if _func is None:
    _candidates = [v for k, v in _globs.items()
                   if callable(v) and not k.startswith("_") and k not in dir(builtins)]
    _func = _candidates[0] if _candidates else None

# ── SCRIPT MODE: no function defined — use top-level printed output as the answer ──
# This handles exercises where students write top-level code (like a Colab cell)
# instead of a named function.  The output is compared to expected_output exactly
# as it would be for a function's printed output.
if _func is None:
    print(json.dumps({{
        "result": None,
        "printed": _exec_printed or None,
        "error": None,
    }}))
    sys.exit(0)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _serialise(v):
    # Convert non-JSON-serialisable values (DataFrames, arrays) to plain Python
    try:
        json.dumps(v)
        return v
    except (TypeError, ValueError):
        pass
    _pd = sys.modules.get("pandas")
    _np = sys.modules.get("numpy")
    if _pd is not None:
        if isinstance(v, _pd.DataFrame):
            return v.where(_pd.notnull(v), None).to_dict(orient="list")
        if isinstance(v, _pd.Series):
            return v.tolist()
    if _np is not None and hasattr(v, "tolist"):
        return v.tolist()
    return repr(v)

def _call_func(func, params):
    # Try multiple calling conventions so students can structure code freely:
    #   None params   -> func()  then func(None)
    #   dict params   -> func(**params)  then func(params)  then func(DataFrame(params))
    #   list params   -> func(*params)   then func(params)  then func(DataFrame(params))
    #   scalar        -> func(params)
    _pd = sys.modules.get("pandas")

    if params is None:
        # Zero-argument functions (hello_world, etc.)
        try:
            return func(), None
        except TypeError:
            pass
        except Exception as e:
            return None, str(e)
        # One-argument function that accepts None
        try:
            return func(None), None
        except Exception as e:
            return None, str(e)

    if isinstance(params, dict):
        # Named parameters: func(a=1, b=2)
        try:
            return func(**params), None
        except TypeError:
            pass
        except Exception as e:
            return None, str(e)
        # Single dict argument: func(dict_value)
        try:
            return func(params), None
        except TypeError:
            pass
        except Exception as e:
            return None, str(e)
        # Pandas DataFrame: func(pd.DataFrame(dict_value))
        if _pd is not None:
            try:
                return func(_pd.DataFrame(params)), None
            except Exception as e:
                return None, str(e)
        return None, "dict input could not be matched to function signature"

    if isinstance(params, list):
        # Positional args: func(1, 2, 3)
        try:
            return func(*params), None
        except TypeError:
            pass
        except Exception as e:
            return None, str(e)
        # Single list argument: func([1, 2, 3])
        try:
            return func(params), None
        except TypeError:
            pass
        except Exception as e:
            return None, str(e)
        # Pandas DataFrame from list-of-records
        if _pd is not None:
            try:
                return func(_pd.DataFrame(params)), None
            except Exception as e:
                return None, str(e)
        return None, "list input could not be matched to function signature"

    # Scalar (int, float, str, bool)
    try:
        return func(params), None
    except Exception as e:
        return None, str(e)

# ── FUNCTION MODE ─────────────────────────────────────────────────────────────
_buf = io.StringIO()
sys.stdout = _buf
_result = _err = None
try:
    _result, _err = _call_func(_func, _params)
except Exception as e:
    _err = str(e)
finally:
    sys.stdout = sys.__stdout__

# Prefer output captured during the function call; fall back to exec-level output
_fn_printed  = _buf.getvalue().strip()
_printed     = _fn_printed or _exec_printed or None

_result = _serialise(_result)
print(json.dumps({{"result": _result, "printed": _printed or None, "error": _err}}))
"""


# ---------------------------------------------------------------------------
# Python live-run harness (no test cases — just run the code, capture output)
# Network access allowed: socket/ssl not blocked so pd.read_csv(url) works.
# ---------------------------------------------------------------------------

_PY_RUN_HARNESS = r"""
import sys, json, builtins, io, traceback

try:
    import resource as _res
    _MB = 1024 * 1024
    _res.setrlimit(_res.RLIMIT_FSIZE, (0, 0))
    _res.setrlimit(_res.RLIMIT_AS,    (1024 * _MB, 1024 * _MB))
    _res.setrlimit(_res.RLIMIT_NPROC, (0, 0))
except Exception:
    pass

_BLOCKED = {blocked_set}

class _BlockImporter:
    def find_module(self, name, path=None):
        return self if name.split(".")[0] in _BLOCKED else None
    def load_module(self, name):
        raise ImportError(f"Import of {{name!r}} is not permitted.")

sys.meta_path.insert(0, _BlockImporter())

_ro = builtins.open
def _safe_open(file, mode="r", *args, **kwargs):
    if any(c in mode for c in "wax"):
        raise PermissionError("File writing is not allowed.")
    return _ro(file, mode, *args, **kwargs)
builtins.open = _safe_open

_code_path = sys.argv[1]
try:
    _student_src = _ro(_code_path, encoding="utf-8").read()
except Exception as e:
    print(json.dumps({{"stdout": "", "stderr": f"Could not read code: {{e}}"}}))
    sys.exit(0)

_out_buf = io.StringIO()
_err_buf = io.StringIO()
sys.stdout = _out_buf
sys.stderr = _err_buf

_globs = {{"__builtins__": builtins, "__name__": "__main__"}}
try:
    exec(compile(_student_src, "<cell>", "exec"), _globs)
except SystemExit:
    pass
except Exception:
    sys.stderr.write(traceback.format_exc())
finally:
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

print(json.dumps({{"stdout": _out_buf.getvalue(), "stderr": _err_buf.getvalue()}}))
"""


# ---------------------------------------------------------------------------
# Execution backend dispatch (host subprocess  ↔  isolated container)
# ---------------------------------------------------------------------------
# _exec_python_harness runs `python <harness> <pre_args…> <code_path>` and
# returns (stdout, stderr). It is the single seam between the two backends:
#
#   host      (default)                 : child subprocess of the worker, guarded
#                                         by the in-process import/open shims +
#                                         RLIMIT_* baked into the harness.
#   container (SANDBOX_USE_CONTAINER)   : the same harness + code, bind-mounted
#                                         read-only into a locked-down container
#                                         (see services/container_runner.py).
#
# Both raise subprocess.TimeoutExpired on timeout; the container backend also
# raises container_runner.ContainerUnavailable so callers can FAIL CLOSED rather
# than fall back to the host and give a false sense of isolation.


def _exec_python_harness(
    harness: str, student_code: str, pre_args: list, timeout: int, network: str
) -> tuple:
    """Run the Python harness against student_code; return (stdout, stderr)."""
    if config.SANDBOX_USE_CONTAINER:
        proc = container_runner.run_in_container(
            files={"harness.py": harness, "code.py": student_code},
            entry="harness.py",
            args=[*pre_args, f"{container_runner.MOUNT}/code.py"],
            timeout=timeout,
            network=network,
        )
        return proc.stdout, proc.stderr

    # Host backend — unchanged behaviour: secret-free env, neutral cwd, RLIMITs.
    harness_path = None
    code_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="aq_py_"
        ) as f:
            f.write(harness)
            harness_path = f.name
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="aq_src_", encoding="utf-8"
        ) as cf:
            cf.write(student_code)
            code_path = cf.name

        proc = subprocess.run(
            [sys.executable, harness_path, *pre_args, code_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=_SANDBOX_ENV,
            cwd=_SANDBOX_CWD,
        )
        return proc.stdout, proc.stderr
    finally:
        if harness_path:
            _rm(harness_path)
        if code_path:
            _rm(code_path)


def _run_python_free(student_code: str, timeout: int) -> dict:
    """Execute code in the live sandbox; return stdout + stderr."""
    harness = _PY_RUN_HARNESS.format(
        blocked_set=repr(set(_RUN_BLOCKED_PY_MODULES)),
    )
    try:
        stdout, stderr = _exec_python_harness(
            harness, student_code, [], timeout, config.SANDBOX_CONTAINER_NETWORK_RUN
        )
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timed out after {timeout}s.", "timed_out": True}
    except container_runner.ContainerUnavailable as exc:
        logger.error("Code sandbox container unavailable (run): %s", exc)
        return {
            "stdout": "",
            "stderr": "The code sandbox is temporarily unavailable. Please try again later.",
            "timed_out": False,
        }

    raw = (stdout or "").strip()
    if not raw:
        stderr = (stderr or "")[:2000]
        return {"stdout": "", "stderr": stderr or "No output.", "timed_out": False}
    try:
        data = json.loads(raw)
        data["timed_out"] = False
        return data
    except json.JSONDecodeError:
        return {"stdout": raw[:5000], "stderr": "", "timed_out": False}


def run_code(student_code: str, language: str = "python", timeout: int = 15) -> dict:
    """
    Execute student code and return stdout/stderr — no grading, no test cases.
    This powers the live Colab-style code cell in the playground.
    Network access is allowed so pd.read_csv(url) and similar work.

    Returns
    -------
    {
      stdout    : str   — everything printed to stdout
      stderr    : str   — tracebacks / error messages
      timed_out : bool
    }
    """
    lang = _normalise_language(language)
    stripped = (student_code or "").strip()
    if not stripped:
        return {"stdout": "", "stderr": "No code to run.", "timed_out": False}
    if len(student_code.encode()) > MAX_CODE_BYTES:
        return {
            "stdout": "",
            "stderr": f"Code exceeds the {MAX_CODE_BYTES // 1000} KB limit.",
            "timed_out": False,
        }
    if lang == "python":
        return _run_python_free(student_code, timeout)
    return {
        "stdout": "",
        "stderr": f"Live execution for '{language}' is not yet supported.",
        "timed_out": False,
    }


def _run_python(student_code: str, fn_name: str, tc: dict, timeout: int) -> dict:
    # The harness no longer embeds student code via repr() — it reads it from a
    # dedicated temp file (last argv).  This avoids repr/format edge cases that
    # corrupted code containing backslashes, Unicode characters (e.g. smart
    # quotes introduced by browser autocorrect in LTI iframes), or other chars
    # that survive .strip() but are not valid Python syntax.
    harness = _PY_HARNESS.format(
        blocked_set=repr(set(BLOCKED_PY_MODULES)),
    )
    # Grading is deterministic and network-independent → hard network block in
    # container mode (SANDBOX_CONTAINER_NETWORK_TEST defaults to "none").
    pre_args = [json.dumps(tc.get("input", {})), fn_name or ""]
    try:
        stdout, stderr = _exec_python_harness(
            harness, student_code, pre_args, timeout, config.SANDBOX_CONTAINER_NETWORK_TEST
        )
    except subprocess.TimeoutExpired:
        return {"timed_out": True}
    except container_runner.ContainerUnavailable as exc:
        logger.error("Code sandbox container unavailable (grading): %s", exc)
        return {"error": "runtime_missing", "message": "The code sandbox is unavailable."}
    return _parse_proc(stdout, stderr)


# ---------------------------------------------------------------------------
# JavaScript (Node.js) harness
# ---------------------------------------------------------------------------

_JS_HARNESS = """'use strict';
{student_code}

const _params  = JSON.parse(process.argv[2]);
const _fn_name = process.argv[3];
let _func;
try {{ _func = eval(_fn_name); }} catch(_) {{}}
if (typeof _func !== 'function') {{
    process.stdout.write(JSON.stringify({{error:'no_function',message:`Function "${{_fn_name}}" not found.`}}));
    process.exit(0);
}}
let _result = null, _err = null;
try {{
    if (Array.isArray(_params))         _result = _func(..._params);
    else if (typeof _params==='object') _result = _func(...Object.values(_params));
    else                                _result = _func(_params);
}} catch(e) {{ _err = e.message; }}
process.stdout.write(JSON.stringify({{result: _result, error: _err}}));
"""


def _run_javascript(student_code: str, fn_name: str, tc: dict, timeout: int) -> dict:
    import subprocess
    import shutil

    if not shutil.which("node"):
        return {"error": "runtime_missing", "message": "Node.js is not installed on this server."}
    harness = _JS_HARNESS.format(student_code=student_code)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, prefix="aq_js_") as f:
        f.write(harness)
        path = f.name
    try:
        proc = subprocess.run(
            [
                "node",
                "--disallow-code-generation-from-strings",
                path,
                json.dumps(tc.get("input", {})),
                fn_name,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=_SANDBOX_ENV,
            cwd=_SANDBOX_CWD,
        )
        return _parse_proc(proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired:
        return {"timed_out": True}
    finally:
        _rm(path)


# ---------------------------------------------------------------------------
# R harness
# ---------------------------------------------------------------------------

_R_HARNESS = """suppressMessages(suppressWarnings({{
{student_code}
}}))
.params  <- jsonlite::fromJSON(commandArgs(trailingOnly=TRUE)[1], simplifyVector=FALSE)
.fn_name <- commandArgs(trailingOnly=TRUE)[2]
if (!exists(.fn_name)) {{
    cat(jsonlite::toJSON(list(error="no_function",
        message=paste0("Function '", .fn_name, "' not found.")), auto_unbox=TRUE))
    quit(status=0)
}}
.fn <- get(.fn_name)
.result <- tryCatch({{
    if (is.list(.params)) do.call(.fn, .params)
    else .fn(.params)
}}, error=function(e) list(.err=conditionMessage(e)))
if (is.list(.result) && !is.null(.result$.err)) {{
    cat(jsonlite::toJSON(list(error=.result$.err), auto_unbox=TRUE))
}} else {{
    cat(jsonlite::toJSON(list(result=.result), auto_unbox=TRUE))
}}
"""


def _run_r(student_code: str, fn_name: str, tc: dict, timeout: int) -> dict:
    import subprocess
    import shutil

    if not shutil.which("Rscript"):
        return {"error": "runtime_missing", "message": "Rscript is not installed on this server."}
    harness = _R_HARNESS.format(student_code=student_code)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, prefix="aq_r_") as f:
        f.write(harness)
        path = f.name
    try:
        proc = subprocess.run(
            ["Rscript", path, json.dumps(tc.get("input", {})), fn_name],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=_SANDBOX_ENV,
            cwd=_SANDBOX_CWD,
        )
        return _parse_proc(proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired:
        return {"timed_out": True}
    finally:
        _rm(path)


# ---------------------------------------------------------------------------
# SQL harness — SQLite in-process
# ---------------------------------------------------------------------------


def _run_sql(student_code: str, fn_name: str, tc: dict, timeout: int) -> dict:
    """
    tc["input"] = {"setup": "<DDL + INSERT statements>"}
    student_code = SELECT query the student wrote
    tc["expected_output"] = list of rows (list of lists)
    """
    import sqlite3

    setup_sql = ""
    if isinstance(tc.get("input"), dict):
        setup_sql = tc["input"].get("setup", "")

    # SIGALRM timeout on Unix
    import signal as _sig

    class _Timeout(Exception):
        pass

    def _handler(s, f):
        raise _Timeout()

    result = error = None
    try:
        if hasattr(_sig, "SIGALRM"):
            _sig.signal(_sig.SIGALRM, _handler)
            _sig.alarm(timeout)
        con = sqlite3.connect(":memory:")
        try:
            if setup_sql:
                con.executescript(setup_sql)
            cur = con.execute(student_code)
            result = [list(r) for r in cur.fetchall()]
        finally:
            con.close()
            if hasattr(_sig, "SIGALRM"):
                _sig.alarm(0)
    except _Timeout:
        return {"timed_out": True}
    except sqlite3.Error as exc:
        error = str(exc)
    except Exception as exc:
        error = str(exc)

    return {"result": result, "printed": None, "error": error}


# ---------------------------------------------------------------------------
# Java harness
# ---------------------------------------------------------------------------

_JAVA_HARNESS = """{student_code}

public class _Harness {{
    public static void main(String[] args) throws Exception {{
        // Pass raw JSON input as first arg; function receives it as String.
        // Student's class must be named Solution with a public static method.
        java.lang.reflect.Method m = Solution.class.getMethod("{fn_name}", String.class);
        Object result = m.invoke(null, args[0]);
        System.out.print("{\\"result\\":" + result + "}");
    }}
}}
"""


def _run_java(student_code: str, fn_name: str, tc: dict, timeout: int) -> dict:
    import subprocess
    import shutil

    if not shutil.which("javac") or not shutil.which("java"):
        return {"error": "runtime_missing", "message": "Java is not installed on this server."}
    with tempfile.TemporaryDirectory(prefix="aq_java_") as tmpdir:
        src = os.path.join(tmpdir, "_Harness.java")
        with open(src, "w") as f:
            f.write(_JAVA_HARNESS.format(student_code=student_code, fn_name=fn_name))
        cp = subprocess.run(
            ["javac", src],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=tmpdir,
            env=_SANDBOX_ENV,
        )
        if cp.returncode != 0:
            return {"result": None, "printed": None, "error": f"Compile error: {cp.stderr[:500]}"}
        try:
            rp = subprocess.run(
                ["java", "-cp", tmpdir, "_Harness", json.dumps(tc.get("input", {}))],
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                cwd=tmpdir,
                env=_SANDBOX_ENV,
            )
            return _parse_proc(rp.stdout, rp.stderr)
        except subprocess.TimeoutExpired:
            return {"timed_out": True}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_test_cases(
    student_code: str,
    language: str,
    function_name: str,
    test_cases: list,
    timeout: int = 5,
) -> dict:
    """
    Run student_code against every test case.  Grading is output-based:
    the actual return value (or printed output) is compared to expected_output.
    No string similarity, no Levenshtein, no time bonus.

    Parameters
    ----------
    student_code  : raw source code submitted by the student
    language      : "Python" | "R" | "JavaScript" | "SQL" | "Java" | …
    function_name : name of the function/method to call per test case
    test_cases    : list of {description, input, expected_output, weight}
    timeout       : per-test time limit in seconds (default 5)

    Returns
    -------
    {
      correctness_score : int   0-80
      quality_score     : int   0-20
      total_score       : int   0-100
      tests_passed      : int
      tests_total       : int
      language          : str
      results           : list  per-test detail
      quality_details   : dict
    }
    """
    lang = _normalise_language(language)

    stripped = (student_code or "").strip()
    if not stripped:
        return _zero(lang, "Empty submission — no code was provided.")
    if len(student_code.encode()) > MAX_CODE_BYTES:
        return _zero(lang, f"Submission exceeds the {MAX_CODE_BYTES // 1000} KB limit.")
    if not test_cases:
        return _zero(lang, "No test cases found for this exercise.")

    _dispatch = {
        "python": _run_python,
        "javascript": _run_javascript,
        "r": _run_r,
        "sql": _run_sql,
        "java": _run_java,
    }
    runner = _dispatch.get(lang)
    if runner is None:
        return _zero(lang, f"Language '{language}' is not yet supported for automatic grading.")

    results: list = []
    total_weight: float = sum(tc.get("weight", 1) for tc in test_cases)
    earned_weight: float = 0.0
    any_ran: bool = False
    compile_error = None

    for tc in test_cases:
        expected = tc.get("expected_output")
        weight = tc.get("weight", 1)
        description = tc.get("description", "")

        try:
            raw = runner(student_code, function_name, tc, timeout)
        except Exception as exc:
            logger.exception("Unexpected runner error for test case %r", tc)
            results.append(
                {
                    "description": description,
                    "passed": False,
                    "error": f"Internal error: {exc}",
                    "weight": weight,
                }
            )
            continue

        # Timed out
        if raw.get("timed_out"):
            results.append(
                {
                    "description": description,
                    "passed": False,
                    "error": f"Timed out after {timeout} s.",
                    "weight": weight,
                }
            )
            continue

        # Runtime missing
        if raw.get("error") == "runtime_missing":
            results.append(
                {
                    "description": description,
                    "passed": False,
                    "error": raw.get("message", "Runtime unavailable."),
                    "weight": weight,
                }
            )
            continue

        # Compile / function-not-found errors
        if raw.get("error") in ("compile_error", "no_function"):
            if raw.get("error") == "compile_error":
                compile_error = raw.get("message")
            results.append(
                {
                    "description": description,
                    "passed": False,
                    "error": raw.get("message", ""),
                    "weight": weight,
                }
            )
            continue

        # Other runtime error
        if raw.get("error"):
            results.append(
                {
                    "description": description,
                    "passed": False,
                    "error": f"Runtime error: {raw['error']}",
                    "weight": weight,
                }
            )
            continue

        # --- Output comparison (logic-based, NOT string similarity) ----------
        any_ran = True
        actual = raw.get("result")
        printed = raw.get("printed")

        passed = _match(actual, expected)

        # Fallback: student printed instead of returning
        if not passed and printed:
            try:
                passed = _match(json.loads(printed), expected)
            except (json.JSONDecodeError, TypeError):
                passed = _match(str(printed).strip(), str(expected).strip())

        if passed:
            earned_weight += weight

        results.append(
            {
                "description": description,
                "passed": passed,
                "actual": actual,
                "printed": printed,
                "expected": expected,
                "weight": weight,
            }
        )

    correctness = round((earned_weight / total_weight) * 80) if total_weight else 0
    tests_passed = sum(1 for r in results if r.get("passed"))

    quality = _quality(student_code, lang, any_ran, compile_error)
    total = min(100, correctness + quality["total"])

    return {
        "correctness_score": correctness,
        "quality_score": quality["total"],
        "total_score": total,
        "tests_passed": tests_passed,
        "tests_total": len(results),
        "language": lang,
        "results": results,
        "quality_details": quality,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_proc(stdout: str, stderr: str) -> dict:
    raw = (stdout or "").strip()
    if not raw:
        return {
            "result": None,
            "printed": None,
            "error": f"No output from runner. stderr: {(stderr or '')[:300]}",
        }
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "result": None,
            "printed": None,
            "error": f"Could not parse runner output: {exc}. raw={raw[:200]}",
        }


def _match(actual: Any, expected: Any) -> bool:
    """
    Output-based comparison — no string similarity, no partial credit.
    Returns True only when actual matches expected within defined tolerances.

    Extra cases handled beyond strict equality:
    - Numeric tolerance for floats
    - Tuple serialised as list: [4, 1] matches "(4, 1)"
    - repr(actual) matches str(expected) — covers shapes, named tuples, etc.
    - str(actual) matches str(expected) — last-resort string normalisation
    """
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual == expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if expected == 0:
            return abs(actual - expected) < 1e-9
        return abs(actual - expected) / abs(expected) < 1e-9
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.strip() == actual.strip()
    if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        return len(expected) == len(actual) and all(_match(a, e) for a, e in zip(actual, expected))
    # Tuple serialised as JSON list vs string expected: [4, 1] vs "(4, 1)"
    if isinstance(actual, list) and isinstance(expected, str):
        if str(tuple(actual)).strip() == expected.strip():
            return True
    # repr comparison: covers DataFrames summarised as strings, named tuples, etc.
    if isinstance(expected, str):
        if repr(actual).strip() == expected.strip():
            return True
        if str(actual).strip() == expected.strip():
            return True
    return actual == expected


def _strip_comments(code: str, lang: str) -> str:
    """Strip inline comments line-by-line.

    Simplified: does not handle comment markers inside string literals,
    which is acceptable for heuristic quality scoring.
    """
    markers = {
        "python": ("#",),
        "r": ("#",),
        "javascript": ("//",),
        "java": ("//",),
        "sql": ("--",),
    }
    comment_chars = markers.get(lang, ("#",))
    stripped = []
    for line in code.splitlines():
        for marker in comment_chars:
            idx = line.find(marker)
            if idx != -1:
                line = line[:idx]
        stripped.append(line)
    return "\n".join(stripped)


def _quality(code: str, lang: str, any_ran: bool, compile_error) -> dict:
    """Quality score 0-20: runs(10) + no-hardcode(5) + style(5)."""
    runs = 10 if (any_ran and compile_error is None) else 0

    code_no_comments = _strip_comments(code, lang)

    # Hardcode check: all substantive lines are bare literal outputs.
    # Uses comment-stripped lines so inline comments don't mask hardcoded returns.
    lines = [
        ln.strip()
        for ln in code_no_comments.splitlines()
        if ln.strip() and not re.match(r"^\s*(#|//|--|/\*|\*)", ln)
    ]
    code_lines = [
        ln
        for ln in lines
        if not re.match(
            r"^(import|from|using|require|library|package|def\s|function\s|public\s)", ln
        )
    ]
    _literal_pat = {
        "python": r"^\s*(return|print)\s*\(?\s*[\d.\"\'\[\]{}True False None,\s]+\s*\)?$",
        "javascript": r"^\s*(return|console\.log)\s*\(?\s*[\d.\"\'\[\]{}true false null,\s]+\s*\)?;?$",
        "r": r"^\s*(return\s*\(?\s*[\d.\"\',\s]+\s*\)?|cat\s*\([\d.\"\',\s]+\))$",
        "java": r"^\s*(return|System\.out\.print(ln)?)\s*\(?\s*[\d.\"\',\s]+\s*\)?;?$",
    }
    pat = _literal_pat.get(lang)
    hardcoded = bool(
        pat and code_lines and all(re.match(pat, ln, re.IGNORECASE) for ln in code_lines)
    )
    no_hc = 0 if hardcoded else 5

    # Style: at least one variable assignment with a meaningful name (>1 char).
    # Uses comment-stripped code so commented-out assignments don't award points.
    _assign_pat = {
        "python": r"\b[a-zA-Z_]{2,}\w*\s*=(?!=)",
        "javascript": r"\b(let|const|var)\s+[a-zA-Z_]{2,}",
        "r": r"\b[a-zA-Z_.]{2,}\w*\s*(<-|=)(?!=)",
        "java": r"\b[a-zA-Z_]{2,}\w*\s+[a-zA-Z_]\w*\s*=",
        "sql": None,
    }
    ap = _assign_pat.get(lang, r"\b[a-zA-Z_]{2,}\w*\s*=(?!=)")
    style = 5 if (ap is None or re.search(ap, code_no_comments)) else 0

    return {
        "total": runs + no_hc + style,
        "runs_cleanly": runs,
        "no_hardcoded_answers": no_hc,
        "basic_style": style,
    }


def _zero(lang: str, reason: str) -> dict:
    return {
        "correctness_score": 0,
        "quality_score": 0,
        "total_score": 0,
        "tests_passed": 0,
        "tests_total": 0,
        "language": lang,
        "results": [{"description": reason, "passed": False, "error": reason, "weight": 0}],
        "quality_details": {
            "total": 0,
            "runs_cleanly": 0,
            "no_hardcoded_answers": 0,
            "basic_style": 0,
        },
    }


def _rm(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
