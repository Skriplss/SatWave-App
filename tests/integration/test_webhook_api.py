"""Integration тесты для webhook API."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from satwave.adapters.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Фикстура для тестового клиента."""
    app = create_app()
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Тест health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client: TestClient) -> None:
    """Тест корневого endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "SatWave"
    assert data["status"] == "ok"


def test_receive_photo_success(client: TestClient) -> None:
    """Тест успешной отправки фото через webhook."""
    # Создаем фейковое фото
    fake_photo = BytesIO(b"fake image data")
    fake_photo.name = "test.jpg"

    response = client.post(
        "/webhook/photo",
        files={"photo": ("test.jpg", fake_photo, "image/jpeg")},
        data={
            "latitude": 55.7558,
            "longitude": 37.6173,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "analysis_id" in data
    assert data["status"] == "completed"
    assert data["location"]["latitude"] == 55.7558
    assert data["location"]["longitude"] == 37.6173
    assert data["detections_count"] > 0


def test_receive_photo_invalid_coordinates(client: TestClient) -> None:
    """Тест отправки фото с невалидными координатами."""
    fake_photo = BytesIO(b"fake image data")
    fake_photo.name = "test.jpg"

    response = client.post(
        "/webhook/photo",
        files={"photo": ("test.jpg", fake_photo, "image/jpeg")},
        data={
            "latitude": 100.0,  # Невалидная широта
            "longitude": 37.6173,
        },
    )

    assert response.status_code == 422  # Validation error от FastAPI


def test_receive_photo_duplicate_location(client: TestClient) -> None:
    """Тест отправки фото дубликата локации."""
    fake_photo1 = BytesIO(b"fake image data 1")
    fake_photo1.name = "test1.jpg"

    # Первая отправка
    response1 = client.post(
        "/webhook/photo",
        files={"photo": ("test1.jpg", fake_photo1, "image/jpeg")},
        data={
            "latitude": 55.7558,
            "longitude": 37.6173,
        },
    )
    assert response1.status_code == 201

    # Вторая отправка той же локации
    fake_photo2 = BytesIO(b"fake image data 2")
    fake_photo2.name = "test2.jpg"

    response2 = client.post(
        "/webhook/photo",
        files={"photo": ("test2.jpg", fake_photo2, "image/jpeg")},
        data={
            "latitude": 55.7558,
            "longitude": 37.6173,
        },
    )
    assert response2.status_code == 409  # Conflict


def test_get_analysis(client: TestClient) -> None:
    """Тест получения анализа по ID."""
    # Сначала создаем анализ
    fake_photo = BytesIO(b"fake image data")
    fake_photo.name = "test.jpg"

    create_response = client.post(
        "/webhook/photo",
        files={"photo": ("test.jpg", fake_photo, "image/jpeg")},
        data={
            "latitude": 55.7558,
            "longitude": 37.6173,
        },
    )
    analysis_id = create_response.json()["analysis_id"]

    # Получаем анализ
    get_response = client.get(f"/webhook/analysis/{analysis_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["analysis_id"] == analysis_id


def test_get_analysis_not_found(client: TestClient) -> None:
    """Тест получения несуществующего анализа."""
    from uuid import uuid4

    fake_id = str(uuid4())
    response = client.get(f"/webhook/analysis/{fake_id}")
    assert response.status_code == 404

