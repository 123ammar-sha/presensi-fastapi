from sqlmodel import SQLModel, create_engine

from config import settings

engine = create_engine(settings.database_url)

def buat_tabel():
    SQLModel.metadata.create_all(engine)
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_absen_user_tgl "
                "ON absensi (user_id, tanggal)"
            )