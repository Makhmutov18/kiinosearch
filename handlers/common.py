from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()


def main_keyboard() -> ReplyKeyboardMarkup:
    """Build and return the persistent reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Случайный фильм")],
            [KeyboardButton(text="🍿 Фильтр по жанрам")],
        ],
        resize_keyboard=True,
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle the /start command — send a welcome message with the keyboard."""
    await message.answer(
        "👋 Привет! Я — бот для поиска фильмов.\n\n"
        "Используй кнопки ниже, чтобы найти что посмотреть:",
        reply_markup=main_keyboard(),
    )


@router.message(F.text == "🎬 Случайный фильм")
async def random_movie(message: Message) -> None:
    """Handle the 'Случайный фильм' button — placeholder response."""
    await message.answer(
        "🔍 Ищу случайный фильм... (тут будет интеграция с API)",
        reply_markup=main_keyboard(),
    )