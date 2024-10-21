from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy.orm import Mapped

from src.base_db_config import BaseDbModel, IntPk, String100


class UserDbModel(SQLAlchemyBaseUserTable[int], BaseDbModel):
	__tablename__ = "user"

	id: Mapped[IntPk]
	first_name: Mapped[String100]
	last_name: Mapped[String100]