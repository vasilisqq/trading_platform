from pydantic import SecretStr, model_validator, ConfigDict
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_NAME: str
    APP_NAME: str
    PUBLIC_URL: str
    SECRET_KEY: SecretStr
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    REDIS_URL: SecretStr
    RESEND_API_KEY: SecretStr
    TEMPLATE_ID: str
    TEMPLATE_PASSWORD_ID: str
    EXPIRE_EMAIL_HOURS: int
    GOOGLE_CLIENT_ID: SecretStr
    GOOGLE_CLIENT_SECRET: SecretStr
    GOOGLE_REDIRECT_URI: SecretStr

    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    DATABASE_URL: SecretStr = SecretStr("")
    SYNC_DATABASE_URL: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def assemble_database_url(self) -> "Settings":
        password = quote_plus(self.DB_PASSWORD.get_secret_value())
        url = f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        sync_url = f"postgresql+psycopg2://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        self.DATABASE_URL = SecretStr(url)
        self.SYNC_DATABASE_URL = SecretStr(sync_url)
        return self


settings = Settings()
