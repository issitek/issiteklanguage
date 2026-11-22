"""Duración de WAV, incluido el encabezado de streaming de Kokoro."""

from app.tts import _tone_wav, wav_duration_ms


def test_duracion_wav_normal():
    audio = _tone_wav(250)
    assert 240 <= wav_duration_ms(audio) <= 260


def test_duracion_wav_con_nframes_desconocido():
    # Kokoro/FastAPI devuelve a veces nframes=0x7FFFFFFF; el tamaño real está
    # en los frames presentes. El offset 40 es el tamaño del chunk `data`.
    audio = bytearray(_tone_wav(250))
    audio[40:44] = (0x7FFFFFFF).to_bytes(4, "little")
    assert 240 <= wav_duration_ms(bytes(audio)) <= 260
