"""Booking business rules. Routers stay thin and call these functions."""

from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CANCELLED, CONFIRMED, Booking, Resource, User
from app.schemas import BookingCreate

MIN_DURATION = timedelta(minutes=30)
MAX_DURATION = timedelta(hours=4)
MAX_DAYS_IN_ADVANCE = 90


def as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; PostgreSQL returns aware ones. Normalize both to UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _conflict() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The resource is already booked for that time")


def find_overlapping(db: Session, resource_id: int, start: datetime, end: datetime) -> Booking | None:
    # Two ranges overlap when each one starts before the other ends.
    # Touching ranges (10:00-11:00 and 11:00-12:00) do NOT overlap.
    return db.scalar(
        select(Booking)
        .where(
            Booking.resource_id == resource_id,
            Booking.status == CONFIRMED,
            Booking.start_at < end,
            Booking.end_at > start,
        )
        .limit(1)
    )


def create_booking(db: Session, user: User, data: BookingCreate) -> Booking:
    start, end = as_utc(data.start_at), as_utc(data.end_at)
    now = datetime.now(UTC)

    if start <= now:
        raise _unprocessable("Bookings must start in the future")
    if start > now + timedelta(days=MAX_DAYS_IN_ADVANCE):
        raise _unprocessable(f"Bookings can be made at most {MAX_DAYS_IN_ADVANCE} days in advance")
    if not MIN_DURATION <= end - start <= MAX_DURATION:
        raise _unprocessable("Bookings must last between 30 minutes and 4 hours")

    resource = db.get(Resource, data.resource_id)
    if resource is None or not resource.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    if find_overlapping(db, resource.id, start, end):
        raise _conflict()

    booking = Booking(resource_id=resource.id, user_id=user.id, start_at=start, end_at=end, notes=data.notes)
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        # Two requests passed the check above at the same time; PostgreSQL's EXCLUDE
        # constraint rejected the second one. Report it as a normal conflict.
        db.rollback()
        raise _conflict() from None
    db.refresh(booking)
    return booking


def get_user_booking(db: Session, user: User, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    # 404 (not 403) for other users' bookings, so ids aren't leaked. Admins can see all.
    if booking is None or (booking.user_id != user.id and not user.is_admin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


def cancel_booking(db: Session, user: User, booking_id: int) -> Booking:
    booking = get_user_booking(db, user, booking_id)
    if booking.status != CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is already cancelled")
    if as_utc(booking.start_at) <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Past or ongoing bookings can't be cancelled")
    booking.status = CANCELLED
    db.commit()
    db.refresh(booking)
    return booking


def booked_slots(db: Session, resource_id: int, day: date) -> list[Booking]:
    day_start = datetime.combine(day, time.min, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)
    return list(
        db.scalars(
            select(Booking)
            .where(
                Booking.resource_id == resource_id,
                Booking.status == CONFIRMED,
                Booking.start_at < day_end,
                Booking.end_at > day_start,
            )
            .order_by(Booking.start_at)
        )
    )
