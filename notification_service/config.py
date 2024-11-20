import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str

    MESSENGER_URL: str
    MESSENGER_PORT: str

    NOTIFICATION_SERVICE_PORT: int

    # model_config = SettingsConfigDict(env_file=".env")
    model_config = SettingsConfigDict(env_file=".env-non-dev")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%d-%m-%y %H:%M:%S',
)


logger = logging.getLogger('notification_service')

settings = Settings()
