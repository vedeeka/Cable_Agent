from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise AI OS"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "enterprise_user"
    POSTGRES_PASSWORD: str = "enterprise_password"
    POSTGRES_DB: str = "enterprise_db"
    POSTGRES_PORT: str = "5432"

    # Authentication
    SECRET_KEY: str = "a_very_secret_key"
    GOOGLE_CLIENT_ID: str = "862296237561-fhjgg5lt0ag94ki9u9b2qu3cjqr5m1qi.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = "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"
    GEMINI_API_KEY: str | None = None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
