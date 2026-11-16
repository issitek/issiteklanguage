"""Evaluación del set de 30 prompts es-MX (TD-F0-008 / TD-F0-019).

Lee los casos de docs/fase0/prompts-es-mx.md (tabla markdown), los pasa al
llama.cpp local con el prompt pedagógico del laboratorio y evalúa:
1. JSON válido con claves §8.3 (reply_text, correction, emotion)
2. correction presente y `corrected` igual al esperado (o alternativa antes de " / ")
3. emotion dentro del whitelist del maestro §8.3

Uso:
  python3 lab/eval_prompts.py [--url http://127.0.0.1:9080/v1] [--model qwen3.5-4b]
"""

import argparse
import json
import re
import time
import urllib.request

SYSTEM = (
    "Eres 'Alex', profesor de inglés para mexicanos. Nivel A2. Corriges con amabilidad. "
    "Responde SOLO un JSON válido con estas claves: "
    '{"reply_text": string, "correction": {"original": string, "corrected": string, "reason": string} | null, '
    '"emotion": "neutral|encouraging|surprised|confused|approving|playful"}. Sin texto adicional.'
)

SYSTEM_FEWSHOT = (
    "Eres 'Alex', profesor de inglés para mexicanos. Nivel A2. Corriges con amabilidad. "
    "Responde SOLO un JSON válido con estas claves: "
    '{"reply_text": string, "correction": {"original": string, "corrected": string, "reason": string} | null, '
    '"emotion": "neutral|encouraging|surprised|confused|approving|playful"}. Sin texto adicional.\n'
    "Ejemplos:\n"
    'Usuario: "She don\'t like coffee."\n'
    'Respuesta: {"reply_text": "¡Casi! Con ' +
    'she/he/it el auxiliar es doesn\'t.", "correction": {"original": "She don\'t like coffee.", "corrected": "She doesn\'t like coffee.", "reason": "3rd person singular"}, "emotion": "encouraging"}\n'
    'Usuario: "I am agree with you."\n'
    'Respuesta: {"reply_text": "En inglés se dice \'I agree\'.", "correction": {"original": "I am agree with you.", "corrected": "I agree with you.", "reason": "calco del español"}, "emotion": "encouraging"}'
)

EMOTION_WHITELIST = {"neutral", "encouraging", "surprised", "confused", "approving", "playful"}


def parse_cases(path):
    cases = []
    row = re.compile(r"^\|\s*(\d+)\s*\|(.*?)\|(.*?)\|(.*?)\|\s*$")
    for line in open(path, encoding="utf-8"):
        m = row.match(line.rstrip("\n"))
        if not m:
            continue
        num, phrase, expected, kind = (c.strip() for c in m.groups())
        cases.append((int(num), phrase, expected, kind))
    return cases


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[.!?¡¿,;:\"“”«»()\[\]]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def expected_alternatives(expected: str):
    # "A / B / C" son alternativas aceptables
    return [normalize(part) for part in expected.split(" / ")]


def call_llm(base_url: str, model: str, phrase: str, system: str, timeout=120):
    body = json.dumps({
        "model": model,
        "temperature": 0.2,
        "max_tokens": 250,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": phrase},
        ],
    }).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    dt = time.perf_counter() - t0
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    return content, dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:9080/v1")
    ap.add_argument("--model", default="qwen3.5-4b")
    ap.add_argument("--cases", default="docs/fase0/prompts-es-mx.md")
    ap.add_argument("--fewshot", action="store_true", help="usa SYSTEM_FEWSHOT (2 ejemplos)")
    args = ap.parse_args()
    system = SYSTEM_FEWSHOT if args.fewshot else SYSTEM

    cases = parse_cases(args.cases)
    print(f"Evaluando {len(cases)} casos contra {args.url} ({args.model})\n")
    json_ok = 0
    correction_ok = 0
    emotion_ok = 0
    rows = []
    for num, phrase, expected, kind in cases:
        raw, dt = call_llm(args.url, args.model, phrase, system)
        verdict = {"json": False, "correction": False, "emotion": None}
        corrected = None
        try:
            content = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
            data = json.loads(content)
            verdict["json"] = True
            corr = data.get("correction") or {}
            corrected = corr.get("corrected")
            emotion = data.get("emotion")
            verdict["emotion"] = emotion in EMOTION_WHITELIST
            expected_norms = expected_alternatives(expected)
            if corrected and normalize(corrected) in expected_norms:
                verdict["correction"] = True
        except json.JSONDecodeError:
            pass
        json_ok += verdict["json"]
        correction_ok += verdict["correction"]
        emotion_ok += bool(verdict["emotion"])
        rows.append((num, verdict["json"], verdict["correction"], bool(verdict["emotion"]),
                     corrected, expected, dt))
        mark = lambda ok: "✓" if ok else "✗"
        print(f"{num:02d} [json{mark(verdict['json'])} corr{mark(verdict['correction'])} "
              f"emo{mark(bool(verdict['emotion']))}] {dt:5.2f}s | exp: {expected[:60]} | got: {str(corrected)[:60]}")

    n = len(cases)
    print(f"\nJSON válido:      {json_ok}/{n} ({100 * json_ok / n:.0f}%)")
    print(f"Corrección exacta: {correction_ok}/{n} ({100 * correction_ok / n:.0f}%)")
    print(f"Emotion en whitelist: {emotion_ok}/{n}")
    print("Criterios TD-F0-008: JSON ≥ 95% (29/30) · corrección ≥ 80% (24/30)")


if __name__ == "__main__":
    main()
