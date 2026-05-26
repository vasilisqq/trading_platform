from pydantic import SecretStr, model_validator, PostgresDsn
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_NAME: str
    APP_NAME: str

    class Config:
        env_file = ".env"
        case_sensitive = True

    # Это поле НЕ читается из .env, а вычисляется
    DATABASE_URL: SecretStr = SecretStr("")
    SYNC_DATABASE_URL: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def assemble_database_url(self) -> "Settings":
        # url_quote автоматически кодирует спецсимволы в пароле!

        password = quote_plus(self.DB_PASSWORD.get_secret_value())
        url = f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        sync_url = f"postgresql+psycopg2://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        self.DATABASE_URL = SecretStr(url)
        self.SYNC_DATABASE_URL = SecretStr(sync_url)
        return self


settings = Settings()
