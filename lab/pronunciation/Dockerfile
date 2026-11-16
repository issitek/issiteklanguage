# talkdrill — PoC OpenPronounce (Fase 0b) · CPU aislada de la P100
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg espeak-ng build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
# tts-kokoro = voz de referencia offline (af_heart); sin gTTS ni red por frase
# en-core-web-sm evita que openpronounce la pip-instale en runtime (red)
RUN pip install --no-cache-dir "openpronounce[tts-kokoro]" \
 && python -m spacy download en_core_web_sm

ENV OPENPRONOUNCE_TTS=kokoro
ENV OPENPRONOUNCE_TTS_VOICE=af_heart
ENV OPENPRONOUNCE_DEVICE=cpu
ENV HF_HOME=/models

WORKDIR /data
ENTRYPOINT ["openpronounce"]
