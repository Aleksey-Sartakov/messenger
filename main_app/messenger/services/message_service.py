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
    """
    The class stores the business logic of message interaction.
    """

    @classmethod
    async def get_between_two_users(
            cls,
            session: AsyncSession,
            first_user_id: int,
            second_user_id: int,
            pagination: DefaultPagination | None = None
    ) -> list[Message] | None:
        """
        Get the message history of a conversation between two people.

        :param session: Active session with the database.
        :param first_user_id: id of one of the participants in the dialogue.
        :param second_user_id: id of the second participant in the dialogue.
        :param pagination: It has two parameters:
            - limit: The number of messages you need to get.
            - offset: The number of messages to skip from the beginning.
        :return: List of instances of the "Message" class or None if there
        has not yet been a dialogue.
        """

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
        """
        Save the message to cache.

        If there are already messages from a dialog with the specified recipient
        in the cache for the current user, it will be updated with a new message.
        If the recipient also has messages from the same dialog in their cache,
        their cache will be updated too.

        :param message: The new message
        :param sender_cache_key: The key used to store the current user's cache for the dialog
        :param recipient_cache_key:The key used to store the recipient's cache for the dialog
        """

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
        """
        Add a group of messages to the cache using the specified key.

        :param key: Cache key.
        :param messages: List of messages.
        """

        json_valid_messages = jsonable_encoder(messages)

        await redis_client.set(key, json.dumps(json_valid_messages), ex=MESSAGES_CACHE_TTL)

    @classmethod
    async def get_cache(cls, key: str, pagination: DefaultPagination | None = None) -> list[MessageRead] | None:
        """
        Get messages from the cache using the specified key.

        :param key: Cache key.
        :param pagination: It has two parameters:
            - limit: The number of messages you need to get.
            - offset: The number of messages to skip from the beginning.
        """

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
        """
        Add a new group of messages to the cache using the specified key.

        If the cache for a given key already exists, the program adds a
        group of messages to the beginning of it. Otherwise, it simply
        saves messages for that key.

        :param key: Cache key.
        :param messages: List of messages.
        """

        json_valid_messages = jsonable_encoder(messages)

        cached_messages = await redis_client.get(key)
        if cached_messages:
            cached_messages = json.loads(cached_messages)
            json_valid_messages.extend(cached_messages)

        await redis_client.set(key, json.dumps(json_valid_messages), ex=MESSAGES_CACHE_TTL)

    @classmethod
    async def cache_exists(cls, key: str) -> bool:
        """
        Check if the specified key exists in the cache.

        :param key: Cache key.
        :return: True or False
        """

        cached_messages = await redis_client.get(key)
        if cached_messages:
            return True
        else:
            return False
