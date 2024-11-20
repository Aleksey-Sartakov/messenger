from datetime import datetime
from typing import Annotated, Literal

import aioredis
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, mapped_column

from main_app.config import settings


async_engine = create_async_engine(settings.db_connection_url_async)
async_sessionmaker_instance = async_sessionmaker(async_engine, expire_on_commit=False)

redis_client = aioredis.from_url(
    settings.redis_connection_url,
    encoding="utf-8",
    decode_responses=True
)


IntPk = Annotated[int, mapped_column(primary_key=True)]
String100 = Annotated[str, mapped_column(String(100))]
OrderingMethods = Literal["asc", "desc"]


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
