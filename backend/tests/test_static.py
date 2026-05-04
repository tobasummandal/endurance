from helios.analysis.static import run_static_checks


def test_off_by_one_detected():
    src = open("tests/fixtures/integrate_off_by_one.py").read()
    findings = run_static_checks(src)
    cats = [f["category"] for f in findings]
    assert "off_by_one" in cats


def test_mutable_default():
    findings = run_static_checks("def f(x=[]):\n    x.append(1)\n    return x\n")
    assert any(f["category"] == "mutable_default" for f in findings)


def test_bare_except():
    findings = run_static_checks("try:\n    x = 1\nexcept:\n    x = 2\n")
    assert any(f["category"] == "bare_except" for f in findings)


def test_float_equality():
    findings = run_static_checks("a = 0.1 + 0.2\nif a == 0.3:\n    pass\n")
    assert any(f["category"] == "float_equality" for f in findings)
