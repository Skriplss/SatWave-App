"""SatWave domain models."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class WasteType(str, Enum):
    """Waste types."""

    # Old types (for backward compatibility)
    PLASTIC = "plastic"
    METAL = "metal"
    PAPER = "paper"
    GLASS = "glass"
    ORGANIC = "organic"
    TEXTILE = "textile"
    ELECTRONICS = "electronics"
    MIXED = "mixed"
    UNKNOWN = "unknown"
    
    # New waste categories
    CONSTRUCTION_WASTE = "construction_waste"
    HAZARDOUS_WASTE = "hazardous_waste"
    HOUSEHOLD_WASTE = "household_waste"
    MIXED_WASTE = "mixed_waste"
    WASTE_SEPARATION_FACILITIES = "waste_separation_facilities"


class AnalysisStatus(str, Enum):
    """Photo analysis status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Location:
    """Geographic location."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        """Validate coordinates."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")

    def to_wkt(self) -> str:
        """Convert to WKT format for PostGIS."""
        return f"POINT({self.longitude} {self.latitude})"


@dataclass
class WasteDetection:
    """Waste detection result on photo."""

    waste_type: WasteType
    confidence: float
    bounding_box: Optional[tuple[float, float, float, float]] = None

    def __post_init__(self) -> None:
        """Validate confidence."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class PhotoAnalysis:
    """Photo analysis result."""

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
        """Create new analysis."""
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
        Check if this is a duplicate by location.
        
        Args:
            other: Other analysis for comparison
            threshold_meters: Distance threshold in meters
            
        Returns:
            True if distance is less than threshold
        """
        # Simplified Haversine formula for small distances
        lat_diff = abs(self.location.latitude - other.location.latitude)
        lon_diff = abs(self.location.longitude - other.location.longitude)
        
        # Approximate distance in meters (1 degree ≈ 111 km)
        distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111000
        
        return distance < threshold_meters

    def get_dominant_waste_type(self) -> WasteType:
        """Get dominant waste type based on confidence."""
        if not self.detections:
            return WasteType.UNKNOWN
        
        return max(self.detections, key=lambda d: d.confidence).waste_type

