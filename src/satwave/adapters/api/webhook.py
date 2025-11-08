"""Webhook endpoints для приема фото."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from satwave.core.domain.exceptions import (
    DuplicateLocationError,
    InvalidLocationError,
    PhotoProcessingError,
)
from satwave.core.domain.models import AnalysisStatus, WasteType
from satwave.core.services.photo_analysis_service import PhotoAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


class PhotoAnalysisResponse(BaseModel):
    """Ответ на запрос анализа фото."""

    analysis_id: str
    status: AnalysisStatus
    location: dict[str, float]
    dominant_waste_type: WasteType
    detections_count: int
    photo_url: str


class ErrorResponse(BaseModel):
    """Ответ с ошибкой."""

    error: str
    detail: str


from satwave.adapters.api.dependencies import (
    get_photo_analysis_service as get_service,
)

# Используем реальную DI функцию
get_photo_analysis_service = get_service


@router.post(
    "/photo",
    response_model=PhotoAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid location"},
        409: {"model": ErrorResponse, "description": "Duplicate location"},
        500: {"model": ErrorResponse, "description": "Processing error"},
    },
)
async def receive_photo(
    photo: Annotated[UploadFile, File(description="Фото мусора")],
    latitude: Annotated[float, Form(description="Широта", ge=-90, le=90)],
    longitude: Annotated[float, Form(description="Долгота", ge=-180, le=180)],
    skip_duplicate_check: Annotated[bool, Form(description="Пропустить проверку на дубликаты")] = False,
    service: PhotoAnalysisService = Depends(get_photo_analysis_service),
) -> PhotoAnalysisResponse:
    """
    Webhook для получения фото от Максима или из SaaS.
    
    Процесс:
    1. Получить фото и координаты
    2. Проверить валидность местоположения
    3. Проверить, не было ли это место уже проанализировано
    4. Запустить ML-анализ типа мусора
    5. Сохранить результат в БД
    6. Вернуть результат (Максим получит тип мусора + метку для дальнейшей обработки)
    """
    logger.info(f"Received photo webhook: lat={latitude}, lon={longitude}")

    # Читаем данные фото
    try:
        photo_data = await photo.read()
        if not photo_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty photo file",
            )
    except Exception as e:
        logger.error(f"Failed to read photo: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read photo: {e}",
        )

    # Обрабатываем фото
    try:
        analysis = await service.process_photo(
            photo_data=photo_data,
            latitude=latitude,
            longitude=longitude,
            skip_duplicate_check=skip_duplicate_check,
        )

        return PhotoAnalysisResponse(
            analysis_id=str(analysis.id),
            status=analysis.status,
            location={"latitude": analysis.location.latitude, "longitude": analysis.location.longitude},
            dominant_waste_type=analysis.get_dominant_waste_type(),
            detections_count=len(analysis.detections),
            photo_url=analysis.photo_url,
        )

    except InvalidLocationError as e:
        logger.warning(f"Invalid location: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except DuplicateLocationError as e:
        logger.warning(f"Duplicate location: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except PhotoProcessingError as e:
        logger.error(f"Photo processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/analysis/{analysis_id}",
    response_model=PhotoAnalysisResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
    },
)
async def get_analysis(
    analysis_id: str,
    service: PhotoAnalysisService = Depends(get_photo_analysis_service),
) -> PhotoAnalysisResponse:
    """
    Получить результат анализа по ID.
    
    Максим может использовать это для получения статуса обработки.
    """
    from uuid import UUID

    try:
        analysis_uuid = UUID(analysis_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID format",
        )

    analysis = await service.get_analysis(analysis_uuid)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    return PhotoAnalysisResponse(
        analysis_id=str(analysis.id),
        status=analysis.status,
        location={"latitude": analysis.location.latitude, "longitude": analysis.location.longitude},
        dominant_waste_type=analysis.get_dominant_waste_type(),
        detections_count=len(analysis.detections),
        photo_url=analysis.photo_url,
    )

