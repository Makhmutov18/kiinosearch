import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from config import settings

logger = logging.getLogger(__name__)

router = Router()


def webapp_keyboard() -> ReplyKeyboardMarkup:
    """Build a keyboard with a single WebApp button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="🎬 Открыть Кино-Лабораторию",
                web_app=WebAppInfo(url=f"{settings.app_url}/web-app"),
            )],
        ],
        resize_keyboard=True,
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle the /start command — send a welcome message with the WebApp button."""
    await message.answer(
        "👋 Привет! Я — бот для поиска фильмов.\n\n"
        "Нажми кнопку ниже, чтобы открыть Кино-Лабораторию 🎬",
        reply_markup=webapp_keyboard(),
    )