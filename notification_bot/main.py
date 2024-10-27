import httpx as httpx
import asyncio
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from fastapi import FastAPI, HTTPException


TELEGRAM_BOT_TOKEN = "7875873156:AAFqIkUld5qxc1nnQsKaNmLslJ6xaQcZa0k"


bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()


@app.post("/notify/")
async def notify(telegram_id: int, sender_full_name: str):
    try:
        await bot.send_message(telegram_id, f"User {sender_full_name} has sent you a message!")

        return {"status": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "status": "success",
            "details": str(e)
        })


@dp.message(CommandStart())
async def send_welcome(message: Message):
    await message.answer("Привет! Отправьте ваш email для привязки аккаунта.")


@dp.message(lambda message: '@' in message.text)
async def link_email(message: Message):
    user_telegram_id = message.from_user.id
    user_email = message.text.strip()

    # Отправка запроса на привязку email к telegram_id
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://messenger:8000/link_telegram_id/",
            params={"email": user_email, "telegram_id": user_telegram_id}
        )

        if response.status_code == 200:
            await message.reply("Аккаунт успешно привязан!")
        else:
            await message.reply("Ошибка: email не найден или привязка не удалась (К одному Telegram-аккаунту "
                                "невозможно привязать более одного пользователя).")


# if __name__ == "__main__":
#     import asyncio
#     import uvicorn
#     from threading import Thread
#
#     def start_polling():
#         asyncio.run(dp.start_polling(bot))
#
#     polling_thread = Thread(target=start_polling)
#     polling_thread.start()
#
#     uvicorn.run(app, host="0.0.0.0", port=8001)


async def start_bot():
    await dp.start_polling(bot)


async def start_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=8001, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    bot_task = asyncio.create_task(start_bot())
    api_task = asyncio.create_task(start_api())
    await asyncio.gather(bot_task, api_task)


if __name__ == "__main__":
    asyncio.run(main())
