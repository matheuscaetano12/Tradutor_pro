from sqlalchemy import (
    Column,
    Integer,
    String,
    Text
)

from app.models.base import Base

class Translation(Base):

    __tablename__ = "translations"

    id = Column(Integer, primary_key=True)

    file_name = Column(String)

    source_language = Column(String)

    target_language = Column(String)

    original_text = Column(Text)

    translated_text = Column(Text)