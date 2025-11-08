# 📡 API Endpoints

REST API документация для SatWave.

## Base URL

```
http://localhost:8000
```

В продакшне:
```
https://api.satwave.io
```

## Authentication

**Текущая версия**: без аутентификации

**TODO**: JWT токены или API keys

## Endpoints

### Health Check

#### `GET /health`

Проверка здоровья сервиса.

**Response**:
```json
{
  "status": "ok"
}
```

**Status codes**:
- `200 OK` - сервис работает

---

#### `GET /`

Корневой endpoint с информацией о сервисе.

**Response**:
```json
{
  "app": "SatWave",
  "version": "0.1.0",
  "status": "ok"
}
```

---

### Webhook - Photo Analysis

#### `POST /webhook/photo`

Отправить фото для анализа.

**Content-Type**: `multipart/form-data`

**Parameters**:

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `photo` | file | Да | Фото мусора (JPEG/PNG) |
| `latitude` | float | Да | Широта (-90 до 90) |
| `longitude` | float | Да | Долгота (-180 до 180) |
| `skip_duplicate_check` | boolean | Нет | Пропустить проверку дубликатов (default: false) |

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/webhook/photo" \
  -H "Content-Type: multipart/form-data" \
  -F "photo=@/path/to/photo.jpg" \
  -F "latitude=55.7558" \
  -F "longitude=37.6173"
```

**Python Example**:
```python
import requests

with open("photo.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/webhook/photo",
        files={"photo": f},
        data={
            "latitude": 55.7558,
            "longitude": 37.6173,
        },
    )

print(response.json())
```

**Response** (`201 Created`):
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "location": {
    "latitude": 55.7558,
    "longitude": 37.6173
  },
  "dominant_waste_type": "plastic",
  "detections_count": 3,
  "photo_url": "http://localhost:8000/photos/550e8400-e29b-41d4-a716-446655440000.jpg"
}
```

**Error Responses**:

**400 Bad Request** - Невалидные координаты:
```json
{
  "detail": "Invalid latitude: 100.0"
}
```

**409 Conflict** - Дубликат локации:
```json
{
  "detail": "Location (55.7558, 37.6173) was already analyzed"
}
```

**422 Unprocessable Entity** - Ошибка валидации:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "photo"],
      "msg": "Field required"
    }
  ]
}
```

**500 Internal Server Error** - Ошибка обработки:
```json
{
  "detail": "Failed to process photo: ..."
}
```

---

#### `GET /webhook/analysis/{analysis_id}`

Получить результат анализа по ID.

**Path Parameters**:

| Параметр | Тип | Описание |
|----------|-----|----------|
| `analysis_id` | UUID | ID анализа |

**cURL Example**:
```bash
curl -X GET "http://localhost:8000/webhook/analysis/550e8400-e29b-41d4-a716-446655440000"
```

**Response** (`200 OK`):
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "location": {
    "latitude": 55.7558,
    "longitude": 37.6173
  },
  "dominant_waste_type": "plastic",
  "detections_count": 3,
  "photo_url": "http://localhost:8000/photos/550e8400-e29b-41d4-a716-446655440000.jpg"
}
```

**Error Responses**:

**400 Bad Request** - Невалидный формат ID:
```json
{
  "detail": "Invalid analysis ID format"
}
```

**404 Not Found** - Анализ не найден:
```json
{
  "detail": "Analysis 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

## Response Models

### PhotoAnalysisResponse

```python
{
  "analysis_id": str,           # UUID анализа
  "status": str,                # pending | processing | completed | failed
  "location": {
    "latitude": float,          # Широта
    "longitude": float          # Долгота
  },
  "dominant_waste_type": str,   # Преобладающий тип мусора
  "detections_count": int,      # Количество детекций
  "photo_url": str              # URL фото
}
```

### Waste Types

Возможные значения `dominant_waste_type`:

| Значение | Описание | Эмодзи |
|----------|----------|--------|
| `plastic` | Пластик | 🥤 |
| `metal` | Металл | 🔩 |
| `paper` | Бумага | 📄 |
| `glass` | Стекло | 🍾 |
| `organic` | Органика | 🍎 |
| `textile` | Текстиль | 👕 |
| `electronics` | Электроника | 💻 |
| `mixed` | Смешанный | ♻️ |
| `unknown` | Неизвестно | ❓ |

### Status Values

| Значение | Описание |
|----------|----------|
| `pending` | Создан, ждет обработки |
| `processing` | В процессе обработки |
| `completed` | Успешно завершен |
| `failed` | Ошибка при обработке |

---

## Rate Limiting

**Текущая версия**: без ограничений

**TODO**: 
- 100 запросов/минуту для незарегистрированных
- 1000 запросов/минуту для зарегистрированных

---

## OpenAPI / Swagger

Интерактивная документация доступна после запуска:

```
http://localhost:8000/docs
```

Альтернативный интерфейс (ReDoc):
```
http://localhost:8000/redoc
```

OpenAPI схема (JSON):
```
http://localhost:8000/openapi.json
```

---

## Интеграция

### Максим (спутниковые данные)

После получения спутниковых снимков:

```python
# 1. Определить координаты подозрительной зоны
lat, lon = extract_coordinates_from_satellite_data()

# 2. Отправить запрос на анализ (если есть фото)
response = requests.post(
    "http://api.satwave.io/webhook/photo",
    files={"photo": satellite_image},
    data={"latitude": lat, "longitude": lon},
)

# 3. Получить ID анализа
analysis_id = response.json()["analysis_id"]

# 4. Использовать analysis_id для связи с БД
save_to_database(analysis_id, satellite_data)
```

### IoT урны

```python
# Когда урна заполнена и есть фото
photo_data = smart_bin.take_photo()
location = smart_bin.get_gps_location()

response = requests.post(
    "http://api.satwave.io/webhook/photo",
    files={"photo": photo_data},
    data={
        "latitude": location.lat,
        "longitude": location.lon,
    },
)

# Отправить тип мусора обратно на урну
waste_type = response.json()["dominant_waste_type"]
smart_bin.update_waste_type(waste_type)
```

---

## Postman Collection

**TODO**: Создать Postman коллекцию

---

## См. также

- [Webhook документация](webhook.md)
- [Алгоритм анализа](../architecture/analysis-flow.md)
- [OpenAPI Docs](http://localhost:8000/docs)

