"""Заглушка ML-классификатора (пока без реальной модели)."""

import logging
import random

from satwave.core.domain.models import WasteDetection, WasteType
from satwave.core.domain.ports import IWasteClassifier

logger = logging.getLogger(__name__)


class StubWasteClassifier(IWasteClassifier):
    """
    Заглушка классификатора для тестирования архитектуры.
    
    TODO: Заменить на реальную реализацию с YOLOv8/Detectron2.
    """

    def __init__(self) -> None:
        """Инициализация заглушки."""
        self._is_ready = True
        logger.info("StubWasteClassifier initialized")

    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        """
        Заглушка классификации - возвращает случайный тип мусора.
        
        Args:
            photo_data: Бинарные данные фото
            
        Returns:
            Список детекций (пока случайные)
        """
        logger.info(f"Stub classification for photo ({len(photo_data)} bytes)")

        # Генерируем случайные детекции для тестирования
        num_detections = random.randint(1, 3)
        detections = []

        waste_types = [t for t in WasteType if t != WasteType.UNKNOWN]

        for _ in range(num_detections):
            detection = WasteDetection(
                waste_type=random.choice(waste_types),
                confidence=random.uniform(0.6, 0.95),
                bounding_box=(
                    random.uniform(0, 0.5),
                    random.uniform(0, 0.5),
                    random.uniform(0.5, 1.0),
                    random.uniform(0.5, 1.0),
                ),
            )
            detections.append(detection)

        logger.info(f"Generated {len(detections)} stub detections")
        return detections

    async def is_ready(self) -> bool:
        """Заглушка всегда готова."""
        return self._is_ready

