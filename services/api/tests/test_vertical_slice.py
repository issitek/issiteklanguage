"""Vertical slice de F1: lección → TTS → grabación → intento → progreso."""

import hashlib
import io
import wave

import httpx


def _wav_bytes(seconds: float = 1.0, rate: int = 16_000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * int(rate * seconds))
    return buffer.getvalue()


def _exercise(lesson: dict, kind: str) -> dict:
    for exercise in lesson["exercises"]:
        if exercise["type"] == kind:
            return exercise
    raise AssertionError(f"No hay ejercicio de tipo {kind}")


def _grant_recording(client, headers):
    response = client.post(
        "/api/v1/consents", headers=headers, json={"kind": "recording"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["active"] is True


def _upload_recording(client, headers, exercise_id: str) -> dict:
    presign = client.post(
        "/api/v1/recordings/presign",
        headers=headers,
        json={"exercise_id": exercise_id, "duration_ms": 1200, "mime": "audio/wav"},
    )
    assert presign.status_code == 201, presign.text
    presign_body = presign.json()

    audio = _wav_bytes()
    upload = httpx.put(
        presign_body["url"],
        content=audio,
        headers={"Content-Type": "audio/wav"},
        timeout=10,
    )
    assert upload.status_code == 200, upload.text

    complete = client.post(
        f"/api/v1/recordings/{presign_body['recording_id']}/complete",
        headers=headers,
        json={"sha256": hashlib.sha256(audio).hexdigest(), "bytes": len(audio)},
    )
    assert complete.status_code == 200, complete.text
    return complete.json()


def test_health_ready_incluye_storage(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["checks"] == {"postgres": "ok", "storage": "ok"}


def test_vertical_slice_completa(client, auth, first_lesson):
    headers = auth["headers"]

    courses = client.get("/api/v1/courses", headers=headers)
    assert courses.status_code == 200
    assert len(courses.json()) == 1
    assert len(courses.json()[0]["lessons"]) == 10
    assert len(first_lesson["exercises"]) == 3

    repeat = _exercise(first_lesson, "listen_repeat")
    choice = _exercise(first_lesson, "multiple_choice")
    text = _exercise(first_lesson, "translate")

    # Sin consentimiento no se puede grabar.
    blocked = client.post(
        "/api/v1/recordings/presign",
        headers=headers,
        json={"exercise_id": repeat["id"], "duration_ms": 1000, "mime": "audio/wav"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "consent_required"

    _grant_recording(client, headers)
    consents = client.get("/api/v1/consents", headers=headers).json()
    assert any(c["kind"] == "recording" and c["active"] for c in consents)

    too_long = client.post(
        "/api/v1/recordings/presign",
        headers=headers,
        json={"exercise_id": repeat["id"], "duration_ms": 15_001, "mime": "audio/wav"},
    )
    assert too_long.status_code == 422
    assert too_long.json()["error"]["code"] == "recording_too_long"

    # TTS de referencia: primero genera, segundo usa caché.
    tts1 = client.get(
        "/api/v1/tts/reference",
        headers=headers,
        params={"text": "Hello", "voice_id": "af_heart"},
    )
    assert tts1.status_code == 200, tts1.text
    assert tts1.json()["provider"] == "fake"
    assert tts1.json()["cached"] is False
    assert tts1.json()["url"].startswith("http")

    tts2 = client.get(
        "/api/v1/tts/reference",
        headers=headers,
        params={"text": "Hello", "voice_id": "af_heart"},
    )
    assert tts2.json()["cached"] is True
    assert tts2.json()["url"] == tts1.json()["url"]

    # Grabación del alumno: presign → PUT → complete (SHA-256).
    recording = _upload_recording(client, headers, repeat["id"])
    assert recording["sha256"]
    assert recording["duration_ms"] == 1200

    repeat_attempt = client.post(
        f"/api/v1/exercises/{repeat['id']}/attempts",
        headers=headers,
        json={"response": {"word": "Hello"}, "recording_id": recording["id"]},
    )
    assert repeat_attempt.status_code == 200, repeat_attempt.text
    assert repeat_attempt.json()["score"] is None
    assert repeat_attempt.json()["is_correct"] is None
    assert "Práctica libre" in repeat_attempt.json()["feedback"]

    # Opción múltiple: una incorrecta y una correcta (score educativo).
    correct_index = int(choice["payload"]["answer"])
    wrong_index = (correct_index + 1) % len(choice["payload"]["options"])
    wrong = client.post(
        f"/api/v1/exercises/{choice['id']}/attempts",
        headers=headers,
        json={"response": {"answer": wrong_index}},
    )
    assert wrong.status_code == 200
    assert wrong.json()["is_correct"] is False
    assert wrong.json()["score"] == 0.0

    right = client.post(
        f"/api/v1/exercises/{choice['id']}/attempts",
        headers=headers,
        json={"response": {"answer": correct_index}},
    )
    assert right.json()["is_correct"] is True
    assert right.json()["score"] == 100.0

    # Traducción con respuesta válida.
    answer = text["payload"]["answers"][0]
    translated = client.post(
        f"/api/v1/exercises/{text['id']}/attempts",
        headers=headers,
        json={"response": {"text": answer}},
    )
    assert translated.status_code == 200
    assert translated.json()["is_correct"] is True

    progress = client.get("/api/v1/me/progress", headers=headers)
    assert progress.status_code == 200, progress.text
    body = progress.json()
    assert body["total_lessons"] == 10
    assert body["completed_lessons"] == 0
    assert body["attempts"] == 4
    assert body["pronunciation_eval_enabled"] is False

    completed = client.post(
        f"/api/v1/lessons/{first_lesson['id']}/complete", headers=headers
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    after = client.get("/api/v1/me/progress", headers=headers).json()
    assert after["completed_lessons"] == 1
    assert any(item["status"] == "completed" for item in after["items"])

    # Borrado de la grabación.
    deleted = client.delete(f"/api/v1/recordings/{recording['id']}", headers=headers)
    assert deleted.status_code == 204
    gone = client.get(f"/api/v1/recordings/{recording['id']}", headers=headers)
    assert gone.status_code == 410


def test_hash_invalido_y_revocacion_de_consentimiento(client, auth, first_lesson):
    headers = auth["headers"]
    repeat = _exercise(first_lesson, "listen_repeat")
    _grant_recording(client, headers)

    presign = client.post(
        "/api/v1/recordings/presign",
        headers=headers,
        json={"exercise_id": repeat["id"], "duration_ms": 900, "mime": "audio/wav"},
    ).json()
    audio = _wav_bytes(0.5)
    httpx.put(
        presign["url"], content=audio, headers={"Content-Type": "audio/wav"}, timeout=10
    )

    bad = client.post(
        f"/api/v1/recordings/{presign['recording_id']}/complete",
        headers=headers,
        json={"sha256": "0" * 64, "bytes": len(audio)},
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "recording_hash_mismatch"

    gone = client.get(f"/api/v1/recordings/{presign['recording_id']}", headers=headers)
    assert gone.status_code == 410

    # Los dos consentimientos son independientes.
    third = client.post(
        "/api/v1/consents",
        headers=headers,
        json={"kind": "third_party_processing"},
    )
    assert third.status_code == 200
    assert third.json()["active"] is True

    revoked = client.delete("/api/v1/consents/recording", headers=headers)
    assert revoked.status_code == 200
    assert revoked.json()["active"] is False

    consents = client.get("/api/v1/consents", headers=headers).json()
    recording = next(c for c in consents if c["kind"] == "recording")
    third_party = next(c for c in consents if c["kind"] == "third_party_processing")
    assert recording["active"] is False
    assert third_party["active"] is True

    blocked = client.post(
        "/api/v1/recordings/presign",
        headers=headers,
        json={"exercise_id": repeat["id"], "duration_ms": 900, "mime": "audio/wav"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "consent_required"
