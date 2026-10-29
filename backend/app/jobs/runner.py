"""Safe subprocess execution of tool binaries (HF-SEC-010, ADR-004/010).

- Argument arrays only; stdin closed; controlled working directory.
- Environment allowlist (no inherited credentials).
- Output written to files under the job run dir, size-capped.
- Timeout and cooperative cancellation: poll a cancel predicate, then kill the
  process group (SIGKILL escalation).
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..core.config import Settings

MAX_OUTPUT_BYTES = 50 * 1024 * 1024  # 50 MB per stream


@dataclass
class ToolRunResult:
    exit_code: int | None
    status: str  # completed | failed | cancelled | timeout
    stdout_path: Path | None
    stderr_path: Path | None
    duration_seconds: float


def _safe_env(settings: Settings) -> dict[str, str]:
    home = settings.data_dir / "home"
    tmp = settings.data_dir / "tmp"
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(home),
        "TMPDIR": str(tmp),
        "LANG": "C.UTF-8",
    }


def _kill_group(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


class ToolRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(
        self,
        args: list[str],
        run_dir: Path,
        timeout_seconds: int | None = None,
        cancel: Callable[[], bool] | None = None,
    ) -> ToolRunResult:
        timeout_seconds = timeout_seconds or self.settings.tool_timeout_seconds
        run_dir.mkdir(parents=True, exist_ok=True)
        (self.settings.data_dir / "home").mkdir(parents=True, exist_ok=True)
        (self.settings.data_dir / "tmp").mkdir(parents=True, exist_ok=True)
        stdout_path = run_dir / "stdout.txt"
        stderr_path = run_dir / "stderr.txt"
        start = time.monotonic()
        kwargs: dict = {
            "stdin": subprocess.DEVNULL,
            "cwd": str(run_dir),
            "env": _safe_env(self.settings),
        }
        if os.name != "nt":
            kwargs["start_new_session"] = True
        else:
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
            try:
                proc = subprocess.Popen(args, stdout=out, stderr=err, **kwargs)
            except FileNotFoundError:
                return ToolRunResult(
                    exit_code=None,
                    status="failed",
                    stdout_path=None,
                    stderr_path=None,
                    duration_seconds=time.monotonic() - start,
                )
            cancelled = False
            while True:
                code = proc.poll()
                if code is not None:
                    break
                if cancel is not None and cancel():
                    _kill_group(proc)
                    cancelled = True
                try:
                    proc.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    if time.monotonic() - start > timeout_seconds:
                        _kill_group(proc)
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                        return ToolRunResult(
                            exit_code=proc.poll(),
                            status="timeout",
                            stdout_path=stdout_path,
                            stderr_path=stderr_path,
                            duration_seconds=time.monotonic() - start,
                        )
                    continue
                if cancelled:
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    return ToolRunResult(
                        exit_code=proc.poll(),
                        status="cancelled",
                        stdout_path=stdout_path,
                        stderr_path=stderr_path,
                        duration_seconds=time.monotonic() - start,
                    )
        if _too_large(stdout_path) or _too_large(stderr_path):
            return ToolRunResult(
                exit_code=proc.poll(),
                status="failed",
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                duration_seconds=time.monotonic() - start,
            )
        return ToolRunResult(
            exit_code=proc.poll(),
            status="completed" if proc.returncode == 0 else "failed",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            duration_seconds=time.monotonic() - start,
        )


def _too_large(path: Path) -> bool:
    try:
        return path.stat().st_size > MAX_OUTPUT_BYTES
    except OSError:
        return False

