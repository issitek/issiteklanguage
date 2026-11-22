"""TTS de referencia con caché en Postgres + almacenamiento S3 (Kokoro o fake local)."""

from __future__ import annotations

import hashlib
import io
import math
import struct
import wave

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .errors import AppError
from .models import TtsCache
from .storage import Storage, get_storage


def _tone_wav(duration_ms: int = 600, freq: int = 440, rate: int = 24_000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        total = int(rate * duration_ms / 1000)
        frames = b"".join(
            struct.pack("<h", int(0.2 * 32767 * math.sin(2 * math.pi * freq * i / rate)))
            for i in range(total)
        )
        wav.writeframes(frames)
    return buf.getvalue()


def wav_duration_ms(data: bytes) -> int | None:
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            return int(1000 * wav.getnframes() / wav.getframerate())
    except (wave.Error, EOFError, ZeroDivisionError):
        return None


class TtsService:
    def __init__(self, db: Session, storage: Storage | None = None) -> None:
        self.db = db
        self.settings = get_settings()
        self.storage = storage or get_storage()

    def reference(self, text: str, voice_id: str | None = None) -> dict:
        normalized = " ".join(text.split())
        if not normalized:
            raise AppError(422, "invalid_text", "El texto no puede estar vacío.")
        if len(normalized) > 400:
            raise AppError(422, "invalid_text", "El texto supera 400 caracteres.")

        voice = voice_id or self.settings.tts_default_voice
        text_hash = hashlib.sha256(f"{normalized}|{voice}|en-US".encode()).hexdigest()
        bucket = self.settings.minio_bucket_reference

        row = self.db.scalars(
            select(TtsCache).where(TtsCache.text_hash == text_hash, TtsCache.voice_id == voice)
        ).first()
        if row is not None:
            # El objeto puede haber desaparecido (limpieza manual o storage de
            # desarrollo reiniciado): se regenera en lugar de devolver un 404.
            try:
                self.storage.stat(bucket, row.storage_key)
            except Exception:  # noqa: BLE001
                self.db.delete(row)
                self.db.commit()
                row = None
        if row is not None:
            row.hit_count += 1
            self.db.commit()
            return {
                "url": self.storage.presign_get(bucket, row.storage_key),
                "duration_ms": row.duration_ms,
                "cached": True,
                "provider": self.settings.tts_provider,
                "expires_in": self.settings.minio_presign_ttl_s,
            }

        audio = self._synthesize(normalized, voice)
        duration_ms = wav_duration_ms(audio)
        key = f"en-US/{voice}/{text_hash}.wav"
        self.storage.put_bytes(bucket, key, audio, "audio/wav")

        row = TtsCache(
            text_hash=text_hash,
            voice_id=voice,
            locale="en-US",
            storage_key=key,
            duration_ms=duration_ms,
            hit_count=0,
        )
        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError:
            # Otro request generó el mismo audio en paralelo: reutilizarlo.
            self.db.rollback()
            row = self.db.scalars(
                select(TtsCache).where(TtsCache.text_hash == text_hash, TtsCache.voice_id == voice)
            ).first()

        return {
            "url": self.storage.presign_get(bucket, row.storage_key if row else key),
            "duration_ms": row.duration_ms if row else duration_ms,
            "cached": False,
            "provider": self.settings.tts_provider,
            "expires_in": self.settings.minio_presign_ttl_s,
        }

    def _synthesize(self, text: str, voice: str) -> bytes:
        if self.settings.tts_provider == "fake":
            return _tone_wav()
        if self.settings.tts_provider != "kokoro":
            raise AppError(503, "tts_unavailable", "Proveedor TTS no configurado.")

        try:
            response = httpx.post(
                f"{self.settings.tts_local_url.rstrip('/')}/v1/audio/speech",
                json={
                    "model": "kokoro",
                    "voice": voice,
                    "input": text,
                    "response_format": "wav",
                },
                timeout=15.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError(
                503, "tts_unavailable", "El servicio de voz de referencia no está disponible."
            ) from exc
        if not response.content:
            raise AppError(503, "tts_unavailable", "El servicio TTS devolvió audio vacío.")
        return response.content
