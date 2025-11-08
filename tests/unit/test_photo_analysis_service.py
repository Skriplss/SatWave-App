"""Тесты для PhotoAnalysisService."""

import pytest

from satwave.adapters.ml.stub_classifier import StubWasteClassifier
from satwave.adapters.storage.stub_photo_storage import StubPhotoStorage
from satwave.adapters.storage.stub_repository import StubAnalysisRepository
from satwave.core.domain.exceptions import DuplicateLocationError, InvalidLocationError
from satwave.core.domain.models import AnalysisStatus
from satwave.core.services.photo_analysis_service import PhotoAnalysisService


@pytest.fixture
def service() -> PhotoAnalysisService:
    """Фикстура для сервиса."""
    return PhotoAnalysisService(
        photo_storage=StubPhotoStorage(),
        analysis_repo=StubAnalysisRepository(),
        waste_classifier=StubWasteClassifier(),
    )


@pytest.mark.asyncio
async def test_process_photo_success(service: PhotoAnalysisService) -> None:
    """Тест успешной обработки фото."""
    photo_data = b"fake image data"
    latitude = 55.7558
    longitude = 37.6173

    analysis = await service.process_photo(
        photo_data=photo_data,
        latitude=latitude,
        longitude=longitude,
    )

    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.location.latitude == latitude
    assert analysis.location.longitude == longitude
    assert len(analysis.detections) > 0
    assert analysis.photo_url.startswith("http://")


@pytest.mark.asyncio
async def test_process_photo_invalid_location(service: PhotoAnalysisService) -> None:
    """Тест обработки фото с невалидными координатами."""
    photo_data = b"fake image data"

    with pytest.raises(InvalidLocationError):
        await service.process_photo(
            photo_data=photo_data,
            latitude=100.0,  # Невалидная широта
            longitude=37.6173,
        )


@pytest.mark.asyncio
async def test_process_photo_duplicate_location(service: PhotoAnalysisService) -> None:
    """Тест обработки фото дубликата локации."""
    photo_data = b"fake image data"
    latitude = 55.7558
    longitude = 37.6173

    # Первая обработка
    await service.process_photo(
        photo_data=photo_data,
        latitude=latitude,
        longitude=longitude,
    )

    # Вторая обработка той же локации должна упасть
    with pytest.raises(DuplicateLocationError):
        await service.process_photo(
            photo_data=photo_data,
            latitude=latitude,
            longitude=longitude,
        )


@pytest.mark.asyncio
async def test_process_photo_skip_duplicate_check(service: PhotoAnalysisService) -> None:
    """Тест обработки с пропуском проверки на дубликаты."""
    photo_data = b"fake image data"
    latitude = 55.7558
    longitude = 37.6173

    # Первая обработка
    analysis1 = await service.process_photo(
        photo_data=photo_data,
        latitude=latitude,
        longitude=longitude,
    )

    # Вторая обработка той же локации с пропуском проверки
    analysis2 = await service.process_photo(
        photo_data=photo_data,
        latitude=latitude,
        longitude=longitude,
        skip_duplicate_check=True,
    )

    assert analysis1.id != analysis2.id
    assert analysis2.status == AnalysisStatus.COMPLETED


@pytest.mark.asyncio
async def test_find_nearby_analyses(service: PhotoAnalysisService) -> None:
    """Тест поиска анализов рядом с точкой."""
    photo_data = b"fake image data"

    # Создаем несколько анализов
    await service.process_photo(photo_data, 55.7558, 37.6173)
    await service.process_photo(photo_data, 55.7560, 37.6175, skip_duplicate_check=True)

    # Ищем рядом
    nearby = await service.find_nearby_analyses(55.7559, 37.6174, radius_meters=200.0)

    assert len(nearby) == 2

