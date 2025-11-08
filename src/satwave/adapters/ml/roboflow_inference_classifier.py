"""Roboflow Inference API классификатор мусора."""

import logging
from io import BytesIO
from typing import Optional

from PIL import Image

from satwave.core.domain.models import WasteDetection, WasteType
from satwave.core.domain.ports import IWasteClassifier

logger = logging.getLogger(__name__)

try:
    from inference_sdk import InferenceHTTPClient
except ImportError:
    InferenceHTTPClient = None
    logger.warning("inference-sdk not installed, RoboflowInferenceClassifier will not work")


class RoboflowInferenceClassifier(IWasteClassifier):
    """
    Классификатор мусора через Roboflow Inference API.
    
    Использует hosted API - не требует скачивания модели локально.
    """

    def __init__(
        self,
        api_key: str,
        model_id: str = "trash-sorter-all-classes/4",
        api_url: str = "https://serverless.roboflow.com",
        confidence_threshold: float = 0.25,
    ) -> None:
        """
        Инициализация Roboflow Inference API классификатора.
        
        Args:
            api_key: Roboflow API ключ
            model_id: ID модели (формат: "project/version")
            api_url: URL API (по умолчанию serverless.roboflow.com)
            confidence_threshold: Порог confidence для детекций (0.0-1.0)
        """
        if InferenceHTTPClient is None:
            raise ImportError(
                "inference-sdk not installed. Install with: pip install inference-sdk"
            )

        self.api_key = api_key
        self.model_id = model_id
        self.api_url = api_url
        self.confidence_threshold = confidence_threshold
        self._client: Optional[InferenceHTTPClient] = None
        self._is_ready = False

        logger.info(
            f"RoboflowInferenceClassifier initializing: "
            f"model_id={model_id}, api_url={api_url}, conf={confidence_threshold}"
        )

    def _init_client(self) -> None:
        """Инициализировать клиент Inference API."""
        if self._client is not None:
            return

        logger.info("Initializing Roboflow Inference API client...")
        self._client = InferenceHTTPClient(
            api_url=self.api_url,
            api_key=self.api_key,
        )
        self._is_ready = True
        logger.info("Roboflow Inference API client initialized")

    def _map_class_to_waste_type(self, class_name: str) -> WasteType:
        """
        Маппинг классов модели Trash Sorter в типы мусора.
        
        Модель уже обучена на мусоре, классы правильные.
        """
        class_name_lower = class_name.lower()
        
        # Маппинг классов из Trash Sorter модели
        waste_mapping = {
            "plastic": WasteType.PLASTIC,
            "paper": WasteType.PAPER,
            "cardboard": WasteType.PAPER,
            "metal": WasteType.METAL,
            "glass": WasteType.GLASS,
            "organic": WasteType.ORGANIC,
            "food": WasteType.ORGANIC,
            "textile": WasteType.TEXTILE,
            "clothes": WasteType.TEXTILE,
            "electronics": WasteType.ELECTRONICS,
            "electronic": WasteType.ELECTRONICS,
            "battery": WasteType.ELECTRONICS,
            "mixed": WasteType.MIXED,
            "trash": WasteType.MIXED,
            "waste": WasteType.MIXED,
            "garbage": WasteType.MIXED,
        }
        
        # Пробуем найти точное совпадение
        for key, waste_type in waste_mapping.items():
            if key == class_name_lower or key in class_name_lower:
                logger.debug(f"Mapped class '{class_name}' -> {waste_type.value}")
                return waste_type
        
        # Если не нашли - возвращаем MIXED
        logger.warning(f"Unknown class: '{class_name}', mapping to MIXED")
        return WasteType.MIXED

    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        """
        Классифицировать мусор на фото через Roboflow Inference API.
        
        Args:
            photo_data: Бинарные данные фото
            
        Returns:
            Список детекций с типами мусора
        """
        if not self._is_ready:
            self._init_client()

        logger.info(f"Classifying photo via Roboflow Inference API ({len(photo_data)} bytes)")

        try:
            # Сохраняем изображение во временный файл или используем BytesIO
            # Inference SDK может принимать файл или bytes
            image = Image.open(BytesIO(photo_data))
            
            # Конвертируем в RGB если нужно
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Сохраняем во временный файл для API
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                image.save(tmp_file.name, "JPEG")
                tmp_path = tmp_file.name
            
            try:
                # Вызываем Inference API
                logger.debug(f"Calling Roboflow Inference API for model: {self.model_id}")
                result = self._client.infer(tmp_path, model_id=self.model_id)
                
                logger.debug(f"API response: {result}")
                
                # Обрабатываем результаты
                detections = []
                
                # Структура ответа от Roboflow Inference API
                if "predictions" in result:
                    predictions = result["predictions"]
                    logger.info(f"API returned {len(predictions)} predictions")
                    
                    for pred in predictions:
                        # Извлекаем данные детекции
                        class_name = pred.get("class", "unknown")
                        confidence = float(pred.get("confidence", 0.0))
                        
                        # Фильтруем по confidence threshold
                        if confidence < self.confidence_threshold:
                            logger.debug(
                                f"Skipping detection '{class_name}' "
                                f"(confidence {confidence:.3f} < {self.confidence_threshold})"
                            )
                            continue
                        
                        # Получаем bounding box (если есть)
                        bbox = None
                        if "x" in pred and "y" in pred and "width" in pred and "height" in pred:
                            # Конвертируем из формата Roboflow (центр + размер) в формат (x1, y1, x2, y2)
                            x_center = pred["x"]
                            y_center = pred["y"]
                            width = pred["width"]
                            height = pred["height"]
                            
                            # Нормализуем координаты (предполагаем, что они в пикселях)
                            # Нужно знать размер изображения для нормализации
                            img_width = image.width
                            img_height = image.height
                            
                            x1 = (x_center - width / 2) / img_width
                            y1 = (y_center - height / 2) / img_height
                            x2 = (x_center + width / 2) / img_width
                            y2 = (y_center + height / 2) / img_height
                            
                            bbox = (x1, y1, x2, y2)
                        
                        # Маппим класс в тип мусора
                        waste_type = self._map_class_to_waste_type(class_name)
                        
                        detection = WasteDetection(
                            waste_type=waste_type,
                            confidence=confidence,
                            bounding_box=bbox,
                        )
                        detections.append(detection)
                        
                        logger.info(
                            f"Detection: {waste_type.value} "
                            f"(class={class_name}, conf={confidence:.3f})"
                        )
                
                logger.info(f"Total detections after filtering: {len(detections)}")
                
                # Если ничего не нашли
                if not detections:
                    logger.warning("No detections found via Inference API")
                    detections.append(
                        WasteDetection(
                            waste_type=WasteType.UNKNOWN,
                            confidence=0.0,
                            bounding_box=None,
                        )
                    )
                
                return detections
                
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")

        except Exception as e:
            logger.error(f"Error during Inference API classification: {e}", exc_info=True)
            # Возвращаем UNKNOWN при ошибке
            return [
                WasteDetection(
                    waste_type=WasteType.UNKNOWN,
                    confidence=0.0,
                    bounding_box=None,
                )
            ]

    async def is_ready(self) -> bool:
        """Проверить, готова ли модель к работе."""
        if not self._is_ready:
            try:
                self._init_client()
            except Exception as e:
                logger.error(f"Failed to initialize Inference API client: {e}")
                return False
        
        return self._is_ready

