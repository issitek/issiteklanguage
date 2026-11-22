"""Healthchecks: liveness y readiness (Postgres + S3)."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..storage import get_storage

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "issitek-api", "version": "0.1.0"}


@router.get("/health/ready")
def ready(response: Response, db: Session = Depends(get_db)) -> dict:
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "fail"

    try:
        settings = get_settings()
        get_storage().bucket_exists(settings.minio_bucket_recordings)
        checks["storage"] = "ok"
    except Exception:
        checks["storage"] = "fail"

    ok = all(value == "ok" for value in checks.values())
    if not ok:
        response.status_code = 503
    return {"status": "ok" if ok else "degraded", "checks": checks}
