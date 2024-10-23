from typing import Annotated, Literal

from fastapi import Depends, Query, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.config import auth_backend
from src.auth.db_models import UserDbModel
from src.auth.manager import auth_manager
from src.auth.pydantic_schemas import UserRead, UserUpdate
from src.base_db_config import get_async_session, FilterParams
from src.config import settings


current_active_user = auth_manager.current_user(active=True, optional=True)

auth_router = auth_manager.get_auth_router(auth_backend)

templates = Jinja2Templates(directory=settings.TEMPLATES_PATH)


@auth_router.get("/", response_class=HTMLResponse, summary="Страница авторизации")
async def get_auth_page(request: Request, current_user: UserDbModel | None = Depends(current_active_user)):
	if not current_user:
		return templates.TemplateResponse("auth.html", {"request": request})
	else:
		return RedirectResponse(url="/messenger")


users_router = auth_manager.get_users_router(UserRead, UserUpdate)


@users_router.get("/", response_model=list[UserRead])
async def get_all_users(
		filter_params: Annotated[FilterParams, Query()],
		session: AsyncSession = Depends(get_async_session)
):
	default_sort_by = "id"
	default_order = "asc"

	query = (
		select(UserDbModel)
	)

	if filter_params.sort_by:
		for i, attribute in enumerate(filter_params.sort_by):
			if hasattr(UserDbModel, attribute):
				if filter_params.order and len(filter_params.order) > i:
					if filter_params.order[i] == "desc":
						query = query.order_by(desc(getattr(UserDbModel, attribute)))
					else:
						query = query.order_by(asc(getattr(UserDbModel, attribute)))

				else:
					query = query.order_by(asc(getattr(UserDbModel, attribute)))

			else:
				raise HTTPException(status_code=422, detail={
					"status": "error",
					"details": f"The specified sorting field '{attribute}' doesn't exist."
				})
	else:
		if default_order == "desc":
			query = query.order_by(desc(getattr(UserDbModel, default_sort_by)))
		else:
			query = query.order_by(asc(getattr(UserDbModel, default_sort_by)))

	query = query.limit(filter_params.limit).offset(filter_params.offset)
	all_users = await session.scalars(query)

	return all_users.all()
