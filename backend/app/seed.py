"""Synthetic demo data (NO real student data). Run: python -m app.seed

Creates BCN College demo org, a 7th-grade math exam with 5 questions, 24 synthetic students,
and processes their (synthetic) transcripts through the full pipeline using the mock provider.
Learning outcome codes follow the MEB pattern but must be verified against the official program.
"""
from __future__ import annotations

import json
import random
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import (
    AnswerKey,
    AnswerType,
    Campus,
    Exam,
    ExamClass,
    ExamQuestion,
    ExamStatus,
    LearningOutcome,
    Organization,
    ProcessingJob,
    Question,
    QuestionOutcomeMapping,
    RoleName,
    SchoolClass,
    Student,
    StudentSubmission,
    Subject,
    SubmissionFile,
    TeacherAssignment,
    User,
    UserRole,
)
from app.services import pipeline
from app.services.storage import get_storage

DEMO_PASSWORD = "Demo123!"  # synthetic accounts only

FIRST = ["Ada", "Ayşe", "Ali", "Mehmet", "Zeynep", "Elif", "Can", "Deniz", "Ece", "Emre", "Selin", "Kerem",
         "Defne", "Yusuf", "Nehir", "Berk", "Duru", "Arda", "Ela", "Mert", "Irmak", "Efe", "Lina", "Kaan"]
LAST = ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Aydın", "Öztürk", "Arslan", "Doğan", "Kılıç", "Aslan"]

# (position, type, stem, key, points, ref_steps, options, outcome_code)
QUESTIONS = [
    (1, AnswerType.EQUATION, "3x + 5 = 20 denklemini çözünüz.", "x=5", 20,
     ["3x+5=20", "3x=15", "x=5"], None, "M.7.2.2.2"),
    (2, AnswerType.EQUATION, "2(x + 3) = 10 denklemini çözünüz.", "x=2", 20,
     ["2(x+3)=10", "2x+6=10", "2x=4", "x=2"], None, "M.7.2.2.2"),
    (3, AnswerType.NUMERIC, "1/2 + 1/3 işleminin sonucunu bulunuz.", "5/6", 20,
     ["1/2+1/3", "3/6+2/6", "5/6"], None, "M.7.1.3.1"),
    (4, AnswerType.MULTIPLE_CHOICE, "4x - 7 = 9 denkleminin çözümü hangisidir?", "C", 20, [],
     {"A": {"text": "x = 1/2", "misconception": "incorrect_procedure", "note": "Sabit terim yanlış işaretle aktarılmış olabilir."},
      "B": {"text": "x = 2", "misconception": "arithmetic_error", "note": "16/4 hesaplamasında hata olabilir."},
      "C": {"text": "x = 4"}, "D": {"text": "x = 64", "misconception": "incorrect_procedure", "note": "Bölme yerine çarpma yapılmış olabilir."}},
     "M.7.2.2.2"),
    (5, AnswerType.EXPRESSION, "3(a - 2) + 4a ifadesini sadeleştiriniz.", "7a-6", 20,
     ["3(a-2)+4a", "3a-6+4a", "7a-6"], None, "M.7.2.1.2"),
]

OUTCOMES = [
    ("M.7.1.3.1", "Rasyonel sayılarla toplama ve çıkarma işlemlerini yapar.", []),
    ("M.7.2.1.2", "Cebirsel ifadelerde toplama ve çıkarma işlemlerini yapar, sadeleştirir.", []),
    ("M.7.2.2.2", "Birinci dereceden bir bilinmeyenli denklemleri çözer.", ["M.7.1.3.1"]),
]

# synthetic student work patterns per question: (final_answer, steps)
PATTERNS = {
    1: [("x=5", ["3x+5=20", "3x=15", "x=5"]), ("x=25/3", ["3x+5=20", "3x=20+5", "3x=25", "x=25/3"]),
        ("x=6", ["3x+5=20", "3x=15", "x=6"]), ("x=12", ["3x+5=20", "3x=15", "x=15-3"]), (None, ["3x+5=20", "3x=15"])],
    2: [("x=2", ["2(x+3)=10", "2x+6=10", "2x=4", "x=2"]), ("x=7/2", ["2(x+3)=10", "2x+3=10", "2x=7", "x=7/2"]),
        ("x=8", ["2(x+3)=10", "2x+6=10", "2x=4", "x=8"])],
    3: [("5/6", ["1/2+1/3", "3/6+2/6", "5/6"]), ("2/5", ["1/2+1/3", "2/5"]), ("5/6", []), ("4/6", ["1/2+1/3", "3/6+2/6", "4/6"])],
    4: [("C", []), ("A", []), ("B", []), ("D", [])],
    5: [("7a-6", ["3(a-2)+4a", "3a-6+4a", "7a-6"]), ("7a-2", ["3(a-2)+4a", "3a-2+4a", "7a-2"]),
        ("7a-6", ["3(a-2)+4a", "3a-6+4a", "7a-6"])],
}


def _transcript(rng: random.Random, ability: float) -> dict:
    responses = []
    for pos, pats in PATTERNS.items():
        correct_first = rng.random() < ability
        fa, steps = pats[0] if correct_first else rng.choice(pats[1:])
        ocr = round(rng.uniform(0.55, 0.99), 2)
        responses.append({
            "position": pos, "final_answer": fa, "answer_confidence": round(rng.uniform(0.75, 0.99), 2),
            "page": 1 + (pos - 1) // 3, "bbox": [0.08, 0.08 + 0.3 * ((pos - 1) % 3), 0.92, 0.33 + 0.3 * ((pos - 1) % 3)],
            "steps": [{"raw_text": s, "ocr_confidence": ocr, "page": 1 + (pos - 1) // 3,
                       "bbox": [0.12, 0.12 + 0.3 * ((pos - 1) % 3) + 0.045 * i, 0.6, 0.155 + 0.3 * ((pos - 1) % 3) + 0.045 * i]}
                      for i, s in enumerate(steps)],
        })
    return {"responses": responses, "warnings": []}


def seed(db: Session, *, process: bool = True, email_suffix: str = "") -> dict:
    s = get_settings()
    org = Organization(name=f"BCN College (Demo){email_suffix}")
    db.add(org)
    db.flush()
    campus = Campus(organization_id=org.id, name="Demo Kampüsü")
    math = Subject(organization_id=org.id, name="Matematik")
    db.add_all([campus, math])
    db.flush()
    c7a = SchoolClass(organization_id=org.id, campus_id=campus.id, grade_level=7, name="7-A")
    c7b = SchoolClass(organization_id=org.id, campus_id=campus.id, grade_level=7, name="7-B")
    db.add_all([c7a, c7b])
    db.flush()

    def user(email, name, *roles, campus_scoped=False):
        u = User(organization_id=org.id, email=email.replace("@", f"{email_suffix}@"), full_name=name, password_hash=hash_password(DEMO_PASSWORD),
                 roles=[UserRole(role=r, campus_id=campus.id if campus_scoped else None) for r in roles])
        db.add(u)
        return u

    teacher = user("ogretmen@demo.bcn", "Demo Öğretmen", RoleName.TEACHER, campus_scoped=True)
    other_teacher = user("ogretmen2@demo.bcn", "İkinci Öğretmen", RoleName.TEACHER, campus_scoped=True)
    user("koordinator@demo.bcn", "Demo Koordinatör", RoleName.ACADEMIC_COORDINATOR)
    user("kampus@demo.bcn", "Demo Kampüs Yöneticisi", RoleName.CAMPUS_ADMIN, campus_scoped=True)
    user("veli@demo.bcn", "Demo Veli", RoleName.PARENT)
    db.flush()
    db.add(TeacherAssignment(organization_id=org.id, teacher_user_id=teacher.id, class_id=c7a.id, subject_id=math.id))
    db.add(TeacherAssignment(organization_id=org.id, teacher_user_id=other_teacher.id, class_id=c7b.id, subject_id=math.id))

    oc = {}
    for code, desc, _ in OUTCOMES:
        o = LearningOutcome(organization_id=org.id, code=code, description=desc, grade_level=7, subject_id=math.id)
        db.add(o)
        oc[code] = o
    db.flush()
    for code, _, prereqs in OUTCOMES:
        oc[code].prerequisite_ids = [str(oc[p].id) for p in prereqs]

    exam = Exam(organization_id=org.id, campus_id=campus.id, subject_id=math.id, grade_level=7,
                title="7. Sınıf Matematik – 1. Dönem 1. Yazılı (Demo)", exam_date=date(2026, 11, 5),
                created_by=teacher.id, status=ExamStatus.PUBLISHED, published_at=datetime.now(UTC),
                classes=[ExamClass(class_id=c7a.id)])
    db.add(exam)
    db.flush()
    for pos, typ, stem, key, pts, ref, opts, code in QUESTIONS:
        q = Question(organization_id=org.id, subject_id=math.id, stem_text=stem, answer_type=typ, options=opts)
        db.add(q)
        db.flush()
        db.add(QuestionOutcomeMapping(question_id=q.id, learning_outcome_id=oc[code].id, validated_by=teacher.id))
        exam.questions.append(ExamQuestion(question=q, position=pos, points=pts, answer_key=AnswerKey(
            correct_answer=key, reference_steps=ref, validated_by=teacher.id, validated_at=datetime.now(UTC))))

    rng = random.Random(7)
    students = []
    for i in range(24):
        st = Student(organization_id=org.id, campus_id=campus.id, class_id=c7a.id if i < 20 else c7b.id,
                     student_number=str(1001 + i), full_name=f"{FIRST[i]} {LAST[i % len(LAST)]}")
        db.add(st)
        students.append(st)
    db.flush()

    sub_ids = []
    if process:
        storage = get_storage(s)
        for st in students[:20]:
            data = json.dumps(_transcript(rng, ability=rng.uniform(0.3, 0.9))).encode()
            key = storage.put(org.id, data, ".json")
            sub = StudentSubmission(organization_id=org.id, exam_id=exam.id, student_id=st.id, uploaded_by=teacher.id,
                                    files=[SubmissionFile(storage_key=key, original_name=f"{st.student_number}.transcript.json",
                                                          mime_type="application/json", size_bytes=len(data),
                                                          sha256="synthetic", malware_scan="not_scanned")],
                                    job=ProcessingJob(organization_id=org.id, log=[], attempts=0))
            db.add(sub)
            db.flush()
            pipeline.mark_queued(sub.job)
            sub_ids.append(sub.id)
        db.commit()
        for sid in sub_ids:
            pipeline.process_submission(db, sid, settings=s)
    db.commit()
    return {"org_id": org.id, "exam_id": exam.id, "teacher_id": teacher.id, "class_7a": c7a.id, "class_7b": c7b.id,
            "subject_id": math.id, "outcomes": {k: v.id for k, v in oc.items()}, "submission_ids": sub_ids,
            "student_ids": [s.id for s in students]}


if __name__ == "__main__":
    from app.core.db import Base, SessionLocal, engine

    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        info = seed(session)
        print(f"Seed tamamlandı. Sınav: {info['exam_id']}  Giriş: ogretmen@demo.bcn / {DEMO_PASSWORD}")
