import logging

from celery import Celery
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

	NOTIFICATION_SERVICE_HOST: str
	NOTIFICATION_SERVICE_PORT: int

	@property
	def db_connection_url_async(self):
		return f"postgresql+asyncpg://{self.DB_USER_NAME}:{self.DB_USER_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

	@property
	def redis_connection_url(self):
		return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

	# model_config = SettingsConfigDict(env_file=".env")
	model_config = SettingsConfigDict(env_file=".env-non-dev")


logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(levelname)s: %(message)s',
	datefmt='%d-%m-%y %H:%M:%S',
)


logger = logging.getLogger('messenger')

settings = Settings()

celery_manager = Celery("tasks", broker=settings.redis_connection_url)
celery_manager.autodiscover_tasks(['main_app.messenger.tasks'])
