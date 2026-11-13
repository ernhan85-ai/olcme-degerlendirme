from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AnswerType,
    Exam,
    ExamClass,
    ExamQuestion,
    QuestionOutcomeMapping,
    StudentResponse,
    StudentSubmission,
    Subject,
)
from app.schemas import ExamDetailOut, ExamOut, JobOut, QuestionOut, StudentOut, SubmissionFileOut, SubmissionOut


def question_out(db: Session, eq: ExamQuestion) -> QuestionOut:
    outcome_ids = list(db.execute(select(QuestionOutcomeMapping.learning_outcome_id)
                                  .where(QuestionOutcomeMapping.question_id == eq.question_id)).scalars())
    k = eq.answer_key
    return QuestionOut(
        exam_question_id=eq.id, question_id=eq.question_id, position=eq.position, points=eq.points,
        stem_text=eq.question.stem_text, answer_type=eq.question.answer_type, options=eq.question.options,
        correct_answer=k.correct_answer if k else None, reference_steps=list(k.reference_steps or []) if k else [],
        key_validated=bool(k and k.validated_at), outcome_ids=outcome_ids,
    )


def publish_blockers(db: Session, exam: Exam, questions: list[QuestionOut]) -> list[str]:
    b: list[str] = []
    if not questions:
        b.append("Sınavda hiç soru yok.")
    for q in questions:
        if q.correct_answer is None:
            b.append(f"{q.position}. sorunun cevap anahtarı yok.")
        elif not q.key_validated:
            b.append(f"{q.position}. sorunun cevap anahtarı öğretmen tarafından doğrulanmadı.")
        if not q.outcome_ids:
            b.append(f"{q.position}. soru bir kazanımla eşleştirilmedi.")
        if q.answer_type in (AnswerType.EQUATION, AnswerType.EXPRESSION) and not q.reference_steps:
            b.append(f"{q.position}. soru için referans çözüm adımları girilmedi (hata analizi sınırlı kalır).")
    return b


def exam_out(db: Session, exam: Exam, detail: bool = False) -> ExamOut | ExamDetailOut:
    class_ids = list(db.execute(select(ExamClass.class_id).where(ExamClass.exam_id == exam.id)).scalars())
    sub_count = db.scalar(select(func.count()).select_from(StudentSubmission).where(StudentSubmission.exam_id == exam.id)) or 0
    pending = db.scalar(
        select(func.count()).select_from(StudentResponse).join(StudentSubmission)
        .where(StudentSubmission.exam_id == exam.id, StudentResponse.needs_review.is_(True))
    ) or 0
    subject = db.get(Subject, exam.subject_id)
    base = dict(id=exam.id, title=exam.title, subject_id=exam.subject_id, subject_name=subject.name if subject else None,
                grade_level=exam.grade_level, class_ids=class_ids, exam_date=exam.exam_date, status=exam.status,
                has_booklet=bool(exam.booklet_file_key), question_count=len(exam.questions),
                submission_count=sub_count, pending_review_count=pending, created_at=exam.created_at)
    if not detail:
        return ExamOut(**base)
    qs = [question_out(db, eq) for eq in exam.questions]
    return ExamDetailOut(**base, questions=qs, publish_blockers=publish_blockers(db, exam, qs))


def submission_out(sub: StudentSubmission, student) -> SubmissionOut:
    return SubmissionOut(
        id=sub.id, exam_id=sub.exam_id, student=StudentOut.model_validate(student),
        total_score=sub.total_score, max_score=sub.max_score,
        job=JobOut.model_validate(sub.job) if sub.job else None,
        files=[SubmissionFileOut.model_validate(f) for f in sub.files],
        needs_review_count=sum(1 for r in sub.responses if r.needs_review),
        created_at=sub.created_at,
    )
