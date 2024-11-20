from pydantic import BaseModel, Field


class DefaultPagination(BaseModel):
    limit: int = Field(5, gt=0, le=100)
    offset: int = Field(0, ge=0)
