from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	DB_HOST: str
	DB_PORT: int
	DB_NAME: str
	DB_USER_NAME: str
	DB_USER_PASSWORD: str

	SECRET_KEY_FOR_JWT: str
	SECRET_KEY_FOR_RESET_PASSWORD: str

	@property
	def db_connection_url_async(self):
		return f"postgresql+asyncpg://{self.DB_USER_NAME}:{self.DB_USER_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

	model_config = SettingsConfigDict(env_file=".env")


settings = Settings()