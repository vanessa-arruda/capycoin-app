from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    username: str
    password: str
    host: str
    port: int
    dbname: str

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "../../.env")


settings = Settings()
