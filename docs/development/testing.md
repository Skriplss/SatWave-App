# 🧪 Testing Guide

Стратегия тестирования SatWave.

## Test Pyramid

```
        /\
       /  \
      / E2E\         End-to-End (немного)
     /______\
    /        \
   /Integration\     Integration (средне)
  /____________\
 /              \
/   Unit Tests   \   Unit (много)
/__________________\
```

## Запуск тестов

### Все тесты

```bash
pytest
```

### Только unit тесты

```bash
pytest tests/unit/
```

### Только integration тесты

```bash
pytest tests/integration/
```

### Конкретный файл

```bash
pytest tests/unit/test_models.py
```

### Конкретный тест

```bash
pytest tests/unit/test_models.py::test_location_validation
```

### С покрытием

```bash
pytest --cov=satwave --cov-report=html
```

Откроется `htmlcov/index.html` с детальным отчетом.

## Unit Tests

Тестируют **доменную логику** без внешних зависимостей.

### Примеры

#### Тестирование моделей

```python
# tests/unit/test_models.py

def test_location_validation():
    """Тест валидации координат."""
    # Valid
    loc = Location(latitude=55.7558, longitude=37.6173)
    assert loc.latitude == 55.7558
    
    # Invalid latitude
    with pytest.raises(ValueError, match="Invalid latitude"):
        Location(latitude=100.0, longitude=37.6173)

def test_waste_detection():
    """Тест детекции мусора."""
    detection = WasteDetection(
        waste_type=WasteType.PLASTIC,
        confidence=0.85,
    )
    assert detection.waste_type == WasteType.PLASTIC
    assert 0 <= detection.confidence <= 1
```

#### Тестирование сервисов

```python
# tests/unit/test_photo_analysis_service.py

@pytest.mark.asyncio
async def test_process_photo_success():
    """Тест успешной обработки фото."""
    # Arrange
    service = PhotoAnalysisService(
        photo_storage=StubPhotoStorage(),
        analysis_repo=StubAnalysisRepository(),
        waste_classifier=StubWasteClassifier(),
    )
    
    # Act
    analysis = await service.process_photo(
        photo_data=b"fake photo",
        latitude=55.7558,
        longitude=37.6173,
    )
    
    # Assert
    assert analysis.status == AnalysisStatus.COMPLETED
    assert len(analysis.detections) > 0
```

### Фикстуры

```python
# tests/conftest.py

@pytest.fixture
def photo_analysis_service():
    """Фикстура для сервиса."""
    return PhotoAnalysisService(
        photo_storage=StubPhotoStorage(),
        analysis_repo=StubAnalysisRepository(),
        waste_classifier=StubWasteClassifier(),
    )

# Использование
def test_something(photo_analysis_service):
    result = await photo_analysis_service.process_photo(...)
```

## Integration Tests

Тестируют **интеграцию компонентов** (API, Bot).

### API Tests

```python
# tests/integration/test_webhook_api.py

from fastapi.testclient import TestClient

def test_receive_photo_success(client: TestClient):
    """Тест отправки фото через API."""
    fake_photo = BytesIO(b"fake image")
    
    response = client.post(
        "/webhook/photo",
        files={"photo": ("test.jpg", fake_photo, "image/jpeg")},
        data={
            "latitude": 55.7558,
            "longitude": 37.6173,
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "analysis_id" in data
    assert data["status"] == "completed"
```

### Bot Tests (TODO)

```python
# tests/integration/test_bot_handlers.py

from aiogram.test_utils.mocked_bot import MockedBot

async def test_start_command():
    """Тест команды /start."""
    bot = MockedBot()
    # TODO: Implement
```

## Property-Based Testing (TODO)

Для математических инвариантов:

```python
from hypothesis import given, strategies as st

@given(
    lat=st.floats(min_value=-90, max_value=90),
    lon=st.floats(min_value=-180, max_value=180),
)
def test_location_always_valid(lat, lon):
    """Любые валидные координаты создают валидную Location."""
    loc = Location(latitude=lat, longitude=lon)
    assert -90 <= loc.latitude <= 90
    assert -180 <= loc.longitude <= 180
```

## Coverage

### Целевое покрытие

- **Core**: ≥ 80%
- **Adapters**: ≥ 60%
- **Overall**: ≥ 70%

### Проверка coverage

```bash
pytest --cov=satwave --cov-report=term-missing

# Показывает, какие строки не покрыты
```

### HTML Report

```bash
pytest --cov=satwave --cov-report=html
open htmlcov/index.html
```

## Mocking

### Mock адаптеров

```python
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_with_mock():
    # Mock classifier
    mock_classifier = AsyncMock(spec=IWasteClassifier)
    mock_classifier.classify.return_value = [
        WasteDetection(waste_type=WasteType.PLASTIC, confidence=0.9)
    ]
    
    service = PhotoAnalysisService(
        classifier=mock_classifier,
        ...
    )
    
    result = await service.process_photo(...)
    
    mock_classifier.classify.assert_called_once()
```

### Mock HTTP запросов

```python
import responses

@responses.activate
def test_external_api_call():
    responses.add(
        responses.POST,
        "https://api.external.com/analyze",
        json={"result": "plastic"},
        status=200,
    )
    
    # Код, который делает запрос
    result = call_external_api(...)
    assert result == "plastic"
```

## Test Data

### Фикстуры данных

```python
# tests/fixtures/photos.py

import base64

FAKE_PHOTO_JPG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD..."  # Минимальный JPEG
)

MOSCOW_LOCATION = Location(latitude=55.7558, longitude=37.6173)
SPB_LOCATION = Location(latitude=59.9343, longitude=30.3351)
```

### Использование

```python
from tests.fixtures.photos import FAKE_PHOTO_JPG, MOSCOW_LOCATION

async def test_with_fixtures():
    analysis = await service.process_photo(
        photo_data=FAKE_PHOTO_JPG,
        latitude=MOSCOW_LOCATION.latitude,
        longitude=MOSCOW_LOCATION.longitude,
    )
```

## CI/CD Integration

### GitHub Actions

`.github/workflows/tests.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          pytest --cov=satwave --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Best Practices

### 1. Arrange-Act-Assert

```python
def test_something():
    # Arrange - подготовка
    service = create_service()
    data = create_test_data()
    
    # Act - действие
    result = service.process(data)
    
    # Assert - проверка
    assert result.status == "success"
```

### 2. Один assert на тест (идеально)

```python
# Плохо
def test_analysis():
    assert analysis.status == "completed"
    assert len(analysis.detections) > 0
    assert analysis.location is not None

# Хорошо - разбить на отдельные тесты
def test_analysis_status():
    assert analysis.status == "completed"

def test_analysis_has_detections():
    assert len(analysis.detections) > 0
```

### 3. Тестовые имена описательные

```python
# Плохо
def test_1():
    ...

# Хорошо
def test_location_validation_rejects_invalid_latitude():
    ...
```

### 4. Независимые тесты

```python
# Плохо - зависимость от порядка
def test_create():
    global obj
    obj = create()

def test_update():
    obj.update()  # Зависит от test_create

# Хорошо - каждый тест независим
def test_create():
    obj = create()
    assert obj is not None

def test_update():
    obj = create()
    obj.update()
    assert obj.updated
```

## Debugging Tests

### Verbose output

```bash
pytest -v
```

### Show print statements

```bash
pytest -s
```

### Stop on first failure

```bash
pytest -x
```

### Run last failed

```bash
pytest --lf
```

### PDB debugger

```bash
pytest --pdb
```

Или в коде:
```python
def test_something():
    result = do_something()
    import pdb; pdb.set_trace()  # Breakpoint
    assert result == expected
```

## Performance Tests (TODO)

```python
import time

def test_analysis_performance():
    """Анализ должен завершаться < 5 секунд."""
    start = time.time()
    
    analysis = await service.process_photo(...)
    
    duration = time.time() - start
    assert duration < 5.0, f"Too slow: {duration}s"
```

## См. также

- [Development Setup](setup.md)
- [Architecture](../architecture/overview.md)
- [pytest docs](https://docs.pytest.org/)

