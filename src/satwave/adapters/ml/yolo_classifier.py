"""YOLOv8 waste classifier based on Waste-Classification-using-YOLOv8 model."""

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
    logger.warning("ultralytics not installed, YOLOv8 classifier will not work")


class YOLOv8WasteClassifier(IWasteClassifier):
    """
    YOLOv8 waste classifier.
    
    Classifies waste into 5 categories:
    - construction_waste - construction waste
    - hazardous_waste - hazardous waste (batteries, etc.)
    - household_waste - household waste
    - mixed_waste - mixed waste
    - waste_separation_facilities - waste for sorting facilities (recyclable)
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.25,
        device: Optional[str] = None,
    ) -> None:
        """
        Initialize YOLOv8 classifier.
        
        Args:
            model_path: Path to model file (.pt)
            confidence_threshold: Confidence threshold for detections (0.0-1.0)
            device: Device for inference ('cpu', 'cuda', 'mps' or None for auto)
        """
        if YOLO is None:
            raise ImportError(
                "ultralytics package is not installed. "
                "Install it with: pip install ultralytics"
            )

        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.device = device
        self._model: Optional[YOLO] = None
        self._is_ready = False

        # Model class mapping to WasteType
        # New model classes (12 classes):
        # battery → hazardous_waste
        # biological → household_waste
        # brown-glass, green-glass, white-glass → waste_separation_facilities
        # cardboard → waste_separation_facilities
        # clothes → household_waste
        # metal → waste_separation_facilities
        # paper → waste_separation_facilities
        # plastic → waste_separation_facilities
        # shoes → household_waste
        # trash → mixed_waste
        # 
        # Note: construction_waste is not directly determined by the model,
        # can be determined by context or additional logic
        
        # Note: class order may differ depending on the model
        # Mapping works by class names (dynamic), so order doesn't matter
        
        self._class_mapping: dict[int, WasteType] = {
            # Expected class order (check in your model)
            0: WasteType.HAZARDOUS_WASTE,  # battery
            1: WasteType.HOUSEHOLD_WASTE,  # biological
            2: WasteType.WASTE_SEPARATION_FACILITIES,  # brown-glass
            3: WasteType.WASTE_SEPARATION_FACILITIES,  # green-glass
            4: WasteType.WASTE_SEPARATION_FACILITIES,  # white-glass
            5: WasteType.WASTE_SEPARATION_FACILITIES,  # cardboard
            6: WasteType.HOUSEHOLD_WASTE,  # clothes
            7: WasteType.WASTE_SEPARATION_FACILITIES,  # metal
            8: WasteType.WASTE_SEPARATION_FACILITIES,  # paper
            9: WasteType.WASTE_SEPARATION_FACILITIES,  # plastic
            10: WasteType.HOUSEHOLD_WASTE,  # shoes
            11: WasteType.MIXED_WASTE,  # trash
        }

        # Reverse mapping for logging (class names from model)
        self._class_names = {
            0: "battery",
            1: "biological",
            2: "brown-glass",
            3: "green-glass",
            4: "white-glass",
            5: "cardboard",
            6: "clothes",
            7: "metal",
            8: "paper",
            9: "plastic",
            10: "shoes",
            11: "trash",
        }
        
        # Dynamic mapping by class names (if order differs)
        self._name_to_waste_type: dict[str, WasteType] = {
            "battery": WasteType.HAZARDOUS_WASTE,
            "biological": WasteType.HOUSEHOLD_WASTE,
            "brown-glass": WasteType.WASTE_SEPARATION_FACILITIES,
            "green-glass": WasteType.WASTE_SEPARATION_FACILITIES,
            "white-glass": WasteType.WASTE_SEPARATION_FACILITIES,
            "cardboard": WasteType.WASTE_SEPARATION_FACILITIES,
            "clothes": WasteType.HOUSEHOLD_WASTE,
            "metal": WasteType.WASTE_SEPARATION_FACILITIES,
            "paper": WasteType.WASTE_SEPARATION_FACILITIES,
            "plastic": WasteType.WASTE_SEPARATION_FACILITIES,
            "shoes": WasteType.HOUSEHOLD_WASTE,
            "trash": WasteType.MIXED_WASTE,
        }

        logger.info(
            f"YOLOv8WasteClassifier initializing: "
            f"model_path={model_path}, "
            f"confidence_threshold={confidence_threshold}, "
            f"device={device}"
        )

    def _load_model(self) -> None:
        """Load YOLOv8 model."""
        if self._model is not None:
            return

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}. "
                f"Please download the model from "
                f"https://github.com/teamsmcorg/Waste-Classification-using-YOLOv8"
            )

        logger.info(f"Loading YOLOv8 model from {self.model_path}")
        try:
            self._model = YOLO(str(self.model_path))
            logger.info("YOLOv8 model loaded successfully")
            self._is_ready = True
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            raise

    def _aggregate_detections(self, detections: list[WasteDetection]) -> list[WasteDetection]:
        """
        Aggregate detections: keep only one detection per category.
        
        If multiple detections map to one category (e.g., 
        brown-glass, green-glass, white-glass → waste_separation_facilities),
        keep only the detection with maximum confidence.
        
        Args:
            detections: List of all detections
            
        Returns:
            Aggregated list of detections (maximum 5 categories)
        """
        if not detections:
            return []
        
        # Group by categories
        category_detections: dict[WasteType, WasteDetection] = {}
        
        logger.info(f"Aggregating {len(detections)} detections...")
        for detection in detections:
            waste_type = detection.waste_type
            logger.info(
                f"  Processing: {waste_type.value} (conf={detection.confidence:.2f})"
            )
            
            # If category already exists, select detection with higher confidence
            if waste_type not in category_detections:
                category_detections[waste_type] = detection
                logger.info(f"    -> New category: {waste_type.value}")
            else:
                existing = category_detections[waste_type]
                if detection.confidence > existing.confidence:
                    logger.info(
                        f"    -> Replacing (old conf={existing.confidence:.2f}, "
                        f"new conf={detection.confidence:.2f})"
                    )
                    category_detections[waste_type] = detection
                else:
                    logger.info(
                        f"    -> Keeping existing (conf={existing.confidence:.2f} > "
                        f"{detection.confidence:.2f})"
                    )
        
        # Return list of aggregated detections
        aggregated = list(category_detections.values())
        
        # Sort by confidence (from highest to lowest)
        aggregated.sort(key=lambda d: d.confidence, reverse=True)
        
        logger.info(
            f"Aggregated {len(detections)} detections into {len(aggregated)} categories: "
            f"{[d.waste_type.value for d in aggregated]}"
        )
        
        return aggregated

    def _map_class_to_waste_type(self, class_id: int, class_name: Optional[str] = None) -> WasteType:
        """
        Map model class to WasteType.
        
        Args:
            class_id: Class ID from model
            class_name: Class name from model (if available, used for precise mapping)
            
        Returns:
            WasteType corresponding to the class
        """
        # If class name exists, use dynamic mapping
        if class_name:
            # Normalize class name (remove spaces, convert to lowercase)
            normalized_name = class_name.lower().strip().replace("_", "-")
            waste_type = self._name_to_waste_type.get(normalized_name)
            if waste_type:
                return waste_type
        
        # Fallback to ID mapping
        return self._class_mapping.get(class_id, WasteType.UNKNOWN)

    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        """
        Classify waste in photo using YOLOv8.
        
        Args:
            photo_data: Binary photo data
            
        Returns:
            List of detections with waste types and bounding boxes
        """
        if not self._is_ready:
            self._load_model()

        if self._model is None:
            raise RuntimeError("Model is not loaded")

        logger.info(f"Classifying photo ({len(photo_data)} bytes)")

        try:
            # Open image
            image = Image.open(BytesIO(photo_data))
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")

            logger.debug(f"Image size: {image.size}, mode: {image.mode}")

            # Run inference
            # Use confidence threshold to filter false positives
            results = self._model.predict(
                image,
                conf=self.confidence_threshold,  # Use threshold from settings
                device=self.device,
                verbose=False,
            )

            detections: list[WasteDetection] = []

            # Process results
            for result in results:
                if result.boxes is None:
                    logger.warning("No detections found in image")
                    continue
                
                # Log all found detections (even with low confidence)
                total_boxes = len(result.boxes)
                logger.info(f"Found {total_boxes} raw detections from model")

                boxes = result.boxes
                # Get class names from model
                model_class_names = result.names if hasattr(result, 'names') else None
                if model_class_names is None and self._model is not None:
                    model_class_names = getattr(self._model, 'names', None)
                
                for i in range(len(boxes)):
                    # Get detection data
                    box = boxes[i]
                    class_id = int(box.cls[0].item())
                    confidence = float(box.conf[0].item())
                    
                    # Get class name from model (if available)
                    class_name = None
                    if model_class_names:
                        class_name = model_class_names.get(class_id)
                    if not class_name:
                        class_name = self._class_names.get(class_id, "unknown")
                    
                    # Get bounding box coordinates (xyxy format)
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])
                    
                    # Normalize coordinates (0.0-1.0) relative to image size
                    img_width, img_height = image.size
                    normalized_box = (
                        x1 / img_width,
                        y1 / img_height,
                        x2 / img_width,
                        y2 / img_height,
                    )

                    # Map class to WasteType (use class name for precise mapping)
                    waste_type = self._map_class_to_waste_type(class_id, class_name)
                    
                    # Additional check: filter too small bounding boxes
                    # (may be false positives)
                    box_width = normalized_box[2] - normalized_box[0]
                    box_height = normalized_box[3] - normalized_box[1]
                    box_area = box_width * box_height
                    
                    # Minimum bounding box size (1% of image area)
                    min_box_area = 0.01
                    if box_area < min_box_area:
                        logger.debug(
                            f"Skipping small detection: {class_name} ({waste_type.value}) "
                            f"conf={confidence:.2f}, area={box_area:.4f} < {min_box_area}"
                        )
                        continue
                    
                    # Filter by confidence threshold
                    if confidence < self.confidence_threshold:
                        logger.debug(
                            f"Skipping low confidence: {class_name} ({waste_type.value}) "
                            f"conf={confidence:.2f} < threshold={self.confidence_threshold}"
                        )
                        continue

                    detection = WasteDetection(
                        waste_type=waste_type,
                        confidence=confidence,
                        bounding_box=normalized_box,
                    )
                    detections.append(detection)

                    logger.info(
                        f"Detection: {class_name} ({waste_type.value}) "
                        f"conf={confidence:.2f}, area={box_area:.4f}, box={normalized_box}"
                    )

            # Aggregate detections: combine multiple detections of same type into one category
            # Keep only detection with maximum confidence for each type
            aggregated_detections = self._aggregate_detections(detections)

            logger.info(
                f"Classification completed: {len(detections)} raw detections -> "
                f"{len(aggregated_detections)} aggregated categories"
            )
            
            if not aggregated_detections:
                logger.warning("No detections above confidence threshold")
                # Return UNKNOWN if nothing found
                return [
                    WasteDetection(
                        waste_type=WasteType.UNKNOWN,
                        confidence=0.0,
                        bounding_box=None,
                    )
                ]

            return aggregated_detections

        except Exception as e:
            logger.error(f"Error during YOLOv8 classification: {e}", exc_info=True)
            # Return UNKNOWN on error
            return [
                WasteDetection(
                    waste_type=WasteType.UNKNOWN,
                    confidence=0.0,
                    bounding_box=None,
                )
            ]

    async def is_ready(self) -> bool:
        """Check if model is ready for work."""
        if not self._is_ready:
            try:
                self._load_model()
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return False

        return self._is_ready

