import json

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from main_app.database import redis_client
from main_app.messenger.constants import MESSAGES_CACHE_TTL
from main_app.messenger.models import Message
from main_app.messenger.schemas import MessageCreate, MessageUpdate, MessageRead
from main_app.pagination import DefaultPagination
from main_app.service import BaseDAO


class MessageService(BaseDAO[Message, MessageCreate, MessageUpdate], model=Message):
    @classmethod
    async def get_between_two_users(
            cls,
            session: AsyncSession,
            first_user_id: int,
            second_user_id: int,
            pagination: DefaultPagination | None = None
    ) -> list[Message] | None:
        subquery = (
            select(Message)
            .where(
                or_(
                    and_(Message.recipient_id == second_user_id, Message.sender_id == first_user_id),
                    and_(Message.recipient_id == first_user_id, Message.sender_id == second_user_id)
                )
            )
            .order_by(Message.id.desc())
        )
        if pagination:
            subquery = subquery.limit(pagination.limit).offset(pagination.offset)
        subquery = subquery.subquery()

        aliased_message = aliased(Message, subquery)
        query = select(aliased_message).order_by(aliased_message.id.asc())

        messages = await session.scalars(query)

        return messages.all()

    @classmethod
    async def add_new_message_to_cache(
            cls,
            message: MessageRead,
            sender_cache_key: str,
            recipient_cache_key: str
    ) -> None:
        json_valid_message = jsonable_encoder(message)

        sender_cached_messages = await redis_client.get(sender_cache_key)

        if sender_cached_messages:
            messages = json.loads(sender_cached_messages)
            messages.append(json_valid_message)

            await redis_client.set(sender_cache_key, json.dumps(messages), ex=MESSAGES_CACHE_TTL)

        else:
            await redis_client.set(sender_cache_key, json.dumps([json_valid_message]), ex=MESSAGES_CACHE_TTL)

        recipient_cached_messages = await redis_client.get(recipient_cache_key)

        if recipient_cached_messages:
            messages = json.loads(recipient_cached_messages)
            messages.append(json_valid_message)

            ttl = await redis_client.ttl(recipient_cache_key)
            await redis_client.set(recipient_cache_key, json.dumps(messages), ex=ttl)

    @classmethod
    async def set_cache(cls, key: str, messages: list[MessageRead]) -> None:
        json_valid_messages = jsonable_encoder(messages)

        await redis_client.set(key, json.dumps(json_valid_messages), ex=MESSAGES_CACHE_TTL)

    @classmethod
    async def get_cache(cls, key: str, pagination: DefaultPagination | None = None) -> list[MessageRead] | None:
        cached_messages = await redis_client.get(key)
        try:
            cached_messages = json.loads(cached_messages)
        except TypeError:
            cached_messages = None

        if cached_messages and pagination:
            cache_len = len(cached_messages)
            if cache_len >= pagination.offset + pagination.limit:
                last_message_index = cache_len - pagination.offset
                first_message_index = cache_len - pagination.offset - pagination.limit

                return cached_messages[first_message_index : last_message_index]

            elif cache_len > pagination.offset:
                last_message_index = cache_len - pagination.offset

                return cached_messages[ : last_message_index]

            else:
                return None

        else:
            return cached_messages

    @classmethod
    async def update_cache(cls, key: str, messages: list[MessageRead]) -> None:
        json_valid_messages = jsonable_encoder(messages)

        cached_messages = await redis_client.get(key)
        if cached_messages:
            cached_messages = json.loads(cached_messages)
            json_valid_messages.extend(cached_messages)

        await redis_client.set(key, json.dumps(json_valid_messages), ex=MESSAGES_CACHE_TTL)

    @classmethod
    async def cache_exists(cls, key: str) -> bool:
        cached_messages = await redis_client.get(key)
        if cached_messages:
            return True
        else:
            return False
