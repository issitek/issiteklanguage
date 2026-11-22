"""Audio de referencia (TTS) cacheado."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import TtsOut
from ..tts import TtsService

router = APIRouter(prefix="/tts", tags=["tts"])


@router.get("/reference", response_model=TtsOut)
def reference(
    text: str,
    voice_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TtsOut:
    result = TtsService(db).reference(text, voice_id)
    return TtsOut(**result)


@router.get("/voices")
def voices(user: User = Depends(get_current_user)) -> list[dict]:
    return [
        {"id": "af_heart", "label": "Kokoro · af_heart", "locale": "en-US"},
        {"id": "af_bella", "label": "Kokoro · af_bella", "locale": "en-US"},
        {"id": "am_michael", "label": "Kokoro · am_michael", "locale": "en-US"},
    ]
