from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="49ers Live Gamecast")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/overlay", include_in_schema=False)
def overlay() -> FileResponse:
    return FileResponse(STATIC_DIR / "overlay.html")
