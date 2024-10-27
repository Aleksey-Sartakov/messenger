from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.db_models import UserDbModel
from src.auth.manager import auth_manager
from src.auth.pydantic_schemas import UserRead, UserCreate
from src.auth.router import auth_router, users_router
from src.base_db_config import get_async_session
from src.messanger.router import messanger_router


tags_metadata = [
	{
		"name": "Auth",
		"description": """
			Basic authorization methods: registration, login, logout. The JWT key in cookies is used.
		""",
	},
	{
		"name": "Messanger",
		"description": """
			Methods for working with messages. Available only to authenticated users.
		""",
	},
	{
		"name": "Users",
		"description": """
			Methods for working with users. Available only to authenticated users.
			For users who are not an admin (superuser), only the "/users/me" methods are available.
		""",
	},
]


app = FastAPI(title="Messanger", openapi_tags=tags_metadata)
app.mount('/static', StaticFiles(directory='src/static'), name='static')

origins = [
	"http://localhost:8000",
]
app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
	allow_headers=[
		"Content-Type",
		"Set-Cookie",
		"Access-Control-Allow-Headers",
		"Access-Control-Allow-Origin",
		"Authorization"
	]
)

app.include_router(
	auth_router,
	prefix="/auth",
	tags=["Auth"]
)
app.include_router(
	auth_manager.get_register_router(UserRead, UserCreate),
	prefix="/auth",
	tags=["Auth"],
)
app.include_router(
	users_router,
	prefix="/users",
	tags=["Users"]
)
app.include_router(messanger_router)


@app.get("/", tags=["Redirect"])
async def redirect_to_auth():
	return RedirectResponse(url="/auth")


@app.exception_handler(HTTPException)
async def handle_401_unauthorized(request: Request, exc: HTTPException):
	if exc.status_code == 401:
		return RedirectResponse(url="/auth")
	else:
		return await http_exception_handler(request, exc)


@app.post("/link_telegram_id/")
async def link_telegram_id(email: str, telegram_id: int, session: AsyncSession = Depends(get_async_session)):
	query = (
		select(UserDbModel)
		.where(UserDbModel.email == email)
	)
	user = await session.scalars(query)
	user = user.first()
	if user:
		try:
			user.telegram_id = telegram_id
			await session.commit()

		except Exception:
			await session.rollback()

			raise HTTPException(status_code=400, detail={
				"status": "error",
				"details": "Another user is already linked to this telegram account."
			})

	else:
		raise HTTPException(status_code=404, detail={
				"status": "error",
				"details": "User not found."
			})

	return {"status": "success"}
