# 🧠 Обзор системы анализа

## Архитектура обработки

```
Фото + Координаты
    ↓
┌─────────────────────────────────────┐
│  PhotoAnalysisService               │
│  (core/services/)                   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  1. Валидация местоположения        │
│  • Проверка координат (-90/90...)  │
│  • WKT конвертация для PostGIS      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  2. Проверка дубликатов             │
│  • Поиск в радиусе (default: 50m)  │
│  • Haversine distance               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  3. Сохранение фото                 │
│  • UUID генерация                   │
│  • Хранилище (S3/Local/Stub)        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  4. ML-классификация                │
│  • Предобработка изображения        │
│  • Inference (YOLOv8/Detectron2)    │
│  • Post-processing результатов      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  5. Сохранение результата           │
│  • PostgreSQL/PostGIS               │
│  • Индексация по геолокации         │
└─────────────────────────────────────┘
    ↓
Результат (Analysis + Detections)
```

## Компоненты

### 1. Валидация местоположения

**Класс**: `Location` (core/domain/models.py)

**Функции**:
- Проверка широты: -90 ≤ lat ≤ 90
- Проверка долготы: -180 ≤ lon ≤ 180
- Конвертация в WKT формат: `POINT(lon lat)`

**Пример**:
```python
location = Location(latitude=55.7558, longitude=37.6173)
wkt = location.to_wkt()  # "POINT(37.6173 55.7558)"
```

**Исключения**:
- `InvalidLocationError` - невалидные координаты

### 2. Дедупликация

**Метод**: `IAnalysisRepository.location_already_analyzed()`

**Алгоритм**:
1. Поиск всех анализов в радиусе threshold_meters
2. Расчет расстояния (упрощенная Haversine)
3. Если distance < threshold → дубликат

**Формула** (упрощенная):
```python
lat_diff = abs(lat1 - lat2)
lon_diff = abs(lon1 - lon2)
distance_meters = sqrt(lat_diff² + lon_diff²) * 111000
```

**Параметры**:
- `threshold_meters` - порог (default: 50m)

**Исключения**:
- `DuplicateLocationError` - локация уже использовалась

**Почему это важно?**
- Предотвращает дублирование данных в БД
- Экономит ресурсы ML-модели
- Улучшает качество данных для маркетплейса

**TODO для продакшна**:
- Использовать PostGIS функции: `ST_DWithin()`
- Учитывать временной интервал (можно анализировать повторно через N дней)

### 3. ML-классификация

**Интерфейс**: `IWasteClassifier` (core/domain/ports.py)

**Реализации**:
- `StubWasteClassifier` - заглушка (случайные детекции)
- `YOLOv8Classifier` - TODO
- `Detectron2Classifier` - TODO

**Результат**:
```python
WasteDetection(
    waste_type=WasteType.PLASTIC,
    confidence=0.85,
    bounding_box=(x1, y1, x2, y2)  # опционально
)
```

**Типы мусора**:
- `PLASTIC` - пластик
- `METAL` - металл
- `PAPER` - бумага
- `GLASS` - стекло
- `ORGANIC` - органика
- `TEXTILE` - текстиль
- `ELECTRONICS` - электроника
- `MIXED` - смешанный
- `UNKNOWN` - неизвестно

**Документация**: [ml-models.md](ml-models.md)

### 4. Сохранение результата

**Класс**: `PhotoAnalysis` (core/domain/models.py)

**Поля**:
```python
@dataclass
class PhotoAnalysis:
    id: UUID                           # Уникальный ID
    photo_url: str                     # URL фото
    location: Location                 # Координаты
    detections: list[WasteDetection]   # Детекции
    status: AnalysisStatus             # pending/processing/completed/failed
    created_at: datetime               # Время создания
    processed_at: datetime | None      # Время обработки
    error_message: str | None          # Сообщение об ошибке
```

**Методы**:
- `create()` - создание нового анализа
- `is_duplicate_location()` - проверка дубликатов
- `get_dominant_waste_type()` - преобладающий тип мусора

## Метрики производительности

### Текущая версия (Stub)

- **Время анализа**: ~100ms
- **Память**: ~50MB
- **CPU**: минимальная нагрузка

### С реальной ML-моделью (TODO)

**YOLOv8**:
- **Время анализа**: 200-500ms (CPU), 50-100ms (GPU)
- **Память**: 500MB - 1GB
- **Требования**: PyTorch, CUDA (опционально)

**Detectron2**:
- **Время анализа**: 500-1000ms (CPU), 100-200ms (GPU)
- **Память**: 1-2GB
- **Требования**: PyTorch, CUDA

## Масштабирование

### Горизонтальное

```yaml
# docker-compose.yml
services:
  api:
    replicas: 3
  
  worker:
    # Отдельные воркеры для ML
    replicas: 5
```

### Очередь задач

```python
# Celery для асинхронной обработки
@celery_app.task
async def process_photo_async(analysis_id: UUID):
    analysis = await repo.get_by_id(analysis_id)
    detections = await classifier.classify(analysis.photo_data)
    analysis.detections = detections
    await repo.save(analysis)
```

### Кэширование

```python
# Redis для кэширования результатов
@cache(expire=3600)
async def get_analysis(analysis_id: UUID):
    return await repo.get_by_id(analysis_id)
```

## Точность и качество

### Confidence Threshold

```python
# Настройка в .env
ML_MODEL_CONFIDENCE_THRESHOLD=0.5

# Использование
detections = [d for d in raw_detections if d.confidence >= threshold]
```

### Валидация результатов

```python
def validate_detection(detection: WasteDetection) -> bool:
    """Проверить валидность детекции."""
    if detection.confidence < 0.5:
        return False
    if detection.bounding_box:
        x1, y1, x2, y2 = detection.bounding_box
        if x2 <= x1 or y2 <= y1:
            return False
    return True
```

### Метрики качества (TODO)

- **Precision** - точность детекций
- **Recall** - полнота детекций
- **F1-score** - гармоническое среднее
- **mAP** - mean Average Precision

## Обработка edge cases

### Пустое фото

```python
if not photo_data or len(photo_data) == 0:
    raise PhotoProcessingError("Empty photo file")
```

### Поврежденное изображение

```python
try:
    img = Image.open(BytesIO(photo_data))
    img.verify()
except Exception:
    raise PhotoProcessingError("Corrupted image file")
```

### ML модель не готова

```python
if not await classifier.is_ready():
    raise MLModelError("ML model is not ready")
```

### Нет детекций

```python
if not detections:
    return WasteDetection(
        waste_type=WasteType.UNKNOWN,
        confidence=0.0
    )
```

## Логирование

```python
logger.info(f"Processing photo at location: {lat}, {lon}")
logger.info(f"Photo saved: {photo_url} ({len(photo_data)} bytes)")
logger.info(f"Analysis completed: {len(detections)} detections")
logger.warning(f"Location already analyzed: {location.to_wkt()}")
logger.error(f"ML model error: {e}")
```

## См. также

- [ML Models](ml-models.md) - Детали ML-моделей
- [Waste Classification](waste-classification.md) - Типы мусора
- [Geolocation](geolocation.md) - Геовалидация
- [Clean Architecture](../architecture/clean-architecture.md)

