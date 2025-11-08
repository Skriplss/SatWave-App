"""Заглушка репозитория (пока без реальной БД)."""

import logging
from typing import Optional
from uuid import UUID

from satwave.core.domain.models import Location, PhotoAnalysis
from satwave.core.domain.ports import IAnalysisRepository

logger = logging.getLogger(__name__)


class StubAnalysisRepository(IAnalysisRepository):
    """
    In-memory репозиторий для тестирования.
    
    TODO: Заменить на реальную реализацию с PostgreSQL/PostGIS.
    """

    def __init__(self) -> None:
        """Инициализация in-memory хранилища."""
        self._storage: dict[UUID, PhotoAnalysis] = {}
        logger.info("StubAnalysisRepository initialized")

    async def save(self, analysis: PhotoAnalysis) -> None:
        """Сохранить анализ в память."""
        self._storage[analysis.id] = analysis
        logger.info(f"Analysis saved: {analysis.id}")

    async def get_by_id(self, analysis_id: UUID) -> Optional[PhotoAnalysis]:
        """Получить анализ по ID."""
        return self._storage.get(analysis_id)

    async def find_by_location(
        self, location: Location, radius_meters: float = 50.0
    ) -> list[PhotoAnalysis]:
        """
        Найти анализы в радиусе (упрощенная реализация).
        
        TODO: В реальной БД использовать ST_DWithin из PostGIS.
        """
        results = []
        for analysis in self._storage.values():
            # Упрощенная проверка расстояния
            lat_diff = abs(analysis.location.latitude - location.latitude)
            lon_diff = abs(analysis.location.longitude - location.longitude)
            distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111000  # ≈ метры

            if distance <= radius_meters:
                results.append(analysis)

        logger.info(f"Found {len(results)} analyses near {location.to_wkt()}")
        return results

    async def location_already_analyzed(
        self, location: Location, threshold_meters: float = 50.0
    ) -> bool:
        """Проверить, было ли место уже проанализировано."""
        nearby = await self.find_by_location(location, threshold_meters)
        return len(nearby) > 0

