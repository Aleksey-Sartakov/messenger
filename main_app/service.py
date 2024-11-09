from typing import TypeVar, Generic, Any

from pydantic import BaseModel
from sqlalchemy import select, inspect, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from main_app.exceptions import CompositePrimaryKeyError
from main_app.database import BaseDbModel


Model = TypeVar("Model", bound=BaseDbModel)
ModelCreateSchema = TypeVar("ModelCreateSchema", bound=BaseModel)
ModelUpdateSchema = TypeVar("ModelUpdateSchema", bound=BaseModel)


class BaseDAOService(Generic[Model, ModelCreateSchema, ModelUpdateSchema]):
	model: type[Model] = None

	def __init_subclass__(cls, *args, model: type[Model], **kwargs):
		super().__init_subclass__(**kwargs)
		cls.model = model

	@classmethod
	async def get_all(cls, session: AsyncSession) -> list[Model]:
		result = await session.scalars(select(cls.model))

		return result.all()

	@classmethod
	async def get_by_pk(cls, session: AsyncSession, pk: Any) -> Model:
		instance = await session.get(cls.model, pk)

		return instance

	@classmethod
	async def create(cls, session: AsyncSession, values: ModelCreateSchema, do_commit: bool = True) -> Model:
		instance = cls.model(**values.model_dump(exclude_unset=True))
		session.add(instance)

		if do_commit:
			await session.commit()

		return instance

	@classmethod
	async def update(cls, session: AsyncSession, pk: Any, values: ModelUpdateSchema, do_commit: bool = True) -> None:
		"""
		For models with a simple primary key. If a model has a composite primary key, the "CompositePrimaryKeyError"
		exception will be raised.
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
		Simple update method where filtering is performed only according to the equality condition as follows:
			.filter_by(param1=value1, param2=value2).

		Other comparison operators are not supported.
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
	async def bulk_update_by_pk(cls, session: AsyncSession, values: list[dict[str, Any]], do_commit: bool = True) -> None:
		"""
		Example of a value for the "values" parameter:
			values = [
				{"id": 1, "fullname": "Spongebob Squarepants"},
				{"id": 3, "fullname": "Patrick Star"},
				{"id": 5, "fullname": "Eugene H. Krabs"},
			]

		:param values: A list of dicts where each dict element include a full primary key
		:param session:
		:param do_commit:
		:return:
		"""

		await session.execute(update(cls.model), values)

		if do_commit:
			await session.commit()

	@classmethod
	async def delete(cls, session: AsyncSession, obj: Model, do_commit: bool = True):
		await session.delete(obj)

		if do_commit:
			await session.commit()

	@classmethod
	async def delete_by_pk(cls, session: AsyncSession, pk: Any, do_commit: bool = True):
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
		Simple delete method where filtering is performed only according to the equality condition as follows:
			.filter_by(param1=value1, param2=value2).

		Other comparison operators are not supported.
		"""

		query = (
			delete(cls.model)
			.filter_by(**filters)
		)
		await session.execute(query)

		if do_commit:
			await session.commit()
