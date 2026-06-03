import asyncio
import json
import logging
import os
from pathlib import Path

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from handlers.common import router as common_router
from services.kinopoisk import get_random_movie, get_movie_by_criteria

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

# ── Bot setup ──────────────────────────────────────────────────────────────

bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(common_router)


# ── API handlers ───────────────────────────────────────────────────────────

async def api_random_movie(request: web.Request) -> web.Response:
    """GET /api/movies/random?type=...&genre=..."""
    collection_type = request.query.get("type")
    genre_raw = request.query.get("genre")

    try:
        if genre_raw:
            genre_id = int(genre_raw)
            movie = await get_movie_by_criteria(genre_id=genre_id)
        elif collection_type:
            movie = await get_movie_by_criteria(collection_type=collection_type)
        else:
            movie = await get_random_movie()
    except Exception as exc:
        logger.exception("API error")
        return web.json_response({"error": str(exc)}, status=500)

    if not movie:
        return web.json_response({"error": "No movie found"}, status=404)

    # Serialize — keep only what the frontend needs
    result = {
        "kinopoiskId": movie.get("kinopoiskId"),
        "nameRu": movie.get("nameRu"),
        "nameOriginal": movie.get("nameOriginal"),
        "year": movie.get("year"),
        "posterUrl": movie.get("posterUrl"),
        "posterUrlPreview": movie.get("posterUrlPreview"),
        "ratingKinopoisk": movie.get("ratingKinopoisk"),
        "ratingImdb": movie.get("ratingImdb"),
        "genres": movie.get("genres", []),
        "description": movie.get("description"),
        "shortDescription": movie.get("shortDescription"),
    }
    return web.json_response(result)


# ── Static file server ─────────────────────────────────────────────────────

async def web_app_page(request: web.Request) -> web.Response:
    """Serve the main HTML page."""
    html_path = STATIC_DIR / "index.html"
    if not html_path.exists():
        return web.Response(text="index.html not found", status=404)
    return web.FileResponse(html_path)


async def redirect_to_webapp(request: web.Request) -> web.Response:
    """Redirect / to /web-app."""
    raise web.HTTPFound("/web-app")


# ── App factory ────────────────────────────────────────────────────────────

async def create_app() -> web.Application:
    app = web.Application()

    # API routes
    app.router.add_get("/api/movies/random", api_random_movie)

    # Static files
    app.router.add_get("/", redirect_to_webapp)
    app.router.add_get("/web-app", web_app_page)
    app.router.add_static("/static", path=str(STATIC_DIR), name="static")

    return app


# ── Main ───────────────────────────────────────────────────────────────────

async def main() -> None:
    # Start the aiohttp web server
    app = await create_app()
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Web server started on 0.0.0.0:%d", port)

    # Start bot polling
    logger.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")