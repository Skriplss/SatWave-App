"""Dependency injection для FastAPI."""

import logging

from satwave.adapters.ml.stub_classifier import StubWasteClassifier
from satwave.adapters.ml.yolo_classifier import YOLOv8WasteClassifier
from satwave.adapters.storage.stub_photo_storage import StubPhotoStorage
from satwave.adapters.storage.stub_repository import StubAnalysisRepository
from satwave.config.settings import Settings, get_settings
from satwave.core.domain.ports import (
    IAnalysisRepository,
    IPhotoStorage,
    IWasteClassifier,
)
from satwave.core.services.photo_analysis_service import PhotoAnalysisService

logger = logging.getLogger(__name__)

# Кэш для компонентов (без Settings в аргументах)
_photo_storage_cache: IPhotoStorage | None = None
_analysis_repo_cache: IAnalysisRepository | None = None
_waste_classifier_cache: IWasteClassifier | None = None


def get_photo_storage(settings: Settings | None = None) -> IPhotoStorage:
    """
    Получить хранилище фото.
    
    TODO: Добавить реализации для local FS и S3.
    """
    global _photo_storage_cache
    
    if _photo_storage_cache is not None:
        return _photo_storage_cache
    
    if settings is None:
        settings = get_settings()
    
    if settings.photo_storage_type == "stub":
        _photo_storage_cache = StubPhotoStorage(base_url=settings.photo_storage_base_url)
    # elif settings.photo_storage_type == "local":
    #     _photo_storage_cache = LocalPhotoStorage(...)
    # elif settings.photo_storage_type == "s3":
    #     _photo_storage_cache = S3PhotoStorage(...)
    else:
        raise ValueError(f"Unknown photo storage type: {settings.photo_storage_type}")
    
    return _photo_storage_cache


def get_analysis_repository(settings: Settings | None = None) -> IAnalysisRepository:
    """
    Получить репозиторий анализов.
    
    TODO: Добавить реализацию с PostgreSQL/PostGIS.
    """
    global _analysis_repo_cache
    
    if _analysis_repo_cache is not None:
        return _analysis_repo_cache
    
    if settings is None:
        settings = get_settings()
    
    # Пока используем stub
    _analysis_repo_cache = StubAnalysisRepository()
    return _analysis_repo_cache


def get_waste_classifier(settings: Settings | None = None) -> IWasteClassifier:
    """
    Получить ML-классификатор мусора.
    
    Поддерживаемые типы:
    - stub: Заглушка для тестов
    - yolo: YOLOv8 классификатор (Waste-Classification-using-YOLOv8)
    """
    global _waste_classifier_cache
    
    if _waste_classifier_cache is not None:
        return _waste_classifier_cache
    
    if settings is None:
        settings = get_settings()
    
    # Выбираем классификатор в зависимости от типа модели
    if settings.ml_model_type == "yolo":
        logger.info(f"Using YOLOv8 classifier with model: {settings.ml_model_path}")
        _waste_classifier_cache = YOLOv8WasteClassifier(
            model_path=settings.ml_model_path,
            confidence_threshold=settings.ml_model_confidence_threshold,
            device=None,  # Auto-detect device
        )
    elif settings.ml_model_type == "stub":
        logger.info("Using stub classifier")
        _waste_classifier_cache = StubWasteClassifier()
    else:
        logger.warning(
            f"Unknown model type: {settings.ml_model_type}, falling back to stub"
        )
        _waste_classifier_cache = StubWasteClassifier()
    
    return _waste_classifier_cache


def get_photo_analysis_service() -> PhotoAnalysisService:
    """Получить сервис анализа фото."""
    settings = get_settings()
    
    photo_storage = get_photo_storage(settings)
    analysis_repo = get_analysis_repository(settings)
    waste_classifier = get_waste_classifier(settings)
    
    return PhotoAnalysisService(
        photo_storage=photo_storage,
        analysis_repo=analysis_repo,
        waste_classifier=waste_classifier,
    )

