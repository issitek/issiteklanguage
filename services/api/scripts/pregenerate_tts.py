"""Pregenera el audio de referencia de todos los ejercicios `listen_repeat`.

Uso con Kokoro real (overlay):

    docker compose -f infra/docker-compose.yml -f infra/docker-compose.kokoro.yml \
      up -d tts api
    docker compose -f infra/docker-compose.yml -f infra/docker-compose.kokoro.yml \
      exec api python scripts/pregenerate_tts.py

El script es idempotente: los textos ya cacheados se reutilizan.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from app.config import get_settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.tts import TtsService  # noqa: E402

CONTENT_DIR = API_DIR / "content" / "a1"


def main() -> None:
    settings = get_settings()
    if settings.tts_provider != "kokoro":
        print(
            "ADVERTENCIA: TTS_PROVIDER no es kokoro; se pregenerará audio fake. "
            "Usa el overlay docker-compose.kokoro.yml."
        )

    generated = cached = 0
    with SessionLocal() as db:
        service = TtsService(db)
        for path in sorted(CONTENT_DIR.glob("*.json")):
            lesson = json.loads(path.read_text(encoding="utf-8"))
            for exercise in lesson["exercises"]:
                if exercise["type"] != "listen_repeat":
                    continue
                payload = exercise["payload"]
                text = payload["word"]
                voice = payload.get("voice_id") or settings.tts_default_voice
                result = service.reference(text, voice)
                if result["cached"]:
                    cached += 1
                else:
                    generated += 1
                print(
                    f"{lesson['slug']}: {text!r} → {result['provider']} "
                    f"{result['duration_ms']} ms "
                    f"({'caché' if result['cached'] else 'generado'})"
                )

    print(f"Listo: {generated} generados, {cached} desde caché.")


if __name__ == "__main__":
    main()
