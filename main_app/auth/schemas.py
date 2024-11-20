from fastapi_users import schemas
from pydantic import ConfigDict


class UserRead(schemas.BaseUser[int]):
    id: int
    first_name: str
    last_name: str
    email: str
    telegram_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(schemas.BaseUserCreate):
    first_name: str
    last_name: str
    email: str
    telegram_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(schemas.BaseUserUpdate):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None

    model_config = ConfigDict(from_attributes=True)
