# 🛠️ Сервисы и компоненты

Описание основных сервисов и их ответственности.

## PhotoAnalysisService

**Путь**: `src/satwave/core/services/photo_analysis_service.py`

**Ответственность**: Orchestration всего процесса анализа фото

### Методы

#### `process_photo()`

Главный метод обработки фото.

**Сигнатура**:
```python
async def process_photo(
    self,
    photo_data: bytes,
    latitude: float,
    longitude: float,
    skip_duplicate_check: bool = False,
) -> PhotoAnalysis
```

**Параметры**:
- `photo_data` - бинарные данные фото
- `latitude` - широта (-90 до 90)
- `longitude` - долгота (-180 до 180)
- `skip_duplicate_check` - пропустить проверку дубликатов

**Возвращает**: `PhotoAnalysis` с результатами

**Исключения**:
- `InvalidLocationError` - невалидные координаты
- `DuplicateLocationError` - дубликат локации
- `PhotoProcessingError` - ошибка обработки

**Пример**:
```python
service = PhotoAnalysisService(
    photo_storage=storage,
    analysis_repo=repo,
    waste_classifier=classifier,
)

analysis = await service.process_photo(
    photo_data=photo_bytes,
    latitude=55.7558,
    longitude=37.6173,
)

print(f"Type: {analysis.get_dominant_waste_type()}")
print(f"Detections: {len(analysis.detections)}")
```

#### `get_analysis()`

Получить анализ по ID.

**Сигнатура**:
```python
async def get_analysis(
    self,
    analysis_id: UUID,
) -> PhotoAnalysis | None
```

#### `find_nearby_analyses()`

Найти анализы рядом с точкой.

**Сигнатура**:
```python
async def find_nearby_analyses(
    self,
    latitude: float,
    longitude: float,
    radius_meters: float = 100.0,
) -> list[PhotoAnalysis]
```

**Пример**:
```python
nearby = await service.find_nearby_analyses(
    latitude=55.7558,
    longitude=37.6173,
    radius_meters=200.0,
)
print(f"Found {len(nearby)} analyses nearby")
```

## Интерфейсы (Ports)

**Путь**: `src/satwave/core/domain/ports.py`

Все адаптеры реализуют эти интерфейсы.

### IPhotoStorage

**Ответственность**: Хранение фотографий

**Методы**:

```python
async def save_photo(photo_data: bytes, photo_id: UUID) -> str
async def get_photo(photo_url: str) -> bytes
```

**Реализации**:
- ✅ `StubPhotoStorage` - in-memory (текущая)
- 🔄 `LocalPhotoStorage` - локальная ФС (TODO)
- 🔄 `S3PhotoStorage` - S3/MinIO (TODO)

### IAnalysisRepository

**Ответственность**: Работа с БД (анализы)

**Методы**:

```python
async def save(analysis: PhotoAnalysis) -> None
async def get_by_id(analysis_id: UUID) -> PhotoAnalysis | None
async def find_by_location(location: Location, radius_meters: float) -> list[PhotoAnalysis]
async def location_already_analyzed(location: Location, threshold_meters: float) -> bool
```

**Реализации**:
- ✅ `StubAnalysisRepository` - in-memory (текущая)
- 🔄 `PostgresAnalysisRepository` - PostgreSQL + PostGIS (TODO)

### IWasteClassifier

**Ответственность**: ML-классификация мусора

**Методы**:

```python
async def classify(photo_data: bytes) -> list[WasteDetection]
async def is_ready() -> bool
```

**Реализации**:
- ✅ `StubWasteClassifier` - случайные детекции (текущая)
- 🔄 `YOLOv8Classifier` - YOLOv8 (TODO)
- 🔄 `Detectron2Classifier` - Detectron2 (TODO)

## Адаптеры

### API Adapter

**Путь**: `src/satwave/adapters/api/`

**Компоненты**:
- `app.py` - FastAPI приложение
- `webhook.py` - webhook endpoints
- `dependencies.py` - DI контейнер

**Endpoints**:

```python
POST /webhook/photo          # Отправить фото
GET  /webhook/analysis/{id}  # Получить результат
GET  /health                 # Health check
GET  /                       # Root
```

### Bot Adapter

**Путь**: `src/satwave/adapters/bot/`

**Компоненты**:
- `telegram_bot.py` - класс бота
- `handlers.py` - обработчики сообщений

**Handlers**:
- `/start` - приветствие
- `/help` - помощь
- `handle_photo()` - прием фото
- `handle_location()` - прием локации
- `process_analysis()` - запуск анализа

### Storage Adapters

**Путь**: `src/satwave/adapters/storage/`

**Текущие**:
- `stub_repository.py` - in-memory БД
- `stub_photo_storage.py` - in-memory хранилище фото

**Будущие**:
- `postgres_repository.py` - PostgreSQL + PostGIS
- `s3_photo_storage.py` - S3/MinIO
- `redis_cache.py` - Redis для кеширования

### ML Adapters

**Путь**: `src/satwave/adapters/ml/`

**Текущие**:
- `stub_classifier.py` - случайные детекции

**Будущие**:
- `yolov8_classifier.py` - YOLOv8
- `detectron2_classifier.py` - Detectron2
- `ensemble_classifier.py` - комбинация моделей

## Доменные модели

**Путь**: `src/satwave/core/domain/models.py`

### Location

Географическая точка.

```python
@dataclass
class Location:
    latitude: float   # -90 до 90
    longitude: float  # -180 до 180
    
    def to_wkt(self) -> str:
        """POINT(lon lat) для PostGIS"""
```

### WasteType

Enum типов мусора.

```python
class WasteType(str, Enum):
    PLASTIC = "plastic"
    METAL = "metal"
    PAPER = "paper"
    GLASS = "glass"
    ORGANIC = "organic"
    TEXTILE = "textile"
    ELECTRONICS = "electronics"
    MIXED = "mixed"
    UNKNOWN = "unknown"
```

### WasteDetection

Одна детекция на фото.

```python
@dataclass
class WasteDetection:
    waste_type: WasteType
    confidence: float  # 0.0 до 1.0
    bounding_box: tuple[float, float, float, float] | None
```

### PhotoAnalysis

Результат анализа фото.

```python
@dataclass
class PhotoAnalysis:
    id: UUID
    photo_url: str
    location: Location
    detections: list[WasteDetection]
    status: AnalysisStatus
    created_at: datetime
    processed_at: datetime | None
    error_message: str | None
    
    def get_dominant_waste_type(self) -> WasteType
    def is_duplicate_location(other, threshold_meters) -> bool
```

### AnalysisStatus

Статус обработки.

```python
class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
```

## Dependency Injection

**Путь**: `src/satwave/adapters/api/dependencies.py`

Функции для получения зависимостей:

```python
@lru_cache
def get_photo_storage(settings: Settings | None = None) -> IPhotoStorage

@lru_cache
def get_analysis_repository(settings: Settings | None = None) -> IAnalysisRepository

@lru_cache
def get_waste_classifier(settings: Settings | None = None) -> IWasteClassifier

def get_photo_analysis_service() -> PhotoAnalysisService
```

**Использование в FastAPI**:
```python
@router.post("/webhook/photo")
async def receive_photo(
    service: PhotoAnalysisService = Depends(get_photo_analysis_service),
):
    analysis = await service.process_photo(...)
```

## Configuration

**Путь**: `src/satwave/config/settings.py`

**Pydantic Settings** с загрузкой из `.env`:

```python
class Settings(BaseSettings):
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Telegram
    telegram_bot_token: str = "YOUR_BOT_TOKEN_HERE"
    
    # Database
    database_url: str = "postgresql+asyncpg://..."
    
    # Storage
    photo_storage_type: str = "stub"  # stub, local, s3
    
    # ML
    ml_model_type: str = "stub"  # stub, yolo, detectron2
    ml_model_confidence_threshold: float = 0.5
    
    # Deduplication
    duplicate_check_threshold_meters: float = 50.0
```

## Расширение системы

### Добавление нового адаптера

1. Создать класс, реализующий интерфейс
2. Добавить в `dependencies.py`
3. Настроить через `settings.py`

**Пример** - добавить S3 storage:

```python
# 1. Создать адаптер
class S3PhotoStorage(IPhotoStorage):
    async def save_photo(...) -> str:
        # Реализация
        
# 2. Добавить в dependencies.py
def get_photo_storage(settings: Settings) -> IPhotoStorage:
    if settings.photo_storage_type == "s3":
        return S3PhotoStorage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
        )
    ...

# 3. Настроить
PHOTO_STORAGE_TYPE=s3
S3_BUCKET=satwave-photos
S3_REGION=eu-west-1
```

### Добавление нового use case

1. Создать метод в сервисе или новый сервис
2. Добавить endpoint в API
3. Добавить handler в Bot

## См. также

- [Архитектура](overview.md)
- [Алгоритм анализа](analysis-flow.md)
- [API документация](../api/endpoints.md)

