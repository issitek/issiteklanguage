"""Bench STT del laboratorio (TD-F0-006).

Transcribe los WAV de lab/data contra el manifiesto esperado y reporta:
- latencia por archivo y total
- hipótesis vs texto esperado (WER simple por palabras)

Uso (con la imagen construida):
  docker build -t talkdrill-lab-stt lab/stt
  docker run --rm -v $PWD/lab/data:/data:ro talkdrill-lab-stt --dir /data --manifest /data/manifest.json
  # plus el wav es-MX de VozNativa (espeak-ng, no voz humana):
  docker run --rm -v /home/dev/share/VozNativa/scratch:/es:ro talkdrill-lab-stt --file /es/bench-es.wav --lang es
"""

import argparse
import json
import re
import time

from faster_whisper import WhisperModel


def wer(ref: str, hyp: str) -> float:
    norm = lambda s: re.findall(r"[\w']+", s.lower())
    r, h = norm(ref), norm(hyp)
    if not r:
        return 0.0
    # Levenshtein por palabras
    d = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        prev, d = d, [i] + [0] * len(h)
        for j, hw in enumerate(h, 1):
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev[j - 1] + (rw != hw))
    return d[-1] / len(r)


def transcribe_one(model, path, lang=None):
    t0 = time.perf_counter()
    segments, _info = model.transcribe(path, language=lang, beam_size=5, vad_filter=False)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    dt = time.perf_counter() - t0
    return text, dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--manifest")
    ap.add_argument("--file")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--model", default="small")
    args = ap.parse_args()

    print(f"faster-whisper model={args.model} (cpu, int8)")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    if args.file:
        text, dt = transcribe_one(model, args.file, lang=args.lang)
        print(f"{args.file}\n  hipótesis: {text}\n  latencia: {dt:.2f}s")
        return

    expected = json.load(open(args.manifest))
    total_wer = 0.0
    n = 0
    for wav, ref in sorted(expected.items()):
        path = f"{args.dir}/{wav}"
        text, dt = transcribe_one(model, path, lang="en")
        e = wer(ref, text)
        total_wer += e
        n += 1
        ok = "OK " if e == 0 else "ERR"
        print(f"[{ok}] {wav:10} WER={e:.2f} {dt:5.2f}s | hyp: {text}")
    print(f"\nMedia WER (n={n}): {total_wer / max(n, 1):.3f}")


if __name__ == "__main__":
    main()
