import asyncio
import logging
from datetime import datetime
from random import randint
from typing import Any

import aiohttp

from config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://kinopoiskapiunofficial.tech/api/v2.2"
BASE_URL_V21 = "https://kinopoiskapiunofficial.tech/api/v2.1"
HEADERS = {
    "X-API-KEY": settings.kp_api_key,
    "Content-Type": "application/json",
}

MAX_PAGE = 5
MAX_PAGE_FILTER = 3
MAX_RETRIES = 15

# Production statuses that indicate the movie hasn't been released yet
UNRELEASED_STATUSES = {"POST_PRODUCTION", "IN_PRODUCTION", "PRE_PRODUCTION"}


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


def _is_valid_movie(movie: dict[str, Any]) -> bool:
    """Check if the movie is valid for display.

    A movie is valid if:
    1. productionStatus is not POST_PRODUCTION, IN_PRODUCTION, or PRE_PRODUCTION.
    2. If the movie is from the current year, it must have a rating
       (ratingKinopoisk or ratingImdb) — this ensures real people have watched it.
    """
    # 1. Check production status
    status = movie.get("productionStatus")
    if status and status.upper() in UNRELEASED_STATUSES:
        logger.debug(
            "Skipping movie %s — production status: %s",
            movie.get("nameRu", movie.get("kinopoiskId")),
            status,
        )
        return False

    # 2. For current-year movies, require a rating
    year = movie.get("year")
    if year:
        try:
            if int(year) >= datetime.now().year:
                rating = movie.get("ratingKinopoisk") or movie.get("ratingImdb")
                if not rating:
                    logger.debug(
                        "Skipping current-year movie %s — no rating yet",
                        movie.get("nameRu", movie.get("kinopoiskId")),
                    )
                    return False
        except (ValueError, TypeError):
            pass

    return True


async def _pick_and_enrich(
    session: aiohttp.ClientSession,
    items: list[dict[str, Any]],
    max_attempts: int = MAX_RETRIES,
) -> dict[str, Any] | None:
    """Pick a random valid movie from items and enrich with details.

    Retries up to max_attempts times if the picked movie isn't valid.
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

        if _is_valid_movie(movie):
            return movie

        logger.debug(
            "Skipping invalid movie (attempt %d/%d): %s",
            attempt + 1,
            max_attempts,
            movie.get("nameRu", movie_id),
        )

    logger.warning("Exhausted %d attempts — no valid movie found in this batch", max_attempts)
    return None


async def get_random_movie() -> dict[str, Any] | None:
    """Fetch a random valid movie from the Kinopoisk TOP-250 collection."""
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
    """Fetch a random valid movie by collection type or genre.

    For genre queries, uses type=FILM and ratingFrom=6.5 to automatically
    filter out unreleased content (movies without ratings won't appear).
    """
    async with aiohttp.ClientSession() as session:
        if collection_type:
            page = randint(1, MAX_PAGE_FILTER)
            url = f"{BASE_URL}/films/collections?type={collection_type}&page={page}"
        elif genre_id:
            page = randint(1, MAX_PAGE_FILTER)
            url = (
                f"{BASE_URL}/films"
                f"?genres={genre_id}"
                f"&order=RATING"
                f"&type=FILM"
                f"&ratingFrom=6.5"
                f"&page={page}"
            )
        else:
            logger.error("get_movie_by_criteria called without collection_type or genre_id")
            return None

        data = await _fetch_json(session, url)
        if not data:
            return None

        items = data.get("items", [])
        if not items:
            logger.warning(
                "No items found for criteria (collection=%s, genre=%s, page=%d)",
                collection_type,
                genre_id,
                page,
            )
            return None

        return await _pick_and_enrich(session, items)


async def get_recent_releases() -> dict[str, Any] | None:
    """Fetch a random recently released movie from digital releases.

    Uses the v2.1/films/releases endpoint with the current year and month.
    Falls back to the previous month if the current one has no results.
    """
    now = datetime.now()
    year = now.year
    month = now.month

    async with aiohttp.ClientSession() as session:
        for offset in range(3):  # try current month, then up to 2 months back
            target_month = month - offset
            target_year = year
            while target_month <= 0:
                target_month += 12
                target_year -= 1

            if target_year < 2020:
                break

            page = randint(1, 3)
            url = f"{BASE_URL_V21}/films/releases?year={target_year}&month={target_month}&page={page}"
            data = await _fetch_json(session, url)

            if not data:
                continue

            items = data.get("items", [])
            if not items:
                logger.debug(
                    "No releases found for %d-%d, trying previous month",
                    target_year,
                    target_month,
                )
                continue

            # Normalize filmId → kinopoiskId (releases endpoint uses filmId)
            for item in items:
                if "filmId" in item and "kinopoiskId" not in item:
                    item["kinopoiskId"] = item["filmId"]

            result = await _pick_and_enrich(session, items)
            if result:
                return result

    logger.warning("No recent releases found after trying multiple months")
    return None