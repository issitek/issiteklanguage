"""Servidor de laboratorio talkdrill (Fase 0).

Propósito: demostrar la conexión WebRTC bidireccional navegador ↔ aiortc:
- POST /offer                : el cliente manda su SDP offer; devolvemos SDP answer
- Audio RTP                  : el audio del alumno vuelve (echo) por el mismo PC
- DataChannel "events"       : recibimos mensajes del cliente y enviamos eventos
                               pedagógicos de prueba (assistant_response con visemas)
- POST /ice-credentials      : cuaja iceServers con HMAC de vida corta (patrón mxerp)
- POST /webrtc/ice-report    : anillo en memoria de telemetría de conexión (max 50)
- GET  /webrtc/ice-report/recent
- GET  /                     : página de prueba (lab/client)

NO ES EL PRODUCTO: no hace STT/LLM/TTS todavía. Es el andamiaje go/no-go.
"""

import asyncio
import json
import logging
import os
import time
from collections import deque
from pathlib import Path

from aiortc import RTCPeerConnection, MediaStreamTrack
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ice import ice_servers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lab-server")

LAB_TOKEN = os.environ.get("LAB_TOKEN", "dev-token")
CLIENT_DIR = Path(__file__).resolve().parent.parent / "client"

app = FastAPI(title="talkdrill lab (Fase 0)")

ice_reports: deque = deque(maxlen=50)
peer_connections: set[RTCPeerConnection] = set()


def check_token(x_lab_token: str | None):
    if x_lab_token != LAB_TOKEN:
        raise HTTPException(status_code=401, detail="x-lab-token inválido")


@app.get("/health")
async def health():
    return {"status": "ok", "peer_connections": len(peer_connections)}


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
    """Reenvía los frames de audio del alumno de vuelta (echo de laboratorio)."""

    kind = "audio"

    def __init__(self, remote: MediaStreamTrack):
        super().__init__()
        self._remote = remote

    async def recv(self):
        return await self._remote.recv()


def sample_assistant_response() -> dict:
    """Evento pedagógico de prueba con timeline de visemas (esquema RN-001)."""
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


@app.post("/offer")
async def post_offer(body: Offer, x_lab_token: str | None = Header(default=None)):
    check_token(x_lab_token)
    from aiortc import RTCSessionDescription

    pc = RTCPeerConnection()
    peer_connections.add(pc)

    @pc.on("connectionstatechange")
    async def on_state_change():
        log.info("pc state: %s", pc.connectionState)
        if pc.connectionState in ("failed", "closed"):
            peer_connections.discard(pc)
            await pc.close()

    @pc.on("track")
    def on_track(track):
        log.info("track remoto recibido: kind=%s", track.kind)
        if track.kind == "audio":
            pc.addTrack(EchoAudioTrack(track))
            log.info("echo track añadida")

    @pc.on("datachannel")
    def on_datachannel(channel):
        log.info("datachannel abierto: %s", channel.label)

        @channel.on("message")
        def on_message(message):
            log.info("mensaje del cliente: %s", str(message)[:200])
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                data = {"raw": str(message)}
            channel.send(json.dumps({"type": "echo", "received": data}))

        # Eventos pedagógicos de prueba al abrir el canal
        channel.send(json.dumps({"type": "listening_state", "v": 1, "state": "listening"}))
        channel.send(json.dumps(sample_assistant_response()))

    offer = RTCSessionDescription(sdp=body.sdp, type=body.type)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return JSONResponse(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )


@app.on_event("shutdown")
async def shutdown():
    for pc in list(peer_connections):
        await pc.close()


# Página de prueba estática en "/" (se monta al final para no tapar las rutas API)
app.mount("/", StaticFiles(directory=str(CLIENT_DIR), html=True), name="client")
