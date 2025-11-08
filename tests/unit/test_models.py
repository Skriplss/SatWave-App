"""Тесты доменных моделей."""

import pytest

from satwave.core.domain.models import Location, WasteDetection, WasteType


class TestLocation:
    """Тесты для Location."""

    def test_valid_location(self) -> None:
        """Тест создания валидной локации."""
        location = Location(latitude=55.7558, longitude=37.6173)  # Москва
        assert location.latitude == 55.7558
        assert location.longitude == 37.6173

    def test_invalid_latitude(self) -> None:
        """Тест невалидной широты."""
        with pytest.raises(ValueError, match="Invalid latitude"):
            Location(latitude=100.0, longitude=37.6173)

    def test_invalid_longitude(self) -> None:
        """Тест невалидной долготы."""
        with pytest.raises(ValueError, match="Invalid longitude"):
            Location(latitude=55.7558, longitude=200.0)

    def test_to_wkt(self) -> None:
        """Тест преобразования в WKT."""
        location = Location(latitude=55.7558, longitude=37.6173)
        wkt = location.to_wkt()
        assert wkt == "POINT(37.6173 55.7558)"


class TestWasteDetection:
    """Тесты для WasteDetection."""

    def test_valid_detection(self) -> None:
        """Тест создания валидной детекции."""
        detection = WasteDetection(
            waste_type=WasteType.PLASTIC,
            confidence=0.85,
            bounding_box=(0.1, 0.2, 0.5, 0.6),
        )
        assert detection.waste_type == WasteType.PLASTIC
        assert detection.confidence == 0.85

    def test_invalid_confidence(self) -> None:
        """Тест невалидного confidence."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            WasteDetection(
                waste_type=WasteType.PLASTIC,
                confidence=1.5,
            )

