from datetime import UTC, datetime

from fastapi import APIRouter, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import CONFIRMED, Booking
from app.schemas import BookingCreate, BookingOut
from app.services import bookings as service

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(data: BookingCreate, db: DbSession, current_user: CurrentUser) -> Booking:
    return service.create_booking(db, current_user, data)


@router.get("/me", response_model=list[BookingOut])
def my_bookings(db: DbSession, current_user: CurrentUser, upcoming: bool = False) -> list[Booking]:
    query = select(Booking).where(Booking.user_id == current_user.id)
    if upcoming:
        query = query.where(Booking.status == CONFIRMED, Booking.start_at > datetime.now(UTC))
    return list(db.scalars(query.order_by(Booking.start_at)))


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: DbSession, current_user: CurrentUser) -> Booking:
    return service.get_user_booking(db, current_user, booking_id)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, db: DbSession, current_user: CurrentUser) -> Booking:
    return service.cancel_booking(db, current_user, booking_id)
