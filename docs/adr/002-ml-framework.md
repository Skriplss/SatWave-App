# ADR-002: Выбор ML-фреймворка для классификации мусора

## Status

**Accepted**

## Date

2024-11-08

## Context

Нужно выбрать ML-фреймворк для классификации мусора на фото. Требования:
- Точность детекции различных типов мусора
- Скорость inference (целевой latency < 500ms)
- Поддержка bounding boxes
- Возможность fine-tuning на своем датасете
- Активное сообщество и поддержка

### Рассмотренные альтернативы

#### 1. YOLOv8 (Ultralytics)

**Плюсы**:
- ✅ Быстрая inference: 50-100ms (GPU), 200-300ms (CPU)
- ✅ Простой API: `model.predict(image)`
- ✅ Хорошая точность для object detection
- ✅ Легко fine-tune на своих данных
- ✅ Поддержка export в ONNX, TensorRT
- ✅ Активное развитие

**Минусы**:
- ❌ Меньше контроля над архитектурой
- ❌ Не подходит для instance segmentation

**Размер модели**: 
- YOLOv8n: ~6 MB (fast)
- YOLOv8m: ~50 MB (balanced)
- YOLOv8x: ~140 MB (accurate)

#### 2. Detectron2 (Facebook AI)

**Плюсы**:
- ✅ State-of-the-art точность
- ✅ Поддержка instance segmentation
- ✅ Гибкая конфигурация
- ✅ Много предобученных моделей
- ✅ От Facebook Research

**Минусы**:
- ❌ Медленнее: 100-200ms (GPU), 500-1000ms (CPU)
- ❌ Сложнее в использовании
- ❌ Требует больше памяти: 1-2GB
- ❌ Сложнее deployment

**Размер модели**: ~100-300 MB

#### 3. TensorFlow Object Detection API

**Плюсы**:
- ✅ Много готовых моделей
- ✅ Хорошая интеграция с TensorFlow Serving
- ✅ Поддержка TPU

**Минусы**:
- ❌ Устаревший API
- ❌ Сложная конфигурация
- ❌ Медленнее современных решений
- ❌ Менее активная поддержка

#### 4. Custom CNN (ResNet + Custom Head)

**Плюсы**:
- ✅ Полный контроль
- ✅ Можно оптимизировать под задачу

**Минусы**:
- ❌ Нужно создавать с нуля
- ❌ Требует больше времени на разработку
- ❌ Сложнее достичь SOTA точности

## Decision

Использовать **YOLOv8** как основной фреймворк с возможностью переключения на Detectron2 для специфических случаев.

### Обоснование

1. **Скорость** - критична для UX (< 500ms)
2. **Простота** - легче внедрить и поддерживать
3. **Точность** - достаточна для MVP
4. **Гибкость** - архитектура позволяет заменить модель

### Реализация

```python
# Интерфейс (core/domain/ports.py)
class IWasteClassifier(ABC):
    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        ...

# YOLOv8 адаптер (adapters/ml/yolo_classifier.py)
class YOLOv8Classifier(IWasteClassifier):
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)
    
    async def classify(self, photo_data: bytes):
        img = Image.open(BytesIO(photo_data))
        results = self.model.predict(img)
        return self._convert_to_detections(results)

# Detectron2 адаптер (опционально, для сложных случаев)
class Detectron2Classifier(IWasteClassifier):
    # Реализация для instance segmentation
    ...
```

### Конфигурация

```bash
# .env
ML_MODEL_TYPE=yolo  # или detectron2
ML_MODEL_PATH=./models/yolov8m-waste.pt
ML_MODEL_CONFIDENCE_THRESHOLD=0.5
```

### Модели

**Для разработки**:
```python
# Stub (быстрый, для тестов)
ML_MODEL_TYPE=stub
```

**Для продакшна**:
```python
# YOLOv8 (баланс скорость/точность)
ML_MODEL_TYPE=yolo
ML_MODEL_PATH=./models/yolov8m-waste.pt
```

**Для высокой точности**:
```python
# Detectron2 (точность важнее скорости)
ML_MODEL_TYPE=detectron2
ML_MODEL_PATH=./models/mask_rcnn_R_50_FPN.pth
```

## Consequences

### Положительные

1. **Быстрая inference**
   - YOLOv8m: ~200-300ms на CPU
   - Удовлетворяет требованиям latency

2. **Простота интеграции**
   ```python
   model = YOLO("yolov8m.pt")
   results = model.predict(image)
   ```

3. **Fine-tuning**
   - Легко дообучить на своем датасете мусора
   - Можно использовать transfer learning

4. **Гибкость**
   - Благодаря порт-адаптер паттерну можно переключиться на Detectron2
   - Или даже использовать оба: YOLOv8 для speed, Detectron2 для accuracy

5. **Export options**
   - ONNX для production
   - TensorRT для GPU optimization
   - CoreML для iOS (будущее)

### Отрицательные

1. **Ограниченность**
   - YOLOv8 не делает instance segmentation
   - Если нужна маска мусора - придется использовать Detectron2

2. **Зависимость от Ultralytics**
   - Если проект перестанет поддерживаться - проблемы
   - Хотя код open-source, можем форкнуть

3. **Размер модели**
   - YOLOv8m: ~50MB
   - Может быть проблемой для edge devices

4. **Fine-tuning требует данных**
   - Нужен датасет размеченного мусора
   - Минимум 1000+ изображений для хорошего качества

### Нейтральные

1. **PyTorch dependency** - и YOLOv8, и Detectron2 используют PyTorch
2. **GPU опционален** - работает на CPU, но медленнее

## План внедрения

### Фаза 1: MVP (текущая)
- [x] Stub classifier для архитектуры
- [ ] YOLOv8 с pre-trained моделью (COCO)
- [ ] Базовая классификация (5-7 категорий)

### Фаза 2: Custom Dataset
- [ ] Собрать датасет мусора (фото + разметка)
- [ ] Fine-tune YOLOv8m на своих данных
- [ ] Достичь accuracy > 80%

### Фаза 3: Optimization
- [ ] Export в ONNX
- [ ] Quantization для speed
- [ ] A/B тест YOLOv8 vs Detectron2

### Фаза 4: Advanced
- [ ] Ensemble: YOLOv8 + Detectron2
- [ ] Active learning для улучшения модели
- [ ] Real-time feedback от пользователей

## Метрики успеха

**Accuracy**:
- Precision > 85%
- Recall > 80%
- F1-score > 82%

**Latency**:
- p50: < 300ms
- p95: < 500ms
- p99: < 1000ms

**Resource Usage**:
- Memory: < 1GB
- CPU: < 50% (на обработку)

## References

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [Detectron2 Documentation](https://detectron2.readthedocs.io/)
- [Waste Detection Datasets](https://github.com/topics/waste-detection)
- [ADR-001: Clean Architecture](001-clean-architecture.md) - почему легко заменить модель
- [ADR-005: Stub Adapters](005-stub-adapters.md) - stub для разработки

