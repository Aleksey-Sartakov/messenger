import traceback

from aioredis.exceptions import ConnectionError as RedisConnectionError
from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from main_app.auth.dependencies import current_active_user_or_none, current_active_user
from main_app.auth.services.auth_service import auth_backend
from main_app.auth.models import User
from main_app.auth.services.auth_service import auth_service
from main_app.auth.schemas import UserRead, UserUpdate, UserCreate
from main_app.auth.services.user_service import UserService
from main_app.dependencies import get_async_session
from main_app.config import settings, logger
from main_app.exceptions import ColumnDoesNotExistError
from main_app.filters import SimpleSorting
from main_app.pagination import DefaultPagination


auth_router = auth_service.get_auth_router(auth_backend)
register_router = auth_service.get_register_router(UserRead, UserCreate)
auth_router.include_router(register_router)

templates = Jinja2Templates(directory=settings.TEMPLATES_PATH)


@auth_router.get("/", response_class=HTMLResponse, summary="Страница авторизации")
async def get_auth_page(request: Request, current_user: User | None = Depends(current_active_user_or_none)):
    if not current_user:
        return templates.TemplateResponse("auth.html", {"request": request})
    else:
        return RedirectResponse(url="/messenger")


users_router = auth_service.get_users_router(UserRead, UserUpdate)


@users_router.get("/", response_model=list[UserRead])
async def get_users_list(
        pagination: DefaultPagination = Depends(),
        sorting: SimpleSorting = Depends(),
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(current_active_user)
):
    logger.info(f"'get_users_list' has called by user with id {current_user.id}")

    try:
        users = await UserService.get_from_cache(sorting, pagination)
    except RedisConnectionError:
        users = None
        logger.warning("Connection to redis failed while getting a cache!")

    if not users:
        try:
            users = await UserService.get(session, sorting, pagination)

            if users:
                await UserService.save_to_cache(users, sorting, pagination)

        except RedisConnectionError:
            logger.warning("Connection to redis failed while saving a cache!")

        except ColumnDoesNotExistError as e:
            traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.error(f"{e} More details:\n{traceback_message}")

            raise HTTPException(status_code=400, detail={
                "status": "error",
                "details": e
            })

        except SQLAlchemyError as e:
            traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.error(f"Details:\n{traceback_message}")

            raise HTTPException(status_code=500, detail={
                "status": "error",
                "details": f"An error occurred while accessing the database: {e}"
            })

        except Exception as e:
            traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.error(f"Details:\n{traceback_message}")

            raise HTTPException(status_code=500, detail={
                "status": "error",
                "details": f"An unexpected server error has occurred: {e}"
            })

    return users


@users_router.post("/link_telegram_id/")
async def link_telegram_id(email: str, telegram_id: int, session: AsyncSession = Depends(get_async_session)):
    user = await UserService.get_one_or_none(session, {"email": email})
    if user:
        try:
            user.telegram_id = telegram_id
            await session.commit()

        except IntegrityError:
            await session.rollback()

            raise HTTPException(status_code=400, detail={
                "status": "error",
                "details": "The specified telegram account is already being used by another user"
            })

        except SQLAlchemyError as e:
            traceback_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.error(f"Details:\n{traceback_message}")

            await session.rollback()

            raise HTTPException(status_code=500, detail={
                "status": "error",
                "details": f"An error occurred while accessing the database: {e}"
            })

    else:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "details": "User not found."
        })

    return {"status": "success"}
