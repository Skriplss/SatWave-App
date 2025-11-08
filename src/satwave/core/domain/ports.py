"""Порты (интерфейсы) для адаптеров."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from satwave.core.domain.models import Location, PhotoAnalysis, WasteDetection


class IPhotoStorage(ABC):
    """Интерфейс для хранения фотографий."""

    @abstractmethod
    async def save_photo(self, photo_data: bytes, photo_id: UUID) -> str:
        """
        Сохранить фото и вернуть URL.
        
        Args:
            photo_data: Бинарные данные фото
            photo_id: ID фото
            
        Returns:
            URL сохраненного фото
        """
        pass

    @abstractmethod
    async def get_photo(self, photo_url: str) -> bytes:
        """Получить фото по URL."""
        pass


class IAnalysisRepository(ABC):
    """Интерфейс для работы с анализами в БД."""

    @abstractmethod
    async def save(self, analysis: PhotoAnalysis) -> None:
        """Сохранить анализ в БД."""
        pass

    @abstractmethod
    async def get_by_id(self, analysis_id: UUID) -> Optional[PhotoAnalysis]:
        """Получить анализ по ID."""
        pass

    @abstractmethod
    async def find_by_location(
        self, location: Location, radius_meters: float = 50.0
    ) -> list[PhotoAnalysis]:
        """
        Найти анализы в радиусе от заданной точки.
        
        Args:
            location: Центральная точка поиска
            radius_meters: Радиус поиска в метрах
            
        Returns:
            Список анализов в радиусе
        """
        pass

    @abstractmethod
    async def location_already_analyzed(
        self, location: Location, threshold_meters: float = 50.0
    ) -> bool:
        """
        Проверить, было ли данное местоположение уже проанализировано.
        
        Args:
            location: Координаты для проверки
            threshold_meters: Порог расстояния в метрах
            
        Returns:
            True если местоположение уже анализировалось
        """
        pass


class IWasteClassifier(ABC):
    """Интерфейс для ML-классификатора мусора."""

    @abstractmethod
    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        """
        Классифицировать мусор на фото.
        
        Args:
            photo_data: Бинарные данные фото
            
        Returns:
            Список детекций с типами мусора
        """
        pass

    @abstractmethod
    async def is_ready(self) -> bool:
        """Проверить, готова ли модель к работе."""
        pass

