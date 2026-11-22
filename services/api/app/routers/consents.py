"""Consentimientos independientes: grabación y procesamiento por terceros."""

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user
from ..errors import AppError
from ..models import Consent, SpeechAsset, User
from ..schemas import ConsentIn, ConsentOut
from ..storage import get_storage

router = APIRouter(prefix="/consents", tags=["consents"])

KINDS = ("recording", "third_party_processing", "parental")


def _latest(db: Session, user_id: uuid.UUID, kind: str) -> Consent | None:
    return db.scalars(
        select(Consent)
        .where(Consent.user_id == user_id, Consent.kind == kind)
        .order_by(Consent.granted_at.desc().nullslast(), Consent.revoked_at.desc().nullslast())
        .limit(1)
    ).first()


def _to_out(row: Consent | None) -> ConsentOut | None:
    if row is None:
        return None
    return ConsentOut(
        kind=row.kind,
        version=row.version,
        granted_at=row.granted_at,
        revoked_at=row.revoked_at,
        active=row.granted_at is not None and row.revoked_at is None,
    )


@router.get("", response_model=list[ConsentOut])
def list_consents(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ConsentOut]:
    result: list[ConsentOut] = []
    for kind in KINDS:
        row = _latest(db, user.id, kind)
        if row is not None:
            result.append(_to_out(row))
    return result


@router.post("", response_model=ConsentOut)
def grant_consent(
    payload: ConsentIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentOut:
    now = datetime.now(timezone.utc)
    if not payload.granted:
        return _revoke(db, user.id, payload.kind)

    settings = get_settings()
    ip_hash = hashlib.sha256(
        f"{request.client.host if request.client else 'unknown'}|{settings.jwt_secret}".encode()
    ).hexdigest()
    ua_hash = hashlib.sha256((request.headers.get("user-agent", "")).encode()).hexdigest()
    evidence = {
        "method": "web_checkbox",
        "ip_hash": ip_hash,
        "user_agent_hash": ua_hash,
        "policy_version": payload.version,
    }

    for active in db.scalars(
        select(Consent).where(
            Consent.user_id == user.id,
            Consent.kind == payload.kind,
            Consent.revoked_at.is_(None),
        )
    ).all():
        active.revoked_at = now

    row = db.scalars(
        select(Consent).where(
            Consent.user_id == user.id,
            Consent.kind == payload.kind,
            Consent.version == payload.version,
        )
    ).first()
    if row is None:
        row = Consent(
            user_id=user.id,
            kind=payload.kind,
            version=payload.version,
            granted_at=now,
            evidence=evidence,
        )
        db.add(row)
    else:
        row.granted_at = now
        row.revoked_at = None
        row.evidence = evidence

    db.commit()
    db.refresh(row)
    return _to_out(row)


def _revoke(db: Session, user_id: uuid.UUID, kind: str) -> ConsentOut:
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(Consent).where(
            Consent.user_id == user_id, Consent.kind == kind, Consent.revoked_at.is_(None)
        )
    ).all()
    for row in rows:
        row.revoked_at = now
    db.commit()

    if kind == "recording":
        _purge_recordings(db, user_id)

    latest = _latest(db, user_id, kind)
    if latest is None:
        raise AppError(404, "consent_not_found", "No hay consentimiento para revocar.")
    return _to_out(latest)


def _purge_recordings(db: Session, user_id: uuid.UUID) -> None:
    storage = get_storage()
    assets = db.scalars(
        select(SpeechAsset).where(
            SpeechAsset.user_id == user_id,
            SpeechAsset.source == "student_recording",
            SpeechAsset.deleted_at.is_(None),
        )
    ).all()
    now = datetime.now(timezone.utc)
    for asset in assets:
        storage.remove(asset.bucket, asset.storage_key)
        asset.deleted_at = now
    db.commit()


@router.delete("/{kind}", response_model=ConsentOut)
def revoke_consent(
    kind: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentOut:
    if kind not in KINDS:
        raise AppError(404, "consent_kind_invalid", "Tipo de consentimiento desconocido.")
    return _revoke(db, user.id, kind)
