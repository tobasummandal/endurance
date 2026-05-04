"""Run user code in a subprocess with resource limits.

Threat model (MVP, document honestly):
  - Code runs in a child process under the API user. We set RLIMIT_AS/CPU/NOFILE,
    a wall-clock timeout, and disable network via env hints (HTTPS_PROXY=, etc).
  - We do NOT run inside a container or namespace here -- production must wrap this
    in a network-namespaced container or a microVM (gVisor / firecracker / sandbox-exec).
  - macOS does not respect RLIMIT_AS reliably; behavior is best-effort there.
  - stdout/stderr are size-capped before being read back.
"""
from __future__ import annotations
import json
import os
import resource
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..config import settings


_TO_JSONABLE = r'''
def _to_jsonable(x, _depth=0):
    if _depth > 6:
        return repr(x)[:200]
    try:
        import numpy as _np
        if isinstance(x, _np.ndarray):
            return {"__np__": True, "shape": list(x.shape), "data": x.tolist()}
        if isinstance(x, (_np.floating, _np.integer, _np.bool_)):
            return x.item()
    except Exception:
        pass
    if isinstance(x, (int, float, bool, str)) or x is None:
        return x
    if isinstance(x, (list, tuple)):
        return [_to_jsonable(v, _depth + 1) for v in x]
    if isinstance(x, dict):
        return {str(k): _to_jsonable(v, _depth + 1) for k, v in x.items()}
    return repr(x)[:200]
'''

_RUNNER_TEMPLATE = r'''
import json, sys, time, traceback

USER_SOURCE = {source!r}
FUNC_NAME = {func!r}
INPUTS_PATH = {inputs_path!r}
OUTPUT_PATH = {output_path!r}

mod_globals = {{"__name__": "__helios_user__"}}
results = []

try:
    compiled = compile(USER_SOURCE, "<user>", "exec")
    eval(compiled, mod_globals)  # noqa: S307 -- intentional sandboxed evaluation
    fn = mod_globals.get(FUNC_NAME)
    if fn is None:
        raise NameError("function " + FUNC_NAME + " not found")
    with open(INPUTS_PATH) as fp:
        inputs = json.load(fp)
    for args in inputs:
        case = {{"output": None, "exception": None, "elapsed_ms": 0.0}}
        t0 = time.perf_counter()
        try:
            out = fn(*args)
            case["elapsed_ms"] = (time.perf_counter() - t0) * 1000.0
            case["output"] = _to_jsonable(out)
        except Exception as e:
            case["elapsed_ms"] = (time.perf_counter() - t0) * 1000.0
            case["exception"] = type(e).__name__ + ": " + str(e)[:200]
        results.append(case)
except Exception as e:
    results = {{"fatal": type(e).__name__ + ": " + str(e)[:400], "trace": traceback.format_exc()[-1000:]}}

with open(OUTPUT_PATH, "w") as fp:
    json.dump(results, fp, default=str)
'''


@dataclass
class SandboxRun:
    cases: list
    fatal: str | None = None
    timeout: bool = False
    stdout: str = ""
    stderr: str = ""


def _set_limits():
    try:
        mem = settings.sandbox_mem_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    except Exception:
        pass
    try:
        cpu = settings.sandbox_timeout_s + 2
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    except Exception:
        pass
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    except Exception:
        pass


def run_function(source: str, func_name: str, inputs: list) -> SandboxRun:
    """Run func_name(*args) for each args in inputs, in an isolated subprocess."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs_path = tmp_path / "inputs.json"
        output_path = tmp_path / "output.json"
        runner_path = tmp_path / "runner.py"

        inputs_path.write_text(json.dumps(inputs))
        runner_src = _TO_JSONABLE + "\n" + _RUNNER_TEMPLATE.format(
            source=source,
            func=func_name,
            inputs_path=str(inputs_path),
            output_path=str(output_path),
        )
        runner_path.write_text(runner_src)

        env = {
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "HTTPS_PROXY": "",
            "HTTP_PROXY": "",
            "NO_PROXY": "*",
        }

        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(runner_path)],
                env=env,
                cwd=tmp,
                capture_output=True,
                timeout=settings.sandbox_timeout_s * max(1, len(inputs)),
                preexec_fn=_set_limits if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired as te:
            return SandboxRun(
                cases=[],
                fatal=f"timeout after {te.timeout}s",
                timeout=True,
                stdout=_cap(te.stdout or b""),
                stderr=_cap(te.stderr or b""),
            )

        stdout = _cap(proc.stdout)
        stderr = _cap(proc.stderr)

        if not output_path.exists():
            return SandboxRun(
                cases=[],
                fatal=f"sandbox produced no output (rc={proc.returncode})",
                stdout=stdout, stderr=stderr,
            )
        try:
            data = json.loads(output_path.read_text())
        except Exception as e:
            return SandboxRun(
                cases=[], fatal=f"failed to parse sandbox output: {e}",
                stdout=stdout, stderr=stderr,
            )

        if isinstance(data, dict) and "fatal" in data:
            return SandboxRun(cases=[], fatal=str(data["fatal"]), stdout=stdout, stderr=stderr)
        if not isinstance(data, list):
            return SandboxRun(cases=[], fatal="sandbox output not a list", stdout=stdout, stderr=stderr)

        return SandboxRun(cases=data, stdout=stdout, stderr=stderr)


def _cap(b) -> str:
    cap = settings.sandbox_stdout_cap_bytes
    if isinstance(b, bytes):
        b = b[:cap]
        try:
            return b.decode("utf-8", errors="replace")
        except Exception:
            return ""
    return b[:cap]
