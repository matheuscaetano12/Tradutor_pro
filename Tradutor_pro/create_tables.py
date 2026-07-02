from app.database.connection import engine

from app.models.user import User
from app.models.translation import Translation

from app.models.base import Base

Base.metadata.create_all(bind=engine)

print("Tabelas criadas!")