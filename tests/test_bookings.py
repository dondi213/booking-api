from datetime import UTC, datetime, timedelta

import pytest

from app.models import Booking
from tests.conftest import slot


def book(client, headers, resource_id, start, end, **extra):
    return client.post(
        "/bookings",
        json={"resource_id": resource_id, "start_at": start, "end_at": end, **extra},
        headers=headers,
    )


def test_create_booking(client, user_headers, room):
    start, end = slot()
    res = book(client, user_headers, room["id"], start, end, notes="Team meeting")

    assert res.status_code == 201, res.text
    assert res.json()["status"] == "confirmed"
    assert res.json()["notes"] == "Team meeting"


def test_requires_auth(client, room):
    start, end = slot()
    assert (
        client.post("/bookings", json={"resource_id": room["id"], "start_at": start, "end_at": end}).status_code == 401
    )


@pytest.mark.parametrize(
    ("hour", "minutes"),
    [
        (10, 60),  # exact same slot
        (9, 90),  # starts before, ends inside (9:00-10:30)
        (10, 30),  # inside (10:00-10:30)
        (9, 180),  # covers it completely (9:00-12:00)
    ],
)
def test_overlapping_booking_rejected(client, user_headers, other_headers, room, hour, minutes):
    book(client, user_headers, room["id"], *slot(hour=10, minutes=60))  # 10:00-11:00

    res = book(client, other_headers, room["id"], *slot(hour=hour, minutes=minutes))
    assert res.status_code == 409


def test_back_to_back_bookings_allowed(client, user_headers, other_headers, room):
    assert book(client, user_headers, room["id"], *slot(hour=10, minutes=60)).status_code == 201  # 10-11
    assert book(client, other_headers, room["id"], *slot(hour=11, minutes=60)).status_code == 201  # 11-12


def test_same_time_different_resource_allowed(client, user_headers, admin_headers, room):
    other_room = client.post("/resources", json={"name": "Room B"}, headers=admin_headers).json()
    assert book(client, user_headers, room["id"], *slot()).status_code == 201
    assert book(client, user_headers, other_room["id"], *slot()).status_code == 201


def test_end_before_start_rejected(client, user_headers, room):
    start, end = slot()
    assert book(client, user_headers, room["id"], end, start).status_code == 422


def test_datetime_without_timezone_rejected(client, user_headers, room):
    res = book(client, user_headers, room["id"], "2030-01-01T10:00:00", "2030-01-01T11:00:00")
    assert res.status_code == 422


@pytest.mark.parametrize(
    ("day_offset", "minutes"),
    [
        (1, 15),  # too short
        (1, 300),  # too long (5 hours)
        (-1, 60),  # in the past
        (120, 60),  # too far in advance
    ],
)
def test_business_rules(client, user_headers, room, day_offset, minutes):
    res = book(client, user_headers, room["id"], *slot(day_offset=day_offset, minutes=minutes))
    assert res.status_code == 422


def test_unknown_resource(client, user_headers):
    assert book(client, user_headers, 999, *slot()).status_code == 404


def test_cancel_frees_the_slot(client, user_headers, other_headers, room):
    booking = book(client, user_headers, room["id"], *slot()).json()

    res = client.post(f"/bookings/{booking['id']}/cancel", headers=user_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"

    assert book(client, other_headers, room["id"], *slot()).status_code == 201


def test_cancel_twice(client, user_headers, room):
    booking = book(client, user_headers, room["id"], *slot()).json()
    client.post(f"/bookings/{booking['id']}/cancel", headers=user_headers)
    assert client.post(f"/bookings/{booking['id']}/cancel", headers=user_headers).status_code == 409


def test_cannot_cancel_past_booking(client, db, user_headers, room):
    past_start = datetime.now(UTC) - timedelta(days=1)
    booking = Booking(resource_id=room["id"], user_id=1, start_at=past_start, end_at=past_start + timedelta(hours=1))
    db.add(booking)
    db.commit()

    assert client.post(f"/bookings/{booking.id}/cancel", headers=user_headers).status_code == 409


def test_cannot_see_or_cancel_others_bookings(client, user_headers, other_headers, room):
    booking = book(client, user_headers, room["id"], *slot()).json()
    assert client.get(f"/bookings/{booking['id']}", headers=other_headers).status_code == 404
    assert client.post(f"/bookings/{booking['id']}/cancel", headers=other_headers).status_code == 404


def test_admin_can_see_any_booking(client, user_headers, admin_headers, room):
    booking = book(client, user_headers, room["id"], *slot()).json()
    assert client.get(f"/bookings/{booking['id']}", headers=admin_headers).status_code == 200


def test_my_bookings(client, user_headers, other_headers, room):
    book(client, user_headers, room["id"], *slot(hour=10))
    mine = book(client, user_headers, room["id"], *slot(hour=12)).json()
    book(client, other_headers, room["id"], *slot(hour=14))
    client.post(f"/bookings/{mine['id']}/cancel", headers=user_headers)

    assert len(client.get("/bookings/me", headers=user_headers).json()) == 2
    upcoming = client.get("/bookings/me?upcoming=true", headers=user_headers).json()
    assert len(upcoming) == 1
