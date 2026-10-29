from sqlmodel import SQLModel, create_engine

from config import settings

engine = create_engine(settings.database_url)

def buat_tabel():
    SQLModel.metadata.create_all(engine)