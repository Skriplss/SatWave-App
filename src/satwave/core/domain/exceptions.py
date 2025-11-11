"""Domain exceptions."""


class SatWaveError(Exception):
    """Base SatWave exception."""


class InvalidLocationError(SatWaveError):
    """Invalid coordinates."""


class DuplicateLocationError(SatWaveError):
    """This location has already been analyzed."""


class PhotoProcessingError(SatWaveError):
    """Photo processing error."""


class MLModelError(SatWaveError):
    """ML model error."""

