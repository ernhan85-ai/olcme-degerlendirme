"""Assessment module data model.

Tables marked [CORE] belong to the Phase-1 foundation (organizations, users, academic
structure). Minimal versions are defined here so the module runs standalone; when merged
into the main monorepo, reuse the core definitions and drop these duplicates.
"""
import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class TenantMixin:
    """Every tenant-owned row carries organization_id; all queries filter on it."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )


# ---------------------------------------------------------------- enums
class RoleName(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    CAMPUS_ADMIN = "campus_admin"
    ACADEMIC_COORDINATOR = "academic_coordinator"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    EXTRACTING = "extracting"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AnswerType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    NUMERIC = "numeric"
    EXPRESSION = "expression"
    EQUATION = "equation"  # answer is a solution set e.g. "x=3"
    OPEN_ENDED = "open_ended"  # requires teacher scoring


class JobStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    REQUIRES_REVIEW = "requires_review"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCategory(str, enum.Enum):
    CONCEPTUAL_MISUNDERSTANDING = "conceptual_misunderstanding"
    MISSING_PREREQUISITE = "missing_prerequisite"
    ARITHMETIC_ERROR = "arithmetic_error"
    INCORRECT_PROCEDURE = "incorrect_procedure"
    PROBLEM_INTERPRETATION = "problem_interpretation"
    INCOMPLETE_SOLUTION = "incomplete_solution"
    INCORRECT_STRATEGY = "incorrect_strategy"
    TRANSFER_DIFFICULTY = "transfer_difficulty"
    POSSIBLE_ATTENTION_MISTAKE = "possible_attention_mistake"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    NOT_REQUIRED = "not_required"  # high-confidence, still visible/overridable by teacher
    APPROVED = "approved"
    MODIFIED = "modified"
    REJECTED = "rejected"


class StepVerdict(str, enum.Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNVERIFIABLE = "unverifiable"
    NOT_CHECKED = "not_checked"


# ---------------------------------------------------------------- [CORE] tenancy & users
class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))


class Campus(Base, TenantMixin, TimestampMixin):
    __tablename__ = "campuses"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))


class User(Base, TenantMixin, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    roles: Mapped[list["UserRole"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role", "campus_id"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[RoleName] = mapped_column(Enum(RoleName, name="role_name"))
    campus_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("campuses.id"), nullable=True)
    user: Mapped[User] = relationship(back_populates="roles")


class Subject(Base, TenantMixin):
    __tablename__ = "subjects"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))


class SchoolClass(Base, TenantMixin):
    __tablename__ = "classes"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    campus_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("campuses.id"), index=True)
    grade_level: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(50))  # e.g. "7-A"


class Student(Base, TenantMixin):
    __tablename__ = "students"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    campus_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("campuses.id"), index=True)
    class_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("classes.id"), index=True)
    student_number: Mapped[str] = mapped_column(String(40))
    full_name: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)


class TeacherAssignment(Base, TenantMixin):
    __tablename__ = "teacher_assignments"
    __table_args__ = (UniqueConstraint("teacher_user_id", "class_id", "subject_id"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    class_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("classes.id"), index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("subjects.id"))


class LearningOutcome(Base, TenantMixin):
    __tablename__ = "learning_outcomes"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), index=True)  # e.g. M.7.2.1.1 (MEB)
    description: Mapped[str] = mapped_column(Text)
    grade_level: Mapped[int] = mapped_column(Integer)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("subjects.id"))
    curriculum: Mapped[str] = mapped_column(String(40), default="MEB")
    # prerequisite outcome ids (full knowledge graph lives in Phase 4)
    prerequisite_ids: Mapped[list] = mapped_column(JSON, default=list)


# ---------------------------------------------------------------- exams
class Exam(Base, TenantMixin, TimestampMixin):
    __tablename__ = "exams"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    campus_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("campuses.id"), index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("subjects.id"))
    grade_level: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    exam_date: Mapped[date] = mapped_column(Date)
    status: Mapped[ExamStatus] = mapped_column(Enum(ExamStatus, name="exam_status"), default=ExamStatus.DRAFT)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    booklet_file_key: Mapped[str | None] = mapped_column(String(500))
    answer_key_file_key: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    classes: Mapped[list["ExamClass"]] = relationship(cascade="all, delete-orphan")
    questions: Mapped[list["ExamQuestion"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestion.position"
    )


class ExamClass(Base):
    __tablename__ = "exam_classes"
    exam_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("exams.id", ondelete="CASCADE"), primary_key=True)
    class_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("classes.id"), primary_key=True)


class Question(Base, TenantMixin, TimestampMixin):
    """Question-bank item. Can be reused across exams."""

    __tablename__ = "questions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("subjects.id"))
    stem_text: Mapped[str] = mapped_column(Text)
    answer_type: Mapped[AnswerType] = mapped_column(Enum(AnswerType, name="answer_type"))
    options: Mapped[dict | None] = mapped_column(JSON)  # {"A": "...", "B": "..."}
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_bbox: Mapped[list | None] = mapped_column(JSON)  # [x0,y0,x1,y1] normalized 0..1
    extraction_confidence: Mapped[float | None] = mapped_column(Float)


class QuestionOutcomeMapping(Base):
    __tablename__ = "question_outcome_mappings"
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    learning_outcome_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("learning_outcomes.id"), primary_key=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    validated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))


class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    __table_args__ = (UniqueConstraint("exam_id", "position"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("exams.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("questions.id"))
    position: Mapped[int] = mapped_column(Integer)
    points: Mapped[float] = mapped_column(Float, default=1.0)
    exam: Mapped[Exam] = relationship(back_populates="questions")
    question: Mapped[Question] = relationship(lazy="joined")
    answer_key: Mapped["AnswerKey | None"] = relationship(
        back_populates="exam_question", uselist=False, cascade="all, delete-orphan"
    )


class AnswerKey(Base, TimestampMixin):
    __tablename__ = "answer_keys"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    exam_question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exam_questions.id", ondelete="CASCADE"), unique=True
    )
    correct_answer: Mapped[str] = mapped_column(String(500))
    # validated reference solution steps, e.g. ["3*x + 5 = 20", "3*x = 15", "x = 5"]
    reference_steps: Mapped[list] = mapped_column(JSON, default=list)
    validated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exam_question: Mapped[ExamQuestion] = relationship(back_populates="answer_key")


# ---------------------------------------------------------------- submissions & processing
class StudentSubmission(Base, TenantMixin, TimestampMixin):
    __tablename__ = "student_submissions"
    __table_args__ = (Index("ix_submission_exam_student", "exam_id", "student_id"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("exams.id", ondelete="CASCADE"))
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("students.id"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    total_score: Mapped[float | None] = mapped_column(Float)
    max_score: Mapped[float | None] = mapped_column(Float)
    files: Mapped[list["SubmissionFile"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan", order_by="SubmissionFile.page_order"
    )
    job: Mapped["ProcessingJob | None"] = relationship(
        back_populates="submission", uselist=False, cascade="all, delete-orphan"
    )
    responses: Mapped[list["StudentResponse"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class SubmissionFile(Base):
    __tablename__ = "submission_files"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("student_submissions.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(500))
    original_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    page_order: Mapped[int] = mapped_column(Integer, default=0)
    malware_scan: Mapped[str] = mapped_column(String(30), default="not_scanned")  # clean|infected|not_scanned
    submission: Mapped[StudentSubmission] = relationship(back_populates="files")


class ProcessingJob(Base, TenantMixin, TimestampMixin):
    __tablename__ = "processing_jobs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("student_submissions.id", ondelete="CASCADE"), unique=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status"), default=JobStatus.UPLOADED, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)  # Turkish, user-facing
    log: Mapped[list] = mapped_column(JSON, default=list)  # [{at, status, note}]
    provider_name: Mapped[str | None] = mapped_column(String(80))
    provider_is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    submission: Mapped[StudentSubmission] = relationship(back_populates="job")


class StudentResponse(Base, TenantMixin, TimestampMixin):
    __tablename__ = "student_responses"
    __table_args__ = (UniqueConstraint("submission_id", "exam_question_id"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("student_submissions.id", ondelete="CASCADE"), index=True)
    exam_question_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("exam_questions.id"), index=True)
    final_answer: Mapped[str | None] = mapped_column(String(500))
    answer_confidence: Mapped[float | None] = mapped_column(Float)  # recognition confidence
    is_correct: Mapped[bool | None] = mapped_column(Boolean)  # None = could not determine
    score: Mapped[float | None] = mapped_column(Float)
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_bbox: Mapped[list | None] = mapped_column(JSON)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reason: Mapped[str | None] = mapped_column(Text)
    transcription_source: Mapped[str] = mapped_column(String(30), default="ai")  # ai | teacher
    submission: Mapped[StudentSubmission] = relationship(back_populates="responses")
    exam_question: Mapped[ExamQuestion] = relationship()
    steps: Mapped[list["SolutionStep"]] = relationship(
        back_populates="response", cascade="all, delete-orphan", order_by="SolutionStep.step_index"
    )
    hypotheses: Mapped[list["ErrorHypothesis"]] = relationship(
        back_populates="response", cascade="all, delete-orphan"
    )


class SolutionStep(Base):
    __tablename__ = "solution_steps"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("student_responses.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int] = mapped_column(Integer)
    raw_text: Mapped[str] = mapped_column(Text)  # as recognized
    normalized_expr: Mapped[str | None] = mapped_column(Text)  # SymPy-parsable
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    is_crossed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    page: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[list | None] = mapped_column(JSON)
    verdict: Mapped[StepVerdict] = mapped_column(Enum(StepVerdict, name="step_verdict"), default=StepVerdict.NOT_CHECKED)
    verdict_detail: Mapped[str | None] = mapped_column(Text)
    edited_by_teacher: Mapped[bool] = mapped_column(Boolean, default=False)
    response: Mapped[StudentResponse] = relationship(back_populates="steps")


class ErrorHypothesis(Base, TenantMixin, TimestampMixin):
    __tablename__ = "error_hypotheses"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("student_responses.id", ondelete="CASCADE"), index=True)
    category: Mapped[ErrorCategory] = mapped_column(Enum(ErrorCategory, name="error_category"), index=True)
    detector: Mapped[str] = mapped_column(String(80))  # which rule produced it
    observed_error: Mapped[str] = mapped_column(Text)  # what is visible on paper (TR)
    inferred_cause: Mapped[str] = mapped_column(Text)  # hypothesis (TR), never a diagnosis
    alternative_explanations: Mapped[list] = mapped_column(JSON, default=list)
    diagnostic_questions: Mapped[list] = mapped_column(JSON, default=list)
    raw_confidence: Mapped[float] = mapped_column(Float)
    calibrated_confidence: Mapped[float] = mapped_column(Float)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_explanation: Mapped[str | None] = mapped_column(Text)  # never treated as verified
    llm_explanation_is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus, name="review_status"), default=ReviewStatus.PENDING, index=True)
    engine_version: Mapped[str] = mapped_column(String(20))
    response: Mapped[StudentResponse] = relationship(back_populates="hypotheses")
    evidence: Mapped[list["EvidenceItem"]] = relationship(back_populates="hypothesis", cascade="all, delete-orphan")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    hypothesis_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("error_hypotheses.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))  # step_transition | final_answer | missing_work | ocr
    description: Mapped[str] = mapped_column(Text)
    step_index: Mapped[int | None] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[list | None] = mapped_column(JSON)
    verified_by: Mapped[str] = mapped_column(String(30))  # sympy | rule | ocr | llm_unverified
    hypothesis: Mapped[ErrorHypothesis] = relationship(back_populates="evidence")


class TeacherReview(Base, TenantMixin):
    __tablename__ = "teacher_reviews"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    hypothesis_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("error_hypotheses.id", ondelete="SET NULL"), index=True)
    response_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("student_responses.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    action: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus, name="review_status"))
    original_category: Mapped[ErrorCategory | None] = mapped_column(Enum(ErrorCategory, name="error_category"))
    corrected_category: Mapped[ErrorCategory | None] = mapped_column(Enum(ErrorCategory, name="error_category"))
    detector: Mapped[str | None] = mapped_column(String(80))  # copied for calibration stats
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
