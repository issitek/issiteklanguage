#!/usr/bin/env python3
"""Genera los controles A/B/C/D para el PoC (solo stdlib, sin dependencias).

A) Mismatch: el WAV se evalúa contra una FRASE EQUIVOCADA → deben aparecer errores y score bajo
B) Ruido: el WAV con ruido blanco a SNR 20 / 10 dB → estabilidad del score
C) Truncado: primeros 0.8 s → señal débil/incompleta
D) Volumen bajo: -15 dB → sensibilidad al gain

Salidas en lab/data/pronunciation/controls/
"""

import json
import math
import random
import wave
from pathlib import Path

BASE = Path(__file__).resolve().parent / ".." / "data" / "pronunciation"
CONTROL = BASE / "controls"
CONTROL.mkdir(parents=True, exist_ok=True)
random.seed(20261116)


def read_wav(path):
    with wave.open(str(path)) as w:
        return w.getframerate(), w.getnchannels(), w.getsampwidth(), w.readframes(w.getnframes())


def write_wav(path, rate, ch, width, frames):
    with wave.open(str(path), "wb") as w:
        w.setframerate(rate)
        w.setnchannels(ch)
        w.setsampwidth(width)
        w.writeframes(frames)


def to_samples(frames):
    return [int.from_bytes(frames[i:i + 2], "little", signed=True) for i in range(0, len(frames), 2)]


def to_frames(samples):
    return b"".join(max(-32768, min(32767, int(s))).to_bytes(2, "little", signed=True) for s in samples)


manifest = []

# A) mismatch
think_wav = BASE / "smoke" / "smoke-think.wav"
how_wav = BASE / "smoke" / "smoke-howareyou.wav"
import shutil
shutil.copy(think_wav, CONTROL / "smoke-think.wav")
shutil.copy(how_wav, CONTROL / "smoke-howareyou.wav")
manifest.append({"id": "A1", "file": "smoke-think.wav", "text": "How are you?",
                 "expected_behavior": "score bajo + errores detectados"})
manifest.append({"id": "A2", "file": "smoke-howareyou.wav", "text": "I think this is the right thing.",
                 "expected_behavior": "score bajo + errores detectados"})

# B) ruido a SNR 20 / 10 dB
rate, ch, width, frames = read_wav(think_wav)
sig = to_samples(frames)
p_sig = sum(s * s for s in sig) / len(sig)
for snr_db in (20, 10):
    p_noise = p_sig / (10 ** (snr_db / 10))
    sigma = math.sqrt(p_noise)
    noisy = [s + int(random.gauss(0, sigma)) for s in sig]
    out = CONTROL / f"noise-snr{snr_db}.wav"
    write_wav(out, rate, ch, width, to_frames(noisy))
    manifest.append({"id": f"B{20 if snr_db == 20 else 10}", "file": out.name,
                     "text": "I think this is the right thing.",
                     "expected_behavior": "score algo menor; degradación acotada"})

# C) truncado 0.8 s
trunc = sig[: int(0.8 * rate)]
out = CONTROL / "truncated.wav"
write_wav(out, rate, ch, width, to_frames(trunc))
manifest.append({"id": "C1", "file": out.name, "text": "I think this is the right thing.",
                 "expected_behavior": "score bajo / errores por frase incompleta"})

# D) -15 dB
quiet = [int(s * 10 ** (-15 / 20)) for s in sig]
out = CONTROL / "quiet.wav"
write_wav(out, rate, ch, width, to_frames(quiet))
manifest.append({"id": "D1", "file": out.name, "text": "I think this is the right thing.",
                 "expected_behavior": "score similar; robustez al gain"})

with open(CONTROL / "controls-manifest.json", "w", encoding="utf-8") as f:
    json.dump({"phrases": [m for m in manifest]}, f, ensure_ascii=False, indent=2)
print("controles generados en", CONTROL)
