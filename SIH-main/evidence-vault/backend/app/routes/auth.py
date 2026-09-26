"""Authentication routes"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import LoginRequest, LoginResponse, MfaVerifyRequest, TokenResponse, UserOut
from app.security.auth import (
    verify_password, create_access_token, get_current_user,
)
from app.security.mfa import (
    get_user_totp_secret,
    generate_current_totp,
    verify_user_mfa,
    create_temp_mfa_token,
    decode_temp_mfa_token,
)
from app.utils.helpers import create_audit_log

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def _detect_device(request: Request) -> str:
    ua = request.headers.get("user-agent", "")
    if "Mobile" in ua or "Android" in ua or "iPhone" in ua:
        return "Mobile Browser"
    if "Windows" in ua:
        return "Windows Workstation"
    if "Macintosh" in ua or "Mac OS" in ua:
        return "macOS Workstation"
    if "Linux" in ua:
        return "Linux Terminal / Browser"
    return "Web Console"


def _issue_authenticated_session(user: User, client_ip: str, device: str, db: Session) -> LoginResponse:
    from app.security.auth import normalize_role
    canonical_role = normalize_role(user.role)
    token = create_access_token({
        "sub": str(user.id),
        "user_id": user.id,
        "role": canonical_role,
        "email": user.email,
        "full_name": user.full_name,
        "department": user.department or "General",
        "badge_number": user.badge_number or f"USR-{user.id:04d}",
    })
    user.last_login = datetime.utcnow()
    db.commit()


    officer_label = f"Officer {user.full_name}"
    if user.badge_number:
        officer_label += f" [Badge: {user.badge_number}]"
    if user.department:
        officer_label += f" ({user.department})"

    create_audit_log(
        db,
        user_id=user.id,
        user_email=user.email,
        role=user.role,
        action="LOGIN",
        status="SUCCESS",
        ip_address=client_ip,
        resource_type="AUTH",
        resource_id=user.badge_number or f"USR-{user.id:04d}",
        details=f"{officer_label} authenticated successfully via {device}",
    )

    return LoginResponse(
        mfa_required=False,
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
        officer_name=user.full_name,
        badge_number=user.badge_number,
        role=user.role,
    )


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = _extract_client_ip(request)
    device = _detect_device(request)

    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        create_audit_log(
            db,
            action="LOGIN",
            status="FAILED",
            user_email=req.email,
            role=user.role if user else "UNKNOWN",
            ip_address=client_ip,
            resource_type="AUTH",
            resource_id=req.email,
            details=f"Failed password authentication attempt via {device} (IP: {client_ip})",
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        create_audit_log(
            db,
            user_id=user.id,
            user_email=user.email,
            role=user.role,
            action="LOGIN",
            status="BLOCKED",
            ip_address=client_ip,
            resource_type="AUTH",
            resource_id=str(user.id),
            details=f"Blocked authentication for deactivated user {user.full_name} ({user.email})",
        )
        raise HTTPException(status_code=403, detail="Account disabled")

    # Issue direct authenticated session
    return _issue_authenticated_session(user, client_ip, device, db)


@router.post("/verify-mfa", response_model=LoginResponse)
def verify_mfa_code(req: MfaVerifyRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = _extract_client_ip(request)
    device = _detect_device(request)

    try:
        payload = decode_temp_mfa_token(req.temp_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account invalid or disabled")

    if not verify_user_mfa(user.email, req.mfa_code):
        create_audit_log(
            db,
            user_id=user.id,
            user_email=user.email,
            role=user.role,
            action="MFA_CHALLENGE",
            status="FAILED",
            ip_address=client_ip,
            resource_type="AUTH",
            resource_id=user.badge_number or f"USR-{user.id:04d}",
            details=f"Failed MFA TOTP challenge for {user.full_name} via {device}",
        )
        raise HTTPException(status_code=401, detail="Invalid 6-digit MFA security code")

    return _issue_authenticated_session(user, client_ip, device, db)


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    client_ip = _extract_client_ip(request)
    create_audit_log(
        db,
        user_id=user.id,
        user_email=user.email,
        role=user.role,
        action="LOGOUT",
        status="SUCCESS",
        ip_address=client_ip,
        resource_type="AUTH",
        resource_id=user.badge_number or f"USR-{user.id:04d}",
        details=f"Officer {user.full_name} logged out securely.",
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)

