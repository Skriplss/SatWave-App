"""Доменные модели SatWave."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class WasteType(str, Enum):
    """Типы мусора."""

    PLASTIC = "plastic"
    METAL = "metal"
    PAPER = "paper"
    GLASS = "glass"
    ORGANIC = "organic"
    TEXTILE = "textile"
    ELECTRONICS = "electronics"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class AnalysisStatus(str, Enum):
    """Статус анализа фото."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Location:
    """Географическое местоположение."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        """Валидация координат."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")

    def to_wkt(self) -> str:
        """Преобразование в WKT формат для PostGIS."""
        return f"POINT({self.longitude} {self.latitude})"


@dataclass
class WasteDetection:
    """Результат детекции мусора на фото."""

    waste_type: WasteType
    confidence: float
    bounding_box: Optional[tuple[float, float, float, float]] = None

    def __post_init__(self) -> None:
        """Валидация confidence."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class PhotoAnalysis:
    """Результат анализа фотографии."""

    id: UUID
    photo_url: str
    location: Location
    detections: list[WasteDetection]
    status: AnalysisStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    @staticmethod
    def create(photo_url: str, location: Location) -> "PhotoAnalysis":
        """Создание нового анализа."""
        return PhotoAnalysis(
            id=uuid4(),
            photo_url=photo_url,
            location=location,
            detections=[],
            status=AnalysisStatus.PENDING,
            created_at=datetime.utcnow(),
        )

    def is_duplicate_location(self, other: "PhotoAnalysis", threshold_meters: float = 50.0) -> bool:
        """
        Проверка, является ли это дубликатом по местоположению.
        
        Args:
            other: Другой анализ для сравнения
            threshold_meters: Порог расстояния в метрах
            
        Returns:
            True если расстояние меньше порога
        """
        # Упрощенная формула Haversine для малых расстояний
        lat_diff = abs(self.location.latitude - other.location.latitude)
        lon_diff = abs(self.location.longitude - other.location.longitude)
        
        # Приблизительное расстояние в метрах (1 градус ≈ 111 км)
        distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111000
        
        return distance < threshold_meters

    def get_dominant_waste_type(self) -> WasteType:
        """Получить преобладающий тип мусора на основе confidence."""
        if not self.detections:
            return WasteType.UNKNOWN
        
        return max(self.detections, key=lambda d: d.confidence).waste_type

