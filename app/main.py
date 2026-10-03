import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes_control, routes_game, routes_ws
from app.dependencies import (
    SYNC_INTERVAL_SECONDS,
    get_game_service,
    get_provider,
    get_provider_health,
)
from app.services.provider_sync import sync_forever

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync = asyncio.create_task(
        sync_forever(
            get_provider(), get_game_service(), get_provider_health(), SYNC_INTERVAL_SECONDS
        )
    )
    yield
    sync.cancel()
    with suppress(asyncio.CancelledError):
        await sync


app = FastAPI(title="49ers Live Gamecast", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(routes_game.router)
app.include_router(routes_ws.router)
app.include_router(routes_control.router)


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/overlay", include_in_schema=False)
def overlay() -> FileResponse:
    return FileResponse(STATIC_DIR / "overlay.html")


@app.get("/control", include_in_schema=False)
def control() -> FileResponse:
    return FileResponse(STATIC_DIR / "control.html")
