import json

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin, FastAPIUsers
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.config import auth_backend
from src.auth.db_models import UserDbModel
from src.auth.pydantic_schemas import UserRead
from src.base_db_config import get_async_session
from src.config import settings, redis_client


class UserManager(IntegerIDMixin, BaseUserManager[UserDbModel, int]):
	reset_password_token_secret = settings.SECRET_KEY_FOR_RESET_PASSWORD
	verification_token_secret = settings.SECRET_KEY_FOR_JWT

	# обновление списка пользователей в кэше при регистрации нового пользователя
	async def on_after_register(self, user: UserDbModel, request: Request | None = None):
		new_user_info = UserRead.model_validate(user).model_dump()

		cached_users = await redis_client.get(f"{settings.KEY_PREFIX_FOR_CACHE_USERS}:{settings.KEY_FOR_CACHE_ALL_USERS}")
		if cached_users:
			users = json.loads(cached_users)
			users.append(new_user_info)

			await redis_client.set(
				f"{settings.KEY_PREFIX_FOR_CACHE_USERS}:{settings.KEY_FOR_CACHE_ALL_USERS}",
				json.dumps(users)
			)

		else:
			await redis_client.set(
				f"{settings.DEFAULT_KEY_PREFIX_FOR_CACHE_USERS}:{settings.KEY_FOR_CACHE_ALL_USERS}",
				json.dumps([new_user_info])
			)


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
	yield SQLAlchemyUserDatabase(session, UserDbModel)


async def get_user_manager(user_db=Depends(get_user_db)):
	yield UserManager(user_db)


auth_manager = FastAPIUsers[UserDbModel, int](
	get_user_manager,
	[auth_backend],
)
