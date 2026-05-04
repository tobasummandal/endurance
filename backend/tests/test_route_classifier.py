from helios.analysis.route_classifier import find_candidates


def test_nested_loop_detected():
    src = """
def outer():
    for i in range(10):
        for j in range(10):
            x = i * j
"""
    cands = find_candidates(src)
    assert any(c["pattern"] == "nested_numeric_loop" for c in cands)


def test_matmul_detected():
    src = "import numpy as np\n\ndef f(a, b):\n    return a @ b\n"
    cands = find_candidates(src)
    assert any(c["pattern"] == "matmul" for c in cands)
