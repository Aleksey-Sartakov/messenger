import json
from datetime import datetime

from sqlalchemy import select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from main_app.auth.constants import USERS_CACHE_KEY_TEMPLATE, USERS_CACHE_TTL
from main_app.auth.models import User
from main_app.auth.schemas import UserCreate, UserUpdate, UserRead
from main_app.database import redis_client
from main_app.exceptions import ColumnDoesNotExistError
from main_app.filters import SimpleSorting
from main_app.pagination import DefaultPagination
from main_app.service import BaseDAOService


class UserService(BaseDAOService[User, UserCreate, UserUpdate], model=User):
	@classmethod
	async def get(
			cls,
			session: AsyncSession,
			sorting: SimpleSorting | None = None,
			pagination: DefaultPagination | None = None
	) -> list[User]:
		if not hasattr(User, sorting.sort_by):
			raise ColumnDoesNotExistError(sorting.sort_by)

		query = select(User)
		if sorting:
			if sorting.order == "desc":
				query = query.order_by(desc(getattr(User, sorting.sort_by)))
			else:
				query = query.order_by(asc(getattr(User, sorting.sort_by)))

		if pagination:
			query = query.limit(pagination.limit).offset(pagination.offset)

		all_users = await session.scalars(query)

		return all_users.all()

	@classmethod
	async def get_one_or_none(cls, session: AsyncSession, filters: dict[str, str | int | float | bool | datetime]) -> User:
		query = select(User).filter_by(**filters)
		users = await session.scalars(query)

		return users.first()

	@classmethod
	async def get_from_cache(cls, sorting: SimpleSorting, pagination: DefaultPagination) -> list[User] | None:
		cache_key = USERS_CACHE_KEY_TEMPLATE.format(sorting.sort_by, sorting.order, pagination.limit, pagination.offset)
		cached_users = await redis_client.get(cache_key)

		if cached_users:
			await redis_client.expire(cache_key, USERS_CACHE_TTL)

			return json.loads(cached_users)
		else:
			return None

	@classmethod
	async def save_to_cache(cls, users: list[User], sorting: SimpleSorting, pagination: DefaultPagination) -> None:
		validated_users = [UserRead.model_validate(user).model_dump() for user in users]
		cache_key = USERS_CACHE_KEY_TEMPLATE.format(sorting.sort_by, sorting.order, pagination.limit, pagination.offset)

		await redis_client.set(
			cache_key,
			json.dumps(validated_users),
			ex=USERS_CACHE_TTL
		)
