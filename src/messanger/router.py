# TODO: Добавить фичу с прочитанными \ непрочитанными сообщениями

from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.db_models import UserDbModel
from src.auth.manager import auth_manager
from src.auth.pydantic_schemas import UserRead
from src.auth.router import get_all_users
from src.base_db_config import get_async_session
from src.config import settings
from src.messanger.db_models import MessageDbModel
from src.messanger.pydantic_schemas import MessageRead, MessageCreate


current_active_user = auth_manager.current_user(active=True)

messanger_router = APIRouter(prefix="/messenger", tags=["Messanger"])

templates = Jinja2Templates(directory=settings.TEMPLATES_PATH)

# можно открывать как один и тот же чат в нескольких вкладках, так и разные чаты в нескольких вкладках
active_connections: dict[int, dict[int, list[WebSocket]]] = {}


async def send_message_to_recipient(
		recipient_id: int,
		content: MessageRead,
		current_user: UserDbModel = Depends(current_active_user)
):
	if recipient_id in active_connections:
		if current_user.id in active_connections[recipient_id]:
			# если у получателя открыт данный чат в нескольких вкладках
			for connection in active_connections[recipient_id][current_user.id]:
				await connection.send_json(content.model_dump())

		# Отправка сообщения в глобальный вебсокет страницы. Если у пользователя, кроме вкладки с этим чатом,
		# открыты еще вкладки с другими чатами, то эти вкладки получат уведомление о том, что в этот чат пришло сообщение
		for connection in active_connections[recipient_id][0]:
			await connection.send_json(content.model_dump())

	else:
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
		limit: int = 20,
		offset: int = 0,
		current_user: UserDbModel = Depends(current_active_user),
		session: AsyncSession = Depends(get_async_session)
):
	query = (
		select(MessageDbModel)
		.where(
			or_(
				and_(MessageDbModel.recipient_id == second_user_id, MessageDbModel.sender_id == current_user.id),
				and_(MessageDbModel.recipient_id == current_user.id, MessageDbModel.sender_id == second_user_id)
			)
		)
		.order_by(MessageDbModel.id.desc())
		.limit(limit)
		.offset(offset)
		.order_by(MessageDbModel.id.asc())
	)

	messages = await session.scalars(query)

	return messages.all()


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


@messanger_router.websocket("/ws/{recipient_id}")
async def websocket_endpoint(
		websocket: WebSocket,
		recipient_id: int,
		current_user: UserDbModel = Depends(current_active_user),
		session: AsyncSession = Depends(get_async_session)
):
	await websocket.accept()

	# Добавление нового соединения в пул всех активных соединений
	if current_user.id in active_connections:
		if recipient_id in active_connections[current_user.id]:
			active_connections[current_user.id][recipient_id].append(websocket)
		else:
			active_connections[current_user.id][recipient_id] = [websocket]
	else:
		active_connections[current_user.id] = {recipient_id: [websocket]}

	try:
		while True:
			received_message = await websocket.receive_json()
			try:
				received_message = MessageCreate.model_validate(received_message)

				new_message = MessageDbModel(**received_message.model_dump(), sender_id=current_user.id)
				session.add(new_message)
				await session.commit()

				# Отправка нового сообщения назад по вебсокету для его отображения в интерфейсе
				await websocket.send_json(MessageRead.model_validate(new_message))

				await send_message_to_recipient(recipient_id, MessageRead.model_validate(new_message))

			except Exception as e:
				await session.rollback()

	except WebSocketDisconnect:
		active_connections[current_user.id][recipient_id].remove(websocket)
		if not active_connections[current_user.id][recipient_id]:
			del active_connections[current_user.id][recipient_id]
			if not active_connections[current_user.id]:
				del active_connections[current_user.id]
