"""Authentication + backend-enforced RBAC + tenant scoping."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import Exam, ExamClass, RoleName, TeacherAssignment, User

_bearer = HTTPBearer(auto_error=False)

STAFF_ADMIN = {RoleName.SUPER_ADMIN, RoleName.ORG_ADMIN, RoleName.CAMPUS_ADMIN}
ACADEMIC = {RoleName.ACADEMIC_COORDINATOR}

# permission -> roles allowed. Object-level checks (own classes, campus) happen in ensure_* helpers.
PERMISSIONS: dict[str, set[RoleName]] = {
    "exam:read": STAFF_ADMIN | ACADEMIC | {RoleName.TEACHER},
    "exam:write": STAFF_ADMIN | ACADEMIC | {RoleName.TEACHER},
    "exam:publish": STAFF_ADMIN | ACADEMIC | {RoleName.TEACHER},
    "submission:upload": STAFF_ADMIN | ACADEMIC | {RoleName.TEACHER},
    "analysis:review": ACADEMIC | {RoleName.TEACHER},
    "analytics:read": STAFF_ADMIN | ACADEMIC | {RoleName.TEACHER},
}


@dataclass
class CurrentUser:
    id: uuid.UUID
    organization_id: uuid.UUID
    roles: set[RoleName]
    campus_ids: set[uuid.UUID] = field(default_factory=set)  # empty + admin role => org-wide

    def has(self, *roles: RoleName) -> bool:
        return bool(self.roles & set(roles))

    @property
    def is_org_wide(self) -> bool:
        return self.has(RoleName.SUPER_ADMIN, RoleName.ORG_ADMIN, RoleName.ACADEMIC_COORDINATOR)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> CurrentUser:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Oturum açmanız gerekiyor.")
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Oturum geçersiz veya süresi dolmuş.") from None
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active or str(user.organization_id) != payload["org"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kullanıcı bulunamadı veya pasif.")
    # roles are re-read from DB (token roles are informational only)
    return CurrentUser(
        id=user.id, organization_id=user.organization_id,
        roles={r.role for r in user.roles},
        campus_ids={r.campus_id for r in user.roles if r.campus_id},
    )


def require(permission: str):
    def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not (user.roles & PERMISSIONS[permission]):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu işlem için yetkiniz yok.")
        return user

    return _dep


def teacher_class_ids(db: Session, user: CurrentUser) -> set[uuid.UUID]:
    return set(db.execute(
        select(TeacherAssignment.class_id).where(TeacherAssignment.teacher_user_id == user.id,
                                                 TeacherAssignment.organization_id == user.organization_id)
    ).scalars())


def ensure_exam_access(db: Session, user: CurrentUser, exam: Exam | None) -> Exam:
    """404 (not 403) for other tenants to avoid leaking existence."""
    if exam is None or exam.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sınav bulunamadı.")
    if user.is_org_wide:
        return exam
    if user.has(RoleName.CAMPUS_ADMIN) and exam.campus_id in user.campus_ids:
        return exam
    if user.has(RoleName.TEACHER):
        if exam.created_by == user.id:
            return exam
        exam_classes = set(db.execute(select(ExamClass.class_id).where(ExamClass.exam_id == exam.id)).scalars())
        if exam_classes & teacher_class_ids(db, user):
            return exam
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Sınav bulunamadı.")
