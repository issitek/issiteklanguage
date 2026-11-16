"""Servidor de laboratorio talkdrill (Fase 0) — modo conversación.

Dos modos (env LAB_MODE):
- conversation (default): mic → VAD → faster-whisper → LLM local (llama.cpp)
  → Kokoro TTS → RTP de regreso + visemes + barge-in (TD-F0-005/011/013)
- echo: el audio del alumno vuelve (regresión TD-F0-003/004)

Endpoints:
- POST /offer              : negociación WebRTC (offer del cliente → answer)
- POST /ice-credentials    : iceServers TURN REST/HMAC de vida corta
- POST /webrtc/ice-report  : anillo de telemetría (max 50)
- GET  /webrtc/ice-report/recent
- GET  /                   : página de prueba (lab/client)

NO ES EL PRODUCTO: es el andamiaje go/no-go de la Fase 0.
"""

import asyncio
import json
import logging
import os
import time
from collections import deque
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from aiortc import RTCPeerConnection, MediaStreamTrack
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from conversation import (
    EnergyVAD,
    SpeakerTrack,
    _load_whisper,
    _stt_sync,
    call_llm,
    synth_tts,
    text_visemes,
    wav_to_rtp_frames,
)
from ice import ice_servers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lab-server")

LAB_TOKEN = os.environ.get("LAB_TOKEN", "dev-token")
LAB_MODE = os.environ.get("LAB_MODE", "conversation")
CLIENT_DIR = Path(__file__).resolve().parent.parent / "client"

app = FastAPI(title="talkdrill lab (Fase 0)", version="0.2.0")

ice_reports: deque = deque(maxlen=50)
peer_connections: set[RTCPeerConnection] = set()


def check_token(x_lab_token: str | None):
    if x_lab_token != LAB_TOKEN:
        raise HTTPException(status_code=401, detail="x-lab-token inválido")


@app.get("/health")
async def health():
    return {"status": "ok", "mode": LAB_MODE, "peer_connections": len(peer_connections)}


@app.post("/ice-credentials")
async def post_ice_credentials(x_lab_token: str | None = Header(default=None)):
    check_token(x_lab_token)
    return {"iceServers": ice_servers(), "ttl": 300}


@app.post("/webrtc/ice-report")
async def post_ice_report(payload: dict, x_lab_token: str | None = Header(default=None)):
    check_token(x_lab_token)
    entry = {"received_at": time.time(), **payload}
    ice_reports.appendleft(entry)
    log.info("ice-report: %s", json.dumps(payload, ensure_ascii=False)[:300])
    return {"stored": True}


@app.get("/webrtc/ice-report/recent")
async def get_ice_reports(x_lab_token: str | None = Header(default=None)):
    check_token(x_lab_token)
    return {"count": len(ice_reports), "reports": list(ice_reports)}


class Offer(BaseModel):
    sdp: str
    type: str


class EchoAudioTrack(MediaStreamTrack):
    """Modo echo: reenvía el audio del alumno (regresión)."""

    kind = "audio"

    def __init__(self, remote: MediaStreamTrack):
        super().__init__()
        self._remote = remote

    async def recv(self):
        return await self._remote.recv()


def sample_assistant_response() -> dict:
    return {
        "type": "assistant_response",
        "v": 1,
        "session_id": "lab-session",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "text": "Good try! You should say: Yesterday I went to school.",
        "display_translation": "¡Bien! Deberías decir: Yesterday I went to school.",
        "correction": {
            "original": "Yesterday I go to the school.",
            "corrected": "Yesterday I went to school.",
            "reason": "Past simple",
            "error_type": "grammar_tense",
        },
        "emotion": "encouraging",
        "visemes": [
            {"t_ms": 0, "id": "sil", "weight": 0.0},
            {"t_ms": 120, "id": "B", "weight": 0.9},
            {"t_ms": 240, "id": "AA", "weight": 1.0},
            {"t_ms": 360, "id": "EE", "weight": 0.8},
            {"t_ms": 520, "id": "sil", "weight": 0.1},
        ],
        "audio_seq": 1,
        "model": "lab-echo",
    }


class PeerSession:
    """Estado de una conexión: speaker track, VAD, historial, canal de eventos."""

    def __init__(self):
        self.speaker = SpeakerTrack()
        self.vad = EnergyVAD()
        self.dc: object | None = None
        self.history: list[dict] = []
        self._acc = np.array([], dtype=np.int16)
        self._speech: list[np.ndarray] = []
        self.tts_active = False
        self.audio_seq = 0
        self._end_speaking_task: asyncio.Task | None = None

    async def send_event(self, payload: dict):
        payload.setdefault("v", 1)
        payload.setdefault(
            "ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        dc = self.dc
        if dc is not None and getattr(dc, "readyState", None) == "open":
            dc.send(json.dumps(payload, ensure_ascii=False))

    async def on_window(self, window: np.ndarray):
        event = self.vad.feed(window)
        if self.vad.in_speech or event == "speech_start":
            self._speech.append(window)
        if event == "speech_end":
            pcm = np.concatenate(self._speech).tobytes() if self._speech else b""
            self._speech = []
            if self.tts_active:
                await self._barge_in()
                return
            if len(pcm) >= 25600:  # >0.8 s de audio (16-bit mono @16 kHz)
                asyncio.create_task(self.respond(pcm))

    async def consume_remote(self, track):
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        try:
            while True:
                frame = await track.recv()
                for out in resampler.resample(frame) or []:
                    arr = out.to_ndarray().reshape(-1).astype(np.int16)
                    self._acc = np.concatenate([self._acc, arr])
                    while len(self._acc) >= 320:  # 20 ms @16 kHz
                        window, self._acc = self._acc[:320], self._acc[320:]
                        await self.on_window(window)
        except Exception as exc:  # track termina o error
            log.info("track remoto terminado: %s", exc)

    async def _barge_in(self):
        t0 = time.perf_counter()
        cleared = self.speaker.clear()
        if self._end_speaking_task:
            self._end_speaking_task.cancel()
        self.tts_active = False
        await self.send_event({"type": "interrupt", "v": 1, "frames_dropped": cleared})
        await self.send_event({"type": "listening_state", "state": "listening"})
        log.info("barge-in: %d frames descartados en %.0f ms", cleared, (time.perf_counter() - t0) * 1000)

    async def respond(self, pcm: bytes):
        loop = asyncio.get_running_loop()
        t0 = time.perf_counter()
        student_text, stt_dt = await loop.run_in_executor(None, _stt_sync, pcm)
        stt_ms = int(stt_dt * 1000)
        if len(student_text.strip()) < 2:
            log.info("STT vacío, se ignora el turno")
            await self.send_event({"type": "listening_state", "state": "listening"})
            return
        log.info("STT (%d ms): %s", stt_ms, student_text)
        self.history.append({"role": "user", "content": student_text})
        await self.send_event({"type": "student_transcript", "text": student_text,
                               "metrics": {"stt_ms": stt_ms}})

        await self.send_event({"type": "listening_state", "state": "thinking"})
        answer, llm_dt = await call_llm(self.history, student_text)
        reply = answer["reply_text"]
        correction = answer.get("correction")
        translation_es = answer.get("translation_es", "")
        emotion = answer.get("emotion", "neutral")
        llm_ms = int(llm_dt * 1000)
        self.history.append({"role": "assistant", "content": reply})

        wav_bytes, tts_dt = await synth_tts(reply)
        tts_ms = int(tts_dt * 1000)
        frames, duration_ms = wav_to_rtp_frames(wav_bytes)
        for f in frames:
            self.speaker.put(f)
        self.tts_active = True
        self.audio_seq += 1

        await self.send_event({
            "type": "assistant_response",
            "session_id": "lab-session",
            "text": reply,
            "translation_es": translation_es,
            "correction": correction,
            "emotion": emotion,
            "visemes": text_visemes(reply, duration_ms),
            "audio_seq": self.audio_seq,
            "model": "qwen3.5-4b-local",
            "metrics": {"stt_ms": stt_ms, "llm_ms": llm_ms, "tts_ms": tts_ms,
                        "utt_ms": int((time.perf_counter() - t0) * 1000)},
        })
        await self.send_event({"type": "listening_state", "state": "speaking"})
        log.info("turno (%d ms) stt=%d llm=%d tts=%d reply=%d chars",
                 int((time.perf_counter() - t0) * 1000), stt_ms, llm_ms, tts_ms, len(reply))

        async def _end_speaking():
            await asyncio.sleep(duration_ms / 1000 + 0.4)
            self.tts_active = False
            await self.send_event({"type": "listening_state", "state": "listening"})

        if self._end_speaking_task:
            self._end_speaking_task.cancel()
        self._end_speaking_task = asyncio.create_task(_end_speaking())


@app.post("/offer")
async def post_offer(body: Offer, x_lab_token: str | None = Header(default=None)):
    check_token(x_lab_token)
    from aiortc import RTCSessionDescription

    pc = RTCPeerConnection()
    peer_connections.add(pc)
    session = PeerSession()

    @pc.on("connectionstatechange")
    async def on_state_change():
        log.info("pc state: %s", pc.connectionState)
        if pc.connectionState in ("failed", "closed"):
            peer_connections.discard(pc)
            await pc.close()

    if LAB_MODE == "echo":
        @pc.on("track")
        def on_track(track):
            if track.kind == "audio":
                pc.addTrack(EchoAudioTrack(track))
    else:
        pc.addTrack(session.speaker)

        @pc.on("track")
        def on_track(track):
            if track.kind == "audio":
                asyncio.create_task(session.consume_remote(track))

    @pc.on("datachannel")
    def on_datachannel(channel):
        log.info("datachannel abierto: %s", channel.label)
        session.dc = channel

        @channel.on("message")
        def on_message(message):
            log.info("mensaje del cliente: %s", str(message)[:200])
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                data = {"raw": str(message)}
            channel.send(json.dumps({"type": "echo", "received": data}))

        asyncio.create_task(session.send_event({"type": "listening_state", "state": "listening"}))
        if LAB_MODE == "echo":
            channel.send(json.dumps(sample_assistant_response()))

    offer = RTCSessionDescription(sdp=body.sdp, type=body.type)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return JSONResponse(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )


@app.on_event("startup")
async def on_startup():
    if LAB_MODE == "conversation":
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _load_whisper)


@app.on_event("shutdown")
async def shutdown():
    for pc in list(peer_connections):
        await pc.close()


# Página de prueba estática en "/" (se monta al final para no tapar las rutas API)
app.mount("/", StaticFiles(directory=str(CLIENT_DIR), html=True), name="client")
