"""Autenticación: registro, login, refresh, logout y formato de errores."""

from app.security import hash_refresh_token


def test_flujo_completo_de_auth(client):
    email = "auth-full@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secreto123", "display_name": "Ana"},
    )
    assert response.status_code == 201, response.text
    tokens = response.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    me = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["role"] == "student"

    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secreto123"}
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login.json()["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != login.json()["refresh_token"]

    # El refresh anterior quedó revocado.
    reused = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login.json()["refresh_token"]}
    )
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "invalid_refresh"


def test_correo_duplicado_y_credenciales_invalidas(client):
    email = "duplicado@example.com"
    payload = {"email": email, "password": "secreto123", "display_name": "Luis"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_taken"

    bad = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "incorrecta"}
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "invalid_credentials"


def test_logout_revoca_refresh(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "secreto123",
            "display_name": "Eva",
        },
    )
    tokens = response.json()
    out = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 204

    again = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert again.status_code == 401


def test_errores_incluyen_request_id(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "corto@example.com", "password": "123", "display_name": "X"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["request_id"]
    assert response.headers["X-Request-ID"] == body["error"]["request_id"]


def test_token_invalido_no_autoriza(client):
    response = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer no-es-un-jwt"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_refresh_hash_es_sha256():
    assert len(hash_refresh_token("abc")) == 64


def test_login_se_bloquea_tras_cinco_intentos(client):
    email = "limite@example.com"
    payload = {"email": email, "password": "secreto123", "display_name": "Límite"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "incorrecta"}
        )
        assert response.status_code == 401

    blocked = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "incorrecta"}
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
