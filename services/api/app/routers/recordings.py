"""Grabaciones del alumno: presign, verificación SHA-256, lectura y borrado."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import get_active_consent, get_current_user, require_recording_consent
from ..errors import AppError
from ..models import Exercise, SpeechAsset, User
from ..schemas import CompleteIn, PresignIn, PresignOut, RecordingOut
from ..storage import get_storage

router = APIRouter(prefix="/recordings", tags=["recordings"])

MIME_EXT = {
    "audio/webm": "webm",
    "audio/webm;codecs=opus": "webm",
    "audio/wav": "wav",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
}


def _owned(db: Session, user: User, recording_id: uuid.UUID) -> SpeechAsset:
    asset = db.get(SpeechAsset, recording_id)
    if asset is None or asset.user_id != user.id:
        raise AppError(404, "recording_not_found", "Grabación no encontrada.")
    if asset.deleted_at is not None:
        raise AppError(410, "recording_deleted", "La grabación fue eliminada.")
    return asset


@router.post("/presign", response_model=PresignOut, status_code=201)
def presign(
    payload: PresignIn,
    user: User = Depends(require_recording_consent),
    db: Session = Depends(get_db),
) -> PresignOut:
    settings = get_settings()
    if payload.duration_ms > settings.recording_max_seconds * 1000:
        raise AppError(
            422,
            "recording_too_long",
            f"La grabación supera {settings.recording_max_seconds} segundos.",
        )
    if payload.exercise_id is not None:
        exercise = db.get(Exercise, payload.exercise_id)
        if exercise is None:
            raise AppError(404, "exercise_not_found", "Ejercicio no encontrado.")

    consent = get_active_consent(db, user.id, "recording")
    if consent is None:
        raise AppError(403, "consent_required", "Se requiere consentimiento para grabar voz.")

    now = datetime.now(timezone.utc)
    asset_id = uuid.uuid4()
    key = (
        f"{user.id}/{now:%Y}/{now:%m}/{asset_id}.{MIME_EXT[payload.mime]}"
    )
    asset = SpeechAsset(
        id=asset_id,
        user_id=user.id,
        exercise_id=payload.exercise_id,
        bucket=settings.minio_bucket_recordings,
        storage_key=key,
        bytes=0,
        duration_ms=payload.duration_ms,
        source="student_recording",
        consent_id=consent.id,
        mime=payload.mime,
        retention_until=now + timedelta(seconds=settings.recording_retention_seconds),
    )
    db.add(asset)
    db.commit()

    storage = get_storage()
    url = storage.presign_put(settings.minio_bucket_recordings, key)
    return PresignOut(
        recording_id=asset_id,
        url=url,
        expires_in=settings.minio_presign_ttl_s,
    )


@router.post("/{recording_id}/complete", response_model=RecordingOut)
def complete(
    recording_id: uuid.UUID,
    payload: CompleteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordingOut:
    settings = get_settings()
    asset = _owned(db, user, recording_id)
    storage = get_storage()

    if asset.sha256 is None:
        try:
            stat = storage.stat(asset.bucket, asset.storage_key)
        except Exception as exc:
            raise AppError(422, "recording_missing", "La grabación no se subió.") from exc
        if stat.size > settings.recording_max_bytes or stat.size != payload.bytes:
            storage.remove(asset.bucket, asset.storage_key)
            asset.deleted_at = datetime.now(timezone.utc)
            db.commit()
            raise AppError(422, "recording_size_mismatch", "El tamaño no coincide.")

        data = storage.get_bytes(asset.bucket, asset.storage_key, settings.recording_max_bytes)
        actual = hashlib.sha256(data).hexdigest()
        if actual != payload.sha256:
            storage.remove(asset.bucket, asset.storage_key)
            asset.deleted_at = datetime.now(timezone.utc)
            db.commit()
            raise AppError(422, "recording_hash_mismatch", "La verificación SHA-256 falló.")

        asset.bytes = len(data)
        asset.sha256 = actual
        db.commit()
        db.refresh(asset)

    return RecordingOut(
        id=asset.id,
        url=storage.presign_get(asset.bucket, asset.storage_key),
        expires_in=settings.minio_presign_ttl_s,
        sha256=asset.sha256,
        duration_ms=asset.duration_ms,
        mime=asset.mime,
    )


@router.get("/{recording_id}", response_model=RecordingOut)
def get_recording(
    recording_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordingOut:
    settings = get_settings()
    asset = _owned(db, user, recording_id)
    storage = get_storage()
    return RecordingOut(
        id=asset.id,
        url=storage.presign_get(asset.bucket, asset.storage_key),
        expires_in=settings.minio_presign_ttl_s,
        sha256=asset.sha256,
        duration_ms=asset.duration_ms,
        mime=asset.mime,
    )


@router.delete("/{recording_id}", status_code=204)
def delete_recording(
    recording_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    asset = _owned(db, user, recording_id)
    get_storage().remove(asset.bucket, asset.storage_key)
    asset.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)
