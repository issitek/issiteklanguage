"""E2E del loop conversacional completo (TD-F0-011).

El cliente aiortc envía lab/data/s02.wav ("Yesterday I went to school.", voz
Kokoro) como si fuera el micrófono del alumno. El servidor lab-server en modo
`conversation` debe: VAD → STT → LLM → TTS y devolver audio + DataChannel
`assistant_response`.

Uso (dentro del contenedor lab-server, con /data montado):
  LAB_TOKEN=… LAB_SERVER_URL=http://lab-server:9090 \
    python /app/tests/test_conversation_e2e.py [s02.wav]
"""

import asyncio
import json
import os
import sys
import time
from fractions import Fraction

import av
import numpy as np
import urllib.request
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack

BASE = os.environ.get("LAB_SERVER_URL", "http://lab-server:9090")
TOKEN = os.environ.get("LAB_TOKEN", "dev-token")
WAV = os.environ.get("STUDENT_WAV", "/data/s02.wav")


def http(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method="POST" if data is not None else "GET",
        headers={"Content-Type": "application/json", "x-lab-token": TOKEN},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


class WavTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, path):
        super().__init__()
        import wave as wavemod

        with wavemod.open(path) as w:
            rate = w.getframerate()
            raw = w.readframes(w.getnframes())
        samples = np.frombuffer(raw, dtype=np.int16)
        if rate != 48000:
            frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format="s16", layout="mono")
            frame.sample_rate = rate
            res = av.AudioResampler(format="s16", layout="mono", rate=48000)
            out = [f.to_ndarray().reshape(-1) for f in res.resample(frame)]
            samples = np.concatenate(out) if out else samples
        self.samples = samples
        self._i = 0

    async def recv(self):
        await asyncio.sleep(0.02)
        n = 960
        start = self._i * n
        if start < len(self.samples):
            chunk = self.samples[start:start + n]
            if len(chunk) < n:
                chunk = np.pad(chunk, (0, n - len(chunk)))
        else:
            chunk = np.zeros(n, dtype=np.int16)
        frame = av.AudioFrame.from_ndarray(chunk.reshape(1, n), format="s16", layout="mono")
        frame.sample_rate = 48000
        frame.pts = self._i * n
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
            while len(received) < 500:
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

    pc.addTrack(WavTrack(WAV))
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    while pc.iceGatheringState != "complete":
        await asyncio.sleep(0.05)

    answer = http("/offer", {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})
    await pc.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"], type=answer["type"]))

    deadline = time.time() + 90
    answer_seen = None
    while time.time() < deadline:
        for m in dc_messages:
            try:
                parsed = json.loads(m)
            except json.JSONDecodeError:
                continue
            if parsed.get("type") == "assistant_response":
                answer_seen = parsed
                break
        if answer_seen and len(received) >= 50:
            break
        await asyncio.sleep(0.2)

    ok = (
        pc.connectionState == "connected"
        and answer_seen is not None
        and bool(answer_seen.get("text"))
        and len(received) >= 50
    )
    print(json.dumps({
        "connectionState": pc.connectionState,
        "audio_frames_profesor": len(received),
        "assistant_text": (answer_seen or {}).get("text"),
        "correction": (answer_seen or {}).get("correction"),
        "emotion": (answer_seen or {}).get("emotion"),
        "visemes": len((answer_seen or {}).get("visemes", [])),
        "metrics": (answer_seen or {}).get("metrics"),
        "pass": ok,
    }, ensure_ascii=False, indent=2))
    await pc.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
