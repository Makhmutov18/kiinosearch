import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.html import escape

from services.kinopoisk import get_random_movie

logger = logging.getLogger(__name__)

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


def _format_movie_caption(movie: dict) -> str:
    """Format a movie dict into an HTML caption for the photo message."""
    name = movie.get("nameRu") or movie.get("nameOriginal") or "Без названия"
    year = movie.get("year", "")
    rating = movie.get("ratingKinopoisk") or movie.get("ratingImdb", "")
    description = movie.get("description") or movie.get("shortDescription", "")

    # Collect genres
    genres_raw = movie.get("genres", [])
    genres = ", ".join(g.get("genre", "") for g in genres_raw if g.get("genre"))

    parts = [f"<b>{escape(name)}</b>"]
    if year:
        parts.append(f"📅 {escape(str(year))}")
    if genres:
        parts.append(f"🎭 {escape(genres)}")
    if rating:
        parts.append(f"⭐ Рейтинг КП: <b>{escape(str(rating))}</b>")
    if description:
        # Truncate long descriptions
        desc = description if len(description) <= 500 else description[:497] + "..."
        parts.append(f"\n{escape(desc)}")

    return "\n".join(parts)


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
    """Handle the 'Случайный фильм' button — fetch a random movie from Kinopoisk API."""
    await message.answer("🔍 Ищу случайный фильм...", reply_markup=main_keyboard())

    try:
        movie = await get_random_movie()
    except Exception:
        logger.exception("Unexpected error while fetching random movie")
        movie = None

    if not movie:
        await message.answer(
            "😔 Ой, не удалось получить фильм, попробуй еще раз!",
            reply_markup=main_keyboard(),
        )
        return

    poster_url = (
        movie.get("posterUrl")
        or movie.get("posterUrlPreview")
    )

    caption = _format_movie_caption(movie)

    if poster_url:
        try:
            await message.answer_photo(
                photo=poster_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
            return
        except Exception:
            logger.warning("Failed to send photo for movie %s, falling back to text", movie.get("kinopoiskId"))

    # Fallback: send as text if no poster or photo send failed
    await message.answer(
        caption,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )