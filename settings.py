from pydantic import SecretStr, model_validator, PostgresDsn
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr
    DB_NAME: str = "trade_db"
    
    # Это поле НЕ читается из .env, а вычисляется
    DATABASE_URL: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def assemble_database_url(self) -> "Settings":
        # url_quote автоматически кодирует спецсимволы в пароле!
        from urllib.parse import quote_plus
        
        password = quote_plus(self.DB_PASSWORD.get_secret_value())
        url = f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        
        self.DATABASE_URL = SecretStr(url)
        return self