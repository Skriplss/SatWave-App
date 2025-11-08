"""Заглушка хранилища фото (пока без реального S3/файловой системы)."""

import logging
from pathlib import Path
from uuid import UUID

from satwave.core.domain.ports import IPhotoStorage

logger = logging.getLogger(__name__)


class StubPhotoStorage(IPhotoStorage):
    """
    In-memory хранилище фото для тестирования.
    
    TODO: Заменить на реальную реализацию с S3/MinIO или локальной ФС.
    """

    def __init__(self, base_url: str = "http://localhost:8000/photos") -> None:
        """
        Инициализация заглушки.
        
        Args:
            base_url: Базовый URL для генерации ссылок на фото
        """
        self.base_url = base_url
        self._storage: dict[str, bytes] = {}
        logger.info("StubPhotoStorage initialized")

    async def save_photo(self, photo_data: bytes, photo_id: UUID) -> str:
        """
        Сохранить фото в память и вернуть URL.
        
        Args:
            photo_data: Бинарные данные фото
            photo_id: ID фото
            
        Returns:
            URL фото
        """
        photo_url = f"{self.base_url}/{photo_id}.jpg"
        self._storage[photo_url] = photo_data
        logger.info(f"Photo saved: {photo_url} ({len(photo_data)} bytes)")
        return photo_url

    async def get_photo(self, photo_url: str) -> bytes:
        """Получить фото по URL."""
        if photo_url not in self._storage:
            raise FileNotFoundError(f"Photo not found: {photo_url}")
        return self._storage[photo_url]

