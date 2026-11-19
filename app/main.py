from fastapi import FastAPI
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers import auth, bookings, resources

# The schema is managed by Alembic migrations (`alembic upgrade head`), not create_all().
app = FastAPI(
    title=settings.app_name,
    description="Book rooms, courts or desks without double bookings.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(resources.router)
app.include_router(bookings.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
