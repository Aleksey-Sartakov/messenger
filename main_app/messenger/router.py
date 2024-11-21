import asyncio
import traceback

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from aioredis.exceptions import ConnectionError as RedisConnectionError

from main_app.auth.dependencies import current_active_user
from main_app.auth.models import User
from main_app.auth.schemas import UserRead
from main_app.auth.router import get_users_list
from main_app.database import redis_client
from main_app.dependencies import get_async_session
from main_app.config import settings, logger
from main_app.messenger.constants import (
    CHAT_PUBSUB_NAME_TEMPLATE,
    MESSAGES_CACHE_KEY_TEMPLATE,
    SESSIONS_COUNT_KEY_TEMPLATE
)
from main_app.messenger.schemas import MessageRead
from main_app.messenger.services.message_service import MessageService
from main_app.messenger.services.websocket_service import WebsocketService
from main_app.pagination import DefaultPagination


messanger_router = APIRouter(prefix="/messenger", tags=["Messenger"])

templates = Jinja2Templates(directory=settings.TEMPLATES_PATH)


@messanger_router.get("/", response_class=HTMLResponse, summary="Страница чата")
async def get_messenger_page(
        request: Request,
        current_user: User = Depends(current_active_user),
        users: list[UserRead] = Depends(get_users_list)
):
    return templates.TemplateResponse(
        "messenger.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users
        }
    )


@messanger_router.get(
    "/messages/{second_user_id}",
    response_model=list[MessageRead],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "The user with the requested id was not found."
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "An error when requesting the database, or another unexpected server error."
        },
    }
)
async def get_messages_between_users_by_second_user_id(
        second_user_id: int,
        pagination: DefaultPagination = Depends(),
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    """
    Get the message history between the current and requested users.

    The cache is first checked. If all the required messages are found
    in the cache, they are returned. If the required messages are not
    present in the cache, they are retrieved from the database and
    stored in the cache before being returned to the client.

    If only a portion of the requested messages are present in the cache,
    then the missing messages will be retrieved from the database as well.
    These missing messages are then added to the cache, and then combined
    with the messages that were already there. Finally, all the messages
    are returned to the client in their entirety.
    """

    cache_key = MESSAGES_CACHE_KEY_TEMPLATE.format(sender_id=current_user.id, recipient_id=second_user_id)
    try:
        cached_messages = await MessageService.get_cache(
            cache_key,
            DefaultPagination(limit=pagination.limit, offset=pagination.offset)
        )

        if not cached_messages:
            messages = await MessageService.get_between_two_users(
                session,
                current_user.id,
                second_user_id,
                DefaultPagination(limit=pagination.limit, offset=pagination.offset)
            )
            if messages:
                messages = [MessageRead.model_validate(message) for message in messages]
                await MessageService.update_cache(cache_key, messages)

        else:
            messages = cached_messages
            messages_count = len(cached_messages)

            if messages_count < pagination.limit:
                new_messages = await MessageService.get_between_two_users(
                    session,
                    current_user.id,
                    second_user_id,
                    DefaultPagination(
                        limit=pagination.limit - messages_count,
                        offset=pagination.offset + messages_count
                    )
                )

                if new_messages:
                    messages = [MessageRead.model_validate(message) for message in new_messages]
                    await MessageService.update_cache(cache_key, messages)

                    messages.extend(cached_messages)

    except RedisConnectionError as e:
        traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.warning(f"User with ID {current_user.id} or {second_user_id} does not exist."
                       f"More details:\n{traceback_message}")

        messages = await MessageService.get_between_two_users(
            session,
            current_user.id,
            second_user_id,
            DefaultPagination(limit=pagination.limit, offset=pagination.offset)
        )
        if messages:
            messages = [MessageRead.model_validate(message) for message in messages]

    except IntegrityError as e:
        traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"User with ID {current_user.id} or {second_user_id} does not exist."
                     f"More details:\n{traceback_message}")

        raise HTTPException(status_code=404, detail={
            "status": "error",
            "details": "One or both users with requested IDs do not exists."
        })

    except Exception as e:
        traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"Details:\n{traceback_message}")

        raise HTTPException(status_code=500, detail={
            "status": "error",
            "details": "..."
        })

    json_valid_messages = jsonable_encoder(messages)

    return json_valid_messages


@messanger_router.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        recipient_id: int,
        current_user_id: int,
        session_marker: bool = False,
        session: AsyncSession = Depends(get_async_session)
):
    """
    Creates a web socket connection between the client and the server.

    A received connection can be processed in two different scenarios,
    depending on the value of the 'session_marker' parameter.

    ## Scenario 1, when 'session_marker=True' ##:
        in this scenario, the connection is intended to track an active
        user session. Every time a tab is opened / closed in the
        browser, the counter of active sessions of this user in redis
        increases / decreases. The counter value '> 0' indicates that
        the user is online, otherwise it is considered offline.
        This counter is used when sending notifications to telegram.

    ## Scenario 2, when 'session_marker=False' ##:
        in this scenario, the connection is designed for real-time
        communication between users. When a connection is established,
        it subscribes to a Redis channel. Whenever a new message is
        received through the WebSocket, it is sent to this channel,
        and all subscribers to the channel receive it. The message
        is then sent via the WebSocket to the client, ensuring that
        the new message appears on all open browser tabs in real time.

        This architecture allows to run multiple instances of the
        application that can simultaneously handle incoming websocket
        connections.
    """

    websocket_service = WebsocketService(websocket)
    await websocket_service.connect()

    sessions_count_redis_key = SESSIONS_COUNT_KEY_TEMPLATE.format(id=current_user_id)
    if session_marker:
        await redis_client.incr(sessions_count_redis_key, 1)

    pubsub_name = CHAT_PUBSUB_NAME_TEMPLATE.format(
        min_user_id=min(current_user_id, recipient_id),
        max_user_id=max(current_user_id, recipient_id)
    )

    listen_pubsub_task = asyncio.create_task(websocket_service.handle_messages_from_pubsub(channel_name=pubsub_name))

    await websocket_service.listen(session, current_user_id, pubsub_name, session_marker)

    listen_pubsub_task.cancel()

    if session_marker:
        await redis_client.decr(sessions_count_redis_key, 1)

        sessions_count = await redis_client.get(sessions_count_redis_key)
        if int(sessions_count) <= 0:
            await redis_client.delete(sessions_count_redis_key)
