import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import settings
from handlers.common import router as common_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Initialize the bot, register routers and start polling."""
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(common_router)

    logger.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())