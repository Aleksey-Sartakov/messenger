import json
import traceback

from fastapi.encoders import jsonable_encoder
from fastapi.websockets import WebSocket
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from aioredis.exceptions import ConnectionError as RedisConnectionError

from main_app.config import logger
from main_app.database import redis_client
from main_app.messenger.constants import MESSAGES_CACHE_KEY_TEMPLATE, SESSIONS_COUNT_KEY_TEMPLATE
from main_app.messenger.schemas import MessageRead, MessageCreate
from main_app.messenger.services.message_service import MessageService
from main_app.messenger.services.pubsub_service import PubSubService
from main_app.messenger.tasks import send_notification


class WebsocketService:
    """
    The service for managing a websocket connection.
    """

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def connect(self) -> None:
        await self.websocket.accept()

    async def listen(
            self,
            session: AsyncSession,
            sender_id: int,
            channel_name: str,
            session_marker: bool = False
    ) -> None:
        """
        Process incoming messages if the connection is not intended
        to track the user's session.

        1. Save the received message to the database.
        2. If the message is saved successfully, add it to the cache.
        3. Post the message in pub/sub
        4. Send a notification to telegram if the user is offline.

        If an error occurs when saving a message in the database or when trying
        to send it via the Redis channel, it cancels saving the record in the
        database and sends the error status message back to the sender via WebSocket.

        :param session: Active session with the database.
        :param sender_id: The ID of the user who sent the message.
        :param channel_name: The name of the pub/sub channel for this chat.
        :param session_marker: A flag that indicates whether this WebSocket connection
        is intended to monitor an active user's session (online/offline status).
        """

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
                    await MessageService.add_new_message_to_cache(
                        validated_message,
                        sender_cache_key,
                        recipient_cache_key
                    )

                    json_valid_message = jsonable_encoder(validated_message)
                    json_valid_message["status"] = "OK"
                    await PubSubService.send(channel_name, json.dumps(json_valid_message))

                    recipient_sessions_count_redis_key = SESSIONS_COUNT_KEY_TEMPLATE.format(
                        id=validated_message.recipient_id
                    )
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
        """
        The websocket starts listening to the pub/sub channel
        of the dialog that it is linked to and sends all messages
        received on that channel to the client.

        :param message: The message received from the pub/sub channel.
        """

        await self.websocket.send_text(message)
