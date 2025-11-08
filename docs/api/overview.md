# 📡 API Overview

## Введение

SatWave предоставляет REST API для интеграции с внешними системами.

## Способы отправки данных

### 1. Webhook API (HTTP)

**Для кого**: IoT-устройства, веб-приложения, интеграции

**Endpoint**: `POST /webhook/photo`

**Преимущества**:
- Прямая интеграция через HTTP
- Подходит для автоматизации
- Легко интегрировать с другими сервисами

**Недостатки**:
- Требует программирования
- Нужна обработка ошибок

**Документация**: [webhook.md](webhook.md)

### 2. Telegram Bot

**Для кого**: Граждане, волонтеры, сотрудники на местах

**Интерфейс**: Telegram мессенджер

**Преимущества**:
- Не требует программирования
- Удобный UX для людей
- Мгновенная обратная связь

**Недостатки**:
- Не подходит для автоматизации
- Зависит от Telegram

**Документация**: [../bot/setup.md](../bot/setup.md)

## Base URL

### Локальная разработка
```
http://localhost:8000
```

### Продакшн (TODO)
```
https://api.satwave.io
```

## Форматы данных

### Request

- **Content-Type**: `multipart/form-data` (для фото)
- **Content-Type**: `application/json` (для остальных запросов)

### Response

- **Content-Type**: `application/json`
- **Encoding**: UTF-8

### Коды ответов

| Код | Описание |
|-----|----------|
| 200 | OK - запрос успешен |
| 201 | Created - ресурс создан |
| 400 | Bad Request - невалидные данные |
| 401 | Unauthorized - требуется аутентификация |
| 404 | Not Found - ресурс не найден |
| 409 | Conflict - конфликт (дубликат) |
| 422 | Unprocessable Entity - ошибка валидации |
| 500 | Internal Server Error - ошибка сервера |

## Аутентификация

### Текущая версия

Аутентификация не требуется (разработка).

### Будущая версия (TODO)

```http
POST /webhook/photo
Authorization: Bearer YOUR_API_KEY
```

**Документация**: [authentication.md](authentication.md)

## Обработка ошибок

### Формат ошибки

```json
{
  "error": "Error type",
  "detail": "Detailed error message"
}
```

### Примеры

**Невалидные координаты**:
```json
{
  "error": "Invalid location",
  "detail": "Invalid latitude: 100.0"
}
```

**Дубликат локации**:
```json
{
  "error": "Duplicate location",
  "detail": "Location (55.7558, 37.6173) was already analyzed"
}
```

**Внутренняя ошибка**:
```json
{
  "error": "Processing error",
  "detail": "Failed to process photo: ML model not loaded"
}
```

## Пагинация (TODO)

Для endpoint'ов, возвращающих списки:

```http
GET /api/analyses?page=1&per_page=20
```

Response:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

## Фильтрация (TODO)

```http
GET /api/analyses?waste_type=plastic&date_from=2024-01-01
```

## Версионирование (TODO)

```http
GET /api/v1/analyses
GET /api/v2/analyses
```

## Interactive Documentation

FastAPI автоматически генерирует интерактивную документацию:

### Swagger UI
```
http://localhost:8000/docs
```

### ReDoc
```
http://localhost:8000/redoc
```

### OpenAPI Schema
```
http://localhost:8000/openapi.json
```

## Limits и Quotas (TODO)

### Rate Limiting

- 100 запросов в минуту с одного IP
- 1000 запросов в час с одного API ключа

### File Size Limits

- Максимальный размер фото: 10 MB
- Поддерживаемые форматы: JPEG, PNG

## CORS

### Разрешенные источники

Текущая конфигурация (dev):
```python
allow_origins=["*"]
```

Продакшн (TODO):
```python
allow_origins=[
    "https://satwave.io",
    "https://app.satwave.io",
]
```

## Health Check

```http
GET /health
```

Response:
```json
{
  "status": "ok"
}
```

```http
GET /
```

Response:
```json
{
  "app": "SatWave",
  "version": "0.1.0",
  "status": "ok"
}
```

## WebSocket (TODO)

Для real-time обновлений:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New analysis:', data);
};
```

## Client Libraries (TODO)

### Python

```bash
pip install satwave-client
```

```python
from satwave import SatWaveClient

client = SatWaveClient(api_key="YOUR_KEY")
result = await client.analyze_photo("photo.jpg", 55.7558, 37.6173)
```

### JavaScript

```bash
npm install @satwave/client
```

```javascript
import { SatWaveClient } from '@satwave/client';

const client = new SatWaveClient({ apiKey: 'YOUR_KEY' });
const result = await client.analyzePhoto('photo.jpg', 55.7558, 37.6173);
```

## См. также

- [Webhook API](webhook.md) - Детальная документация
- [Examples](examples.md) - Примеры использования
- [Authentication](authentication.md) - Аутентификация

