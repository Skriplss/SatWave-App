# 🏗️ Clean Architecture в SatWave

## Введение

SatWave использует принципы **Clean Architecture** (Чистая архитектура) от Robert C. Martin.

## Основные принципы

### 1. Dependency Rule

**Зависимости направлены внутрь** (к core):

```
┌─────────────────────────────────────┐
│   Adapters (внешний слой)           │
│   • API (FastAPI)                   │
│   • Bot (Telegram)                  │
│   • Storage (PostgreSQL)            │
│   • ML (YOLOv8)                     │
│                                     │
│   ┌──────────────────────────────┐ │
│   │  Core (внутренний слой)      │ │
│   │  • Domain Models             │ │
│   │  • Business Logic            │ │
│   │  • Ports (интерфейсы)        │ │
│   └──────────────────────────────┘ │
└─────────────────────────────────────┘

    Adapters → Core (✅)
    Core → Adapters (❌)
```

### 2. Независимость от фреймворков

Core не знает о:
- FastAPI
- Telegram (aiogram)
- PostgreSQL
- AWS S3

Core работает с **абстракциями** (интерфейсами).

### 3. Тестируемость

```python
# Unit тест без БД, без API, без ML
def test_location_validation():
    location = Location(latitude=55.7558, longitude=37.6173)
    assert location.to_wkt() == "POINT(37.6173 55.7558)"

# Быстро: < 1ms
```

## Структура проекта

```
src/satwave/
├── core/                           # 🎯 Бизнес-логика
│   ├── domain/
│   │   ├── models.py              # Доменные модели
│   │   ├── exceptions.py          # Бизнес-исключения
│   │   └── ports.py               # Интерфейсы (контракты)
│   └── services/
│       └── photo_analysis_service.py  # Use cases
│
├── adapters/                       # 🔌 Реализации портов
│   ├── api/                       # FastAPI
│   ├── bot/                       # Telegram
│   ├── storage/                   # БД репозитории
│   └── ml/                        # ML-модели
│
└── config/                         # ⚙️ Конфигурация, DI
    └── settings.py
```

## Слои архитектуры

### Core (Центр)

**Содержит**:
- Бизнес-правила
- Доменные модели
- Интерфейсы (порты)

**Не содержит**:
- Импорты FastAPI, aiogram, SQLAlchemy
- HTTP/Telegram специфику
- Детали БД или ML

**Пример**:

```python
# core/domain/models.py
@dataclass
class Location:
    latitude: float
    longitude: float
    
    def __post_init__(self):
        if not -90 <= self.latitude <= 90:
            raise ValueError("Invalid latitude")

# core/domain/ports.py
class IWasteClassifier(ABC):
    """Интерфейс для ML-классификатора."""
    @abstractmethod
    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        ...

# core/services/photo_analysis_service.py
class PhotoAnalysisService:
    def __init__(self, classifier: IWasteClassifier):
        self.classifier = classifier  # Зависимость от интерфейса
    
    async def process_photo(self, photo_data: bytes, lat: float, lon: float):
        location = Location(lat, lon)  # Валидация
        detections = await self.classifier.classify(photo_data)
        return PhotoAnalysis(...)
```

### Adapters (Внешний слой)

**Содержит**:
- Реализации интерфейсов (ports)
- Интеграции с внешними системами
- Фреймворк-специфичный код

**Примеры**:

```python
# adapters/ml/yolo_classifier.py
class YOLOv8Classifier(IWasteClassifier):
    """Реализация порта IWasteClassifier."""
    
    def __init__(self, model_path: str):
        from ultralytics import YOLO
        self.model = YOLO(model_path)
    
    async def classify(self, photo_data: bytes):
        # YOLOv8 специфичная логика
        img = Image.open(BytesIO(photo_data))
        results = self.model.predict(img)
        return self._convert(results)

# adapters/api/webhook.py
@router.post("/webhook/photo")
async def receive_photo(
    photo: UploadFile,
    latitude: float,
    longitude: float,
    service: PhotoAnalysisService = Depends(...)
):
    # FastAPI → Core
    photo_data = await photo.read()
    analysis = await service.process_photo(photo_data, latitude, longitude)
    return {"analysis_id": str(analysis.id), ...}

# adapters/bot/handlers.py
@router.message(lambda m: m.photo)
async def handle_photo(message: Message):
    # Telegram → Core
    photo_data = await download_photo(message.photo[-1])
    analysis = await service.process_photo(photo_data, lat, lon)
    await message.answer(f"Тип мусора: {analysis.get_dominant_waste_type()}")
```

## Ports & Adapters Pattern

### Ports (Интерфейсы)

Определяются в `core/domain/ports.py`:

```python
class IPhotoStorage(ABC):
    @abstractmethod
    async def save_photo(self, photo_data: bytes, photo_id: UUID) -> str:
        """Сохранить фото и вернуть URL."""
        pass

class IAnalysisRepository(ABC):
    @abstractmethod
    async def save(self, analysis: PhotoAnalysis) -> None:
        pass

class IWasteClassifier(ABC):
    @abstractmethod
    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        pass
```

### Adapters (Реализации)

Множество реализаций одного порта:

```python
# adapters/storage/stub_photo_storage.py
class StubPhotoStorage(IPhotoStorage):
    """In-memory для разработки."""
    async def save_photo(self, photo_data, photo_id):
        url = f"http://localhost:8000/photos/{photo_id}.jpg"
        self._storage[url] = photo_data
        return url

# adapters/storage/s3_photo_storage.py
class S3PhotoStorage(IPhotoStorage):
    """AWS S3 для продакшна."""
    async def save_photo(self, photo_data, photo_id):
        await self.s3_client.put_object(
            Bucket=self.bucket,
            Key=f"{photo_id}.jpg",
            Body=photo_data
        )
        return f"https://{self.bucket}.s3.amazonaws.com/{photo_id}.jpg"

# adapters/storage/local_photo_storage.py
class LocalPhotoStorage(IPhotoStorage):
    """Локальная ФС."""
    async def save_photo(self, photo_data, photo_id):
        path = Path(self.storage_path) / f"{photo_id}.jpg"
        path.write_bytes(photo_data)
        return f"file://{path}"
```

**Выбор реализации** через конфигурацию:

```python
# config/dependencies.py
def get_photo_storage(settings: Settings) -> IPhotoStorage:
    if settings.photo_storage_type == "stub":
        return StubPhotoStorage()
    elif settings.photo_storage_type == "local":
        return LocalPhotoStorage(settings.photo_storage_path)
    elif settings.photo_storage_type == "s3":
        return S3PhotoStorage(settings.aws_bucket)
```

## Dependency Injection

### Текущая реализация (ручная)

```python
# adapters/api/dependencies.py
def get_photo_analysis_service() -> PhotoAnalysisService:
    settings = get_settings()
    
    photo_storage = get_photo_storage(settings)
    analysis_repo = get_analysis_repository(settings)
    waste_classifier = get_waste_classifier(settings)
    
    return PhotoAnalysisService(
        photo_storage=photo_storage,
        analysis_repo=analysis_repo,
        waste_classifier=waste_classifier,
    )

# adapters/api/webhook.py
@router.post("/webhook/photo")
async def receive_photo(
    service: PhotoAnalysisService = Depends(get_photo_analysis_service),
):
    ...
```

### Будущая реализация (DI контейнер)

TODO: рассмотреть `dependency-injector` или `punq`

```python
# config/container.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    photo_storage = providers.Singleton(
        get_photo_storage,
        config=config,
    )
    
    analysis_repo = providers.Singleton(
        get_analysis_repository,
        config=config,
    )
    
    waste_classifier = providers.Singleton(
        get_waste_classifier,
        config=config,
    )
    
    photo_analysis_service = providers.Factory(
        PhotoAnalysisService,
        photo_storage=photo_storage,
        analysis_repo=analysis_repo,
        waste_classifier=waste_classifier,
    )
```

## Преимущества

### 1. Гибкость

Легко заменить компоненты:

```bash
# Разработка
ML_MODEL_TYPE=stub
PHOTO_STORAGE_TYPE=stub

# Staging
ML_MODEL_TYPE=yolo
PHOTO_STORAGE_TYPE=local

# Продакшн
ML_MODEL_TYPE=yolo
PHOTO_STORAGE_TYPE=s3
```

Core не меняется!

### 2. Тестируемость

```python
# tests/unit/test_photo_analysis_service.py
def test_process_photo():
    # Используем stub реализации
    service = PhotoAnalysisService(
        photo_storage=StubPhotoStorage(),
        analysis_repo=StubAnalysisRepository(),
        waste_classifier=StubWasteClassifier(),
    )
    
    result = await service.process_photo(b"photo", 55.7558, 37.6173)
    assert result.status == AnalysisStatus.COMPLETED

# Быстро, без БД, без ML, без сети
```

### 3. Параллельная разработка

- Дима: Telegram бот (адаптер)
- Максим: Спутниковые данные (адаптер)
- ML-инженер: YOLOv8 (адаптер)

Core остается стабильным.

### 4. Независимость от фреймворков

FastAPI → Flask → Django:

```python
# Было (FastAPI)
@router.post("/webhook/photo")
async def receive_photo(service: PhotoAnalysisService = Depends(...)):
    ...

# Станет (Flask)
@app.route("/webhook/photo", methods=["POST"])
def receive_photo():
    service = get_photo_analysis_service()
    ...

# Core не меняется!
```

## Недостатки и trade-offs

### Больше кода

Без Clean Architecture:
```python
# all-in-one.py (100 строк)
@app.post("/photo")
async def analyze(file: UploadFile):
    s3.upload(file)  # Прямой вызов AWS
    model = YOLO("model.pt")  # Прямой вызов ML
    results = model.predict(file)
    db.save(results)  # Прямой вызов БД
```

С Clean Architecture:
```
models.py (50 строк)
ports.py (100 строк)
services.py (150 строк)
yolo_classifier.py (100 строк)
s3_storage.py (80 строк)
postgres_repo.py (150 строк)
dependencies.py (80 строк)
webhook.py (100 строк)
= 810 строк
```

**Но**:
- Каждый файл простой и понятный
- Легко тестировать
- Легко расширять

### Сложность для новичков

Нужно понять:
- Dependency Injection
- Inversion of Control
- Ports & Adapters

**Решение**: Документация (этот файл!)

## Best Practices

### 1. Core не импортирует адаптеры

❌ **Плохо**:
```python
# core/services/photo_analysis_service.py
from adapters.ml.yolo_classifier import YOLOv8Classifier  # ❌

class PhotoAnalysisService:
    def __init__(self):
        self.classifier = YOLOv8Classifier()  # ❌ Прямая зависимость
```

✅ **Хорошо**:
```python
# core/services/photo_analysis_service.py
from core.domain.ports import IWasteClassifier  # ✅ Интерфейс

class PhotoAnalysisService:
    def __init__(self, classifier: IWasteClassifier):  # ✅ DI
        self.classifier = classifier
```

### 2. Адаптеры реализуют интерфейсы

```python
# adapters/ml/yolo_classifier.py
from core.domain.ports import IWasteClassifier  # ✅

class YOLOv8Classifier(IWasteClassifier):  # ✅ Наследует интерфейс
    async def classify(self, photo_data: bytes):
        # Реализация...
        pass
```

### 3. Бизнес-логика в Core

❌ **Плохо** (логика в адаптере):
```python
# adapters/api/webhook.py
@router.post("/photo")
async def receive_photo(photo: UploadFile, lat: float, lon: float):
    # Валидация координат в API layer ❌
    if not -90 <= lat <= 90:
        raise HTTPException(400, "Invalid latitude")
    
    # Проверка дубликатов в API layer ❌
    existing = await db.find_nearby(lat, lon)
    if existing:
        raise HTTPException(409, "Duplicate")
    
    # ML в API layer ❌
    model = YOLO("model.pt")
    results = model.predict(photo)
```

✅ **Хорошо** (логика в Core):
```python
# core/services/photo_analysis_service.py
async def process_photo(self, photo_data, lat, lon):
    # Валидация в Core ✅
    location = Location(lat, lon)  # Raises ValueError if invalid
    
    # Дедупликация в Core ✅
    if await self.repo.location_already_analyzed(location):
        raise DuplicateLocationError(...)
    
    # ML через интерфейс ✅
    detections = await self.classifier.classify(photo_data)
    
    return PhotoAnalysis(...)

# adapters/api/webhook.py
@router.post("/photo")
async def receive_photo(photo: UploadFile, lat: float, lon: float):
    # Адаптер только конвертирует FastAPI → Core
    photo_data = await photo.read()
    try:
        analysis = await service.process_photo(photo_data, lat, lon)
        return {"analysis_id": str(analysis.id)}
    except DuplicateLocationError as e:
        raise HTTPException(409, str(e))
```

## Примеры из кодовой базы

- **[Core Models](../../src/satwave/core/domain/models.py)** - Location, PhotoAnalysis, WasteDetection
- **[Ports](../../src/satwave/core/domain/ports.py)** - IWasteClassifier, IAnalysisRepository
- **[Service](../../src/satwave/core/services/photo_analysis_service.py)** - PhotoAnalysisService
- **[Adapters](../../src/satwave/adapters/)** - API, Bot, Storage, ML

## См. также

- [ADR-001: Clean Architecture](../adr/001-clean-architecture.md) - Почему выбрали этот подход
- [Ports & Adapters](ports-adapters.md) - Детали паттерна
- [Components](components.md) - Обзор компонентов системы
- [Clean Architecture Book](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

