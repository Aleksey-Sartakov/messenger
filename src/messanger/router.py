# TODO: Добавить фичу с прочитанными \ непрочитанными сообщениями
import json
import traceback

import aioredis
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy import select, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import aliased

from src.auth.db_models import UserDbModel
from src.auth.manager import auth_manager
from src.auth.pydantic_schemas import UserRead
from src.auth.router import get_all_users
from src.base_db_config import get_async_session
from src.config import settings, redis_client
from src.messanger.db_models import MessageDbModel
from src.messanger.pydantic_schemas import MessageRead, MessageCreate


current_active_user = auth_manager.current_user(active=True)

messanger_router = APIRouter(prefix="/messenger", tags=["Messanger"])

templates = Jinja2Templates(directory=settings.TEMPLATES_PATH)

# можно открывать как один и тот же чат в нескольких вкладках, так и разные чаты в нескольких вкладках
active_connections: dict[int, dict[int, list[WebSocket]]] = {}


async def get_messages_between_two_users_from_db(
		first_user_id: int,
		second_user_id: int,
		limit: int,
		offset: int
) -> list[MessageRead]:
	subquery = (
		select(MessageDbModel)
		.where(
			or_(
				and_(MessageDbModel.recipient_id == second_user_id, MessageDbModel.sender_id == first_user_id),
				and_(MessageDbModel.recipient_id == first_user_id, MessageDbModel.sender_id == second_user_id)
			)
		)
		.order_by(MessageDbModel.id.desc())
		.limit(limit)
		.offset(offset)
		.subquery()
	)
	aliased_message = aliased(MessageDbModel, subquery)
	query = select(aliased_message).order_by(aliased_message.id.asc())

	async_engine = create_async_engine(settings.db_connection_url_async)
	async_session_maker_instance = async_sessionmaker(async_engine, expire_on_commit=False)
	async with async_session_maker_instance() as session:
		messages = await session.scalars(query)
		validated_messages = [MessageRead.model_validate(message).model_dump() for message in messages]

	return jsonable_encoder(validated_messages)


async def send_message_to_recipient(
		recipient_id: int,
		current_user_id: int,
		content: MessageRead
):
	print("--------")
	if recipient_id in active_connections:
		if current_user_id in active_connections[recipient_id]:
			# если у получателя открыт данный чат в нескольких вкладках
			for connection in active_connections[recipient_id][current_user_id]:
				await connection.send_json(content)

			cache_key = f"{settings.KEY_PREFIX_FOR_CACHE_MESSAGES}:{recipient_id}:{current_user_id}"
			cached_messages = await redis_client.get(cache_key)
			if cached_messages:
				messages = json.loads(cached_messages)
				messages.append(content.model_dump())

				await redis_client.set(cache_key, json.dumps(messages), ex=1800)

		# Отправка сообщения в глобальный вебсокет страницы. Если у пользователя, кроме вкладки с этим чатом,
		# открыты еще вкладки с другими чатами, то эти вкладки получат уведомление о том, что в этот чат пришло сообщение
		for connection in active_connections[recipient_id][0]:
			await connection.send_json(content)

	else:
		print(5)
		# отправка уведомления в тг
		pass


@messanger_router.get("/", response_class=HTMLResponse, summary="Страница чата")
async def get_messenger_page(
		request: Request,
		current_user: UserDbModel = Depends(current_active_user),
		users: list[UserRead] = Depends(get_all_users)
):
	return templates.TemplateResponse("messenger.html", {"request": request, "current_user": current_user, "users": users})


@messanger_router.get("/messages/{second_user_id}", response_model=list[MessageRead])
async def get_messages_between_users_by_second_user_id(
		second_user_id: int,
		limit: int = 50,
		offset: int = 0,
		current_user: UserDbModel = Depends(current_active_user)
):
	cache_key = f"{settings.KEY_PREFIX_FOR_CACHE_MESSAGES}:{current_user.id}:{second_user_id}"
	try:
		cached_messages = await redis_client.get(cache_key)
		cached_messages = json.loads(cached_messages)
		cache_len = len(cached_messages)

	except:
		cache_len = 0
		cached_messages = None

	# все запрошенные сообщения есть в кеше
	if cached_messages and cache_len >= offset + limit:
		end_message_index = cache_len - offset
		start_message_index = cache_len - offset - limit
		messages = cached_messages[start_message_index : end_message_index]

	else:
		try:
			if cached_messages:
				# запрошенные сообщения идут попорядку за теми, которые сохранены в кеше,
				# либо какая-то часть запрошенных сообщений уже сохранена в кеше, а оставшаяся часть - нет
				if cache_len >= offset:
					# переопределяем limit и offset, чтобы запрашивать из бд только недостающие сообщения,
					# если часть необходимых сообщений уже находится в кеше
					limit_for_db_query = limit + offset - cache_len
					offset = cache_len

					new_messages_for_caching = await get_messages_between_two_users_from_db(
						current_user.id,
						second_user_id,
						limit_for_db_query,
						offset
					)
					new_messages_for_caching.extend(cached_messages)

					messages = new_messages_for_caching[ : limit]

					await redis_client.set(cache_key, json.dumps(new_messages_for_caching), ex=1800)

				# запрошенные сообщения не идут попорядку за теми сообщениями, которые находятся в кеше
				# (то есть между запрошенными сообщениями и сообщениями из кеша пропущено несколько сообщений),
				# поэтому запрошенные сообщения НЕ сохраняем в кеш
				else:
					messages = await get_messages_between_two_users_from_db(current_user.id, second_user_id, limit, offset)

			# кеш пустой
			else:
				messages = await get_messages_between_two_users_from_db(current_user.id, second_user_id, limit, offset)

				await redis_client.set(cache_key, json.dumps(messages), ex=1800)

		except IntegrityError:
			print(traceback.format_exc())
			raise HTTPException(status_code=400, detail={
				"status": "error",
				"details": "One or both users with such IDs do not exist."
			})

		except aioredis.exceptions.ConnectionError:
			print("--Connection to Redis failed!--")

		except Exception:
			print(traceback.format_exc())
			raise HTTPException(status_code=500, detail={
				"status": "error",
				"details": "A category with that name already exists!"
			})

	return messages


# @messanger_router.post("/messages", response_model=MessageRead)
# async def add_message(
# 		message_data: MessageCreate,
# 		current_user: UserDbModel = Depends(current_active_user),
# 		session: AsyncSession = Depends(get_async_session)
# ):
# 	new_message = MessageDbModel(**message_data.model_dump(), sender_id=current_user.id)
#
# 	try:
# 		session.add(new_message)
# 		await session.commit()
#
# 	except Exception as e:
# 		await session.rollback()
#
# 	return new_message


@messanger_router.websocket("/ws")
async def websocket_endpoint(
		websocket: WebSocket,
		recipient_id: int,
		current_user_id: int,
		session: AsyncSession = Depends(get_async_session)
):
	await websocket.accept()

	# Добавление нового соединения в пул всех активных соединений
	if current_user_id in active_connections:
		if recipient_id in active_connections[current_user_id]:
			active_connections[current_user_id][recipient_id].append(websocket)
		else:
			active_connections[current_user_id][recipient_id] = [websocket]
	else:
		active_connections[current_user_id] = {recipient_id: [websocket]}

	try:
		while True:
			received_message = await websocket.receive_json()
			try:
				received_message = MessageCreate.model_validate(received_message)
				new_message = MessageDbModel(**received_message.model_dump(), sender_id=current_user_id)
				session.add(new_message)
				await session.commit()

				validated_message = jsonable_encoder(MessageRead.model_validate(new_message))

				if recipient_id != current_user_id:
					# Отправка нового сообщения назад по вебсокету для его отображения в интерфейсе
					await websocket.send_json(validated_message)

					cache_key = f"{settings.KEY_PREFIX_FOR_CACHE_MESSAGES}:{current_user_id}:{recipient_id}"
					try:
						cached_messages = await redis_client.get(cache_key)
						if cached_messages:
							messages = json.loads(cached_messages)
							messages.append(validated_message)

							await redis_client.set(cache_key, json.dumps(messages), ex=1800)

						else:
							await redis_client.set(cache_key, json.dumps([validated_message]), ex=1800)

					except:
						await redis_client.delete(cache_key)

				await send_message_to_recipient(recipient_id, current_user_id, validated_message)

			except Exception:
				print(traceback.format_exc())
				await session.rollback()

	except WebSocketDisconnect:
		active_connections[current_user_id][recipient_id].remove(websocket)
		if not active_connections[current_user_id][recipient_id]:
			del active_connections[current_user_id][recipient_id]
			if not active_connections[current_user_id]:
				del active_connections[current_user_id]
