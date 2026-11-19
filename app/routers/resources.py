from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.deps import AdminUser, DbSession
from app.models import Resource
from app.schemas import Availability, ResourceCreate, ResourceOut, TimeSlot
from app.services.bookings import booked_slots

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("", response_model=list[ResourceOut])
def list_resources(db: DbSession) -> list[Resource]:
    return list(db.scalars(select(Resource).where(Resource.is_active.is_(True)).order_by(Resource.name)))


@router.post("", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(data: ResourceCreate, db: DbSession, _admin: AdminUser) -> Resource:
    if db.scalar(select(Resource).where(Resource.name == data.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource name already exists")
    resource = Resource(**data.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("/{resource_id}/availability", response_model=Availability)
def availability(resource_id: int, day: Annotated[date, Query(alias="date")], db: DbSession) -> Availability:
    """Booked time slots (UTC) for one day. Any slot not listed is free."""
    resource = db.get(Resource, resource_id)
    if resource is None or not resource.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    slots = booked_slots(db, resource_id, day)
    return Availability(
        resource_id=resource_id,
        date=day,
        booked=[TimeSlot(start_at=b.start_at, end_at=b.end_at) for b in slots],
    )
