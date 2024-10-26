import aioredis
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	DB_HOST: str
	DB_PORT: int
	DB_NAME: str
	DB_USER_NAME: str
	DB_USER_PASSWORD: str

	SECRET_KEY_FOR_JWT: str
	SECRET_KEY_FOR_RESET_PASSWORD: str

	APP_ADMIN_USER_FIRST_NAME: str
	APP_ADMIN_USER_LAST_NAME: str
	APP_ADMIN_USER_EMAIL: str
	APP_ADMIN_USER_PASSWORD: str

	TEMPLATES_PATH: str

	REDIS_HOST: str
	REDIS_PORT: str

	KEY_PREFIX_FOR_CACHE_USERS: str
	KEY_FOR_CACHE_ALL_USERS: str
	KEY_PREFIX_FOR_CACHE_MESSAGES: str

	@property
	def db_connection_url_async(self):
		return f"postgresql+asyncpg://{self.DB_USER_NAME}:{self.DB_USER_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

	@property
	def redis_connection_url(self):
		return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

	model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

redis_client = aioredis.from_url(
	settings.redis_connection_url,
	encoding="utf-8",
	decode_responses=True
)