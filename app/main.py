from fastapi import FastAPI

app = FastAPI(title="49ers Live Gamecast")


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok"}
