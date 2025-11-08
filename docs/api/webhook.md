# 📡 Webhook API

## Обзор

Webhook API позволяет отправлять фото мусора для анализа через HTTP запросы.

**Base URL**: `http://localhost:8000` (локальная разработка)

**Формат**: multipart/form-data

## Endpoints

### POST /webhook/photo

Отправить фото на анализ.

#### Request

**Headers**:
```
Content-Type: multipart/form-data
```

**Form Data**:
| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `photo` | file | ✅ | Фото мусора (JPEG/PNG) |
| `latitude` | float | ✅ | Широта (-90 до 90) |
| `longitude` | float | ✅ | Долгота (-180 до 180) |
| `skip_duplicate_check` | boolean | ❌ | Пропустить проверку дубликатов (default: false) |

#### Response 201 Created

```json
{
  "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "location": {
    "latitude": 55.7558,
    "longitude": 37.6173
  },
  "dominant_waste_type": "plastic",
  "detections_count": 2,
  "photo_url": "http://localhost:8000/photos/123e4567.jpg"
}
```

#### Response 400 Bad Request

Невалидные координаты:
```json
{
  "error": "Invalid location",
  "detail": "Invalid latitude: 100.0"
}
```

#### Response 409 Conflict

Дубликат локации:
```json
{
  "error": "Duplicate location",
  "detail": "Location (55.7558, 37.6173) was already analyzed"
}
```

#### Response 500 Internal Server Error

Ошибка обработки:
```json
{
  "error": "Processing error",
  "detail": "Failed to process photo: ML model error"
}
```

### GET /webhook/analysis/{analysis_id}

Получить результат анализа по ID.

#### Request

**Path Parameters**:
| Параметр | Тип | Описание |
|----------|-----|----------|
| `analysis_id` | UUID | ID анализа |

#### Response 200 OK

```json
{
  "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "location": {
    "latitude": 55.7558,
    "longitude": 37.6173
  },
  "dominant_waste_type": "plastic",
  "detections_count": 2,
  "photo_url": "http://localhost:8000/photos/123e4567.jpg"
}
```

#### Response 404 Not Found

```json
{
  "error": "Not found",
  "detail": "Analysis 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

## Примеры использования

### cURL

```bash
# Отправить фото
curl -X POST "http://localhost:8000/webhook/photo" \
  -F "photo=@/path/to/photo.jpg" \
  -F "latitude=55.7558" \
  -F "longitude=37.6173"

# Получить результат
curl "http://localhost:8000/webhook/analysis/123e4567-e89b-12d3-a456-426614174000"
```

### Python (requests)

```python
import requests

# Отправка фото
with open("photo.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/webhook/photo",
        files={"photo": f},
        data={
            "latitude": 55.7558,
            "longitude": 37.6173,
        }
    )

result = response.json()
print(f"Analysis ID: {result['analysis_id']}")
print(f"Waste Type: {result['dominant_waste_type']}")

# Получение результата
analysis_id = result["analysis_id"]
response = requests.get(f"http://localhost:8000/webhook/analysis/{analysis_id}")
print(response.json())
```

### JavaScript (axios)

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

// Отправка фото
async function analyzePhoto() {
  const form = new FormData();
  form.append('photo', fs.createReadStream('photo.jpg'));
  form.append('latitude', 55.7558);
  form.append('longitude', 37.6173);
  
  const response = await axios.post(
    'http://localhost:8000/webhook/photo',
    form,
    { headers: form.getHeaders() }
  );
  
  console.log('Analysis ID:', response.data.analysis_id);
  console.log('Waste Type:', response.data.dominant_waste_type);
  
  return response.data.analysis_id;
}

// Получение результата
async function getAnalysis(analysisId) {
  const response = await axios.get(
    `http://localhost:8000/webhook/analysis/${analysisId}`
  );
  
  console.log(response.data);
}
```

### Python (httpx, async)

```python
import httpx
import asyncio

async def analyze_photo():
    async with httpx.AsyncClient() as client:
        with open("photo.jpg", "rb") as f:
            response = await client.post(
                "http://localhost:8000/webhook/photo",
                files={"photo": f},
                data={
                    "latitude": 55.7558,
                    "longitude": 37.6173,
                }
            )
        
        result = response.json()
        return result["analysis_id"]

asyncio.run(analyze_photo())
```

## Интеграция с Максимом

### Флоу обработки

```
1. Максим получает спутниковый снимок
2. Обнаруживает подозрительное скопление мусора
3. Отправляет запрос на webhook с координатами центра
4. Получает analysis_id и waste_type
5. Сохраняет в свою БД для дальнейшей обработки
6. Анализирует площадь свалки
7. Преобразует в текстовые метрики
8. Отправляет на маркетплейс
```

### Пример интеграции

```python
from satwave_client import SatWaveClient

# Инициализация клиента
client = SatWaveClient(base_url="http://satwave-api:8000")

# Обработка спутникового снимка
for detection in satellite_detections:
    # Отправка на анализ
    result = await client.analyze_waste(
        photo=detection.image,
        latitude=detection.center_lat,
        longitude=detection.center_lon,
    )
    
    # Сохранение результата
    await maxim_db.save({
        "analysis_id": result.analysis_id,
        "waste_type": result.dominant_waste_type,
        "location": detection.location,
        "area_m2": calculate_area(detection.polygon),
    })
```

## Rate Limiting

В текущей версии rate limiting не реализован.

**TODO для продакшна**:
- Ограничить количество запросов с одного IP
- Добавить аутентификацию по API ключу
- Throttling для тяжелых операций

## Мониторинг

### Логирование

Все запросы логируются:
```
INFO - Received photo webhook: lat=55.7558, lon=37.6173
INFO - User uploaded photo (12345 bytes)
INFO - Analysis completed: 2 detections, dominant type: plastic
```

### Метрики (TODO)

- Количество запросов в секунду
- Время обработки фото
- Процент ошибок
- Распределение по типам мусора

## См. также

- [API Overview](overview.md)
- [Authentication](authentication.md)
- [Examples](examples.md)
- [Telegram Bot](../bot/setup.md) - Альтернативный способ отправки
