import asyncio
import logging
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

# Maximum page number for TOP_250_MOVIES collection
MAX_PAGE = 5


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


async def get_random_movie() -> dict[str, Any] | None:
    """Fetch a random movie from the Kinopoisk TOP-250 collection.

    Returns a dict with movie details, or None if something went wrong.
    """
    async with aiohttp.ClientSession() as session:
        # 1. Pick a random page and fetch the collection
        page = randint(1, MAX_PAGE)
        collection_url = f"{BASE_URL}/films/collections?type=TOP_250_MOVIES&page={page}"
        collection_data = await _fetch_json(session, collection_url)

        if not collection_data:
            return None

        items = collection_data.get("items", [])
        if not items:
            logger.warning("No items found on page %d", page)
            return None

        # 2. Pick a random movie from the page
        movie = items[randint(0, len(items) - 1)]
        movie_id = movie.get("kinopoiskId")

        if not movie_id:
            return None

        # 3. Fetch full movie details (description, etc.)
        detail_url = f"{BASE_URL}/films/{movie_id}"
        detail_data = await _fetch_json(session, detail_url)

        if detail_data:
            movie.update(detail_data)

        return movie