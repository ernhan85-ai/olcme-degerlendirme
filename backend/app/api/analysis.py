"""AI Hata Analizi: response analysis view, teacher transcription correction, hypothesis review, score override."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import question_out
from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import CurrentUser, ensure_exam_access, require
from app.models import (
    ErrorHypothesis,
    Exam,
    ReviewStatus,
    SolutionStep,
    Student,
    StudentResponse,
    StudentSubmission,
    TeacherReview,
)
from app.schemas import (
    HypothesisOut,
    ResponseAnalysisOut,
    ReviewIn,
    ReviewQueueItem,
    ScoreOverrideIn,
    StepOut,
    StudentOut,
    SubmissionFileOut,
    TranscriptionIn,
)
from app.services import pipeline
from app.services.ai.providers import get_explainer
from app.services.audit import audit
from app.services.error_reasoning import ErrorReasoningEngine

router = APIRouter(tags=["analysis"])


def _load_response(db: Session, user: CurrentUser, response_id: uuid.UUID) -> tuple[StudentResponse, StudentSubmission, Exam]:
    r = db.get(StudentResponse, response_id)
    if r is None or r.organization_id != user.organization_id:
        raise HTTPException(404, "Cevap bulunamadı.")
    sub = db.get(StudentSubmission, r.submission_id)
    exam = ensure_exam_access(db, user, db.get(Exam, sub.exam_id))
    return r, sub, exam


def _out(db: Session, r: StudentResponse, sub: StudentSubmission, exam: Exam) -> ResponseAnalysisOut:
    return ResponseAnalysisOut(
        id=r.id, submission_id=sub.id, student=StudentOut.model_validate(db.get(Student, sub.student_id)),
        exam_id=exam.id, exam_title=exam.title, question=question_out(db, r.exam_question),
        final_answer=r.final_answer, answer_confidence=r.answer_confidence, is_correct=r.is_correct, score=r.score,
        needs_review=r.needs_review, review_reason=r.review_reason, transcription_source=r.transcription_source,
        source_page=r.source_page, source_bbox=r.source_bbox,
        files=[SubmissionFileOut.model_validate(f) for f in sub.files if f.mime_type != "application/json"],
        steps=[StepOut.model_validate(s) for s in r.steps],
        hypotheses=[HypothesisOut.model_validate(h) for h in sorted(r.hypotheses, key=lambda h: -h.calibrated_confidence)],
        provider_is_mock=bool(sub.job and sub.job.provider_is_mock),
    )


@router.get("/submissions/{submission_id}/responses", response_model=list[ResponseAnalysisOut])
def list_responses(submission_id: uuid.UUID, user: CurrentUser = Depends(require("exam:read")), db: Session = Depends(get_db)):
    sub = db.get(StudentSubmission, submission_id)
    if sub is None or sub.organization_id != user.organization_id:
        raise HTTPException(404, "Kayıt bulunamadı.")
    exam = ensure_exam_access(db, user, db.get(Exam, sub.exam_id))
    return [_out(db, r, sub, exam) for r in sorted(sub.responses, key=lambda r: r.exam_question.position)]


@router.get("/responses/{response_id}", response_model=ResponseAnalysisOut)
def get_response(response_id: uuid.UUID, user: CurrentUser = Depends(require("exam:read")), db: Session = Depends(get_db)):
    return _out(db, *_load_response(db, user, response_id))


@router.put("/responses/{response_id}/transcription", response_model=ResponseAnalysisOut)
def correct_transcription(response_id: uuid.UUID, body: TranscriptionIn,
                          user: CurrentUser = Depends(require("analysis:review")), db: Session = Depends(get_db)):
    """Teacher corrects OCR (answer + steps). Analysis is re-run deterministically."""
    r, sub, exam = _load_response(db, user, response_id)
    before = {"final_answer": r.final_answer, "steps": [s.raw_text for s in r.steps]}
    r.steps.clear()
    db.flush()
    r.final_answer = body.final_answer
    r.answer_confidence = 1.0
    r.transcription_source = "teacher"
    r.steps = [SolutionStep(step_index=i, raw_text=st.raw_text, normalized_expr=st.normalized_expr, ocr_confidence=1.0,
                            is_crossed_out=st.is_crossed_out, page=st.page, bbox=st.bbox, edited_by_teacher=True)
               for i, st in enumerate(body.steps)]
    db.flush()
    s = get_settings()
    pipeline.analyze_response(db, r, engine=ErrorReasoningEngine(s.ocr_min_confidence, s.review_confidence_threshold),
                              explainer=get_explainer(s))
    pipeline.recompute_totals(sub)
    audit(db, org_id=user.organization_id, actor_id=user.id, action="transcription_corrected", entity_type="response",
          entity_id=r.id, before=before, after=body.model_dump())
    db.commit()
    db.refresh(r)
    return _out(db, r, sub, exam)


@router.post("/hypotheses/{hypothesis_id}/review", response_model=ResponseAnalysisOut)
def review_hypothesis(hypothesis_id: uuid.UUID, body: ReviewIn,
                      user: CurrentUser = Depends(require("analysis:review")), db: Session = Depends(get_db)):
    h = db.get(ErrorHypothesis, hypothesis_id)
    if h is None or h.organization_id != user.organization_id:
        raise HTTPException(404, "Hipotez bulunamadı.")
    r, sub, exam = _load_response(db, user, h.response_id)
    if body.action == ReviewStatus.MODIFIED and body.corrected_category is None:
        raise HTTPException(422, "Düzeltme için doğru hata kategorisini seçin.")
    db.add(TeacherReview(organization_id=user.organization_id, hypothesis_id=h.id, response_id=r.id, reviewer_id=user.id,
                         action=body.action, original_category=h.category, corrected_category=body.corrected_category,
                         detector=h.detector, note=body.note))
    h.review_status = body.action
    if body.action == ReviewStatus.MODIFIED:
        h.category = body.corrected_category
    # response leaves the queue when no hypothesis is pending
    r.needs_review = any(x.review_status == ReviewStatus.PENDING for x in r.hypotheses)
    if not r.needs_review:
        r.review_reason = None
    audit(db, org_id=user.organization_id, actor_id=user.id, action="hypothesis_review", entity_type="error_hypothesis",
          entity_id=h.id, review=body.model_dump(mode="json"))
    db.commit()
    db.refresh(r)
    return _out(db, r, sub, exam)


@router.post("/responses/{response_id}/score", response_model=ResponseAnalysisOut)
def override_score(response_id: uuid.UUID, body: ScoreOverrideIn,
                   user: CurrentUser = Depends(require("analysis:review")), db: Session = Depends(get_db)):
    r, sub, exam = _load_response(db, user, response_id)
    if body.score > r.exam_question.points:
        raise HTTPException(422, f"Puan en fazla {r.exam_question.points} olabilir.")
    old = r.score
    r.score = body.score
    r.is_correct = body.score == r.exam_question.points
    if not r.hypotheses:
        r.needs_review = False
        r.review_reason = None
    db.add(TeacherReview(organization_id=user.organization_id, response_id=r.id, reviewer_id=user.id,
                         action=ReviewStatus.MODIFIED, note=f"Puan: {old} → {body.score}. {body.note or ''}".strip()))
    pipeline.recompute_totals(sub)
    audit(db, org_id=user.organization_id, actor_id=user.id, action="score_override", entity_type="response",
          entity_id=r.id, old=old, new=body.score)
    db.commit()
    db.refresh(r)
    return _out(db, r, sub, exam)


@router.get("/reviews/queue", response_model=list[ReviewQueueItem])
def review_queue(exam_id: uuid.UUID | None = None, user: CurrentUser = Depends(require("analysis:review")),
                 db: Session = Depends(get_db)):
    q = (select(StudentResponse, StudentSubmission, Exam, Student)
         .join(StudentSubmission, StudentResponse.submission_id == StudentSubmission.id)
         .join(Exam, StudentSubmission.exam_id == Exam.id)
         .join(Student, StudentSubmission.student_id == Student.id)
         .where(StudentResponse.organization_id == user.organization_id, StudentResponse.needs_review.is_(True)))
    if exam_id:
        q = q.where(Exam.id == exam_id)
    out: list[ReviewQueueItem] = []
    for r, _sub, exam, st in db.execute(q.limit(500)).all():
        try:
            ensure_exam_access(db, user, exam)
        except HTTPException:
            continue
        prim = next((h for h in r.hypotheses if h.is_primary), None)
        out.append(ReviewQueueItem(response_id=r.id, exam_id=exam.id, exam_title=exam.title, student_name=st.full_name,
                                   position=r.exam_question.position, reason=r.review_reason,
                                   primary_category=prim.category if prim else None,
                                   confidence=prim.calibrated_confidence if prim else None))
    return sorted(out, key=lambda x: (x.confidence if x.confidence is not None else -1))
