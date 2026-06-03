import logging
from html import escape

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.kinopoisk import get_movie_by_criteria

logger = logging.getLogger(__name__)

router = Router()

# ── Genre mapping ──────────────────────────────────────────────────────────
GENRES: dict[str, int] = {
    "🎭 Драма": 2,
    "👽 Фантастика": 6,
    "🔪 Триллер": 1,
    "😂 Комедия": 13,
    "💥 Боевик": 11,
}

# ── Keyboard builders ──────────────────────────────────────────────────────

def categories_keyboard() -> InlineKeyboardMarkup:
    """Build the top-level categories inline keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👑 Культовые", callback_data="cat_TOP_250_MOVIES"),
    )
    builder.row(
        InlineKeyboardButton(text="🔥 Популярные", callback_data="cat_TOP_POPULAR_MOVIES"),
    )
    builder.row(
        InlineKeyboardButton(text="⚡️ Новинки", callback_data="cat_CLOSING_RELEASES"),
    )
    builder.row(
        InlineKeyboardButton(text="🎭 По жанрам", callback_data="open_genres"),
    )
    return builder.as_markup()


def genres_keyboard() -> InlineKeyboardMarkup:
    """Build the genres inline keyboard."""
    builder = InlineKeyboardBuilder()
    for name, gid in GENRES.items():
        builder.row(
            InlineKeyboardButton(text=name, callback_data=f"genre_{gid}"),
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_categories"),
    )
    return builder.as_markup()


# ── Helper: send movie card ────────────────────────────────────────────────

async def _send_movie_card(callback: CallbackQuery, movie: dict) -> None:
    """Send a movie card (photo + caption) as a new message."""
    poster_url = movie.get("posterUrl") or movie.get("posterUrlPreview")

    name = movie.get("nameRu") or movie.get("nameOriginal") or "Без названия"
    year = movie.get("year", "")
    rating = movie.get("ratingKinopoisk") or movie.get("ratingImdb", "")
    description = movie.get("description") or movie.get("shortDescription", "")

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
        desc = description if len(description) <= 500 else description[:497] + "..."
        parts.append(f"\n{escape(desc)}")

    caption = "\n".join(parts)

    if poster_url:
        try:
            await callback.message.answer_photo(
                photo=poster_url,
                caption=caption,
                parse_mode="HTML",
            )
            return
        except Exception:
            logger.warning("Failed to send photo for movie %s, falling back to text", movie.get("kinopoiskId"))

    await callback.message.answer(caption, parse_mode="HTML")


# ── Callback handlers ──────────────────────────────────────────────────────

@router.callback_query(F.data == "🍿 Фильтр по жанрам")
@router.callback_query(F.data == "back_to_categories")
async def show_categories(callback: CallbackQuery) -> None:
    """Show the categories inline keyboard."""
    await callback.message.edit_text(
        "Выберите категорию или жанр:",
        reply_markup=categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "open_genres")
async def show_genres(callback: CallbackQuery) -> None:
    """Show the genres inline keyboard."""
    await callback.message.edit_text(
        "Выберите жанр:",
        reply_markup=genres_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def handle_collection(callback: CallbackQuery) -> None:
    """Handle a collection category button press."""
    collection_type = callback.data.removeprefix("cat_")
    await callback.answer("🔍 Ищу фильм...", show_alert=False)

    try:
        movie = await get_movie_by_criteria(collection_type=collection_type)
    except Exception:
        logger.exception("Unexpected error while fetching movie by collection %s", collection_type)
        movie = None

    if not movie:
        await callback.message.answer("😔 Ой, не удалось получить фильм, попробуй еще раз!")
        return

    await _send_movie_card(callback, movie)


@router.callback_query(F.data.startswith("genre_"))
async def handle_genre(callback: CallbackQuery) -> None:
    """Handle a genre button press."""
    genre_id = int(callback.data.removeprefix("genre_"))
    await callback.answer("🔍 Ищу фильм...", show_alert=False)

    try:
        movie = await get_movie_by_criteria(genre_id=genre_id)
    except Exception:
        logger.exception("Unexpected error while fetching movie by genre %d", genre_id)
        movie = None

    if not movie:
        await callback.message.answer("😔 Ой, не удалось получить фильм, попробуй еще раз!")
        return

    await _send_movie_card(callback, movie)