"""Typed API contracts (Pydantic v2). Frontend types in frontend/lib/types.ts mirror these."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AnswerType, ErrorCategory, ExamStatus, JobStatus, ReviewStatus, StepVerdict


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------- auth
class LoginIn(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    roles: list[str]


# ---------------- lookups
class IdName(ORM):
    id: uuid.UUID
    name: str


class ClassOut(ORM):
    id: uuid.UUID
    name: str
    grade_level: int
    campus_id: uuid.UUID


class OutcomeOut(ORM):
    id: uuid.UUID
    code: str
    description: str
    grade_level: int
    subject_id: uuid.UUID


class StudentOut(ORM):
    id: uuid.UUID
    full_name: str
    student_number: str
    class_id: uuid.UUID | None


class LookupsOut(BaseModel):
    subjects: list[IdName]
    classes: list[ClassOut]
    outcomes: list[OutcomeOut]


# ---------------- exams
class QuestionIn(BaseModel):
    position: int = Field(ge=1, le=200)
    stem_text: str = Field(min_length=1, max_length=5000)
    answer_type: AnswerType
    options: dict | None = None
    points: float = Field(default=1.0, gt=0, le=100)
    correct_answer: str = Field(min_length=1, max_length=500)
    reference_steps: list[str] = Field(default_factory=list, max_length=40)
    outcome_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("correct_answer")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ExamCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    subject_id: uuid.UUID
    grade_level: int = Field(ge=1, le=12)
    class_ids: list[uuid.UUID] = Field(min_length=1)
    exam_date: date
    questions: list[QuestionIn] = Field(default_factory=list)


class QuestionOut(BaseModel):
    exam_question_id: uuid.UUID
    question_id: uuid.UUID
    position: int
    points: float
    stem_text: str
    answer_type: AnswerType
    options: dict | None
    correct_answer: str | None
    reference_steps: list[str]
    key_validated: bool
    outcome_ids: list[uuid.UUID]


class ExamOut(BaseModel):
    id: uuid.UUID
    title: str
    subject_id: uuid.UUID
    subject_name: str | None = None
    grade_level: int
    class_ids: list[uuid.UUID]
    exam_date: date
    status: ExamStatus
    has_booklet: bool
    question_count: int
    submission_count: int = 0
    pending_review_count: int = 0
    created_at: datetime


class ExamDetailOut(ExamOut):
    questions: list[QuestionOut]
    publish_blockers: list[str]


# ---------------- submissions & jobs
class JobOut(ORM):
    id: uuid.UUID
    status: JobStatus
    attempts: int
    error_code: str | None
    error_message: str | None
    provider_name: str | None
    provider_is_mock: bool
    log: list
    updated_at: datetime


class SubmissionFileOut(ORM):
    id: uuid.UUID
    original_name: str
    mime_type: str
    size_bytes: int
    page_order: int
    malware_scan: str


class SubmissionOut(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    student: StudentOut
    total_score: float | None
    max_score: float | None
    job: JobOut | None
    files: list[SubmissionFileOut]
    needs_review_count: int
    created_at: datetime


class UploadResultOut(BaseModel):
    created: list[SubmissionOut]
    errors: list[str]


# ---------------- analysis
class StepIn(BaseModel):
    raw_text: str = Field(max_length=300)
    normalized_expr: str | None = Field(default=None, max_length=200)
    is_crossed_out: bool = False
    page: int | None = None
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)


class TranscriptionIn(BaseModel):
    final_answer: str | None = Field(default=None, max_length=200)
    steps: list[StepIn] = Field(default_factory=list, max_length=40)


class StepOut(ORM):
    id: uuid.UUID
    step_index: int
    raw_text: str
    normalized_expr: str | None
    ocr_confidence: float | None
    is_crossed_out: bool
    page: int | None
    bbox: list | None
    verdict: StepVerdict
    verdict_detail: str | None
    edited_by_teacher: bool


class EvidenceOut(ORM):
    id: uuid.UUID
    kind: str
    description: str
    step_index: int | None
    page: int | None
    bbox: list | None
    verified_by: str


class HypothesisOut(ORM):
    id: uuid.UUID
    category: ErrorCategory
    detector: str
    observed_error: str
    inferred_cause: str
    alternative_explanations: list
    diagnostic_questions: list
    raw_confidence: float
    calibrated_confidence: float
    is_primary: bool
    llm_explanation: str | None
    llm_explanation_is_mock: bool
    review_status: ReviewStatus
    engine_version: str
    evidence: list[EvidenceOut]


class ResponseAnalysisOut(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    student: StudentOut
    exam_id: uuid.UUID
    exam_title: str
    question: QuestionOut
    final_answer: str | None
    answer_confidence: float | None
    is_correct: bool | None
    score: float | None
    needs_review: bool
    review_reason: str | None
    transcription_source: str
    source_page: int | None
    source_bbox: list | None
    files: list[SubmissionFileOut]
    steps: list[StepOut]
    hypotheses: list[HypothesisOut]
    provider_is_mock: bool


class ReviewIn(BaseModel):
    action: ReviewStatus
    corrected_category: ErrorCategory | None = None
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("action")
    @classmethod
    def _allowed(cls, v: ReviewStatus) -> ReviewStatus:
        if v not in (ReviewStatus.APPROVED, ReviewStatus.MODIFIED, ReviewStatus.REJECTED):
            raise ValueError("action must be approved|modified|rejected")
        return v


class ScoreOverrideIn(BaseModel):
    score: float = Field(ge=0)
    note: str | None = Field(default=None, max_length=2000)


class ReviewQueueItem(BaseModel):
    response_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    student_name: str
    position: int
    reason: str | None
    primary_category: ErrorCategory | None
    confidence: float | None


# ---------------- analytics
class ItemStatOut(BaseModel):
    exam_question_id: str
    position: int
    n: int
    difficulty_p: float | None
    discrimination_rpbis: float | None
    discrimination_d: float | None
    flags: list[str]
    distractors: dict | None
    error_categories: dict[str, int]


class ItemAnalysisOut(BaseModel):
    exam_id: uuid.UUID
    n_students: int
    n_items: int
    mean_pct: float | None
    sd_pct: float | None
    reliability: float | None
    reliability_method: str
    sem_pct: float | None
    warnings: list[str]
    items: list[ItemStatOut]
    note: str = "Bu değerler tek bir sınav uygulamasına ait gözlenen istatistiklerdir; öğrenme düzeyi (mastery) tahmini değildir."


class OutcomeRow(BaseModel):
    outcome_id: uuid.UUID
    code: str
    description: str
    class_observed_pct: float | None
    n_items: int
    students_below_50: int
    top_error_category: ErrorCategory | None


class OutcomeReportOut(BaseModel):
    exam_id: uuid.UUID
    rows: list[OutcomeRow]
    note: str = "Gözlenen sınav yüzdesidir; kazanım hakimiyet tahmini değildir."
