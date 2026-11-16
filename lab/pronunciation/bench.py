"""Benchmark por lote para OpenPronounce (Fase 0b).

Corre DENTRO del contenedor talkdrill-lab-pronunciation, con la red cortada
(offline real; modelos ya en la caché). Uso:

  docker volume ls | grep pronunciation          # confirmar nombre del volumen
  docker run --rm --network none \
    -v lab_pronunciation-models:/models \
    -v "$PWD/lab/data/pronunciation:/data:ro" \
    -v "$PWD/lab/pronunciation:/poc:ro" \
    --entrypoint python talkdrill-lab-pronunciation:dev \
    /poc/bench.py --dir /data/control-kokoro \
      --manifest /data/control-kokoro/control-kokoro-manifest.json \
      --json-out /data/results-kokoro.json
"""

import argparse
import json
import time
from pathlib import Path

from openpronounce import compare_audio_with_text, load_audio

p = argparse.ArgumentParser()
p.add_argument("--dir", required=True)
p.add_argument("--manifest", required=True)
p.add_argument("--json-out", default=None)
p.add_argument("--limit", type=int, default=0)
args = p.parse_args()

with open(args.manifest, encoding="utf-8") as f:
    mani = json.load(f)
items = mani["phrases"] if isinstance(mani, dict) and "phrases" in mani else mani
if args.limit:
    items = items[: args.limit]

results = []
t_start = time.perf_counter()
for item in items:
    wav = str(Path(args.dir) / item["file"])
    text = item["text"]
    t0 = time.perf_counter()
    try:
        sound = load_audio(wav)
        r = compare_audio_with_text(sound, text)
        dt = time.perf_counter() - t0
        diff = r["differences"]
        results.append({
            "id": item.get("id", "?"), "file": item["file"], "text": text,
            "score": round(float(r["score"]), 2),
            "per": diff["phoneme_error_rate"], "wer": diff["word_error_rate"],
            "errors": [e.get("word") for e in diff["errors"]],
            "seconds": round(dt, 2),
        })
        print(f"{item.get('id', '?'):>3}  score={results[-1]['score']:6.2f}  PER={results[-1]['per']:.2f}  "
              f"WER={results[-1]['wer']:.2f}  err={len(results[-1]['errors'])}  {dt:5.2f}s  | {text[:44]}")
    except Exception as exc:
        results.append({"id": item.get("id", "?"), "file": item["file"], "error": str(exc)})
        print(f"{item.get('id', '?'):>3}  ERROR {exc}")

n = len(results)
ok = [r for r in results if "score" in r]
lat = sorted(r["seconds"] for r in ok)
p50 = lat[len(lat) // 2] if lat else 0
p95 = lat[int(len(lat) * 0.95) - 1] if lat else 0
mean_score = sum(r["score"] for r in ok) / len(ok) if ok else 0
total = time.perf_counter() - t_start
print(f"\nn={n}  ok={len(ok)}  mean_score={mean_score:.2f}  p50={p50}s  p95={p95}s  total={total:.1f}s")
if args.json_out:
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump({"results": results, "summary": {"mean_score": mean_score, "p50": p50, "p95": p95}},
                  f, ensure_ascii=False, indent=2)
    print("json-out:", args.json_out)
