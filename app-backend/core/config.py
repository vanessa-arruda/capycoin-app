from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env"
    )

    username: str
    password: str
    host: str
    port: int
    dbname: str

    email_backend: Literal["console"] = "console"
    # Web app address, used for links in emails.
    app_url: str = "http://localhost:5173"
    # Browser origins allowed to call the API (CORS). JSON list in .env.
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg2",
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.dbname,
        )


settings = Settings()
