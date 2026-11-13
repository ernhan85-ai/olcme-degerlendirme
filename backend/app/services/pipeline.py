"""Document processing pipeline: scan -> extract -> score -> error reasoning.

Job state machine:
    UPLOADED -> QUEUED -> PROCESSING -> (REQUIRES_REVIEW | COMPLETED | FAILED)
    FAILED / REQUIRES_REVIEW --retry--> QUEUED
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.models import (
    AnswerKey,
    ErrorHypothesis,
    EvidenceItem,
    ExamQuestion,
    JobStatus,
    LearningOutcome,
    ProcessingJob,
    QuestionOutcomeMapping,
    ReviewStatus,
    SolutionStep,
    StudentResponse,
    StudentSubmission,
)
from app.services import calibration
from app.services.ai.providers import (
    Explainer,
    PageImage,
    ProviderError,
    QuestionSpec,
    VisionProvider,
    get_explainer,
    get_vision_provider,
)
from app.services.error_reasoning import ErrorReasoningEngine, ResponseInput, StepInput
from app.services.storage import Storage, get_storage

log = logging.getLogger("learndna.pipeline")

ALLOWED_RETRY_FROM = {JobStatus.FAILED, JobStatus.REQUIRES_REVIEW, JobStatus.UPLOADED}


def _log(job: ProcessingJob, status: JobStatus, note: str = "") -> None:
    job.status = status
    job.log = [*(job.log or []), {"at": datetime.now(UTC).isoformat(), "status": status.value, "note": note}]


def mark_queued(job: ProcessingJob) -> None:
    if job.status not in ALLOWED_RETRY_FROM and job.status != JobStatus.QUEUED:
        raise ValueError(f"cannot queue job in status {job.status}")
    job.error_code = None
    job.error_message = None
    _log(job, JobStatus.QUEUED)


def _rasterize(data: bytes, mime: str, start_page: int) -> list[PageImage]:
    if mime != "application/pdf":
        return [PageImage(start_page, mime, data)]
    try:
        import pypdfium2 as pdfium  # optional dependency
    except ImportError as e:
        raise ProviderError("pdf_rasterizer_missing",
                            "PDF sayfaları görüntüye çevrilemedi (pypdfium2 kurulu değil).") from e
    import io
    pdf = pdfium.PdfDocument(data)
    pages = []
    for i in range(len(pdf)):
        img = pdf[i].render(scale=2).to_pil()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        pages.append(PageImage(start_page + i, "image/png", buf.getvalue()))
    return pages


# ---------------------------------------------------------------- per-response analysis
def analyze_response(db: Session, resp: StudentResponse, *, engine: ErrorReasoningEngine,
                     explainer: Explainer | None, stats: dict | None = None) -> None:
    """(Re)score one response and regenerate its hypotheses. Teacher reviews are kept
    (hypothesis_id becomes NULL) so history and calibration data survive re-analysis."""
    eq: ExamQuestion = resp.exam_question
    key: AnswerKey | None = eq.answer_key
    for h in list(resp.hypotheses):
        db.delete(h)
    db.flush()
    resp.hypotheses = []

    if key is None:
        resp.is_correct, resp.score, resp.needs_review = None, None, True
        resp.review_reason = "Bu soru için cevap anahtarı tanımlı değil."
        return

    # prerequisite signal: any mapped outcome declares prerequisites (full graph = Phase 4)
    prereq_lists = db.execute(
        select(LearningOutcome.prerequisite_ids)
        .join(QuestionOutcomeMapping, QuestionOutcomeMapping.learning_outcome_id == LearningOutcome.id)
        .where(QuestionOutcomeMapping.question_id == eq.question_id)
    ).scalars().all()
    has_prereq = any(bool(p) for p in prereq_lists)
    q = eq.question
    rin = ResponseInput(
        answer_type=q.answer_type.value,
        correct_answer=key.correct_answer,
        final_answer=resp.final_answer,
        answer_confidence=resp.answer_confidence,
        steps=[StepInput(s.step_index, s.raw_text, s.normalized_expr, s.ocr_confidence, s.is_crossed_out, s.page, s.bbox)
               for s in resp.steps],
        reference_steps=list(key.reference_steps or []),
        options=q.options,
        has_prerequisites=has_prereq,
        answer_page=resp.source_page,
        answer_bbox=resp.source_bbox,
    )
    result = engine.analyze(rin)

    vmap = {v.index: v for v in result.step_verdicts}
    for s in resp.steps:
        if s.step_index in vmap:
            s.verdict, s.verdict_detail = vmap[s.step_index].verdict, vmap[s.step_index].detail

    resp.is_correct = result.is_correct
    resp.score = eq.points if result.is_correct else (0.0 if result.is_correct is False else None)
    resp.needs_review = result.needs_review
    resp.review_reason = " ".join(result.review_reasons) or None

    stats = stats if stats is not None else calibration.detector_stats(db, resp.organization_id)
    for h in result.hypotheses:
        cal = calibration.calibrate(h.raw_confidence, stats.get(h.detector))
        needs = cal < engine.review_threshold or result.needs_review
        llm_text, llm_mock = None, False
        if explainer is not None and h.is_primary:
            try:
                llm_text = explainer.explain(category=h.category.value, observed=h.observed_error,
                                             inferred=h.inferred_cause, steps=[s.raw_text for s in resp.steps])
                llm_mock = explainer.is_mock
            except ProviderError as e:
                log.warning("explainer failed: %s", e.code)
        hyp = ErrorHypothesis(
            organization_id=resp.organization_id, category=h.category, detector=h.detector,
            observed_error=h.observed_error, inferred_cause=h.inferred_cause,
            alternative_explanations=h.alternative_explanations, diagnostic_questions=h.diagnostic_questions,
            raw_confidence=h.raw_confidence, calibrated_confidence=cal, is_primary=h.is_primary,
            llm_explanation=llm_text, llm_explanation_is_mock=llm_mock,
            review_status=ReviewStatus.PENDING if needs else ReviewStatus.NOT_REQUIRED,
            engine_version=result.engine_version,
            evidence=[EvidenceItem(kind=e.kind, description=e.description, step_index=e.step_index,
                                   page=e.page, bbox=e.bbox, verified_by=e.verified_by) for e in h.evidence],
        )
        resp.hypotheses.append(hyp)
        if needs:
            resp.needs_review = True


def recompute_totals(sub: StudentSubmission) -> None:
    sub.max_score = sum(r.exam_question.points for r in sub.responses)
    sub.total_score = sum((r.score or 0.0) for r in sub.responses)


# ---------------------------------------------------------------- job runner
def process_submission(db: Session, submission_id: uuid.UUID, *, settings: Settings | None = None,
                       vision: VisionProvider | None = None, explainer: Explainer | None = None,
                       storage: Storage | None = None) -> JobStatus:
    s = settings or get_settings()
    sub = db.execute(
        select(StudentSubmission).where(StudentSubmission.id == submission_id)
        .options(selectinload(StudentSubmission.files), selectinload(StudentSubmission.job),
                 selectinload(StudentSubmission.responses).selectinload(StudentResponse.steps))
    ).scalar_one()
    job = sub.job
    job.attempts += 1
    _log(job, JobStatus.PROCESSING, f"deneme {job.attempts}")
    db.commit()

    try:
        storage = storage or get_storage(s)
        vision = vision or get_vision_provider(s)
        explainer = explainer if explainer is not None else get_explainer(s)
        job.provider_name, job.provider_is_mock = vision.name, vision.is_mock

        if any(f.malware_scan == "infected" for f in sub.files):
            raise ProviderError("malware_detected", "Dosyalardan birinde zararlı yazılım tespit edildi. Dosya işlenmedi.")

        pages: list[PageImage] = []
        fixture = None
        for f in sub.files:
            data = storage.get(f.storage_key)
            if f.mime_type == "application/json":
                if s.env != "development":
                    raise ProviderError("fixture_not_allowed", "Test transkripsiyon dosyaları yalnızca geliştirme ortamında kullanılabilir.")
                fixture = json.loads(data)
                continue
            if vision.is_mock:
                pages.append(PageImage(len(pages) + 1, f.mime_type, b""))  # mock never reads bytes
            else:
                pages.extend(_rasterize(data, f.mime_type, len(pages) + 1))

        eqs = db.execute(
            select(ExamQuestion).where(ExamQuestion.exam_id == sub.exam_id).order_by(ExamQuestion.position)
            .options(selectinload(ExamQuestion.answer_key))
        ).scalars().all()
        specs = [QuestionSpec(e.position, e.question.answer_type.value,
                              list((e.question.options or {}).keys()) or None) for e in eqs]
        extraction = vision.extract(pages, specs, fixture=fixture)
        by_pos = {r.position: r for r in extraction.responses}

        # keep teacher-transcribed responses; rebuild AI ones
        existing = {r.exam_question_id: r for r in sub.responses}
        for e in eqs:
            prev = existing.get(e.id)
            if prev is not None and prev.transcription_source == "teacher":
                continue
            if prev is not None:
                sub.responses.remove(prev)
                db.flush()
            x = by_pos.get(e.position)
            resp = StudentResponse(organization_id=sub.organization_id, exam_question_id=e.id, exam_question=e)
            if x is None or x.unreadable:
                resp.final_answer, resp.answer_confidence = None, 0.0
                resp.needs_review = True
                resp.review_reason = "Öğrenci çözümü güvenilir biçimde analiz edilemedi. Öğretmen incelemesi gerekiyor."
            else:
                resp.final_answer, resp.answer_confidence = x.final_answer, x.answer_confidence
                resp.source_page, resp.source_bbox = x.page, x.bbox
                resp.steps = [SolutionStep(step_index=i, raw_text=st.raw_text, normalized_expr=st.normalized_expr,
                                           ocr_confidence=st.ocr_confidence, is_crossed_out=st.is_crossed_out,
                                           page=st.page, bbox=st.bbox) for i, st in enumerate(x.steps)]
            sub.responses.append(resp)
        db.flush()

        engine = ErrorReasoningEngine(s.ocr_min_confidence, s.review_confidence_threshold)
        stats = calibration.detector_stats(db, sub.organization_id)
        for resp in sub.responses:
            if resp.final_answer is None and not resp.steps and resp.transcription_source != "teacher":
                continue  # unreadable: nothing to analyse, already flagged
            analyze_response(db, resp, engine=engine, explainer=explainer, stats=stats)
        recompute_totals(sub)

        note = " | ".join(extraction.warnings)
        final = JobStatus.REQUIRES_REVIEW if any(r.needs_review for r in sub.responses) else JobStatus.COMPLETED
        _log(job, final, note)
        db.commit()
        return final
    except ProviderError as e:
        db.rollback()
        job = db.get(ProcessingJob, job.id)
        job.error_code, job.error_message = e.code, e.message_tr
        _log(job, JobStatus.FAILED, e.code)
        db.commit()
        return JobStatus.FAILED
    except Exception as e:  # noqa: BLE001 - must never leave a job stuck in PROCESSING
        log.exception("pipeline crash for submission %s", submission_id)
        db.rollback()
        job = db.get(ProcessingJob, job.id)
        job.error_code = f"internal:{type(e).__name__}"
        job.error_message = "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin; sorun sürerse sistem yöneticisine bildirin."
        _log(job, JobStatus.FAILED, job.error_code)
        db.commit()
        return JobStatus.FAILED
