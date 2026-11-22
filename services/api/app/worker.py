"""Worker de retención: borra grabaciones vencidas o revocadas.

F1 usa el mismo paquete que la API para no duplicar modelos ni configuración.
El proceso se ejecuta como contenedor independiente (`issitek-worker`) y puede
correr una vez (`WORKER_RUN_ONCE=true`) para tareas operativas.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import SessionLocal
from .models import SpeechAsset
from .storage import Storage, get_storage

logger = logging.getLogger("issitek.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def purge_expired(
    db: Session,
    storage: Storage,
    *,
    now: datetime | None = None,
    batch_size: int = 500,
) -> int:
    """Elimina objetos y anonimiza metadatos de grabaciones fuera de retención.

    Es idempotente: los objetos ya purgados (`purged/...`) no se vuelven a
    procesar. Si el almacenamiento falla, la fila se conserva para reintentar.
    """
    moment = now or datetime.now(timezone.utc)
    assets = db.scalars(
        select(SpeechAsset)
        .where(
            SpeechAsset.source == "student_recording",
            SpeechAsset.storage_key.not_like("purged/%"),
            or_(
                SpeechAsset.deleted_at.is_not(None),
                SpeechAsset.retention_until <= moment,
            ),
        )
        .order_by(SpeechAsset.created_at)
        .limit(batch_size)
    ).all()

    purged = 0
    for asset in assets:
        try:
            storage.remove(asset.bucket, asset.storage_key)
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo borrar el objeto de la grabación %s", asset.id)
            continue
        asset.deleted_at = asset.deleted_at or moment
        asset.storage_key = f"purged/{asset.id}"
        asset.sha256 = None
        asset.bytes = 0
        purged += 1

    db.commit()
    return purged


def _touch_heartbeat(path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch()


def _sleep_with_heartbeat(seconds: int, path: str) -> None:
    deadline = time.monotonic() + max(1, seconds)
    while True:
        _touch_heartbeat(path)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(15, remaining))


def main() -> None:
    settings = get_settings()
    storage = get_storage()
    _touch_heartbeat(settings.worker_heartbeat_path)

    if settings.worker_run_once:
        with SessionLocal() as db:
            purged = purge_expired(db, storage, batch_size=settings.worker_batch_size)
        logger.info("Purga única completada: %s grabaciones.", purged)
        return

    logger.info(
        "Worker de retención iniciado (intervalo %ss, retención %s días).",
        settings.worker_interval_seconds,
        settings.recording_retention_days,
    )
    while True:
        try:
            with SessionLocal() as db:
                purged = purge_expired(db, storage, batch_size=settings.worker_batch_size)
            if purged:
                logger.info("Grabaciones purgadas: %s.", purged)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo en la purga; se reintentará en el siguiente ciclo.")
        _sleep_with_heartbeat(settings.worker_interval_seconds, settings.worker_heartbeat_path)


if __name__ == "__main__":
    main()
