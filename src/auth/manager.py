from fastapi import Depends
from fastapi_users import BaseUserManager, IntegerIDMixin, FastAPIUsers
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.config import auth_backend
from src.auth.db_models import UserDbModel
from src.base_db_config import get_async_session
from src.config import settings


class UserManager(IntegerIDMixin, BaseUserManager[UserDbModel, int]):
	reset_password_token_secret = settings.SECRET_KEY_FOR_RESET_PASSWORD
	verification_token_secret = settings.SECRET_KEY_FOR_JWT


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
	yield SQLAlchemyUserDatabase(session, UserDbModel)


async def get_user_manager(user_db=Depends(get_user_db)):
	yield UserManager(user_db)


auth_manager = FastAPIUsers[UserDbModel, int](
	get_user_manager,
	[auth_backend],
)
