# ADR-005: Stub-реализации адаптеров для разработки

## Status

**Accepted**

## Date

2024-11-08

## Context

На старте проекта отсутствуют:
- Обученная ML-модель
- PostgreSQL/PostGIS база данных
- S3/MinIO хранилище фотографий

Но нужно:
- Разработать архитектуру
- Создать API endpoints
- Написать бизнес-логику
- Протестировать систему end-to-end

Дилемма: ждать готовности всех компонентов или начинать параллельно?

## Decision

Создать **stub-реализации** всех адаптеров для параллельной разработки.

### Stub Adapters

#### 1. StubWasteClassifier

**Вместо**: YOLOv8/Detectron2

**Что делает**: Генерирует случайные детекции

```python
class StubWasteClassifier(IWasteClassifier):
    async def classify(self, photo_data: bytes) -> list[WasteDetection]:
        # Случайное количество детекций (1-3)
        num_detections = random.randint(1, 3)
        
        detections = []
        for _ in range(num_detections):
            detections.append(WasteDetection(
                waste_type=random.choice(list(WasteType)),
                confidence=random.uniform(0.6, 0.95),
                bounding_box=(
                    random.uniform(0, 0.5),
                    random.uniform(0, 0.5),
                    random.uniform(0.5, 1.0),
                    random.uniform(0.5, 1.0),
                )
            ))
        
        return detections
```

**Преимущества**:
- ✅ Мгновенная "обработка" (<1ms)
- ✅ Не требует PyTorch, CUDA
- ✅ Легко тестировать
- ✅ Детерминированные тесты (с фиксированным seed)

#### 2. StubAnalysisRepository

**Вместо**: PostgreSQL/PostGIS

**Что делает**: In-memory хранилище (dict)

```python
class StubAnalysisRepository(IAnalysisRepository):
    def __init__(self):
        self._storage: dict[UUID, PhotoAnalysis] = {}
    
    async def save(self, analysis: PhotoAnalysis):
        self._storage[analysis.id] = analysis
    
    async def get_by_id(self, analysis_id: UUID):
        return self._storage.get(analysis_id)
```

**Преимущества**:
- ✅ Не требует Docker, PostgreSQL
- ✅ Мгновенные операции
- ✅ Легко очищать между тестами
- ✅ Не нужны миграции

**Недостатки**:
- ❌ Данные теряются при перезапуске
- ❌ Не поддерживает сложные запросы (JOIN, агрегация)
- ❌ Упрощенный расчет расстояния

#### 3. StubPhotoStorage

**Вместо**: S3/MinIO/Local FS

**Что делает**: In-memory хранилище фотографий

```python
class StubPhotoStorage(IPhotoStorage):
    def __init__(self):
        self._storage: dict[str, bytes] = {}
    
    async def save_photo(self, photo_data: bytes, photo_id: UUID) -> str:
        url = f"http://localhost:8000/photos/{photo_id}.jpg"
        self._storage[url] = photo_data
        return url
```

**Преимущества**:
- ✅ Не требует AWS credentials
- ✅ Не требует файловой системы
- ✅ Мгновенное "сохранение"

**Недостатки**:
- ❌ Фото теряются при перезапуске
- ❌ URL не работают (фейковые)

### Конфигурация

```bash
# .env для разработки
ML_MODEL_TYPE=stub
PHOTO_STORAGE_TYPE=stub
# DATABASE_URL не нужен для stub repo
```

```bash
# .env для продакшна
ML_MODEL_TYPE=yolo
ML_MODEL_PATH=./models/yolov8m.pt
PHOTO_STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=...
DATABASE_URL=postgresql://...
```

### Dependency Injection

```python
# dependencies.py
def get_waste_classifier(settings: Settings) -> IWasteClassifier:
    if settings.ml_model_type == "stub":
        return StubWasteClassifier()
    elif settings.ml_model_type == "yolo":
        return YOLOv8Classifier(settings.ml_model_path)
    # ...

def get_analysis_repository(settings: Settings) -> IAnalysisRepository:
    if settings.database_url.startswith("stub"):
        return StubAnalysisRepository()
    else:
        return PostgreSQLAnalysisRepository(settings.database_url)
    # ...
```

## Рассмотренные альтернативы

### 1. Ждать готовности всех компонентов

**Недостатки**:
- ❌ Блокирует разработку (ML-модель - недели)
- ❌ Невозможно тестировать систему
- ❌ Поздно обнаружим архитектурные проблемы

### 2. Использовать mock-объекты в тестах

```python
# test.py
mock_classifier = MagicMock()
mock_classifier.classify.return_value = [...]
```

**Недостатки**:
- ❌ Не работает для ручного тестирования
- ❌ Нельзя запустить полную систему
- ❌ Не покрывает integration тесты

### 3. Упрощенные реальные реализации

Например, TensorFlow Lite модель (быстрая, но неточная)

**Недостатки**:
- ❌ Все равно нужна модель
- ❌ Дополнительные зависимости
- ❌ Может ввести в заблуждение (плохая точность)

## Consequences

### Положительные

1. **Параллельная разработка**
   - Дима: Telegram бот + API
   - Максим: Спутниковые данные
   - ML-инженер: Обучение модели
   - Без блокировок!

2. **Быстрые тесты**
   ```bash
   pytest tests/unit/  # < 1 second
   pytest tests/integration/  # < 5 seconds
   ```

3. **Легкий onboarding**
   - Новый разработчик: `pip install -r requirements.txt` → работает
   - Не нужно настраивать PostgreSQL, S3, скачивать модель

4. **End-to-end тестирование**
   - Полная система работает с первого дня
   - Можно показать демо стейкхолдерам

5. **Детерминированные тесты**
   ```python
   random.seed(42)  # Фиксированный seed
   # Теперь stub всегда возвращает одинаковые результаты
   ```

6. **Постепенная миграция**
   - Заменить stub → реальную реализацию поэтапно
   - Сначала БД, потом ML, потом хранилище
   - Система работает на каждом шаге

### Отрицательные

1. **Дополнительный код**
   - Нужно написать 3 stub класса
   - ~150 строк кода
   - **Но**: один раз, переиспользуется в тестах

2. **Риск забыть заменить**
   - Можем случайно запустить продакшн с stub
   - **Митигация**: проверка в CI/CD, алерты

3. **Ложное чувство готовности**
   - "Система работает!" (но с фейковыми данными)
   - **Митигация**: четко маркировать stub

4. **Неполное покрытие функциональности**
   - Stub не поддерживает все возможности реальной БД
   - **Митигация**: документировать ограничения

### Нейтральные

1. **Нужно поддерживать 2 реализации** - но это и так нужно для тестов
2. **Конфигурация** - нужно помнить, что используешь

## Стратегия миграции

### 1. ML-модель

```bash
# Разработка (сейчас)
ML_MODEL_TYPE=stub

# Когда модель готова
ML_MODEL_TYPE=yolo
ML_MODEL_PATH=./models/yolov8m-waste.pt
```

**Тесты**: stub для unit, yolo для e2e

### 2. База данных

```bash
# Разработка (сейчас)
# Используем StubAnalysisRepository

# Когда PostgreSQL настроен
DATABASE_URL=postgresql://...
```

**Миграция данных**: не нужна (stub не хранит)

### 3. Хранилище фотографий

```bash
# Разработка (сейчас)
PHOTO_STORAGE_TYPE=stub

# Локальная ФС (промежуточный этап)
PHOTO_STORAGE_TYPE=local
PHOTO_STORAGE_PATH=./data/photos

# Продакшн (S3)
PHOTO_STORAGE_TYPE=s3
AWS_S3_BUCKET=satwave-photos
```

## Проверки перед продакшном

```python
# healthcheck.py
def check_production_ready():
    settings = get_settings()
    
    errors = []
    
    if settings.ml_model_type == "stub":
        errors.append("ML model is STUB! Use real model for production")
    
    if isinstance(get_analysis_repository(), StubAnalysisRepository):
        errors.append("Database is STUB! Use PostgreSQL for production")
    
    if settings.photo_storage_type == "stub":
        errors.append("Photo storage is STUB! Use S3 for production")
    
    if errors:
        raise RuntimeError("PRODUCTION READINESS FAILED:\n" + "\n".join(errors))
    
    return True
```

```bash
# В CI/CD для production
python -c "from healthcheck import check_production_ready; check_production_ready()"
```

## Документация stub ограничений

### StubWasteClassifier
- ✅ Быстрый
- ✅ Всегда доступен
- ❌ Случайные результаты
- ❌ Не учитывает содержимое фото
- ❌ Confidence не реалистичен

### StubAnalysisRepository
- ✅ Быстрый
- ✅ Простой
- ❌ In-memory (теряется при restart)
- ❌ Упрощенный расчет расстояния
- ❌ Нет индексов, JOIN, агрегаций

### StubPhotoStorage
- ✅ Мгновенный
- ❌ Фотографии не сохраняются
- ❌ URL фейковые (нельзя открыть)

## Best Practices

1. **Именование**: `Stub*` префикс для ясности
2. **Логирование**: `logger.info("StubWasteClassifier initialized")` 
3. **Тесты**: использовать stub для unit, реальные для integration
4. **Документация**: четко описать ограничения
5. **TODO комментарии**: `# TODO: Replace with real implementation`

## References

- [Test Doubles (Stubs, Mocks, Fakes)](https://martinfowler.com/bliki/TestDouble.html)
- [Clean Architecture: The Test Boundary](https://blog.cleancoder.com/uncle-bob/2011/09/30/Screaming-Architecture.html)
- [ADR-001: Clean Architecture](001-clean-architecture.md) - позволяет stub реализации
- [ADR-002: ML Framework](002-ml-framework.md) - реальная ML модель

