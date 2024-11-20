import traceback

from aioredis.exceptions import ConnectionError as RedisConnectionError
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin, FastAPIUsers
from fastapi_users.authentication import JWTStrategy, CookieTransport, AuthenticationBackend
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from main_app.auth.constants import USERS_CACHE_KEY_PREFIX
from main_app.auth.models import User
from main_app.dependencies import get_async_session
from main_app.config import settings, logger
from main_app.database import redis_client


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = settings.SECRET_KEY_FOR_RESET_PASSWORD
    verification_token_secret = settings.SECRET_KEY_FOR_JWT

    # удаление списка пользователей из кеша при регистрации нового пользователя
    async def on_after_register(self, user: User, request: Request | None = None):
        try:
            keys_to_delete = await redis_client.keys(f"{USERS_CACHE_KEY_PREFIX}:*")
            if keys_to_delete:
                await redis_client.delete(*keys_to_delete)
                logger.info("Users cache has successfully cleared!")

        except RedisConnectionError as e:
            traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.error(f"Error while updating cache after registration. More details:\n{traceback_message}")


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY_FOR_JWT, lifetime_seconds=None)


cookie_transport = CookieTransport(cookie_name="auth")
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

auth_service = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)
