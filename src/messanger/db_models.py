from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.base_db_config import BaseDbModel, IntPk


class MessageDbModel(BaseDbModel):
	__tablename__ = "message"

	id: Mapped[IntPk]
	sender_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
	recipient_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
	text_content: Mapped[str] = mapped_column(Text, nullable=False)
	created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
	updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)