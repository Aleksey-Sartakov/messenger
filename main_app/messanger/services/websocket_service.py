import json
import traceback

from fastapi.encoders import jsonable_encoder
from fastapi.websockets import WebSocket
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from aioredis.exceptions import ConnectionError as RedisConnectionError

from main_app.config import logger
from main_app.database import redis_client
from main_app.messanger.constants import MESSAGES_CACHE_KEY_TEMPLATE, SESSIONS_COUNT_KEY_TEMPLATE
from main_app.messanger.schemas import MessageRead, MessageCreate
from main_app.messanger.services.message_service import MessageService
from main_app.messanger.services.pubsub_service import PubSubService
from main_app.messanger.tasks import send_notification


class WebsocketService:
	def __init__(self, websocket: WebSocket):
		self.websocket = websocket

	async def connect(self) -> None:
		await self.websocket.accept()

	async def listen(self, session: AsyncSession, sender_id: int, channel_name: str, session_marker: bool = False) -> None:
		async for new_message in self.websocket.iter_json():
			if not session_marker:
				try:
					new_message["sender_id"] = sender_id
					message_instance = await MessageService.create(session, MessageCreate.model_validate(new_message))

					validated_message = MessageRead.model_validate(message_instance)

					sender_cache_key = MESSAGES_CACHE_KEY_TEMPLATE.format(
						sender_id=sender_id,
						recipient_id=validated_message.recipient_id
					)
					recipient_cache_key = MESSAGES_CACHE_KEY_TEMPLATE.format(
						sender_id=validated_message.recipient_id,
						recipient_id=sender_id
					)
					await MessageService.add_new_message_to_cache(validated_message, sender_cache_key, recipient_cache_key)

					json_valid_message = jsonable_encoder(validated_message)
					json_valid_message["status"] = "OK"
					await PubSubService.send(channel_name, json.dumps(json_valid_message))

					recipient_sessions_count_redis_key = SESSIONS_COUNT_KEY_TEMPLATE.format(id=validated_message.recipient_id)
					recipient_is_online = await redis_client.exists(recipient_sessions_count_redis_key)
					if not recipient_is_online:
						send_notification.delay(validated_message.recipient_id, sender_id)

				except SQLAlchemyError as e:
					traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
					logger.warning(f"Details:\n{traceback_message}")

					await session.rollback()

					new_message["status"] = "error"
					await self.websocket.send_json(new_message)

				except RedisConnectionError as e:
					traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
					logger.warning(f"Redis connection error. More details:\n{traceback_message}")

					await MessageService.delete(session, message_instance)

					new_message["status"] = "error"
					await self.websocket.send_json(new_message)

	@PubSubService.listen
	async def handle_messages_from_pubsub(self, message: str):
		await self.websocket.send_text(message)
