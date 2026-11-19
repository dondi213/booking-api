from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, model_validator


# ---------- Users ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_admin: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Resources ----------
class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    capacity: int = Field(default=1, ge=1, le=500)


class ResourceOut(ResourceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class TimeSlot(BaseModel):
    start_at: datetime
    end_at: datetime


class Availability(BaseModel):
    resource_id: int
    date: date
    booked: list[TimeSlot]


# ---------- Bookings ----------
class BookingCreate(BaseModel):
    resource_id: int
    # AwareDatetime rejects dates without a timezone ("2026-12-01T10:00"), avoiding ambiguity.
    start_at: AwareDatetime
    end_at: AwareDatetime
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def end_after_start(self) -> "BookingCreate":
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_id: int
    user_id: int
    start_at: datetime
    end_at: datetime
    status: str
    notes: str | None
    created_at: datetime
