"""YOLOv8/YOLOv12 классификатор мусора."""

import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image

from satwave.core.domain.models import WasteDetection, WasteType
from satwave.core.domain.ports import IWasteClassifier

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    logger.warning("ultralytics not installed, YOLOv8Classifier will not work")

try:
    from roboflow import Roboflow
except ImportError:
    Roboflow = None
    logger.warning("roboflow not installed, cannot download models from Roboflow")


class YOLOv8Classifier(IWasteClassifier):
    """
    YOLOv8/YOLOv12 классификатор для детекции мусора на фото.
    
    Поддерживает:
    - YOLOv8 (базовая COCO модель)
    - YOLOv12 (Roboflow Trash Sorter - обучена на мусоре)
    - Скачивание моделей с Roboflow
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.25,
        device: Optional[str] = None,
        imgsz: int = 1280,
        roboflow_api_key: Optional[str] = None,
        roboflow_workspace: Optional[str] = None,
        roboflow_project: Optional[str] = None,
        roboflow_version: int = 1,
    ) -> None:
        """
        Инициализация YOLOv8/YOLOv12 классификатора.
        
        Args:
            model_path: Путь к весам модели (.pt файл) или имя модели для загрузки
            confidence_threshold: Порог confidence для детекций (0.0-1.0)
            device: Устройство для inference ('cpu', 'cuda', 'mps')
            imgsz: Размер изображения для inference (640, 1280, etc.)
            roboflow_api_key: API ключ Roboflow (опционально, для скачивания модели)
            roboflow_workspace: Roboflow workspace
            roboflow_project: Roboflow project name
            roboflow_version: Версия модели на Roboflow
        """
        if YOLO is None:
            raise ImportError(
                "ultralytics not installed. Install with: pip install ultralytics"
            )

        self.model_path = Path(model_path) if model_path else None
        self.model_name = model_path if not model_path or not Path(model_path).exists() else None
        self.confidence_threshold = confidence_threshold
        self.device = device or ("cuda" if self._has_cuda() else "cpu")
        self.imgsz = imgsz
        self._model: Optional[YOLO] = None
        self._is_ready = False
        
        # Roboflow настройки
        self.roboflow_api_key = roboflow_api_key
        self.roboflow_workspace = roboflow_workspace
        self.roboflow_project = roboflow_project
        self.roboflow_version = roboflow_version
        self._is_waste_model = False  # Флаг для определения, обучена ли модель на мусоре

        logger.info(
            f"YOLOv8Classifier initializing: model={model_path}, "
            f"device={self.device}, imgsz={imgsz}, conf={confidence_threshold}"
        )

    def _has_cuda(self) -> bool:
        """Проверить наличие CUDA."""
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            return False

    def _download_from_roboflow(self) -> Path:
        """Скачать модель с Roboflow."""
        if Roboflow is None:
            raise ImportError(
                "roboflow not installed. Install with: pip install roboflow"
            )
        
        if not self.roboflow_api_key:
            raise ValueError("Roboflow API key is required to download model")
        
        logger.info(f"Downloading model from Roboflow: {self.roboflow_workspace}/{self.roboflow_project}")
        
        try:
            rf = Roboflow(api_key=self.roboflow_api_key)
            project = rf.workspace(self.roboflow_workspace).project(self.roboflow_project)
            model = project.version(self.roboflow_version).model
            
            # Скачиваем модель
            models_dir = Path("./models")
            models_dir.mkdir(exist_ok=True)
            
            model_path = models_dir / f"{self.roboflow_project}-v{self.roboflow_version}.pt"
            
            # Если файл уже существует, используем его
            if model_path.exists():
                logger.info(f"Model already exists at {model_path}, skipping download")
                return model_path
            
            # Скачиваем модель
            logger.info("Downloading model weights...")
            # Roboflow может скачать в подпапку, проверяем разные варианты
            try:
                model.download("yolov12", str(models_dir))
            except Exception as e:
                logger.warning(f"Download method failed: {e}, trying alternative...")
                # Альтернативный способ - через export
                project.version(self.roboflow_version).download("yolov12", str(models_dir))
            
            # Ищем скачанный файл (может быть в подпапке)
            downloaded_files = list(models_dir.rglob("*.pt"))
            if downloaded_files:
                model_path = downloaded_files[0]
                # Перемещаем в корень models/ если нужно
                if model_path.parent != models_dir:
                    target_path = models_dir / model_path.name
                    if not target_path.exists():
                        import shutil
                        shutil.move(str(model_path), str(target_path))
                    model_path = target_path
                logger.info(f"Model downloaded to: {model_path}")
                return model_path
            else:
                raise FileNotFoundError("Model file not found after download")
                
        except Exception as e:
            logger.error(f"Failed to download model from Roboflow: {e}")
            raise

    def _load_model(self) -> None:
        """Загрузить модель YOLOv8/YOLOv12."""
        if self._model is not None:
            return

        model_file = None

        # Если указан путь к файлу и он существует
        if self.model_path and self.model_path.exists():
            logger.info(f"Loading model from: {self.model_path}")
            model_file = self.model_path
            self._is_waste_model = True  # Предполагаем, что это модель для мусора
        # Если указан путь, но файла нет, и есть Roboflow настройки - пробуем скачать
        elif self.model_path and not self.model_path.exists() and self.roboflow_api_key:
            logger.info("Model file not found, trying to download from Roboflow...")
            try:
                model_file = self._download_from_roboflow()
                self._is_waste_model = True  # Модель с Roboflow обучена на мусоре
            except Exception as e:
                logger.error(f"Failed to download from Roboflow: {e}")
                logger.warning("Falling back to pre-trained YOLOv12n model")
                # Fallback на базовую модель
                model_name = "yolov12n.pt"
                self._model = YOLO(model_name)
                self._is_ready = True
                return
        # Если нет пути, но есть Roboflow настройки - скачиваем
        elif self.roboflow_api_key:
            logger.info("No model path specified, downloading from Roboflow...")
            try:
                model_file = self._download_from_roboflow()
                self._is_waste_model = True
            except Exception as e:
                logger.error(f"Failed to download from Roboflow: {e}")
                logger.warning("Falling back to pre-trained YOLOv12n model")
                # Fallback на базовую модель
                model_name = "yolov12n.pt"
                self._model = YOLO(model_name)
                self._is_ready = True
                return
        else:
            # Пробуем загрузить по имени или скачать pre-trained
            model_name = self.model_name or "yolov12n.pt"
            logger.info(f"Loading pre-trained model: {model_name}")
            try:
                self._model = YOLO(model_name)  # Скачает автоматически
                logger.info(f"Loaded pre-trained model: {model_name}")
                self._is_ready = True
                return
            except Exception as e:
                raise FileNotFoundError(
                    f"Failed to load model {model_name}: {e}"
                )

        if model_file:
            logger.info(f"Loading model from: {model_file}")
            self._model = YOLO(str(model_file))

        self._is_ready = True
        logger.info("YOLOv8/YOLOv12 model loaded successfully")
        
        # Логируем доступные классы модели
        if hasattr(self._model, "names"):
            classes = list(self._model.names.values())
            logger.info(f"Model classes: {len(classes)} classes")
            logger.info(f"Available classes: {classes}")
            
            # Определяем, обучена ли модель на мусоре (по классам)
            waste_keywords = ["trash", "waste", "garbage", "plastic", "paper", "metal", "glass", "organic"]
            if any(keyword in str(classes).lower() for keyword in waste_keywords):
                self._is_waste_model = True
                logger.info("Detected waste-specific model (based on class names)")

    def _map_yolo_class_to_waste_type(self, class_id: int, class_name: str) -> WasteType:
        """
        Маппинг классов модели в типы мусора.
        
        Если модель обучена на мусоре (Roboflow Trash Sorter), классы уже правильные.
        Если базовая COCO модель - используем эвристический маппинг.
        """
        # Если модель обучена на мусоре, классы уже правильные
        if self._is_waste_model:
            # Прямой маппинг для моделей, обученных на мусоре
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
                    logger.info(f"Mapped waste class '{class_name}' -> {waste_type.value}")
                    return waste_type
            
            # Если не нашли - возвращаем MIXED (модель обучена на мусоре, но класс незнакомый)
            logger.warning(f"Unknown waste class: '{class_name}', mapping to MIXED")
            return WasteType.MIXED
        
        # Эвристический маппинг для COCO модели
        # Маппинг для COCO dataset (80 классов)
        # Проблема: COCO не содержит классов для мусора, только общие объекты
        
        waste_mapping = {
            # Пластик (одноразовая посуда и упаковка)
            "cup": WasteType.PLASTIC,  # Одноразовые стаканчики
            "bowl": WasteType.PLASTIC,  # Одноразовые тарелки
            "bottle": WasteType.PLASTIC,  # Пластиковые бутылки
            "fork": WasteType.PLASTIC,
            "knife": WasteType.PLASTIC,
            "spoon": WasteType.PLASTIC,
            
            # Бумага
            "book": WasteType.PAPER,
            "newspaper": WasteType.PAPER,
            
            # Электроника
            "laptop": WasteType.ELECTRONICS,
            "mouse": WasteType.ELECTRONICS,
            "keyboard": WasteType.ELECTRONICS,
            "cell phone": WasteType.ELECTRONICS,
            "tv": WasteType.ELECTRONICS,
            "remote": WasteType.ELECTRONICS,
            "monitor": WasteType.ELECTRONICS,
            
            # Текстиль
            "handbag": WasteType.TEXTILE,
            "backpack": WasteType.TEXTILE,
            "umbrella": WasteType.TEXTILE,
            "suitcase": WasteType.TEXTILE,
            
            # Металл (только явно металлические предметы)
            "scissors": WasteType.METAL,
            "toaster": WasteType.METAL,
            "microwave": WasteType.METAL,
            "oven": WasteType.METAL,
            
            # Стекло
            "wine glass": WasteType.GLASS,
            
            # Органика
            "banana": WasteType.ORGANIC,
            "apple": WasteType.ORGANIC,
            "sandwich": WasteType.ORGANIC,
            "orange": WasteType.ORGANIC,
            "broccoli": WasteType.ORGANIC,
            "carrot": WasteType.ORGANIC,
            "hot dog": WasteType.ORGANIC,
            "pizza": WasteType.ORGANIC,
            "donut": WasteType.ORGANIC,
            "cake": WasteType.ORGANIC,
        }

        # Пробуем найти по имени класса
        class_name_lower = class_name.lower()
        for key, waste_type in waste_mapping.items():
            if key in class_name_lower:
                logger.info(f"Mapped YOLO class '{class_name}' (id={class_id}) -> {waste_type.value}")
                return waste_type

        # Если не нашли - логируем и возвращаем UNKNOWN
        logger.warning(
            f"Unknown YOLO class: '{class_name}' (id={class_id}), mapping to UNKNOWN. "
            f"Consider using a waste-specific model or adding '{class_name}' to waste_mapping."
        )
        return WasteType.UNKNOWN

    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        """
        Классифицировать мусор на фото.
        
        Args:
            photo_data: Бинарные данные фото
            
        Returns:
            Список детекций с типами мусора
        """
        if not self._is_ready:
            self._load_model()

        logger.info(f"Classifying photo ({len(photo_data)} bytes)")

        try:
            # Открываем изображение
            image = Image.open(BytesIO(photo_data))
            
            # Конвертируем в RGB если нужно
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            logger.debug(f"Image size: {image.size}, mode: {image.mode}")

            # Запускаем inference
            results = self._model.predict(
                image,
                conf=self.confidence_threshold,
                imgsz=self.imgsz,
                device=self.device,
                verbose=False,
            )

            # Обрабатываем результаты
            detections = []
            detected_classes_set = set()  # Для логирования
            
            if results and len(results) > 0:
                result = results[0]  # Первый результат (одно изображение)
                
                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes
                    
                    logger.info(f"YOLOv8 detected {len(boxes)} objects")
                    
                    for i in range(len(boxes)):
                        # Получаем данные детекции
                        box = boxes.xyxy[i].cpu().numpy()  # [x1, y1, x2, y2]
                        conf = float(boxes.conf[i].cpu().numpy())
                        cls_id = int(boxes.cls[i].cpu().numpy())
                        cls_name = result.names[cls_id]
                        detected_classes_set.add(cls_name)  # Сохраняем для логирования
                        
                        # Логируем все детекции для отладки
                        logger.info(
                            f"YOLOv8 detection #{i+1}: class='{cls_name}' "
                            f"(id={cls_id}), confidence={conf:.3f}"
                        )
                        
                        # Нормализуем bounding box (относительные координаты 0-1)
                        img_width, img_height = image.size
                        x1_norm = float(box[0] / img_width)
                        y1_norm = float(box[1] / img_height)
                        x2_norm = float(box[2] / img_width)
                        y2_norm = float(box[3] / img_height)
                        
                        # Маппим класс в тип мусора
                        waste_type = self._map_yolo_class_to_waste_type(cls_id, cls_name)
                        
                        detection = WasteDetection(
                            waste_type=waste_type,
                            confidence=conf,
                            bounding_box=(x1_norm, y1_norm, x2_norm, y2_norm),
                        )
                        detections.append(detection)
                        
                        logger.info(
                            f"Final detection: {waste_type.value} "
                            f"(YOLO class={cls_name}, conf={conf:.3f})"
                        )
                    
                    # Логируем все обнаруженные классы
                    if detected_classes_set:
                        logger.info(f"All detected classes: {detected_classes_set}")
                else:
                    logger.warning("YOLOv8 found no objects (result.boxes is None or empty)")

            logger.info(f"Total detections after mapping: {len(detections)}")
            
            # Фильтруем UNKNOWN детекции и считаем их отдельно
            unknown_detections = [d for d in detections if d.waste_type == WasteType.UNKNOWN]
            known_detections = [d for d in detections if d.waste_type != WasteType.UNKNOWN]
            
            # Если есть известные детекции - возвращаем их
            if known_detections:
                logger.info(f"Returning {len(known_detections)} known detections")
                # Если есть UNKNOWN, но есть и известные - добавляем MIXED для неизвестных
                if unknown_detections:
                    logger.info(f"Also found {len(unknown_detections)} unknown objects, adding MIXED")
                    # Берем средний confidence для UNKNOWN
                    avg_conf = sum(d.confidence for d in unknown_detections) / len(unknown_detections)
                    known_detections.append(
                        WasteDetection(
                            waste_type=WasteType.MIXED,
                            confidence=avg_conf,
                            bounding_box=None,
                        )
                    )
                return known_detections
            
            # Если только UNKNOWN детекции - пробуем определить по контексту
            if unknown_detections:
                logger.warning(
                    f"Found {len(unknown_detections)} detections but all mapped to UNKNOWN. "
                    f"Classes detected: {detected_classes_set}"
                )
                # Эвристика: если детектируется несколько объектов - это скорее всего мусор
                if len(unknown_detections) >= 2:
                    logger.info("Multiple objects detected -> returning MIXED waste")
                    avg_conf = sum(d.confidence for d in unknown_detections) / len(unknown_detections)
                    return [
                        WasteDetection(
                            waste_type=WasteType.MIXED,
                            confidence=avg_conf,
                            bounding_box=None,
                        )
                    ]
                else:
                    # Один объект - возвращаем как есть
                    return unknown_detections
            
            # Если вообще ничего не нашли
            logger.warning(
                "No detections found after YOLOv8 inference. "
                "Possible reasons: confidence threshold too high, "
                "or objects not in COCO dataset classes. "
                "Consider using a waste-specific model!"
            )
            detections.append(
                WasteDetection(
                    waste_type=WasteType.UNKNOWN,
                    confidence=0.0,
                    bounding_box=None,
                )
            )

            return detections

        except Exception as e:
            logger.error(f"Error during classification: {e}", exc_info=True)
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
                self._load_model()
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return False
        
        return self._is_ready
