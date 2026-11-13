"""'Yeni Öğrenci Yükle' — student submission upload, bulk upload, job status, retry, file serving."""
from __future__ import annotations

import re
import uuid
from collections import defaultdict

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.serializers import submission_out
from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import CurrentUser, ensure_exam_access, require
from app.models import (
    Exam,
    ExamClass,
    ExamStatus,
    JobStatus,
    ProcessingJob,
    Student,
    StudentSubmission,
    SubmissionFile,
)
from app.schemas import StudentOut, SubmissionOut, UploadResultOut
from app.services import pipeline
from app.services.audit import audit
from app.services.storage import UploadRejected, get_storage, scan_for_malware, suffix_for, validate_upload
from app.workers.tasks import dispatch_processing

router = APIRouter(tags=["submissions"])
MAX_FILES_PER_STUDENT = 30
MAX_FILES_BULK = 300


def _exam_students(db: Session, exam: Exam) -> dict[uuid.UUID, Student]:
    cls = select(ExamClass.class_id).where(ExamClass.exam_id == exam.id)
    return {s.id: s for s in db.execute(select(Student).where(
        Student.class_id.in_(cls), Student.organization_id == exam.organization_id)).scalars()}


async def _create_submission(db: Session, user: CurrentUser, exam: Exam, student: Student,
                             files: list[UploadFile]) -> StudentSubmission:
    s = get_settings()
    storage = get_storage(s)
    sub = StudentSubmission(organization_id=exam.organization_id, exam_id=exam.id, student_id=student.id,
                            uploaded_by=user.id)
    for i, f in enumerate(files):
        try:
            vf = validate_upload(await f.read(), f.filename or f"sayfa_{i + 1}", s,
                                 allow_json_fixture=s.env == "development")
        except UploadRejected as e:
            raise HTTPException(422, e.message_tr) from e
        try:
            scan = scan_for_malware(vf.data, s)
        except OSError:
            raise HTTPException(503, "Virüs tarama servisine ulaşılamadı; dosya kabul edilmedi.") from None
        if scan == "infected":
            audit(db, org_id=user.organization_id, actor_id=user.id, action="upload_malware_blocked",
                  entity_type="exam", entity_id=exam.id, sha256=vf.sha256)
            db.commit()
            raise HTTPException(422, f"'{vf.original_name}' dosyasında zararlı yazılım tespit edildi.")
        key = storage.put(exam.organization_id, vf.data, suffix_for(vf.mime_type))
        sub.files.append(SubmissionFile(storage_key=key, original_name=vf.original_name, mime_type=vf.mime_type,
                                        size_bytes=len(vf.data), sha256=vf.sha256, page_order=i, malware_scan=scan))
    sub.job = ProcessingJob(organization_id=exam.organization_id, log=[], status=JobStatus.UPLOADED, attempts=0)
    pipeline._log(sub.job, JobStatus.UPLOADED, f"{len(files)} dosya yüklendi")
    db.add(sub)
    db.flush()
    pipeline.mark_queued(sub.job)
    return sub


def _require_published(exam: Exam) -> None:
    if exam.status != ExamStatus.PUBLISHED:
        raise HTTPException(409, "Öğrenci kâğıdı yüklemek için önce sınavı doğrulayıp yayımlayın.")


@router.post("/exams/{exam_id}/submissions", response_model=SubmissionOut, status_code=201)
async def upload_submission(
    exam_id: uuid.UUID, background: BackgroundTasks, student_id: uuid.UUID = Form(...),
    files: list[UploadFile] = File(...), user: CurrentUser = Depends(require("submission:upload")),
    db: Session = Depends(get_db),
):
    exam = ensure_exam_access(db, user, db.get(Exam, exam_id))
    _require_published(exam)
    if not 1 <= len(files) <= MAX_FILES_PER_STUDENT:
        raise HTTPException(422, f"Öğrenci başına 1–{MAX_FILES_PER_STUDENT} dosya yüklenebilir.")
    student = _exam_students(db, exam).get(student_id)
    if student is None:
        raise HTTPException(422, "Öğrenci bu sınavın sınıflarında kayıtlı değil.")
    sub = await _create_submission(db, user, exam, student, files)
    audit(db, org_id=user.organization_id, actor_id=user.id, action="submission_upload", entity_type="submission",
          entity_id=sub.id, files=len(files))
    db.commit()
    dispatch_processing(sub.id, background)
    db.refresh(sub)
    return submission_out(sub, student)


@router.post("/exams/{exam_id}/submissions/bulk", response_model=UploadResultOut, status_code=201)
async def bulk_upload(exam_id: uuid.UUID, background: BackgroundTasks, files: list[UploadFile] = File(...),
                      user: CurrentUser = Depends(require("submission:upload")), db: Session = Depends(get_db)):
    """Bulk: file names must start with the student number, e.g. '1024_s1.jpg', '1024-sayfa2.png', '1031.pdf'."""
    exam = ensure_exam_access(db, user, db.get(Exam, exam_id))
    _require_published(exam)
    if len(files) > MAX_FILES_BULK:
        raise HTTPException(422, f"Toplu yüklemede en fazla {MAX_FILES_BULK} dosya gönderilebilir.")
    by_number = {s.student_number: s for s in _exam_students(db, exam).values()}
    groups: dict[str, list[UploadFile]] = defaultdict(list)
    errors: list[str] = []
    for f in files:
        m = re.match(r"^(\d+)", f.filename or "")
        if not m or m.group(1) not in by_number:
            errors.append(f"'{f.filename}': dosya adındaki öğrenci numarası bu sınavın sınıflarında bulunamadı.")
            continue
        groups[m.group(1)].append(f)
    created: list[tuple[StudentSubmission, Student]] = []
    for number, fl in groups.items():
        fl.sort(key=lambda x: x.filename or "")
        try:
            created.append((await _create_submission(db, user, exam, by_number[number], fl), by_number[number]))
        except HTTPException as e:
            errors.append(f"{number}: {e.detail}")
    audit(db, org_id=user.organization_id, actor_id=user.id, action="submission_bulk_upload", entity_type="exam",
          entity_id=exam.id, created=len(created), errors=len(errors))
    db.commit()
    for sub, _ in created:
        dispatch_processing(sub.id, background)
    return UploadResultOut(created=[submission_out(sub, st) for sub, st in created], errors=errors)


@router.get("/exams/{exam_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(exam_id: uuid.UUID, user: CurrentUser = Depends(require("exam:read")), db: Session = Depends(get_db)):
    exam = ensure_exam_access(db, user, db.get(Exam, exam_id))
    subs = db.execute(select(StudentSubmission).where(StudentSubmission.exam_id == exam.id)
                      .options(selectinload(StudentSubmission.files), selectinload(StudentSubmission.job),
                               selectinload(StudentSubmission.responses))
                      .order_by(StudentSubmission.created_at.desc())).scalars().all()
    students = {s.id: s for s in db.execute(select(Student).where(Student.id.in_([x.student_id for x in subs]))).scalars()}
    return [submission_out(s, students[s.student_id]) for s in subs]


@router.get("/exams/{exam_id}/students", response_model=list[StudentOut])
def exam_students(exam_id: uuid.UUID, user: CurrentUser = Depends(require("exam:read")), db: Session = Depends(get_db)):
    exam = ensure_exam_access(db, user, db.get(Exam, exam_id))
    return sorted((StudentOut.model_validate(s) for s in _exam_students(db, exam).values()), key=lambda s: s.full_name)


def _load_submission(db: Session, user: CurrentUser, submission_id: uuid.UUID) -> StudentSubmission:
    sub = db.get(StudentSubmission, submission_id)
    if sub is None or sub.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kayıt bulunamadı.")
    ensure_exam_access(db, user, db.get(Exam, sub.exam_id))
    return sub


@router.post("/submissions/{submission_id}/retry", response_model=SubmissionOut)
def retry(submission_id: uuid.UUID, background: BackgroundTasks,
          user: CurrentUser = Depends(require("submission:upload")), db: Session = Depends(get_db)):
    sub = _load_submission(db, user, submission_id)
    try:
        pipeline.mark_queued(sub.job)
    except ValueError:
        raise HTTPException(409, "Bu iş şu anda yeniden denenemez (işleniyor veya tamamlandı).") from None
    audit(db, org_id=user.organization_id, actor_id=user.id, action="submission_retry", entity_type="submission", entity_id=sub.id)
    db.commit()
    dispatch_processing(sub.id, background)
    db.refresh(sub)
    return submission_out(sub, db.get(Student, sub.student_id))


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: uuid.UUID, user: CurrentUser = Depends(require("exam:read")), db: Session = Depends(get_db)):
    sub = _load_submission(db, user, submission_id)
    return submission_out(sub, db.get(Student, sub.student_id))


@router.get("/files/{file_id}")
def get_file(file_id: uuid.UUID, user: CurrentUser = Depends(require("exam:read")), db: Session = Depends(get_db)):
    f = db.get(SubmissionFile, file_id)
    if f is None:
        raise HTTPException(404, "Dosya bulunamadı.")
    _load_submission(db, user, f.submission_id)
    if f.malware_scan == "infected":
        raise HTTPException(403, "Bu dosya güvenlik nedeniyle engellendi.")
    data = get_storage(get_settings()).get(f.storage_key)
    return Response(data, media_type=f.mime_type, headers={
        "Content-Disposition": "inline", "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
