from datetime import datetime
from typing import AsyncGenerator, Annotated

from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, mapped_column

from src.config import settings


IntPk = Annotated[int, mapped_column(primary_key=True)]


class BaseDbModel(AsyncAttrs, DeclarativeBase):
	type_annotation_map = {
		datetime: TIMESTAMP
	}

	def __repr__(self) -> str:
		columns = []
		for column in self.__table__.columns.keys():
			columns.append(f"{column} = {getattr(self, column)}")

		parameters_separator = ',\n\t'
		return f"{self.__class__.__name__} {{ \n\t{parameters_separator.join(columns)}\n }}"


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
	async_engine = create_async_engine(settings.db_connection_url_async())
	async_session_maker_instance = async_sessionmaker(async_engine, expire_on_commit=False)

	async with async_session_maker_instance() as async_session:
		yield async_session
