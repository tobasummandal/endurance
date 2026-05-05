from helios.detector.scientific import detect_scientific


def test_numpy_code_is_scientific():
    src = """
import numpy as np

def trapz(f, dx):
    n = len(f)
    total = 0.0
    for i in range(1, n - 1):
        total += 0.5 * (f[i] + f[i + 1]) * dx
    return total
"""
    s = detect_scientific(src)
    assert s.is_scientific
    assert s.score >= 0.5
    assert any("numpy" in p for p in s.positive_signals)


def test_torch_code_is_scientific():
    src = "import torch\nx = torch.zeros(10)\n"
    s = detect_scientific(src)
    assert s.is_scientific


def test_fastapi_handler_is_not_scientific():
    src = """
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def list_users():
    return [{"id": 1}]
"""
    s = detect_scientific(src)
    assert not s.is_scientific
    assert any("fastapi" in n for n in s.negative_signals)


def test_django_orm_is_not_scientific():
    src = """
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
"""
    s = detect_scientific(src)
    assert not s.is_scientific


def test_neutral_code_low_confidence():
    src = "def add(a, b):\n    return a + b\n"
    s = detect_scientific(src)
    assert not s.is_scientific
    assert s.confidence == "low"


def test_partial_or_broken_code_handled():
    src = "import numpy as np\ndef f(\n"
    s = detect_scientific(src)
    # syntax error — should still classify via textual signals
    assert s.is_scientific or "numpy" in " ".join(s.positive_signals)


def test_qiskit_is_scientific():
    src = "from qiskit import QuantumCircuit\nqc = QuantumCircuit(2)\n"
    s = detect_scientific(src)
    assert s.is_scientific
