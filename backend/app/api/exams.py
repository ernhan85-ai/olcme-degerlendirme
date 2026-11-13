"""Exam management: create, questions/answer keys/outcome mapping, booklet upload, validate, publish."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import CurrentUser, ensure_exam_access, require, teacher_class_ids
from app.models import (
    AnswerKey,
    AnswerType,
    Exam,
    ExamClass,
    ExamQuestion,
    ExamStatus,
    LearningOutcome,
    Question,
    QuestionOutcomeMapping,
    RoleName,
    SchoolClass,
    Subject,
)
from app.schemas import ExamCreate, ExamDetailOut, ExamOut, QuestionIn
from app.api.serializers import exam_out
from app.services import math_verify as mv
from app.services.audit import audit
from app.services.storage import UploadRejected, get_storage, suffix_for, validate_upload

router = APIRouter(prefix="/exams", tags=["exams"])


def _load(db: Session, user: CurrentUser, exam_id: uuid.UUID) -> Exam:
    return ensure_exam_access(db, user, db.get(Exam, exam_id))


def _check_editable(exam: Exam) -> None:
    if exam.status in (ExamStatus.PUBLISHED, ExamStatus.ARCHIVED):
        raise HTTPException(status.HTTP_409_CONFLICT, "Yayımlanmış sınavın soruları değiştirilemez.")


def _validate_answer(q: QuestionIn) -> None:
    if q.answer_type == AnswerType.MULTIPLE_CHOICE:
        if not q.options or q.correct_answer.upper()[:1] not in {k.upper() for k in q.options}:
            raise HTTPException(422, f"{q.position}. soru: doğru seçenek, seçenekler arasında olmalı.")
    elif q.answer_type in (AnswerType.NUMERIC, AnswerType.EXPRESSION, AnswerType.EQUATION):
        if mv.try_parse(q.correct_answer) is None:
            raise HTTPException(422, f"{q.position}. soru: cevap anahtarı matematiksel olarak okunamadı ({q.correct_answer}).")
        for i, st in enumerate(q.reference_steps):
            if mv.try_parse(st) is None:
                raise HTTPException(422, f"{q.position}. soru, referans adım {i + 1} okunamadı: {st}")
        parsed = [mv.parse_math(s) for s in q.reference_steps]
        for i in range(1, len(parsed)):
            if mv.equivalent(parsed[i - 1], parsed[i]) is False:
                raise HTTPException(422, f"{q.position}. soru: referans adım {i + 1}, önceki adımla denk değil.")
        if parsed and mv.answers_match(q.reference_steps[-1], q.correct_answer, q.answer_type.value) is False:
            raise HTTPException(422, f"{q.position}. soru: referans çözümün son adımı cevap anahtarıyla uyuşmuyor.")


def _replace_questions(db: Session, user: CurrentUser, exam: Exam, questions: list[QuestionIn]) -> None:
    positions = [q.position for q in questions]
    if len(positions) != len(set(positions)):
        raise HTTPException(422, "Soru numaraları tekrar ediyor.")
    outcome_ids = {o for q in questions for o in q.outcome_ids}
    if outcome_ids:
        found = set(db.execute(select(LearningOutcome.id).where(
            LearningOutcome.id.in_(outcome_ids), LearningOutcome.organization_id == user.organization_id)).scalars())
        if found != outcome_ids:
            raise HTTPException(422, "Geçersiz kazanım seçildi.")
    for q in questions:
        _validate_answer(q)
    for eq in list(exam.questions):
        exam.questions.remove(eq)
    db.flush()
    for q in sorted(questions, key=lambda x: x.position):
        bank = Question(organization_id=exam.organization_id, subject_id=exam.subject_id, stem_text=q.stem_text,
                        answer_type=q.answer_type, options=q.options)
        db.add(bank)
        db.flush()
        for oid in q.outcome_ids:
            db.add(QuestionOutcomeMapping(question_id=bank.id, learning_outcome_id=oid))
        eq = ExamQuestion(question=bank, position=q.position, points=q.points,
                          answer_key=AnswerKey(correct_answer=q.correct_answer, reference_steps=q.reference_steps))
        exam.questions.append(eq)
    exam.status = ExamStatus.IN_REVIEW


@router.get("", response_model=list[ExamOut])
def list_exams(
    user: CurrentUser = Depends(require("exam:read")), db: Session = Depends(get_db),
    grade_level: int | None = None, subject_id: uuid.UUID | None = None, class_id: uuid.UUID | None = None,
    status_: ExamStatus | None = Query(None, alias="status"),
) -> list[ExamOut]:
    q = select(Exam).where(Exam.organization_id == user.organization_id)
    if not user.is_org_wide:
        if user.has(RoleName.CAMPUS_ADMIN):
            q = q.where(Exam.campus_id.in_(user.campus_ids))
        else:
            cls = teacher_class_ids(db, user)
            q = q.where((Exam.created_by == user.id) | Exam.id.in_(
                select(ExamClass.exam_id).where(ExamClass.class_id.in_(cls))))
    if grade_level:
        q = q.where(Exam.grade_level == grade_level)
    if subject_id:
        q = q.where(Exam.subject_id == subject_id)
    if class_id:
        q = q.where(Exam.id.in_(select(ExamClass.exam_id).where(ExamClass.class_id == class_id)))
    if status_:
        q = q.where(Exam.status == status_)
    return [exam_out(db, e) for e in db.execute(q.order_by(Exam.exam_date.desc())).scalars()]


@router.post("", response_model=ExamDetailOut, status_code=201)
def create_exam(body: ExamCreate, user: CurrentUser = Depends(require("exam:write")),
                db: Session = Depends(get_db)) -> ExamDetailOut:
    subject = db.get(Subject, body.subject_id)
    if subject is None or subject.organization_id != user.organization_id:
        raise HTTPException(422, "Geçersiz ders.")
    classes = db.execute(select(SchoolClass).where(SchoolClass.id.in_(body.class_ids),
                                                   SchoolClass.organization_id == user.organization_id)).scalars().all()
    if len(classes) != len(set(body.class_ids)):
        raise HTTPException(422, "Geçersiz sınıf seçildi.")
    if len({c.campus_id for c in classes}) != 1:
        raise HTTPException(422, "Bir sınav yalnızca tek bir kampüsün sınıflarına atanabilir.")
    if any(c.grade_level != body.grade_level for c in classes):
        raise HTTPException(422, "Seçilen sınıfların sınıf düzeyi sınav düzeyiyle aynı olmalı.")
    if not user.is_org_wide and not user.has(RoleName.CAMPUS_ADMIN):
        if not set(body.class_ids) <= teacher_class_ids(db, user):
            raise HTTPException(403, "Yalnızca size atanmış sınıflar için sınav oluşturabilirsiniz.")
    exam = Exam(organization_id=user.organization_id, campus_id=classes[0].campus_id, subject_id=body.subject_id,
                grade_level=body.grade_level, title=body.title, exam_date=body.exam_date, created_by=user.id,
                classes=[ExamClass(class_id=c.id) for c in classes])
    db.add(exam)
    db.flush()
    if body.questions:
        _replace_questions(db, user, exam, body.questions)
    audit(db, org_id=user.organization_id, actor_id=user.id, action="exam_create", entity_type="exam", entity_id=exam.id)
    db.commit()
    db.refresh(exam)
    return exam_out(db, exam, detail=True)


@router.get("/{exam_id}", response_model=ExamDetailOut)
def get_exam(exam_id: uuid.UUID, user: CurrentUser = Depends(require("exam:read")), db: Session = Depends(get_db)):
    return exam_out(db, _load(db, user, exam_id), detail=True)


@router.put("/{exam_id}/questions", response_model=ExamDetailOut)
def put_questions(exam_id: uuid.UUID, body: list[QuestionIn], user: CurrentUser = Depends(require("exam:write")),
                  db: Session = Depends(get_db)):
    exam = _load(db, user, exam_id)
    _check_editable(exam)
    _replace_questions(db, user, exam, body)
    audit(db, org_id=user.organization_id, actor_id=user.id, action="exam_questions_replace", entity_type="exam",
          entity_id=exam.id, count=len(body))
    db.commit()
    db.refresh(exam)
    return exam_out(db, exam, detail=True)


CSV_COLUMNS = ["position", "answer_type", "stem_text", "correct_answer", "points", "outcome_codes", "reference_steps", "options"]


@router.post("/{exam_id}/questions/import-csv", response_model=ExamDetailOut)
async def import_questions_csv(exam_id: uuid.UUID, file: UploadFile = File(...),
                               user: CurrentUser = Depends(require("exam:write")), db: Session = Depends(get_db)):
    """CSV (UTF-8, ';' or ','): position;answer_type;stem_text;correct_answer;points;outcome_codes;reference_steps;options
    outcome_codes and reference_steps are '|' separated. options: A=..|B=..|C=..|D=.."""
    exam = _load(db, user, exam_id)
    _check_editable(exam)
    raw = (await file.read())[: 2 * 1024 * 1024].decode("utf-8-sig", errors="replace")
    dialect = csv.Sniffer().sniff(raw.splitlines()[0], delimiters=";,") if raw.strip() else csv.excel
    rows = list(csv.DictReader(io.StringIO(raw), dialect=dialect))
    codes = {o.code: o.id for o in db.execute(select(LearningOutcome).where(
        LearningOutcome.organization_id == user.organization_id)).scalars()}
    out: list[QuestionIn] = []
    for n, r in enumerate(rows, start=2):
        try:
            oc = [c.strip() for c in (r.get("outcome_codes") or "").split("|") if c.strip()]
            missing = [c for c in oc if c not in codes]
            if missing:
                raise ValueError(f"bilinmeyen kazanım kodu: {', '.join(missing)}")
            opts = None
            if r.get("options"):
                opts = dict(p.split("=", 1) for p in r["options"].split("|") if "=" in p)
            out.append(QuestionIn(
                position=int(r["position"]), answer_type=AnswerType(r["answer_type"].strip()),
                stem_text=r["stem_text"], correct_answer=r["correct_answer"], points=float(r.get("points") or 1),
                outcome_ids=[codes[c] for c in oc], options=opts,
                reference_steps=[s.strip() for s in (r.get("reference_steps") or "").split("|") if s.strip()],
            ))
        except (KeyError, ValueError) as e:
            raise HTTPException(422, f"CSV satır {n}: {e}") from e
    _replace_questions(db, user, exam, out)
    audit(db, org_id=user.organization_id, actor_id=user.id, action="exam_questions_import_csv", entity_type="exam",
          entity_id=exam.id, count=len(out))
    db.commit()
    db.refresh(exam)
    return exam_out(db, exam, detail=True)


@router.post("/{exam_id}/booklet", response_model=ExamDetailOut)
async def upload_booklet(exam_id: uuid.UUID, kind: str = Query("booklet", pattern="^(booklet|answer_key)$"),
                         file: UploadFile = File(...), user: CurrentUser = Depends(require("exam:write")),
                         db: Session = Depends(get_db)):
    s = get_settings()
    exam = _load(db, user, exam_id)
    try:
        vf = validate_upload(await file.read(), file.filename or "kitapcik.pdf", s)
    except UploadRejected as e:
        raise HTTPException(422, e.message_tr) from e
    if vf.mime_type != "application/pdf":
        raise HTTPException(422, "Sınav kitapçığı ve cevap anahtarı PDF olmalıdır.")
    key = get_storage(s).put(user.organization_id, vf.data, suffix_for(vf.mime_type))
    if kind == "booklet":
        exam.booklet_file_key = key
    else:
        exam.answer_key_file_key = key
    audit(db, org_id=user.organization_id, actor_id=user.id, action=f"exam_{kind}_upload", entity_type="exam",
          entity_id=exam.id, sha256=vf.sha256)
    db.commit()
    db.refresh(exam)
    return exam_out(db, exam, detail=True)


@router.post("/{exam_id}/validate-keys", response_model=ExamDetailOut)
def validate_keys(exam_id: uuid.UUID, user: CurrentUser = Depends(require("exam:write")), db: Session = Depends(get_db)):
    """Teacher confirms that answer keys and outcome mappings were reviewed."""
    exam = _load(db, user, exam_id)
    _check_editable(exam)
    now = datetime.now(UTC)
    for eq in exam.questions:
        if eq.answer_key:
            eq.answer_key.validated_by, eq.answer_key.validated_at = user.id, now
        for m in db.execute(select(QuestionOutcomeMapping).where(QuestionOutcomeMapping.question_id == eq.question_id)).scalars():
            m.validated_by = user.id
    audit(db, org_id=user.organization_id, actor_id=user.id, action="exam_keys_validated", entity_type="exam", entity_id=exam.id)
    db.commit()
    db.refresh(exam)
    return exam_out(db, exam, detail=True)


@router.post("/{exam_id}/publish", response_model=ExamDetailOut)
def publish(exam_id: uuid.UUID, user: CurrentUser = Depends(require("exam:publish")), db: Session = Depends(get_db)):
    exam = _load(db, user, exam_id)
    detail = exam_out(db, exam, detail=True)
    hard = [b for b in detail.publish_blockers if "referans çözüm" not in b]  # missing ref steps = warning only
    if hard:
        raise HTTPException(409, {"message": "Sınav yayımlanamaz.", "blockers": hard})
    exam.status, exam.published_at = ExamStatus.PUBLISHED, datetime.now(UTC)
    audit(db, org_id=user.organization_id, actor_id=user.id, action="exam_publish", entity_type="exam", entity_id=exam.id)
    db.commit()
    db.refresh(exam)
    return exam_out(db, exam, detail=True)
