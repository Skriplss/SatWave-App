"""Доменные исключения."""


class SatWaveError(Exception):
    """Базовое исключение SatWave."""


class InvalidLocationError(SatWaveError):
    """Невалидные координаты."""


class DuplicateLocationError(SatWaveError):
    """Данное местоположение уже было проанализировано."""


class PhotoProcessingError(SatWaveError):
    """Ошибка при обработке фото."""


class MLModelError(SatWaveError):
    """Ошибка ML-модели."""

