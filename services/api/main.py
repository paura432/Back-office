from fastapi import FastAPI

app = FastAPI(title="TrackFlow API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}