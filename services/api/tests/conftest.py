"""Fixtures de prueba: Postgres de test + almacenamiento S3 de desarrollo."""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://issitek:issitek@localhost:5433/issitek_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-no-usar-en-produccion")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9100")
os.environ.setdefault("MINIO_PUBLIC_ENDPOINT", "")
os.environ.setdefault("MINIO_ACCESS_KEY", "issitek")
os.environ.setdefault("MINIO_SECRET_KEY", "issitek-secret")
os.environ.setdefault("TTS_PROVIDER", "fake")
os.environ.setdefault("PRONUNCIATION_EVAL_ENABLED", "false")

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.seed import seed_content
from app.storage import get_storage


@pytest.fixture(scope="session", autouse=True)
def prepared_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_content()
    # El TestClient sin context manager no ejecuta el lifespan; crear los
    # buckets explícitamente para que las pruebas no dependan de un arranque previo.
    get_storage().ensure_buckets()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client():
    # Sin context manager: no se ejecuta el lifespan (no espera al S3).
    return TestClient(app)


@pytest.fixture()
def auth(client):
    email = f"alumno-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secreto123", "display_name": "Alumno Prueba"},
    )
    assert response.status_code == 201, response.text
    tokens = response.json()
    return {
        "email": email,
        "password": "secreto123",
        "access": tokens["access_token"],
        "refresh": tokens["refresh_token"],
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
    }


@pytest.fixture()
def first_lesson(client, auth):
    courses = client.get("/api/v1/courses", headers=auth["headers"])
    assert courses.status_code == 200, courses.text
    lesson_id = courses.json()[0]["lessons"][0]["id"]
    lesson = client.get(f"/api/v1/lessons/{lesson_id}", headers=auth["headers"])
    assert lesson.status_code == 200, lesson.text
    return lesson.json()
