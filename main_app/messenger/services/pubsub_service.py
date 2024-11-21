import asyncio
from functools import wraps
from typing import Callable, ParamSpec, Awaitable

from main_app.config import logger
from main_app.database import redis_client


Params = ParamSpec("Params")


class PubSubService:
    """
    Redis pub/sub management service
    """

    @classmethod
    async def send(cls, channel_name: str, message: str) -> None:
        """
        Post a message to the channel.
        """

        await redis_client.publish(channel_name, message)

    @classmethod
    def listen(
            cls,
            func: Callable[
                [Params.args, str, Params.kwargs],
                Awaitable[None]
            ]
    ) -> Callable[
        [Params.args, str, Params.kwargs],
        Awaitable[None]
    ]:
        """
        A decorator for a function that handles messages received from the channel.

        :param func: The handler function
        :return: Modified handler function.
        """

        @wraps(func)
        async def wrapper(*args: Params.args, channel_name: str, **kwargs: Params.kwargs) -> None:
            """
            Subscribe to the channel and start listening. When a new message
            is received, call the specified function to handle it.

            :param args: args from handler function.
            :param channel_name: Additional param - the name of the channel you want to listen to.
            :param kwargs: kwargs from handler function.
            """

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
