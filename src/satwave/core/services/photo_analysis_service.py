"""Сервис для анализа фотографий мусора."""

import logging
from uuid import UUID

from satwave.core.domain.exceptions import (
    DuplicateLocationError,
    InvalidLocationError,
    MLModelError,
    PhotoProcessingError,
)
from satwave.core.domain.models import AnalysisStatus, Location, PhotoAnalysis
from satwave.core.domain.ports import (
    IAnalysisRepository,
    IPhotoStorage,
    IWasteClassifier,
)

logger = logging.getLogger(__name__)


class PhotoAnalysisService:
    """
    Сервис для обработки фото через webhook.
    
    Основные функции:
    1. Получение фото
    2. Проверка геолокации
    3. Проверка на дубликаты по местоположению
    4. ML-анализ типа мусора
    5. Сохранение результата в БД
    """

    def __init__(
        self,
        photo_storage: IPhotoStorage,
        analysis_repo: IAnalysisRepository,
        waste_classifier: IWasteClassifier,
    ) -> None:
        """
        Инициализация сервиса.
        
        Args:
            photo_storage: Хранилище фотографий
            analysis_repo: Репозиторий анализов
            waste_classifier: ML-классификатор мусора
        """
        self.photo_storage = photo_storage
        self.analysis_repo = analysis_repo
        self.waste_classifier = waste_classifier

    async def process_photo(
        self,
        photo_data: bytes,
        latitude: float,
        longitude: float,
        skip_duplicate_check: bool = False,
    ) -> PhotoAnalysis:
        """
        Обработать фото из webhook.
        
        Args:
            photo_data: Бинарные данные фото
            latitude: Широта
            longitude: Долгота
            skip_duplicate_check: Пропустить проверку на дубликаты
            
        Returns:
            Результат анализа
            
        Raises:
            InvalidLocationError: Невалидные координаты
            DuplicateLocationError: Местоположение уже анализировалось
            PhotoProcessingError: Ошибка обработки фото
        """
        # 1. Валидация и создание локации
        try:
            location = Location(latitude=latitude, longitude=longitude)
        except ValueError as e:
            logger.error(f"Invalid location: {e}")
            raise InvalidLocationError(str(e)) from e

        logger.info(f"Processing photo at location: {location.latitude}, {location.longitude}")

        # 2. Проверка на дубликаты по местоположению
        if not skip_duplicate_check:
            is_duplicate = await self.analysis_repo.location_already_analyzed(location)
            if is_duplicate:
                logger.warning(f"Location already analyzed: {location.to_wkt()}")
                raise DuplicateLocationError(
                    f"Location ({location.latitude}, {location.longitude}) was already analyzed"
                )

        # 3. Создание записи анализа
        analysis = PhotoAnalysis.create(photo_url="", location=location)
        analysis.status = AnalysisStatus.PROCESSING

        try:
            # 4. Сохранение фото
            photo_url = await self.photo_storage.save_photo(photo_data, analysis.id)
            analysis.photo_url = photo_url
            logger.info(f"Photo saved: {photo_url}")

            # 5. ML-анализ мусора
            if not await self.waste_classifier.is_ready():
                raise MLModelError("ML model is not ready")

            detections = await self.waste_classifier.classify(photo_data)
            analysis.detections = detections
            analysis.status = AnalysisStatus.COMPLETED

            logger.info(
                f"Analysis completed: {len(detections)} detections, "
                f"dominant type: {analysis.get_dominant_waste_type()}"
            )

        except MLModelError as e:
            logger.error(f"ML model error: {e}")
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(e)
            raise

        except Exception as e:
            logger.exception(f"Photo processing error: {e}")
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(e)
            raise PhotoProcessingError(f"Failed to process photo: {e}") from e

        finally:
            # 6. Сохранение результата в БД
            await self.analysis_repo.save(analysis)

        return analysis

    async def get_analysis(self, analysis_id: UUID) -> PhotoAnalysis | None:
        """
        Получить результат анализа по ID.
        
        Args:
            analysis_id: ID анализа
            
        Returns:
            Анализ или None
        """
        return await self.analysis_repo.get_by_id(analysis_id)

    async def find_nearby_analyses(
        self, latitude: float, longitude: float, radius_meters: float = 100.0
    ) -> list[PhotoAnalysis]:
        """
        Найти анализы рядом с заданной точкой.
        
        Args:
            latitude: Широта
            longitude: Долгота
            radius_meters: Радиус поиска в метрах
            
        Returns:
            Список анализов в радиусе
        """
        location = Location(latitude=latitude, longitude=longitude)
        return await self.analysis_repo.find_by_location(location, radius_meters)

