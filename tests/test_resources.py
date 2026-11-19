from tests.conftest import slot


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_me(client, user_headers):
    res = client.get("/auth/me", headers=user_headers)
    assert res.status_code == 200
    assert res.json() == {"id": 1, "email": "ana@example.com", "is_admin": False}


def test_admin_creates_resource(client, admin_headers):
    res = client.post("/resources", json={"name": "Court 1", "capacity": 4}, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["is_active"] is True


def test_non_admin_cannot_create_resource(client, user_headers):
    res = client.post("/resources", json={"name": "Court 1"}, headers=user_headers)
    assert res.status_code == 403


def test_duplicate_resource_name(client, admin_headers, room):
    res = client.post("/resources", json={"name": "Room A"}, headers=admin_headers)
    assert res.status_code == 409


def test_list_resources_is_public(client, room):
    res = client.get("/resources")
    assert res.status_code == 200
    assert [r["name"] for r in res.json()] == ["Room A"]


def test_availability_shows_booked_slots(client, user_headers, room):
    start, end = slot(day_offset=2, hour=9)
    client.post("/bookings", json={"resource_id": room["id"], "start_at": start, "end_at": end}, headers=user_headers)

    day = start[:10]
    res = client.get(f"/resources/{room['id']}/availability?date={day}")

    assert res.status_code == 200
    booked = res.json()["booked"]
    assert len(booked) == 1
    assert booked[0]["start_at"].startswith(f"{day}T09:00")


def test_availability_other_day_is_empty(client, user_headers, room):
    start, end = slot(day_offset=2)
    client.post("/bookings", json={"resource_id": room["id"], "start_at": start, "end_at": end}, headers=user_headers)
    other_day = slot(day_offset=3)[0][:10]
    assert client.get(f"/resources/{room['id']}/availability?date={other_day}").json()["booked"] == []


def test_availability_unknown_resource(client):
    assert client.get("/resources/999/availability?date=2030-01-01").status_code == 404
