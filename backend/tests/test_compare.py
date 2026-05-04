from helios.execution.compare import agree, compare_case


def test_agree_floats_within_tolerance():
    assert agree(1.0, 1.0 + 1e-13)


def test_agree_floats_outside_tolerance():
    assert not agree(1.0, 1.001)


def test_agree_arrays():
    assert agree([1.0, 2.0, 3.0], [1.0, 2.0, 3.0 + 1e-13])
    assert not agree([1.0, 2.0], [1.0, 2.0, 3.0])


def test_compare_case_exception_match():
    a = {"output": None, "exception": "ValueError: bad"}
    b = {"output": None, "exception": "ValueError: also bad"}
    agreed, note = compare_case(a, b)
    assert agreed and "ValueError" in (note or "")


def test_compare_case_one_exception():
    a = {"output": 1.0, "exception": None}
    b = {"output": None, "exception": "ValueError: bad"}
    agreed, _ = compare_case(a, b)
    assert not agreed
