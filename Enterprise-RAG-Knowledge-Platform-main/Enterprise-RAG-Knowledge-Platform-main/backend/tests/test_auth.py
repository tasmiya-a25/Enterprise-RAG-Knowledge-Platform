def test_register_creates_user(client):
    r = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "supersecret123"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@b.com"
    assert body["role"] == "user"
    assert body["is_verified"] is False


def test_register_duplicate_email_rejected(client):
    client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "supersecret123"})
    r = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "anotherpass123"})
    assert r.status_code == 409


def test_login_success_returns_tokens(client):
    client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "supersecret123"})
    r = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "supersecret123"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body and "refresh_token" in body


def test_login_wrong_password_rejected(client):
    client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "supersecret123"})
    r = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "wrongpassword"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/api/v1/me")
    assert r.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    r = client.get("/api/v1/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


def test_refresh_token_issues_new_access_token(client):
    client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "supersecret123"})
    login = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "supersecret123"})
    refresh_token = login.json()["refresh_token"]
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_refresh_rejects_access_token(client):
    client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "supersecret123"})
    login = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "supersecret123"})
    access_token = login.json()["access_token"]
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert r.status_code == 401
