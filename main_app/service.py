from typing import TypeVar, Generic, Any

from pydantic import BaseModel
from sqlalchemy import select, inspect, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from main_app.exceptions import CompositePrimaryKeyError
from main_app.database import BaseDbModel


Model = TypeVar("Model", bound=BaseDbModel)
ModelCreateSchema = TypeVar("ModelCreateSchema", bound=BaseModel)
ModelUpdateSchema = TypeVar("ModelUpdateSchema", bound=BaseModel)


class BaseDAO(Generic[Model, ModelCreateSchema, ModelUpdateSchema]):
    """
    An abstract class for interacting with a database.

    The main universal CRUD methods are implemented here. To implement
    additional specialized methods, you need to create a separate class
    for a specific database entity and specify this class as its parent.

    As generic types, you must pass:
        - Model: ORM model describing a single database entity.
        - ModelCreateSchema: Pydantic model validating the data needed
        to add a new instance of an entity to the database.
        - ModelUpdateSchema: Pydantic model validating the data that is
        needed to update the instance.

    ## Attributes ##
    - model: ORM model.
    """

    model: type[Model] = None

    def __init_subclass__(cls, *args, model: type[Model], **kwargs):
        """
        Initializing the "model" attribute when creating a subclass.

        :param model: ORM model.
        """

        super().__init_subclass__(**kwargs)
        cls.model = model

    @classmethod
    async def get_all(cls, session: AsyncSession) -> list[Model]:
        result = await session.scalars(select(cls.model))

        return result.all()

    @classmethod
    async def get_by_pk(cls, session: AsyncSession, pk: Any) -> Model | None:
        """
        Find the record by the specified primary key.

        :param session: Active session with the database.
        :param pk: The value of the primary key to be searched for.
        :return: An instance of the "Model" class or None if not found.
        """

        instance = await session.get(cls.model, pk)

        return instance

    @classmethod
    async def create(cls, session: AsyncSession, values: ModelCreateSchema, do_commit: bool = True) -> Model:
        """
        Creates a new entry in the database.

        :param session: Active session with the database.
        :param values: A dictionary containing values for each attribute of the model.
        :param do_commit: If True, then executes commit at the end.
        :return: An instance of the "Model" class.
        """

        instance = cls.model(**values.model_dump(exclude_unset=True))
        session.add(instance)

        if do_commit:
            await session.commit()

        return instance

    @classmethod
    async def update(cls, session: AsyncSession, pk: Any, values: ModelUpdateSchema, do_commit: bool = True) -> None:
        """
        Update one record in the database.

        Suitable for tables with a simple primary key
        (not suitable for working with composite keys).
        If a model has a composite primary key, the
        "CompositePrimaryKeyError" exception will be raised.

        :param session: Active session with the database.
        :param pk: A dictionary containing values for each attribute of the model.
        :param values: A dictionary containing values of some attributes of the model.
        :param do_commit: If True, then executes commit at the end.
        """

        mapper = inspect(cls.model)
        primary_key_fields = mapper.primary_key
        if len(primary_key_fields) == 1:
            pk_field = primary_key_fields[0]
            query = (
                update(cls.model)
                .where(pk_field == pk)
                .values(**values.model_dump(exclude_unset=True))
            )
            await session.execute(query)

            if do_commit:
                await session.commit()

        else:
            raise CompositePrimaryKeyError()

    @classmethod
    async def update_many(
            cls,
            session: AsyncSession,
            filters: dict[str, Any],
            values: ModelUpdateSchema,
            do_commit: bool = True
    ) -> None:
        """
        Update several records that match the filters.

        Simple update method where filtering is performed only
        according to the equality condition as follows:
        '.filter_by(param1=value1, param2=value2)'.
        Other comparison operators are not supported.

        :param session: Active session with the database.
        :param filters: A dictionary in which the attribute name corresponds to the value it should be equal to.
        :param values: A dictionary containing values of some attributes of the model.
        :param do_commit: If True, then executes commit at the end.
        """

        query = (
            update(cls.model)
            .filter_by(**filters)
            .values(**values.model_dump(exclude_unset=True))
        )
        await session.execute(query)

        if do_commit:
            await session.commit()

    @classmethod
    async def bulk_update_by_pk(
            cls,
            session: AsyncSession,
            values: list[dict[str, Any]],
            do_commit: bool = True
    ) -> None:
        """
        Update several records.

        Example of a value for the "values" parameter:
            values = [
                {"id": 1, "fullname": "Spongebob Squarepants"},
                {"id": 3, "fullname": "Patrick Star"},
                {"id": 5, "fullname": "Eugene H. Krabs"},
            ]

        :param values: A list of dicts where each dict element include a full primary key
        :param session: Active session with the database.
        :param do_commit: If True, then executes commit at the end.
        """

        await session.execute(update(cls.model), values)

        if do_commit:
            await session.commit()

    @classmethod
    async def delete(cls, session: AsyncSession, obj: Model, do_commit: bool = True) -> None:
        """
        Delete an entry using an instance of the "model" class.

        :param session: Active session with the database.
        :param obj: An instance of the "model" class that needs to be deleted.
        :param do_commit: If True, then executes commit at the end.
        """

        await session.delete(obj)

        if do_commit:
            await session.commit()

    @classmethod
    async def delete_by_pk(cls, session: AsyncSession, pk: Any, do_commit: bool = True) -> None:
        """
        Delete an entry using the primary key value.

        :param session: Active session with the database.
        :param pk: Some value of primary key.
        :param do_commit: If True, then executes commit at the end.
        """

        mapper = inspect(cls.model)
        primary_key_fields = mapper.primary_key
        if len(primary_key_fields) == 1:
            pk_field = primary_key_fields[0]
            query = (
                delete(cls.model)
                .where(pk_field == pk)
            )
            await session.execute(query)

            if do_commit:
                await session.commit()

        else:
            raise CompositePrimaryKeyError()

    @classmethod
    async def delete_by_filters(cls, session: AsyncSession, filters: dict[str, Any], do_commit: bool = True):
        """
        Delete several records corresponding to the specified filters.

        Simple delete method where filtering is performed only according to the equality condition as follows:
        '.filter_by(param1=value1, param2=value2)'.
        Other comparison operators are not supported.

        :param session: Active session with the database.
        :param filters: A dictionary in which the attribute name corresponds to the value it should be equal to.
        :param do_commit: If True, then executes commit at the end.
        """

        query = (
            delete(cls.model)
            .filter_by(**filters)
        )
        await session.execute(query)

        if do_commit:
            await session.commit()
