from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require, teacher_class_ids
from app.core.security import create_access_token, verify_password
from app.models import LearningOutcome, RoleName, SchoolClass, Subject, User
from app.schemas import ClassOut, IdName, LoginIn, LookupsOut, MeOut, OutcomeOut, TokenOut
from app.services.audit import audit

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.execute(select(User).where(User.email == body.email.lower().strip())).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        audit(db, org_id=None, actor_id=None, action="login_failed", entity_type="user")
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-posta veya şifre hatalı.")
    audit(db, org_id=user.organization_id, actor_id=user.id, action="login", entity_type="user", entity_id=user.id)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.organization_id, [r.role.value for r in user.roles]))


@router.get("/auth/me", response_model=MeOut)
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> MeOut:
    u = db.get(User, user.id)
    return MeOut(id=u.id, full_name=u.full_name, email=u.email, roles=sorted(r.value for r in user.roles))


@router.get("/meta/lookups", response_model=LookupsOut)
def lookups(user: CurrentUser = Depends(require("exam:read")), db: Session = Depends(get_db)) -> LookupsOut:
    org = user.organization_id
    q = select(SchoolClass).where(SchoolClass.organization_id == org)
    if not user.is_org_wide:
        if user.has(RoleName.CAMPUS_ADMIN):
            q = q.where(SchoolClass.campus_id.in_(user.campus_ids))
        else:
            q = q.where(SchoolClass.id.in_(teacher_class_ids(db, user)))
    return LookupsOut(
        subjects=[IdName.model_validate(s) for s in db.execute(select(Subject).where(Subject.organization_id == org)).scalars()],
        classes=[ClassOut.model_validate(c) for c in db.execute(q.order_by(SchoolClass.grade_level, SchoolClass.name)).scalars()],
        outcomes=[OutcomeOut.model_validate(o) for o in db.execute(
            select(LearningOutcome).where(LearningOutcome.organization_id == org).order_by(LearningOutcome.code)).scalars()],
    )
