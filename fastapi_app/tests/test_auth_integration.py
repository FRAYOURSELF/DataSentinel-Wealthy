from jose import jwt

from app.core.config import settings


def test_login_success_issues_jwt_and_dispatches_ip_check(client):
    response = client.post("/login", json={"username": "alice", "password": "alice_password"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] > 0

    decoded = jwt.decode(payload["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert decoded["sub"] == "alice"

    assert len(client.dispatched_tasks) == 1
    assert client.dispatched_tasks[0]["task_name"] == "worker.tasks.ip_check.check_login_ip"


def test_login_returns_different_device_flag_when_ip_changes(client):
    first = client.post(
        "/login",
        json={"username": "alice", "password": "alice_password"},
        headers={"x-forwarded-for": "1.1.1.1"},
    )
    assert first.status_code == 200
    assert first.json()["different_device"] is False

    second = client.post(
        "/login",
        json={"username": "alice", "password": "alice_password"},
        headers={"x-forwarded-for": "2.2.2.2"},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["different_device"] is True
    assert "different device" in body["message"].lower()


def test_login_rate_limit_blocks_abuse(client):
    # Use wrong password repeatedly so limiter and lockout behavior can be observed.
    for _ in range(settings.login_max_failures_before_block):
        response = client.post("/login", json={"username": "alice", "password": "bad_password"})
        assert response.status_code in (401, 429)

    blocked_response = client.post("/login", json={"username": "alice", "password": "bad_password"})
    assert blocked_response.status_code == 429


def test_protected_prime_endpoint_requires_bearer_token(client):
    response = client.get("/check-prime", params={"number": 7})
    assert response.status_code == 401
