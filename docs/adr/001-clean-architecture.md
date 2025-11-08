# ADR-001: Использование Clean Architecture

## Status

**Accepted**

## Date

2024-11-08

## Context

При начале проекта SatWave нужно было выбрать архитектурный подход. Проект имеет сложную доменную логику:
- Обработка фото мусора
- ML-классификация
- Геовалидация и дедупликация
- Интеграция с внешними системами (Telegram, спутники, БД)

### Проблемы

1. **Изменчивость требований** - ML-модели, хранилища, API могут меняться
2. **Тестируемость** - нужны быстрые unit-тесты без БД и внешних сервисов
3. **Разделение ответственности** - бизнес-логика не должна зависеть от фреймворков
4. **Масштабируемость** - разные команды работают над разными частями

### Рассмотренные альтернативы

1. **Layered Architecture** (традиционная)
   - ❌ Тесная связанность слоев
   - ❌ Бизнес-логика зависит от БД
   - ✅ Простота понимания
   
2. **MVC/MTV** (Django-style)
   - ❌ Бизнес-логика размазана по views
   - ❌ Тяжело тестировать
   - ✅ Быстрый старт для простых проектов
   
3. **Clean Architecture** (Hexagonal/Ports&Adapters)
   - ✅ Независимость от фреймворков
   - ✅ Тестируемость
   - ✅ Гибкость
   - ❌ Больше кода (boilerplate)

## Decision

Использовать **Clean Architecture** (Hexagonal Architecture) с принципами:

### Структура

```
core/               # Бизнес-логика (независима от всего)
├── domain/         # Модели, исключения, интерфейсы (порты)
└── services/       # Use cases, бизнес-сервисы

adapters/           # Реализации портов (зависят от core)
├── api/            # FastAPI endpoints
├── bot/            # Telegram bot
├── storage/        # БД репозитории
└── ml/             # ML-модели

config/             # Конфигурация и DI
```

### Принципы

1. **Dependency Rule** - зависимости направлены внутрь (к core)
   ```
   Adapters → Core (✅)
   Core → Adapters (❌)
   ```

2. **Ports & Adapters**
   - Core определяет интерфейсы (ports): `IPhotoStorage`, `IWasteClassifier`
   - Adapters реализуют интерфейсы: `S3PhotoStorage`, `YOLOv8Classifier`

3. **Dependency Injection**
   - Конкретные реализации передаются извне
   - Core не знает о FastAPI, Telegram, S3

### Пример

```python
# Core определяет контракт
class IWasteClassifier(ABC):
    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        ...

# Core использует интерфейс
class PhotoAnalysisService:
    def __init__(self, classifier: IWasteClassifier):
        self.classifier = classifier
    
    async def process(self, photo: bytes):
        detections = await self.classifier.classify(photo)
        ...

# Adapter реализует контракт
class YOLOv8Classifier(IWasteClassifier):
    async def classify(self, photo_data: bytes):
        # Реальная реализация с YOLOv8
        ...

# DI связывает все вместе
service = PhotoAnalysisService(
    classifier=YOLOv8Classifier()  # Легко заменить на другую реализацию
)
```

## Consequences

### Положительные

1. **Тестируемость** 
   - Unit-тесты core без БД, API, ML: `pytest tests/unit/ -v` < 1s
   - Легко создавать mock-объекты

2. **Гибкость**
   - Замена ML-модели: создать новый адаптер, не трогая core
   - Замена БД: PostgreSQL → MongoDB → Redis - только адаптер
   - Добавление нового источника данных (WebSocket, gRPC) - новый адаптер

3. **Независимость от фреймворков**
   - FastAPI → Flask → Django - бизнес-логика не меняется
   - aiogram 2.x → 3.x - только bot adapter

4. **Параллельная разработка**
   - Дима работает над Telegram ботом
   - Максим - над спутниковыми данными
   - Core остается стабильным

5. **Понятная структура**
   - Новый разработчик видит, где что искать
   - Бизнес-логика в одном месте (core)

### Отрицательные

1. **Больше кода**
   - Интерфейсы (ports) требуют определения
   - Нужны реализации (adapters) даже для простых вещей
   - Пример: `IPhotoStorage` + `LocalStorage` + `S3Storage` vs прямой вызов boto3

2. **Сложность для новичков**
   - Нужно понимать DI, IoC, Ports & Adapters
   - Не очевидно, где что лежит
   - Требуется документация (этот ADR!)

3. **Overhead для простых операций**
   - CRUD операции требуют больше кода
   - Иногда проще было бы напрямую

4. **Нужен DI контейнер**
   - Ручной DI в `dependencies.py` работает, но не масштабируется
   - TODO: рассмотреть dependency-injector или similar

### Нейтральные

1. **Больше файлов** - структура более разветвленная
2. **Нужны соглашения** - как называть интерфейсы, где их класть
3. **Дублирование типов** - иногда DTO ≈ Domain Model

## Компромиссы

### Когда НЕ использовать Clean Architecture?

- Простой CRUD без бизнес-логики → Django Admin
- Прототип на выходные → MVC
- Очень маленький микросервис (< 3 endpoints) → простой Flask

### Когда ИСПОЛЬЗОВАТЬ?

- ✅ Сложная бизнес-логика (наш случай)
- ✅ Проект > 6 месяцев
- ✅ Команда > 2 человек
- ✅ Требуется тестируемость
- ✅ Высокая изменчивость требований

## Примеры в коде

### До (неправильно)

```python
# service.py - бизнес-логика зависит от FastAPI и S3
from fastapi import UploadFile
import boto3

async def process_photo(file: UploadFile):  # Зависимость от FastAPI!
    s3 = boto3.client('s3')  # Зависимость от AWS!
    # Бизнес-логика...
```

### После (правильно)

```python
# core/services/photo_analysis_service.py - чистая логика
async def process_photo(
    self,
    photo_data: bytes,  # Просто bytes, не FastAPI UploadFile
    latitude: float,
    longitude: float,
) -> PhotoAnalysis:
    # Валидация
    location = Location(latitude, longitude)
    
    # Дедупликация
    if await self.repo.location_already_analyzed(location):
        raise DuplicateLocationError(...)
    
    # Сохранение (через интерфейс)
    url = await self.photo_storage.save_photo(photo_data, id)
    
    # ML (через интерфейс)
    detections = await self.classifier.classify(photo_data)
    
    return PhotoAnalysis(...)
```

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Ports and Adapters Pattern](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/)
- [ADR-005: Stub Adapters](005-stub-adapters.md)
