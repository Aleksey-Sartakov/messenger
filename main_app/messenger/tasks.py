import asyncio

import httpx

from main_app.auth.services.user_service import UserService
from main_app.config import celery_manager, settings
from main_app.database import async_sessionmaker_instance, async_engine


@celery_manager.task
def send_notification(recipient_id: int, sender_id: int) -> None:
    async def notify():
        await async_engine.dispose(close=False)

        async with async_sessionmaker_instance() as session:
            recipient = await UserService.get_by_pk(session, recipient_id)
            telegram_id = recipient.telegram_id

            if telegram_id:
                sender = await UserService.get_by_pk(session, sender_id)
                sender_full_name = f"{sender.first_name} {sender.last_name}"

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"http://{settings.NOTIFICATION_SERVICE_HOST}:{settings.NOTIFICATION_SERVICE_PORT}/notify/",
                        params={"telegram_id": telegram_id, "sender_full_name": sender_full_name}
                    )
                    response.raise_for_status()

    asyncio.run(notify())
