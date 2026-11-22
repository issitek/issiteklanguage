"""Worker de retención: borrado físico e idempotencia."""

import uuid
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.db import SessionLocal
from app.models import SpeechAsset
from app.storage import get_storage
from app.worker import purge_expired


def _asset(user_id, *, retention: datetime, deleted_at: datetime | None = None) -> SpeechAsset:
    settings = get_settings()
    asset_id = uuid.uuid4()
    key = f"{user_id}/test/{asset_id}.wav"
    storage = get_storage()
    storage.put_bytes(settings.minio_bucket_recordings, key, b"RIFFtest", "audio/wav")
    return SpeechAsset(
        id=asset_id,
        user_id=user_id,
        bucket=settings.minio_bucket_recordings,
        storage_key=key,
        bytes=8,
        duration_ms=1000,
        source="student_recording",
        mime="audio/wav",
        retention_until=retention,
        deleted_at=deleted_at,
    )


def test_purga_vencidas_y_soft_deleted(client, auth):
    user_id = uuid.UUID(client.get("/api/v1/users/me", headers=auth["headers"]).json()["id"])
    now = datetime.now(timezone.utc)
    expired = _asset(user_id, retention=now - timedelta(days=1))
    revoked = _asset(user_id, retention=now + timedelta(days=30), deleted_at=now)
    fresh = _asset(user_id, retention=now + timedelta(days=30))

    with SessionLocal() as db:
        db.add_all([expired, revoked, fresh])
        db.commit()
        purged = purge_expired(db, get_storage(), now=now)

    assert purged >= 2
    with SessionLocal() as db:
        for asset in (expired, revoked):
            row = db.get(SpeechAsset, asset.id)
            assert row.deleted_at is not None
            assert row.storage_key == f"purged/{asset.id}"
            assert row.sha256 is None
            assert row.bytes == 0
        kept = db.get(SpeechAsset, fresh.id)
        assert kept.deleted_at is None
        assert kept.storage_key.startswith(str(user_id))

    # Idempotente: una segunda pasada no vuelve a tocar las ya purgadas.
    with SessionLocal() as db:
        assert purge_expired(db, get_storage(), now=now) == 0
