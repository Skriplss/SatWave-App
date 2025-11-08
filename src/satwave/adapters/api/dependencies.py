"""Dependency injection для FastAPI."""

from satwave.adapters.ml.roboflow_inference_classifier import RoboflowInferenceClassifier
from satwave.adapters.ml.stub_classifier import StubWasteClassifier
from satwave.adapters.ml.yolo_classifier import YOLOv8Classifier
from satwave.adapters.storage.stub_photo_storage import StubPhotoStorage
from satwave.adapters.storage.stub_repository import StubAnalysisRepository
from satwave.config.settings import Settings, get_settings
from satwave.core.domain.ports import (
    IAnalysisRepository,
    IPhotoStorage,
    IWasteClassifier,
)
from satwave.core.services.photo_analysis_service import PhotoAnalysisService

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
    Получить ML-классификатор.
    
    TODO: Добавить реализации с YOLOv8/Detectron2.
    """
    global _waste_classifier_cache
    
    if _waste_classifier_cache is not None:
        return _waste_classifier_cache
    
    if settings is None:
        settings = get_settings()
    
    if settings.ml_model_type == "stub":
        _waste_classifier_cache = StubWasteClassifier()
    elif settings.ml_model_type == "yolo":
        _waste_classifier_cache = YOLOv8Classifier(
            model_path=settings.ml_model_path,
            confidence_threshold=settings.ml_model_confidence_threshold,
            imgsz=1280,  # Большое разрешение для лучшей точности
            roboflow_api_key=settings.roboflow_api_key if settings.roboflow_api_key else None,
            roboflow_workspace=settings.roboflow_workspace,
            roboflow_project=settings.roboflow_project,
            roboflow_version=settings.roboflow_version,
        )
    elif settings.ml_model_type == "roboflow_inference":
        if not settings.roboflow_api_key:
            raise ValueError("Roboflow API key is required for roboflow_inference model type")
        _waste_classifier_cache = RoboflowInferenceClassifier(
            api_key=settings.roboflow_api_key,
            model_id=settings.roboflow_inference_model_id,
            api_url=settings.roboflow_inference_api_url,
            confidence_threshold=settings.ml_model_confidence_threshold,
        )
    # elif settings.ml_model_type == "detectron2":
    #     _waste_classifier_cache = Detectron2Classifier(...)
    else:
        raise ValueError(f"Unknown ML model type: {settings.ml_model_type}")
    
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

