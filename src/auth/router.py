import json
from typing import Annotated

from fastapi import Depends, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.config import auth_backend
from src.auth.db_models import UserDbModel
from src.auth.manager import auth_manager
from src.auth.pydantic_schemas import UserRead, UserUpdate
from src.base_db_config import get_async_session, FilterParams
from src.config import settings, redis_client


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

	if filter_params.sort_by:
		sort_by = filter_params.sort_by[0]
		if hasattr(UserDbModel, sort_by):
			if filter_params.order:
				order = filter_params.order[0]
			else:
				order = default_order
		else:
			raise HTTPException(status_code=422, detail={
				"status": "error",
				"details": f"The specified sorting field '{sort_by}' doesn't exist."
			})
	else:
		sort_by = default_sort_by
		order = default_order

	cached_users = await redis_client.get(f"{settings.KEY_PREFIX_FOR_CACHE_USERS}:{settings.KEY_FOR_CACHE_ALL_USERS}")
	if cached_users:
		if order == "asc":
			reverse = False
		else:
			reverse = True

		all_users = json.loads(cached_users)
		all_users.sort(key=lambda x: x[sort_by], reverse=reverse)

		return all_users[filter_params.offset : filter_params.offset + filter_params.limit]

	else:
		query = select(UserDbModel)
		if order == "desc":
			query = query.order_by(desc(getattr(UserDbModel, sort_by)))
		else:
			query = query.order_by(asc(getattr(UserDbModel, sort_by)))
		query = query.limit(filter_params.limit).offset(filter_params.offset)

		all_users = await session.scalars(query)

		return all_users.all()
