from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    oracle_user: str
    oracle_password: str
    oracle_dsn: str
    id_finalidade_aula: int = 1


settings = Settings()
