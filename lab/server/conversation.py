"""Pipeline conversacional del laboratorio talkdrill (Fase 0).

Es el andamiaje go/no-go del loop completo:
micrófono → VAD → faster-whisper (CPU) → AI Router-lite (LLM local llama.cpp)
→ Kokoro TTS → RTP de regreso + visemes por DataChannel + barge-in.

NO es código de producción: el LLM no recibe contexto curricular aún,
la memoria del estudiante no existe, y la voz ES no está integrada.
"""

import asyncio
import json
import logging
import math
import os
import time
import wave
from fractions import Fraction
from io import BytesIO

import av
import numpy as np
from aiohttp import ClientSession, ClientTimeout
from aiortc import MediaStreamTrack
from fractions import Fraction

log = logging.getLogger("lab-conversation")

LLM_URL = os.environ.get("LLM_URL", "http://llm:8080")
TTS_URL = os.environ.get("TTS_URL", "http://tts:8880")
SAMPLERATE_IN = 16000
SAMPLERATE_RTP = 48000
FRAME_SAMPLES_RTP = SAMPLERATE_RTP // 50  # 20 ms

SYSTEM_PROMPT = (
    "Eres 'Alex', profesor de inglés para mexicanos. Nivel A2 (el alumno ya entendió frases "
    "sencillas). Habla en INGLÉS (frases cortas y sencillas); usa español mexicano solo para "
    "aclarar algo esencial, una frase como mucho. Prioriza que el alumno hable inglés. "
    "Corriges con amabilidad. Responde SOLO un JSON válido con estas claves: "
    '{"reply_text": string (tu respuesta en INGLÉS), '
    '"translation_es": string (traducción al español de reply_text), '
    '"correction": {"original": string, "corrected": string, '
    '"reason": string} | null, "emotion": "neutral|encouraging|surprised|confused|approving|playful"}. '
    "Sin texto adicional fuera del JSON."
)

EMOTION_ALIASES = {
    "encouraged": "encouraging", "encourage": "encouraging", "encouragement": "encouraging",
    "happy": "encouraging", "excited": "surprised", "surprise": "surprised",
    "confusing": "confused", "unsure": "confused", "approve": "approving",
    "approval": "approving", "approves": "approving", "playfulness": "playful",
}
EMOTIONS = {"neutral", "encouraging", "surprised", "confused", "approving", "playful"}


def normalize_text(s: str) -> str:
    import re as _re
    s = str(s).lower().strip()
    s = _re.sub(r"[.!?¡¿,;:\"“”«»()\[\]]", "", s)
    return _re.sub(r"\s+", " ", s).strip()


def normalize_emotion(value) -> str:
    v = str(value or "").strip().lower()
    v = EMOTION_ALIASES.get(v, v)
    return v if v in EMOTIONS else "neutral"


def text_visemes(text: str, duration_ms: int) -> list[dict]:
    """Timeline de visemes heurístico: un viseme por run de caracteres.

    Se usa cuando el TTS no entrega pistas fonéticas. Silencios/barras largas → sil.
    """
    mapping = {"a": "AA", "á": "AA", "e": "EE", "i": "EE", "o": "OU", "ó": "OU", "u": "OU"}
    chars = list(text)
    if not chars:
        return [{"t_ms": 0, "id": "sil", "weight": 0.0}]
    per = duration_ms / len(chars)
    out, cur, start = [], None, 0.0
    t = 0.0
    for ch in chars:
        cl = ch.lower()
        if cl in mapping:
            idv = mapping[cl]
        elif cl in "mbp":
            idv = "B"
        elif cl in "fv":
            idv = "B"
        elif cl in ",.;:!?—–-…()\"":
            idv = "sil"
        elif cl == " ":
            idv = "sil"
        else:
            idv = "EE"
        if idv != cur:
            if cur is not None:
                out.append({"t_ms": int(start), "id": cur, "weight": 0.0 if cur == "sil" else 0.9})
            cur, start = idv, t
        t += per
    if cur is not None:
        out.append({"t_ms": int(start), "id": cur, "weight": 1.0 if cur != "sil" else 0.0})
    return out


class SpeakerTrack(MediaStreamTrack):
    """Pista de audio hacia el alumno: cola de frames o silencio (20 ms)."""

    kind = "audio"

    def __init__(self):
        super().__init__()
        self.queue: asyncio.Queue = asyncio.Queue()
        self._pts = 0

    def put(self, frame) -> None:
        self.queue.put_nowait(frame)

    def clear(self) -> int:
        count = 0
        try:
            while True:
                self.queue.get_nowait()
                count += 1
        except asyncio.QueueEmpty:
            pass
        return count

    def _silence_frame(self):
        frame = av.AudioFrame.from_ndarray(
            np.zeros((1, FRAME_SAMPLES_RTP), dtype=np.int16), format="s16", layout="mono"
        )
        frame.sample_rate = SAMPLERATE_RTP
        frame.time_base = Fraction(1, SAMPLERATE_RTP)
        return frame

    async def recv(self):
        await asyncio.sleep(0.02)
        try:
            frame = self.queue.get_nowait()
        except asyncio.QueueEmpty:
            frame = self._silence_frame()
        frame.pts = self._pts
        frame.time_base = Fraction(1, SAMPLERATE_RTP)
        self._pts += FRAME_SAMPLES_RTP
        return frame


class EnergyVAD:
    """VAD por energía con hangover (sin dependencias externas)."""

    def __init__(self, sample_rate=SAMPLERATE_IN, frame_ms=20, threshold=750,
                 speech_start_windows=3, silence_end_windows=25):
        self.threshold = threshold
        self.speech_start = speech_start_windows
        self.silence_end = silence_end_windows
        self.streak_voiced = 0
        self.streak_silence = 0
        self.in_speech = False

    def rms(self, window: np.ndarray) -> float:
        if window.size == 0:
            return 0.0
        x = window.astype(np.float32)
        return float(math.sqrt(np.mean(x * x)))

    def feed(self, window: np.ndarray) -> str | None:
        """Devuelve 'speech_start' | 'speech_end' | None."""
        voiced = self.rms(window) > self.threshold
        if not self.in_speech:
            if voiced:
                self.streak_voiced += 1
                if self.streak_voiced >= self.speech_start:
                    self.in_speech = True
                    self.streak_silence = 0
                    return "speech_start"
            else:
                self.streak_voiced = 0
            return None
        if voiced:
            self.streak_silence = 0
        else:
            self.streak_silence += 1
            if self.streak_silence >= self.silence_end:
                self.in_speech = False
                self.streak_voiced = 0
                return "speech_end"
        return None


_whisper_model = None


def _load_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        log.info("cargando faster-whisper small (cpu int8)…")
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
        log.info("faster-whisper listo")


def _stt_sync(pcm_bytes: bytes) -> tuple[str, float]:
    _load_whisper()
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    t0 = time.perf_counter()
    segments, _info = _whisper_model.transcribe(audio, language=None, beam_size=2, vad_filter=False)
    segs = list(segments)
    # Descartar ruido: si ninguna hipótesis supera el suelo de confianza, es silencio/ruido de sala
    best_logprob = max((getattr(s, "avg_logprob", -10.0) for s in segs), default=-10.0)
    if not segs or best_logprob < -1.1:
        return "", time.perf_counter() - t0
    text = " ".join(s.text.strip() for s in segs).strip()
    return text, time.perf_counter() - t0


def _resample(pcm_s16le: bytes, from_rate: int, to_rate: int, frame_ms: int = 20) -> bytes:
    """Resample PCM int16 mono usando av.AudioResampler."""
    in_frame = av.AudioFrame.from_ndarray(
        np.frombuffer(pcm_s16le, dtype=np.int16).reshape(1, -1), format="s16", layout="mono"
    )
    in_frame.sample_rate = from_rate
    resampler = av.AudioResampler(format="s16", layout="mono", rate=to_rate)
    chunks = []
    for out_frame in resampler.resample(in_frame):
        arr = out_frame.to_ndarray().reshape(-1)
        chunks.append(arr)
    if not chunks:
        return b""
    return np.concatenate(chunks).tobytes()


def wav_to_rtp_frames(wav_bytes: bytes, frame_ms: int = 20) -> tuple[list, int]:
    """WAV PCM s16 mono (24 kHz típico Kokoro) → lista de AudioFrame 48 kHz + duración ms."""
    with wave.open(BytesIO(wav_bytes), "rb") as w:
        rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        pcm = w.readframes(w.getnframes())
    assert width == 2, "esperado WAV 16-bit"
    if ch != 1:
        arr = np.frombuffer(pcm, dtype=np.int16).reshape(-1, ch).mean(axis=1).astype(np.int16)
        pcm = arr.tobytes()
    pcm_48k = _resample(pcm, rate, SAMPLERATE_RTP, frame_ms)
    samples = np.frombuffer(pcm_48k, dtype=np.int16)
    n = SAMPLERATE_RTP * frame_ms // 1000
    frames = []
    for i in range(0, len(samples) - n + 1, n):
        arr = samples[i:i + n].reshape(1, n)
        f = av.AudioFrame.from_ndarray(arr, format="s16", layout="mono")
        f.sample_rate = SAMPLERATE_RTP
        f.time_base = Fraction(1, SAMPLERATE_RTP)
        f.pts = (i // n) * n
        frames.append(f)
    duration_ms = int(1000 * len(samples) / SAMPLERATE_RTP)
    return frames, duration_ms


async def call_llm(history: list[dict], student_text: str) -> tuple[dict, float]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": student_text})
    t0 = time.perf_counter()
    timeout = ClientTimeout(total=12)
    async with ClientSession(timeout=timeout) as http:
        async with http.post(f"{LLM_URL}/v1/chat/completions", json={
            "model": "qwen3.5-4b",
            "temperature": 0.4,
            "max_tokens": 200,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": messages,
        }) as resp:
            data = await resp.json()
    dt = time.perf_counter() - t0
    raw = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    try:
        content = raw.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        parsed = json.loads(content)
    except json.JSONDecodeError:
        log.warning("LLM no devolvió JSON: %s", raw[:300])
        parsed = {"reply_text": "Sorry, could you say that again?", "correction": None, "emotion": "neutral"}
    parsed["emotion"] = normalize_emotion(parsed.get("emotion"))
    if not isinstance(parsed.get("reply_text"), str) or not parsed["reply_text"].strip():
        parsed = {"reply_text": "Sorry, could you say that again?", "correction": None, "emotion": "neutral"}
    correction = parsed.get("correction")
    if isinstance(correction, dict) and correction.get("corrected") and correction.get("original"):
        if normalize_text(correction["corrected"]) == normalize_text(correction["original"]):
            parsed["correction"] = None  # la frase ya era correcta: no hay corrección
    elif not (isinstance(correction, dict) and correction.get("corrected")):
        parsed["correction"] = None
    if not isinstance(parsed.get("translation_es"), str):
        parsed["translation_es"] = ""
    return parsed, dt


async def synth_tts(text: str) -> tuple[bytes, float]:
    t0 = time.perf_counter()
    timeout = ClientTimeout(total=30)
    async with ClientSession(timeout=timeout) as http:
        async with http.post(f"{TTS_URL}/v1/audio/speech", json={
            "model": "kokoro",
            "voice": "af_heart",
            "input": text,
            "response_format": "wav",
        }) as resp:
            wav_bytes = await resp.read()
    return wav_bytes, time.perf_counter() - t0
