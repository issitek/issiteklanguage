"""Dependencias: usuario autenticado, rol y consentimientos."""

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .errors import AppError
from .models import Consent, User
from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError(401, "unauthorized", "Falta el token de acceso.")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError) as exc:
        raise AppError(401, "invalid_token", "Token inválido o expirado.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise AppError(401, "invalid_token", "Token inválido o expirado.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError(403, "forbidden", "Se requiere rol de administrador.")
    return user


def get_active_consent(db: Session, user_id: uuid.UUID, kind: str) -> Consent | None:
    stmt = (
        select(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.kind == kind,
            Consent.revoked_at.is_(None),
            Consent.granted_at.is_not(None),
        )
        .order_by(Consent.granted_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def require_recording_consent(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    if get_active_consent(db, user.id, "recording") is None:
        raise AppError(403, "consent_required", "Se requiere consentimiento para grabar voz.")
    return user
