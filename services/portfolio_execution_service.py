"""
Portfolio Execution Service — freeform (non-graded) code execution for personal projects.

Wraps the existing code_runner.run_code() in "run" mode so personal project code
can be executed in the same sandboxed environment as graded exercises, but without
test cases — just run and return stdout/stderr.
"""

import logging

from services.code_runner import run_code

logger = logging.getLogger(__name__)

# Execution timeout for personal projects (seconds).
PROJECT_EXECUTION_TIMEOUT = 30


def execute_project_code(code: str, language: str = "python") -> dict:
    """
    Execute student's personal project code in the sandbox.

    Same isolation as grading (subprocess, memory limits, import controls)
    but no test cases — just run and return output.

    Returns:
        {
            "stdout": "...",
            "stderr": "...",
            "timed_out": False,
            "execution_time_ms": 245,
        }
    """
    if not code or not code.strip():
        return {"stdout": "", "stderr": "No code to run.", "timed_out": False}

    result = run_code(code, language=language, timeout=PROJECT_EXECUTION_TIMEOUT)
    return {
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "timed_out": result.get("timed_out", False),
    }
