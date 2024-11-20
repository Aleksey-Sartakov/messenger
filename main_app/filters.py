from pydantic import BaseModel, Field

from main_app.database import OrderingMethods


class SimpleSorting(BaseModel):
    sort_by: str = "id"
    order: OrderingMethods = Field(default="asc", description=f"Acceptable parameter values: {OrderingMethods}")
