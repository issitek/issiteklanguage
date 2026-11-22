"""Registro, login, refresh y logout."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import AppError
from ..models import RefreshToken, User
from ..rate_limit import check_rate_limit, reset_rate_limit
from ..schemas import LoginIn, RefreshIn, RegisterIn, TokenOut
from ..security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(db: Session, user: User) -> TokenOut:
    access = create_access_token(user.id, user.role)
    raw, token_hash, expires_at = new_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    return TokenOut(access_token=access, refresh_token=raw)


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    email = payload.email.lower()
    if db.scalars(select(User).where(User.email == email)).first() is not None:
        raise AppError(409, "email_taken", "Ya existe una cuenta con ese correo.")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        birth_year=payload.birth_year,
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_tokens(db, user)


@router.post("/login", response_model=TokenOut)
def login(
    payload: LoginIn, request: Request, db: Session = Depends(get_db)
) -> TokenOut:
    email = payload.email.lower()
    ip = request.client.host if request.client else "desconocida"
    key = f"login:{ip}:{email}"
    if not check_rate_limit(key, limit=5, window_s=60):
        raise AppError(
            429,
            "rate_limited",
            "Demasiados intentos. Espera un minuto antes de volver a probar.",
        )
    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(401, "invalid_credentials", "Correo o contraseña incorrectos.")
    reset_rate_limit(key)
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    token_hash = hash_refresh_token(payload.refresh_token)
    row = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    now = datetime.now(timezone.utc)
    if row is None or row.revoked_at is not None or row.expires_at < now:
        raise AppError(401, "invalid_refresh", "Sesión expirada. Vuelve a iniciar sesión.")

    row.revoked_at = now
    user = db.get(User, row.user_id)
    if user is None:
        raise AppError(401, "invalid_refresh", "Sesión inválida.")
    return _issue_tokens(db, user)


@router.post("/logout", status_code=204)
def logout(payload: RefreshIn, db: Session = Depends(get_db)) -> Response:
    token_hash = hash_refresh_token(payload.refresh_token)
    row = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return Response(status_code=204)
