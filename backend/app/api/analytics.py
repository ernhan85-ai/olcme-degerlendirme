"""Madde analizi (CTT) and per-outcome observed achievement for an exam."""
from __future__ import annotations

import uuid
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, ensure_exam_access, require
from app.models import (
    AnswerType,
    Exam,
    LearningOutcome,
    QuestionOutcomeMapping,
    StudentSubmission,
)
from app.schemas import ItemAnalysisOut, ItemStatOut, OutcomeReportOut, OutcomeRow
from app.services.item_analysis import analyze_items, outcome_achievement

router = APIRouter(prefix="/exams/{exam_id}", tags=["analytics"])


def _collect(db: Session, exam: Exam):
    # latest submission per student wins (re-uploads replace earlier ones in statistics)
    subs = db.execute(select(StudentSubmission).where(StudentSubmission.exam_id == exam.id)
                      .order_by(StudentSubmission.created_at)).scalars().all()
    scores: dict[str, dict[str, float | None]] = {}
    choices: dict[str, dict[str, str | None]] = {}
    cats: dict[str, Counter] = defaultdict(Counter)
    for s in subs:
        if not s.responses:
            continue
        key = str(s.student_id)
        scores[key], choices[key] = {}, {}
        for r in s.responses:
            iid = str(r.exam_question_id)
            scores[key][iid] = r.score
            choices[key][iid] = r.final_answer
            for h in r.hypotheses:
                if h.is_primary and h.review_status.value != "rejected":
                    cats[iid][h.category.value] += 1
    return scores, choices, cats


@router.get("/item-analysis", response_model=ItemAnalysisOut)
def item_analysis(exam_id: uuid.UUID, user: CurrentUser = Depends(require("analytics:read")), db: Session = Depends(get_db)):
    exam = ensure_exam_access(db, user, db.get(Exam, exam_id))
    scores, choices, cats = _collect(db, exam)
    items = [(str(eq.id), eq.position, eq.points) for eq in exam.questions]
    correct = {str(eq.id): eq.answer_key.correct_answer for eq in exam.questions
               if eq.question.answer_type == AnswerType.MULTIPLE_CHOICE and eq.answer_key}
    stats, test = analyze_items(items, scores, choices, correct)
    return ItemAnalysisOut(
        exam_id=exam.id, n_students=test.n_students, n_items=test.n_items, mean_pct=test.mean_pct, sd_pct=test.sd_pct,
        reliability=test.reliability, reliability_method=test.reliability_method, sem_pct=test.sem_pct,
        warnings=test.warnings,
        items=[ItemStatOut(exam_question_id=s.item_id, position=s.position, n=s.n, difficulty_p=s.difficulty_p,
                           discrimination_rpbis=s.discrimination_rpbis, discrimination_d=s.discrimination_d,
                           flags=s.flags, distractors=s.distractors, error_categories=dict(cats.get(s.item_id, {})))
               for s in stats],
    )


@router.get("/outcome-report", response_model=OutcomeReportOut)
def outcome_report(exam_id: uuid.UUID, user: CurrentUser = Depends(require("analytics:read")), db: Session = Depends(get_db)):
    exam = ensure_exam_access(db, user, db.get(Exam, exam_id))
    scores, _, cats = _collect(db, exam)
    mapping: dict[str, list[tuple[str, float]]] = {}
    for eq in exam.questions:
        mapping[str(eq.id)] = [(str(m.learning_outcome_id), m.weight) for m in db.execute(
            select(QuestionOutcomeMapping).where(QuestionOutcomeMapping.question_id == eq.question_id)).scalars()]
    max_pts = {str(eq.id): eq.points for eq in exam.questions}
    per_student = {sid: outcome_achievement(mapping, max_pts, sc) for sid, sc in scores.items()}
    outcome_ids = {o for outs in mapping.values() for o, _ in outs}
    outcomes = {str(o.id): o for o in db.execute(select(LearningOutcome).where(
        LearningOutcome.id.in_([uuid.UUID(x) for x in outcome_ids]))).scalars()} if outcome_ids else {}
    rows: list[OutcomeRow] = []
    for oid, o in sorted(outcomes.items(), key=lambda kv: kv[1].code):
        vals = [p[oid]["observed_pct"] for p in per_student.values() if oid in p and p[oid]["observed_pct"] is not None]
        items_for = [iid for iid, outs in mapping.items() if any(x == oid for x, _ in outs)]
        cat_counter: Counter = Counter()
        for iid in items_for:
            cat_counter.update(cats.get(iid, {}))
        top = cat_counter.most_common(1)[0][0] if cat_counter else None
        rows.append(OutcomeRow(outcome_id=o.id, code=o.code, description=o.description,
                               class_observed_pct=round(sum(vals) / len(vals), 1) if vals else None,
                               n_items=len(items_for), students_below_50=sum(1 for v in vals if v < 50),
                               top_error_category=top))
    return OutcomeReportOut(exam_id=exam.id, rows=rows)
