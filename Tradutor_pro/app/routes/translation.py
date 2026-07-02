from fastapi import APIRouter
from pydantic import BaseModel

from app.services.translator import translate_text
from app.services.grammar import review_text as improve_text
from app.services.save_translation import save_translation

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str
    source: str = "auto"
    target: str = "pt"


@router.post("/translate")
def translate(payload: TranslateRequest):
    draft = translate_text(
        payload.text,
        payload.source,
        payload.target,
    )

    translated = improve_text(draft, payload.target)

    save_translation(
        file_name=None,
        source_language=payload.source,
        target_language=payload.target,
        original_text=payload.text,
        translated_text=translated,
    )

    return {"translated_text": translated}