from datetime import datetime

from pydantic import BaseModel, field_validator


class MessageRead(BaseModel):
	id: int
	sender_id: int
	recipient_id: int
	text_content: str
	created_at: str
	updated_at: str | None

	@classmethod
	@field_validator("created_at", "updated_at")
	def date_to_string(cls, date_instance: datetime | None) -> str | None:
		if date_instance is not None:
			return date_instance.strftime("%Y-%m-%d %H:%M")
		else:
			return date_instance


class MessageCreate(BaseModel):
	recipient_id: int
	text_content: str
