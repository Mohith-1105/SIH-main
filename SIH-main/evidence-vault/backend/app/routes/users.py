"""User management routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import UserOut, UserCreate
from app.security.auth import require_permission, hash_password, ROLE_DEFAULT_RANK
from app.security.mfa import generate_totp_secret

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=list[UserOut])
def list_users(
    user: User = Depends(require_permission("users.read")),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.id).all()
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut)
def create_user(
    req: UserCreate,
    user: User = Depends(require_permission("users.write")),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=req.email,
        full_name=req.full_name,
        hashed_password=hash_password(req.password),
        role=req.role,
        rank_level=req.rank_level or ROLE_DEFAULT_RANK.get(req.role, 3),
        department=req.department,
        badge_number=req.badge_number,
        totp_secret=generate_totp_secret(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserOut.model_validate(new_user)
