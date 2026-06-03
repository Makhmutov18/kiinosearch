import asyncio
import logging
from datetime import datetime
from random import randint
from typing import Any

import aiohttp

from config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://kinopoiskapiunofficial.tech/api/v2.2"
HEADERS = {
    "X-API-KEY": settings.kp_api_key,
    "Content-Type": "application/json",
}

MAX_PAGE = 5
MAX_PAGE_FILTER = 3
MAX_RETRIES = 15


async def _fetch_json(session: aiohttp.ClientSession, url: str) -> dict[str, Any] | None:
    """Make a GET request and return parsed JSON, or None on failure."""
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.warning("API returned status %d for %s", resp.status, url)
                return None
            return await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.error("Request to %s failed: %s", url, exc)
        return None


async def _fetch_movie_details(session: aiohttp.ClientSession, movie_id: int) -> dict[str, Any] | None:
    """Fetch full movie details by ID and return them, or None on failure."""
    detail_url = f"{BASE_URL}/films/{movie_id}"
    return await _fetch_json(session, detail_url)


def _is_released(movie: dict[str, Any]) -> bool:
    """Check if the movie has been released (year <= current year).

    Returns False if year is missing or in the future.
    """
    year = movie.get("year")
    if not year:
        return False
    try:
        return int(year) <= datetime.now().year
    except (ValueError, TypeError):
        return False


async def _pick_and_enrich(
    session: aiohttp.ClientSession,
    items: list[dict[str, Any]],
    max_attempts: int = MAX_RETRIES,
) -> dict[str, Any] | None:
    """Pick a random released movie from items and enrich with details.

    Retries up to max_attempts times if the picked movie hasn't been released yet.
    """
    if not items:
        return None

    for attempt in range(max_attempts):
        movie = items[randint(0, len(items) - 1)]
        movie_id = movie.get("kinopoiskId")

        if not movie_id:
            continue

        detail_data = await _fetch_movie_details(session, movie_id)
        if detail_data:
            movie.update(detail_data)

        if _is_released(movie):
            return movie

        logger.debug("Skipping unreleased movie (attempt %d/%d): %s",
                      attempt + 1, max_attempts, movie.get("nameRu", movie_id))

    logger.warning("Exhausted %d attempts — no released movie found in this batch", max_attempts)
    return None


async def get_random_movie() -> dict[str, Any] | None:
    """Fetch a random released movie from the Kinopoisk TOP-250 collection.

    Returns a dict with movie details, or None if something went wrong.
    """
    async with aiohttp.ClientSession() as session:
        page = randint(1, MAX_PAGE)
        collection_url = f"{BASE_URL}/films/collections?type=TOP_250_MOVIES&page={page}"
        collection_data = await _fetch_json(session, collection_url)

        if not collection_data:
            return None

        items = collection_data.get("items", [])
        if not items:
            logger.warning("No items found on page %d", page)
            return None

        return await _pick_and_enrich(session, items)


async def get_movie_by_criteria(
    collection_type: str | None = None,
    genre_id: int | None = None,
) -> dict[str, Any] | None:
    """Fetch a random released movie by collection type or genre.

    Args:
        collection_type: One of TOP_250_MOVIES, TOP_POPULAR_MOVIES, CLOSING_RELEASES.
        genre_id: Genre ID from Kinopoisk (e.g. 2 for Drama).

    Returns:
        A dict with movie details, or None on failure.
    """
    async with aiohttp.ClientSession() as session:
        if collection_type:
            page = randint(1, MAX_PAGE_FILTER)
            url = f"{BASE_URL}/films/collections?type={collection_type}&page={page}"
        elif genre_id:
            page = randint(1, MAX_PAGE_FILTER)
            url = f"{BASE_URL}/films?genres={genre_id}&order=RATING&type=FILM&ratingFrom=7&page={page}"
        else:
            logger.error("get_movie_by_criteria called without collection_type or genre_id")
            return None

        data = await _fetch_json(session, url)
        if not data:
            return None

        items = data.get("items", [])
        if not items:
            logger.warning("No items found for criteria (collection=%s, genre=%s, page=%d)",
                           collection_type, genre_id, page)
            return None

        return await _pick_and_enrich(session, items)