from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageRead(BaseModel):
	id: int
	sender_id: int
	recipient_id: int
	text_content: str
	created_at: datetime
	updated_at: datetime | None = None

	model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
	sender_id: int
	recipient_id: int
	text_content: str


class MessageUpdate(BaseModel):
	text_content: str
	updated_at: datetime | None = None
