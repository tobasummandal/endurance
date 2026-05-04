import sys
import pytest

from helios.execution.sandbox import run_function


@pytest.mark.skipif(sys.platform == "win32", reason="posix only")
def test_runs_simple_function():
    src = "def add(a, b):\n    return a + b\n"
    run = run_function(src, "add", [[1, 2], [3, 4]])
    assert run.fatal is None
    assert len(run.cases) == 2
    assert run.cases[0]["output"] == 3
    assert run.cases[1]["output"] == 7


def test_captures_exception():
    src = "def f(x):\n    raise ValueError('boom')\n"
    run = run_function(src, "f", [[1]])
    assert run.fatal is None
    assert run.cases[0]["exception"].startswith("ValueError")
