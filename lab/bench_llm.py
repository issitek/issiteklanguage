"""Benchmark rápido del LLM local del laboratorio (TD-F0-008).

Mide, por prompt: tiempo hasta el primer token (TTFT) y tokens/s aproximados,
contra el servidor llama.cpp local (API OpenAI-compatible, P100).

Uso:
  python3 lab/bench_llm.py [--url http://127.0.0.1:9080/v1] [--model qwen3.5-4b]
"""

import argparse
import json
import time
import urllib.request

SYSTEM = (
    "Eres 'Alex', profesor de inglés para mexicanos. Nivel A2. Corriges con amabilidad. "
    "Responde SOLO un JSON válido con estas claves: "
    '{"reply_text": string, "correction": {"original": string, "corrected": string, "reason": string} | null, '
    '"emotion": "neutral|encouraging|surprised|confused|approving"}. Sin texto adicional.'
)

PROMPTS = [
    "Yesterday I go to the school.",
    "I have saw that movie three times.",
    "She don't like coffee.",
    "I work in a office near downtown.",
    "How many money do you need?",
    "I am agree with you.",
]


def stream_prompt(base_url: str, model: str, user: str):
    body = json.dumps({
        "model": model,
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.4,
        # Qwen3.5 piensa por defecto: sin esto el TTFT se va a segundos de reasoning
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    }).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t_start = time.perf_counter()
    t_first = None
    chunks = 0
    usage = {}
    with urllib.request.urlopen(req, timeout=120) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            delta = (obj.get("choices") or [{}])[0].get("delta", {})
            if delta.get("content"):
                if t_first is None:
                    t_first = time.perf_counter()
                chunks += 1
            if obj.get("usage"):
                usage = obj["usage"]
    t_end = time.perf_counter()
    return t_start, t_first, t_end, chunks, usage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:9080/v1")
    ap.add_argument("--model", default="qwen3.5-4b")
    args = ap.parse_args()

    print(f"LLM bench @ {args.url} model={args.model}")
    print(f"{'prompt':<46} {'TTFT':>7} {'total':>7} {'tok/s':>7}")
    for p in PROMPTS:
        t0, t1, t2, chunks, usage = stream_prompt(args.url, args.model, p)
        total = t2 - t0
        ttft = (t1 - t0) if t1 else float("nan")
        completion = usage.get("completion_tokens", chunks) or chunks
        toks = completion / total if total > 0 else 0.0
        print(f"{p[:46]:<46} {ttft:6.2f}s {total:6.2f}s {toks:7.1f}")


if __name__ == "__main__":
    main()
