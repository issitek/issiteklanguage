"""Test E2E automatizado del laboratorio (sin dispositivos físicos).

Verifica el andamiaje TD-F0-003/004:
- La conexión WebRTC contra aiortc llega a "connected"
- El servidor devuelve el audio del alumno (echo) por RTP
- El DataChannel entrega eventos pedagógicos de prueba (assistant_response)

Uso (dentro del contenedor lab-server):
  LAB_TOKEN=... python /app/tests/test_echo_e2e.py
"""

import asyncio
import json
import os
import sys
import time
from fractions import Fraction

import numpy as np
import urllib.request
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import AudioFrame

BASE = os.environ.get("LAB_SERVER_URL", "http://127.0.0.1:9090")
TOKEN = os.environ.get("LAB_TOKEN", "dev-token")


def http(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method="POST" if data is not None else "GET",
        headers={"Content-Type": "application/json", "x-lab-token": TOKEN},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


class SineTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, freq=440.0, seconds=8.0):
        super().__init__()
        self._freq = freq
        self._i = 0
        self._max = int(seconds * 50)  # 20 ms por frame

    async def recv(self):
        await asyncio.sleep(0.02)
        n = 960
        t0 = self._i * n
        samples = (np.sin(2 * np.pi * self._freq * (np.arange(n) + t0) / 48000) * 12000).astype(np.int16)
        frame = AudioFrame.from_ndarray(samples.reshape(1, n), format="s16", layout="mono")
        frame.sample_rate = 48000
        frame.pts = t0
        frame.time_base = Fraction(1, 48000)
        self._i += 1
        return frame


async def main():
    pc = RTCPeerConnection()
    received = []
    dc_messages = []

    @pc.on("track")
    def on_track(track):
        if track.kind != "audio":
            return

        async def reader():
            while len(received) < 200:
                try:
                    frame = await asyncio.wait_for(track.recv(), timeout=5)
                except Exception:
                    break
                received.append(frame)

        asyncio.ensure_future(reader())

    dc = pc.createDataChannel("events", ordered=True)

    @dc.on("message")
    def on_message(message):
        dc_messages.append(str(message))

    pc.addTrack(SineTrack())
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    while pc.iceGatheringState != "complete":
        await asyncio.sleep(0.05)

    answer = http("/offer", {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})
    await pc.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"], type=answer["type"]))

    deadline = time.time() + 25
    while time.time() < deadline:
        if pc.connectionState == "connected" and len(received) >= 20 and dc_messages:
            break
        await asyncio.sleep(0.1)

    types = [json.loads(m).get("type") for m in dc_messages]
    ok = (
        pc.connectionState == "connected"
        and len(received) >= 20
        and "assistant_response" in types
    )
    print(json.dumps({
        "connectionState": pc.connectionState,
        "audio_frames_recibidos": len(received),
        "tipos_datachannel": types,
        "pass": ok,
    }, ensure_ascii=False))
    await pc.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
