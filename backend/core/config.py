from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: AnyUrl = "postgresql+psycopg2://postgres:postgres@localhost:5432/t2_schedule"
    JWT_SECRET_KEY: str = "CHANGE_ME_SECRET"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    AUTO_CREATE_SCHEMA: bool = False
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/integrations/google/callback"
    GOOGLE_CALENDAR_SCOPES: str = (
        "openid email https://www.googleapis.com/auth/calendar.readonly"
    )
    GOOGLE_OAUTH_SUCCESS_REDIRECT_URL: str = ""
    GOOGLE_OAUTH_ERROR_REDIRECT_URL: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

