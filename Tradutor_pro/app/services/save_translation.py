#save_translation.py
from app.database.connection import SessionLocal
from app.models.translation import Translation

def save_translation(
    file_name,
    source_language,
    target_language,
    original_text,
    translated_text
):

    db = SessionLocal()

    item = Translation(
        file_name=file_name,
        source_language=source_language,
        target_language=target_language,
        original_text=original_text,
        translated_text=translated_text
    )

    db.add(item)

    db.commit()

    db.close()