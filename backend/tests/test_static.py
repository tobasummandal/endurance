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


def test_module_state_shared_cache():
    src = (
        "_cache = {}\n"
        "\n"
        "def predict(x):\n"
        "    if x in _cache: return _cache[x]\n"
        "    _cache[x] = x * 2\n"
        "    return _cache[x]\n"
        "\n"
        "def clear():\n"
        "    _cache.clear()\n"
    )
    findings = run_static_checks(src)
    cats = [f["category"] for f in findings]
    assert "module_state" in cats
    ms = [f for f in findings if f["category"] == "module_state"][0]
    assert ms["severity"] == "high"
    assert "_cache" in ms["title"]


def test_module_state_unused_global_not_flagged():
    # Mutable global at module level but only referenced in __main__ — not shared by functions.
    src = "config = {}\n\nif __name__ == '__main__':\n    print(config)\n"
    findings = run_static_checks(src)
    assert not any(f["category"] == "module_state" for f in findings)


def test_module_state_single_reader_not_flagged():
    # One function reads a global but doesn't mutate it — not enough signal to flag.
    src = "TABLE = {1: 2}\n\ndef lookup(k):\n    return TABLE.get(k)\n"
    findings = run_static_checks(src)
    # Single read with no mutation — should NOT flag
    assert not any(f["category"] == "module_state" for f in findings)


def test_module_state_single_mutator_flagged():
    # One function mutates a global — flag, even with one toucher.
    src = "history = []\n\ndef step(x):\n    history.append(x)\n    return x\n"
    findings = run_static_checks(src)
    assert any(f["category"] == "module_state" for f in findings)


def test_module_state_global_rebind_counts_as_mutation():
    # `global counter; counter += 1` — Name target with global declaration.
    src = (
        "counter = []\n"
        "\n"
        "def tick():\n"
        "    global counter\n"
        "    counter = counter + [1]\n"
    )
    findings = run_static_checks(src)
    assert any(f["category"] == "module_state" for f in findings)
