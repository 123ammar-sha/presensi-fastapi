from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    token_menit: int = 480
    database_url: str = "sqlite:///presensi.db"
    face_threshold: float = 0.5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()