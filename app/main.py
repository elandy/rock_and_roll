from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from sqlalchemy import text

from app.db.session import engine
from app.api.ingestion import router as ingestion_router
from app.api.podcasts import router as podcasts_router
from app.api.export import router as export_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    yield


app = FastAPI(
    title="Rock & Roll Podcast Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(ingestion_router)
app.include_router(podcasts_router)
app.include_router(export_router)

@app.get("/health", tags=["Health"])
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "database_unavailable",
                "message": "Database is unavailable",
            },
        ) from exc

    return {"status": "ok"}