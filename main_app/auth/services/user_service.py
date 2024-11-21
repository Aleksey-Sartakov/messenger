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
from main_app.service import BaseDAO


class UserService(BaseDAO[User, UserCreate, UserUpdate], model=User):
    """
    The class stores the business logic of user interaction.
    """

    @classmethod
    async def get(
            cls,
            session: AsyncSession,
            sorting: SimpleSorting | None = None,
            pagination: DefaultPagination | None = None
    ) -> list[User]:
        """
        Get a list of users.

        :param session: Active session with the database.
        :param sorting: It has two parameters:
            - sort_by: the name of the attribute to sort by. If not specified,
            it will sort by "id".
            - order: can take the values "asc" or "desc".
        :param pagination: It has two parameters:
            - limit: The number of users you need to get.
            - offset: The number of users to skip from the beginning.
        :return: List of instances of the "User" class.
        """

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
    async def get_one_or_none(
            cls,
            session: AsyncSession,
            filters: dict[str, str | int | float | bool | datetime]
    ) -> User | None:
        """
        Get one user according to the specified parameters.

        :param session: Active session with the database.
        :param filters: A dictionary in which the key is the name of a property
        from the "User" class and the value is the desired value for that property.
        :return: "User" instance or None, if the user with the specified parameters
        does not exist
        """

        query = select(User).filter_by(**filters)
        users = await session.scalars(query)

        return users.first()

    @classmethod
    async def get_from_cache(cls, sorting: SimpleSorting, pagination: DefaultPagination) -> list[User] | None:
        """
        Returns a list of users from the cache.

        The key for the cache is generated based on the passed parameters.

        :param sorting: It has two parameters:
            - sort_by: the name of the attribute by which the list should be sorted.
            - order: can take the values "asc" or "desc".
        :param pagination: It has two parameters:
            - limit: The number of users you need to get.
            - offset: The number of users to skip from the beginning.
        :return: List of instances of the "User" class or None if there is no cache
        for the specified parameters.
        """

        cache_key = USERS_CACHE_KEY_TEMPLATE.format(sorting.sort_by, sorting.order, pagination.limit, pagination.offset)
        cached_users = await redis_client.get(cache_key)

        if cached_users:
            await redis_client.expire(cache_key, USERS_CACHE_TTL)

            return json.loads(cached_users)
        else:
            return None

    @classmethod
    async def save_to_cache(cls, users: list[User], sorting: SimpleSorting, pagination: DefaultPagination) -> None:
        """
        Save the list of users to the cache.

        The key for saving is generated based on the passed parameters.

        :param users: List of instances of the "User" class
        :param sorting: It has two parameters:
            - sort_by: the name of the attribute by which the list should be sorted.
            - order: can take the values "asc" or "desc".
        :param pagination: It has two parameters:
            - limit: The number of users you need to get.
            - offset: The number of users to skip from the beginning.
        """

        validated_users = [UserRead.model_validate(user).model_dump() for user in users]
        cache_key = USERS_CACHE_KEY_TEMPLATE.format(sorting.sort_by, sorting.order, pagination.limit, pagination.offset)

        await redis_client.set(
            cache_key,
            json.dumps(validated_users),
            ex=USERS_CACHE_TTL
        )
