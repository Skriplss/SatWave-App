# ADR-002: Webhook vs Polling для API интеграций

## Status

✅ **Accepted** (2024-01-15)

## Context

Нам нужно выбрать способ получения данных от внешних систем (Максим, IoT урны, мобильные приложения).

### Проблема

Система должна получать фото мусора от различных источников:
- 🛰️ Спутниковая система Максима
- 📦 IoT умные урны
- 📱 Мобильные приложения граждан
- 🌐 Web-сервисы партнеров

### Требования

1. Низкая латентность обработки
2. Масштабируемость (тысячи запросов в час)
3. Надежность (не терять данные)
4. Простота интеграции для партнеров

## Decision

Использовать **Webhook API** (`POST /webhook/photo`) для получения данных + **Telegram Bot** для граждан.

### Архитектура

```
External System                 SatWave API
     │                               │
     │   POST /webhook/photo         │
     ├──────────────────────────────►│
     │   multipart/form-data         │
     │   - photo                     │
     │   - latitude                  │
     │   - longitude                 │
     │                               │
     │◄──────────────────────────────┤
     │   201 Created                 │
     │   {                           │
     │     analysis_id,              │
     │     waste_type,               │
     │     ...                       │
     │   }                           │
```

### Почему Webhook?

1. **Push модель** - система-источник отправляет данные сама
2. **Instant processing** - обработка начинается сразу
3. **No polling overhead** - не нужно постоянно опрашивать источник
4. **Standard HTTP** - простая интеграция для всех

### Telegram Bot как исключение

Для граждан используем Telegram Bot (polling):
- Пользователи не могут создавать webhooks
- Telegram Bot API работает через polling или webhook
- Выбрали polling для простоты (webhook требует домен + HTTPS)

## Consequences

### Positive ✅

1. **Низкая латентность**
   - Данные обрабатываются сразу при получении
   - Нет задержки polling interval

2. **Масштабируемость**
   - Горизонтальное масштабирование API
   - Нет ограничений частоты опроса

3. **Простота для клиентов**
   - Обычный HTTP POST запрос
   - Любой язык программирования
   - Много примеров и библиотек

4. **Экономия ресурсов**
   - Нет постоянного polling
   - Процессинг только когда нужно
   - Меньше нагрузка на сеть

5. **Синхронный ответ**
   - Клиент сразу получает результат
   - Не нужна очередь для статусов

### Negative ❌

1. **Требует публичный endpoint**
   - Нужен домен и SSL сертификат
   - Firewall настройки
   - DDoS защита

2. **Reliability на клиенте**
   - Клиент должен обрабатывать ошибки
   - Клиент должен делать retry
   - Мы не контролируем повторные попытки

3. **Нет batch processing**
   - Каждое фото отдельный запрос
   - Нельзя отправить 100 фото за раз
   - Больше HTTP overhead

4. **Синхронная обработка**
   - Клиент ждет ответа
   - Долгая обработка = долгий запрос
   - Может быть timeout

### Risks ⚠️

1. **DDoS атаки**
   - Риск: Злоумышленник может флудить webhook
   - Митигация: Rate limiting, API keys, firewall

2. **Потеря данных**
   - Риск: Если клиент не получил ответ, может не повторить
   - Митигация: Idempotency keys, логирование всех запросов

3. **Долгая обработка**
   - Риск: ML модель может работать долго → timeout
   - Митигация: Асинхронная обработка, очереди (TODO)

## Alternatives Considered

### Alternative 1: Polling API

**Описание**: Клиенты сами опрашивают API за новыми задачами

```python
# Клиент постоянно опрашивает:
while True:
    tasks = requests.get("/api/tasks")
    for task in tasks:
        process_task(task)
    time.sleep(60)  # Poll every minute
```

**Почему не выбрали**:
- ❌ Высокая латентность (poll interval)
- ❌ Большая нагрузка на сервер (постоянные запросы)
- ❌ Сложная логика на клиенте (когда опрашивать?)
- ❌ Нужна очередь задач на сервере

**Когда подходит**:
- ✅ Когда клиент за firewall (не может принимать webhook)
- ✅ Когда нужен batch processing

### Alternative 2: Message Queue (RabbitMQ/Kafka)

**Описание**: Клиенты публикуют сообщения в очередь

```python
# Клиент
publisher.publish(
    exchange="photos",
    body=photo_data,
)

# Сервер
consumer.consume(
    queue="photo_analysis",
    callback=process_photo,
)
```

**Почему не выбрали**:
- ❌ Сложнее для клиентов (нужно настроить connection)
- ❌ Дополнительная инфраструктура (RabbitMQ/Kafka)
- ❌ Сложнее мониторинг
- ❌ Избыточно для MVP

**Когда использовать**:
- ✅ High-throughput (миллионы событий)
- ✅ Асинхронная обработка
- ✅ Event-driven архитектура

**TODO**: Рассмотреть для Phase 3

### Alternative 3: GraphQL Subscriptions

**Описание**: Real-time подписки через WebSocket

```graphql
subscription {
  photoAnalysisCompleted {
    id
    wasteType
    location
  }
}
```

**Почему не выбрали**:
- ❌ Сложнее для клиентов
- ❌ Не все клиенты поддерживают WebSocket
- ❌ Избыточно для one-way communication

**Когда подходит**:
- ✅ Real-time UI updates
- ✅ Сложные запросы с вложенностью

## Implementation

### Current (Phase 1)

```python
@router.post("/webhook/photo")
async def receive_photo(
    photo: UploadFile,
    latitude: float,
    longitude: float,
) -> PhotoAnalysisResponse:
    analysis = await service.process_photo(...)
    return analysis
```

### Future (Phase 2) - Асинхронная обработка

```python
@router.post("/webhook/photo")
async def receive_photo(...) -> AcceptedResponse:
    # Быстро принять и вернуть 202 Accepted
    task_id = await queue.enqueue(
        process_photo,
        photo_data=photo,
        location=(lat, lon),
    )
    
    return {
        "task_id": task_id,
        "status": "accepted",
        "callback_url": f"/webhook/status/{task_id}"
    }

# Клиент может опросить статус
@router.get("/webhook/status/{task_id}")
async def get_status(task_id: str):
    return await get_task_status(task_id)
```

## Integration Examples

### Максим (спутниковые данные)

```python
def process_satellite_data(satellite_image):
    response = requests.post(
        "https://api.satwave.io/webhook/photo",
        files={"photo": satellite_image},
        data={
            "latitude": 55.7558,
            "longitude": 37.6173,
        },
        headers={"X-API-Key": API_KEY},
    )
    
    if response.status_code == 201:
        analysis_id = response.json()["analysis_id"]
        save_to_db(analysis_id, ...)
```

### IoT урна

```python
class SmartBin:
    def on_full(self):
        photo = self.camera.take_photo()
        location = self.gps.get_location()
        
        response = requests.post(
            "https://api.satwave.io/webhook/photo",
            files={"photo": photo},
            data={
                "latitude": location.lat,
                "longitude": location.lon,
            },
        )
        
        waste_type = response.json()["dominant_waste_type"]
        self.display.show(f"Type: {waste_type}")
```

## Monitoring

### Метрики

- `webhook_requests_total` - количество запросов
- `webhook_duration_seconds` - время обработки
- `webhook_errors_total` - ошибки
- `webhook_success_rate` - success rate

### Alerts

- Spike in requests (DDoS)
- High error rate (>5%)
- Slow processing (>30s)

## Security

### Current (Phase 1)

- ❌ No authentication
- ⚠️ Rate limiting: TODO

### Future (Phase 2)

```python
@router.post("/webhook/photo")
async def receive_photo(
    api_key: str = Header(..., alias="X-API-Key"),
):
    if not await verify_api_key(api_key):
        raise HTTPException(403, "Invalid API key")
```

### Future (Phase 3)

- HMAC signature verification
- IP whitelist
- OAuth 2.0

## Related ADRs

- [ADR-001: Clean Architecture](001-clean-architecture.md)
- [ADR-003: Duplicate Detection](003-duplicate-detection.md)

## References

- [Webhook Best Practices](https://hookdeck.com/webhooks/guides/webhook-best-practices)
- [Webhook vs Polling](https://blog.hookdeck.com/webhooks-vs-polling/)

## Changelog

- **2024-01-15**: Initial decision (Accepted)

