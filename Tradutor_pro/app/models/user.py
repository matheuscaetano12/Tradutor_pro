from sqlalchemy import Column,Integer,String
from app.models.base import Base

class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    name = Column(String(100))

    email = Column(
        String(150),
        unique=True
    )

    password = Column(String(255))