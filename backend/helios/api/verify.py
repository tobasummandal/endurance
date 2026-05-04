from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from ..analysis.test_synthesizer import (
    diff_changed_lines,
    find_target_functions,
    function_signature,
    function_source,
    synthesize_inputs,
)
from ..db import get_session
from ..errors import HeliosError
from ..execution.compare import compare_case, preview
from ..execution.sandbox import run_function
from ..models import Fix, Session, Verification
from ..schemas import TestCaseResult, VerificationOut

router = APIRouter()


def _verdict(passed: int, failed: int) -> str:
    if passed == 0 and failed == 0:
        return "error"
    if failed == 0:
        return "all_agree"
    if passed == 0:
        return "all_disagree"
    return "partial_disagree"


@router.post("/sessions/{session_id}/fixes/{fix_id}/verify", response_model=VerificationOut)
def verify(session_id: str, fix_id: str, db: DBSession = Depends(get_session)) -> VerificationOut:
    s = db.get(Session, session_id)
    fix = db.get(Fix, fix_id)
    if not s or not fix or fix.session_id != session_id:
        raise HeliosError(404, "not_found", "session or fix not found")

    changed = diff_changed_lines(s.source_code, fix.fixed_code)
    targets = find_target_functions(s.source_code, changed)
    if not targets:
        raise HeliosError(422, "no_target_function", "could not identify a function changed by this fix")

    target = targets[0]
    sig = function_signature(target)
    fn_src = function_source(s.source_code, target)
    inputs = synthesize_inputs(fn_src, sig)
    if not inputs:
        raise HeliosError(422, "no_test_cases", "test synthesizer returned no inputs")

    orig_run = run_function(s.source_code, target.name, inputs)
    fix_run = run_function(fix.fixed_code, target.name, inputs)

    if orig_run.fatal and not orig_run.cases:
        raise HeliosError(504 if orig_run.timeout else 500,
                          "sandbox_original_failed", orig_run.fatal)
    if fix_run.fatal and not fix_run.cases:
        raise HeliosError(504 if fix_run.timeout else 500,
                          "sandbox_fix_failed", fix_run.fatal)

    cases: list[TestCaseResult] = []
    passed = 0
    failed = 0
    n = min(len(orig_run.cases), len(fix_run.cases), len(inputs))
    for i in range(n):
        o = orig_run.cases[i]
        f = fix_run.cases[i]
        agreed, note = compare_case(o, f)
        if agreed:
            passed += 1
        else:
            failed += 1
        cases.append(TestCaseResult(
            index=i,
            input_preview=preview(inputs[i]),
            original_output_preview=preview(o.get("output") if not o.get("exception") else o.get("exception")),
            fix_output_preview=preview(f.get("output") if not f.get("exception") else f.get("exception")),
            agreed=agreed,
            original_ms=float(o.get("elapsed_ms", 0.0)),
            fix_ms=float(f.get("elapsed_ms", 0.0)),
            notes=note,
        ))

    v = Verification(
        fix_id=fix_id,
        test_cases=[c.model_dump() for c in cases],
        passed=passed,
        failed=failed,
        overall_verdict=_verdict(passed, failed),
    )
    db.add(v)
    s.status = "verified"
    db.add(s)
    db.commit()
    db.refresh(v)

    return VerificationOut(
        id=v.id,
        fix_id=v.fix_id,
        test_cases=cases,
        passed=v.passed,
        failed=v.failed,
        overall_verdict=v.overall_verdict,
        created_at=v.created_at,
    )


@router.get("/sessions/{session_id}/verifications/{verification_id}", response_model=VerificationOut)
def get_verification(session_id: str, verification_id: str, db: DBSession = Depends(get_session)) -> VerificationOut:
    v = db.get(Verification, verification_id)
    if not v:
        raise HeliosError(404, "not_found", "verification not found")
    cases = [TestCaseResult.model_validate(c) for c in (v.test_cases or [])]
    return VerificationOut(
        id=v.id, fix_id=v.fix_id, test_cases=cases,
        passed=v.passed, failed=v.failed,
        overall_verdict=v.overall_verdict, created_at=v.created_at,
    )
