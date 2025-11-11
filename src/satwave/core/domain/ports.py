"""Ports (interfaces) for adapters."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from satwave.core.domain.models import Location, PhotoAnalysis, WasteDetection


class IPhotoStorage(ABC):
    """Interface for photo storage."""

    @abstractmethod
    async def save_photo(self, photo_data: bytes, photo_id: UUID) -> str:
        """
        Save photo and return URL.
        
        Args:
            photo_data: Binary photo data
            photo_id: Photo ID
            
        Returns:
            URL of saved photo
        """
        pass

    @abstractmethod
    async def get_photo(self, photo_url: str) -> bytes:
        """Get photo by URL."""
        pass


class IAnalysisRepository(ABC):
    """Interface for working with analyses in database."""

    @abstractmethod
    async def save(self, analysis: PhotoAnalysis) -> None:
        """Save analysis to database."""
        pass

    @abstractmethod
    async def get_by_id(self, analysis_id: UUID) -> Optional[PhotoAnalysis]:
        """Get analysis by ID."""
        pass

    @abstractmethod
    async def find_by_location(
        self, location: Location, radius_meters: float = 50.0
    ) -> list[PhotoAnalysis]:
        """
        Find analyses within radius from given point.
        
        Args:
            location: Center point for search
            radius_meters: Search radius in meters
            
        Returns:
            List of analyses within radius
        """
        pass

    @abstractmethod
    async def location_already_analyzed(
        self, location: Location, threshold_meters: float = 50.0
    ) -> bool:
        """
        Check if this location has already been analyzed.
        
        Args:
            location: Coordinates to check
            threshold_meters: Distance threshold in meters
            
        Returns:
            True if location was already analyzed
        """
        pass


class IWasteClassifier(ABC):
    """Interface for ML waste classifier."""

    @abstractmethod
    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        """
        Classify waste in photo.
        
        Args:
            photo_data: Binary photo data
            
        Returns:
            List of detections with waste types
        """
        pass

    @abstractmethod
    async def is_ready(self) -> bool:
        """Check if model is ready for work."""
        pass

