import asyncio
from functools import wraps
from typing import Callable, ParamSpec, Awaitable

from main_app.config import logger
from main_app.database import redis_client


Params = ParamSpec("Params")


class PubSubService:
	@classmethod
	async def send(cls, channel_name: str, message: str) -> None:
		await redis_client.publish(channel_name, message)

	@classmethod
	def listen(cls, func: Callable[[Params.args, str, Params.kwargs], Awaitable[None]]) -> Callable[
		[Params.args, str, Params.kwargs],
		Awaitable[None]
	]:
		@wraps(func)
		async def wrapper(*args: Params.args, channel_name: str, **kwargs: Params.kwargs) -> None:
			async with redis_client.pubsub() as channel:
				await channel.subscribe(channel_name)
				logger.info(f"Start listening '{channel_name}' pubsub...")
				try:
					async for message in channel.listen():
						if message["type"] == "message":
							await func(*args, message['data'], **kwargs)

				except asyncio.CancelledError:
					await channel.unsubscribe(channel_name)
					logger.info(f"Stop listening '{channel_name}' pubsub.")

		return wrapper
