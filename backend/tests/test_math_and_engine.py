import pytest

from app.models import ErrorCategory, StepVerdict
from app.services import math_verify as mv
from app.services.calibration import DetectorStats, calibrate
from app.services.error_reasoning import UNREADABLE_MESSAGE_TR, ErrorReasoningEngine, ResponseInput, StepInput
from app.services.item_analysis import analyze_items, outcome_achievement


# ------------------------------------------------------------ math_verify
@pytest.mark.parametrize("bad", ["__import__('os')", "exec(1)", "x" * 300, "lambda: 1", "open('f')", "x==2=3"])
def test_unsafe_input_rejected(bad):
    assert mv.try_parse(bad) is None


def test_turkish_notation():
    assert mv.answers_match("2,5", "5/2", "numeric") is True
    assert mv.answers_match("3×4", "12", "numeric") is True
    assert mv.answers_match("x = 5", "5", "equation") is True
    assert mv.answers_match("5", "x=5", "equation") is True
    assert mv.answers_match("b", "B", "multiple_choice") is True
    assert mv.answers_match("", "5", "numeric") is False
    assert mv.answers_match("bilmiyorum", "5", "numeric") is None  # undecidable -> review


def test_equation_equivalence():
    assert mv.equivalent(mv.parse_math("3x+5=20"), mv.parse_math("3x=15")) is True
    assert mv.equivalent(mv.parse_math("3x+5=20"), mv.parse_math("3x=25")) is False
    assert mv.equivalent(mv.parse_math("2(a-1)"), mv.parse_math("2a-2")) is True


# ------------------------------------------------------------ engine
E = ErrorReasoningEngine(0.6, 0.7)


def run(steps, final, correct, ref=None, t="equation", ocr=0.95, crossed=()):
    return E.analyze(ResponseInput(
        answer_type=t, correct_answer=correct, final_answer=final, reference_steps=ref or [],
        steps=[StepInput(i, s, ocr_confidence=ocr, is_crossed_out=i in crossed) for i, s in enumerate(steps)]))


def primary(a):
    return next(h for h in a.hypotheses if h.is_primary)


@pytest.mark.parametrize("steps,final,correct,ref,t,cat,det", [
    (["3x+5=20", "3x=20+5", "3x=25", "x=25/3"], "x=25/3", "x=5", ["3x+5=20"], "equation",
     ErrorCategory.INCORRECT_PROCEDURE, "sign_transposition"),
    (["3x+5=20", "3x=15", "x=6"], "x=6", "x=5", ["3x+5=20"], "equation", ErrorCategory.ARITHMETIC_ERROR, "numeric_slip"),
    (["3x+5=20", "3x=15", "x=15-3"], None, "x=5", ["3x+5=20"], "equation", ErrorCategory.INCORRECT_PROCEDURE, "inverse_operation"),
    (["2(x+3)=10", "2x+3=10", "2x=7", "x=7/2"], None, "x=2", ["2(x+3)=10"], "equation",
     ErrorCategory.INCORRECT_PROCEDURE, "partial_distribution"),
    (["1/2+1/3", "2/5"], "2/5", "5/6", ["1/2+1/3"], "numeric", ErrorCategory.CONCEPTUAL_MISUNDERSTANDING, "fraction_add_num_den"),
    (["3x+5=20", "3x=15"], None, "x=5", ["3x+5=20"], "equation", ErrorCategory.INCOMPLETE_SOLUTION, "unresolved_last_step"),
    (["3x+5=20", "3x=15", "x=5"], "x=3", "x=5", ["3x+5=20"], "equation",
     ErrorCategory.POSSIBLE_ATTENTION_MISTAKE, "answer_transcription"),
    (["3x+8=20", "3x=12", "x=4"], "x=4", "x=5", ["3x+5=20"], "equation", ErrorCategory.PROBLEM_INTERPRETATION, "setup_mismatch"),
])
def test_detectors(steps, final, correct, ref, t, cat, det):
    a = run(steps, final, correct, ref, t)
    assert a.is_correct is False
    p = primary(a)
    assert (p.category, p.detector) == (cat, det)
    assert p.evidence, "every hypothesis must carry evidence"
    assert p.diagnostic_questions
    assert p.observed_error and p.inferred_cause and p.observed_error != p.inferred_cause


def test_correct_answer_no_hypothesis():
    a = run(["3x+5=20", "3x=15", "x=5"], "x=5", "x=5", ["3x+5=20"])
    assert a.is_correct is True and a.hypotheses == [] and not a.needs_review
    assert all(v.verdict == StepVerdict.VALID for v in a.step_verdicts)


def test_unreadable_work_never_invented():
    a = run(["???", "%%"], "x=4", "x=5")
    p = primary(a)
    assert p.category == ErrorCategory.INSUFFICIENT_EVIDENCE
    assert a.needs_review and UNREADABLE_MESSAGE_TR in a.review_reasons


def test_low_ocr_forces_review_and_lowers_confidence():
    hi = primary(run(["3x+5=20", "3x=20+5", "3x=25", "x=25/3"], "x=25/3", "x=5", ["3x+5=20"], ocr=0.99))
    lo_a = run(["3x+5=20", "3x=20+5", "3x=25", "x=25/3"], "x=25/3", "x=5", ["3x+5=20"], ocr=0.4)
    assert lo_a.needs_review
    assert primary(lo_a).raw_confidence < hi.raw_confidence


def test_crossed_out_steps_ignored():
    a = run(["3x+5=20", "3x=99", "3x=15", "x=5"], "x=5", "x=5", ["3x+5=20"], crossed=(1,))
    assert a.is_correct and not a.hypotheses
    assert next(v for v in a.step_verdicts if v.index == 1).verdict == StepVerdict.NOT_CHECKED


def test_mc_without_work_is_insufficient_evidence():
    a = E.analyze(ResponseInput(answer_type="multiple_choice", correct_answer="C", final_answer="A",
                                options={"A": "1", "B": "2", "C": "3"}))
    assert primary(a).category == ErrorCategory.INSUFFICIENT_EVIDENCE


def test_mc_tagged_distractor():
    a = E.analyze(ResponseInput(answer_type="multiple_choice", correct_answer="C", final_answer="D",
                                options={"D": {"text": "64", "misconception": "incorrect_procedure"}}))
    p = primary(a)
    assert p.category == ErrorCategory.INCORRECT_PROCEDURE and p.raw_confidence < 0.7 and a.needs_review


# ------------------------------------------------------------ calibration
def test_calibration_shrinks_toward_teacher_acceptance():
    assert calibrate(0.8, None) == 0.8
    assert calibrate(0.8, DetectorStats("d", reviewed=10, accepted=2)) == pytest.approx((8 + 2) / 20)
    assert calibrate(0.8, DetectorStats("d", reviewed=90, accepted=90)) > 0.95


# ------------------------------------------------------------ item analysis
def test_item_analysis_known_values():
    items = [("i1", 1, 1.0), ("i2", 2, 1.0), ("i3", 3, 1.0)]
    m = {"s1": [1, 1, 1], "s2": [1, 1, 0], "s3": [1, 0, 0], "s4": [0, 0, 0], "s5": [1, 1, 0]}
    scores = {s: {f"i{k + 1}": v for k, v in enumerate(row)} for s, row in m.items()}
    stats, test = analyze_items(items, scores)
    by = {s.item_id: s for s in stats}
    assert by["i1"].difficulty_p == 0.8 and by["i3"].difficulty_p == 0.2
    assert test.reliability_method == "KR-20"
    # KR-20 by hand: k=3, sum pq = .16+.24+.16=.56, var(total)= var([3,2,1,0,2]) = 1.04
    assert test.reliability == pytest.approx(1.5 * (1 - 0.56 / 1.04), abs=1e-3)
    assert any("30" in w for w in test.warnings)


def test_outcome_achievement_is_labelled_observed():
    out = outcome_achievement({"i1": [("o1", 1)], "i2": [("o1", 1), ("o2", 1)]}, {"i1": 10, "i2": 10}, {"i1": 10, "i2": 0})
    assert out["o1"]["observed_pct"] == 50.0 and out["o2"]["observed_pct"] == 0.0
    assert out["o1"]["kind"] == "observed_exam_percentage"
