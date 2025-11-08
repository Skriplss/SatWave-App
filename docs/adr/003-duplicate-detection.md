# ADR-003: Duplicate Detection Strategy

## Status

✅ **Accepted** (2024-01-15)

## Context

Система должна избегать повторного анализа одного и того же места.

### Проблема

Граждане и IoT урны могут:
- Случайно отправить одно и то же фото дважды
- Сфотографировать ту же свалку с разных углов
- Отправить фото свалки, которая уже в системе

Это приводит к:
- ❌ Лишним вычислениям (ML модель дорогая)
- ❌ Дублям в БД
- ❌ Путанице в статистике
- ❌ Лишней нагрузке на переработчиков

### Требования

1. Определять дубликаты с высокой точностью
2. Работать быстро (без ML анализа всех старых фото)
3. Быть настраиваемым (разные пороги для разных случаев)
4. Не блокировать легитимные обновления

## Decision

Использовать **геолокационную дедупликацию** с порогом расстояния.

### Алгоритм

1. Пользователь отправляет фото + координаты
2. Система проверяет: есть ли анализы в радиусе `threshold_meters` от этой точки?
3. Если есть → `DuplicateLocationError` (409 Conflict)
4. Если нет → продолжить обработку

### Формула расстояния

Упрощенная (для in-memory стаба):
```python
lat_diff = abs(lat1 - lat2)
lon_diff = abs(lon1 - lon2)
distance_meters = sqrt(lat_diff² + lon_diff²) * 111000
```

PostGIS (для продакшна):
```sql
SELECT ST_DWithin(
    location::geography,
    ST_MakePoint(lon, lat)::geography,
    threshold_meters
)
```

### Конфигурация

```env
DUPLICATE_CHECK_THRESHOLD_METERS=50.0
```

- **50 метров** - по умолчанию
- **10 метров** - для городов с высокой плотностью
- **100 метров** - для сельской местности

### Пропуск проверки

Для особых случаев (мониторинг динамики):
```python
await service.process_photo(
    ...,
    skip_duplicate_check=True,
)
```

## Consequences

### Positive ✅

1. **Простота**
   - Понятный алгоритм
   - Быстрая реализация
   - Легко объяснить пользователю

2. **Производительность**
   - Один запрос к БД (spatial index)
   - Нет необходимости в ML анализе для сравнения
   - O(log n) с spatial index

3. **Настраиваемость**
   - Разные пороги для разных случаев
   - Можно отключить проверку
   - Легко изменить логику

4. **User Experience**
   - Понятное сообщение об ошибке
   - "Эта локация уже анализировалась"
   - Пользователь понимает, что делать

### Negative ❌

1. **False Positives**
   - Две разные свалки рядом = дубликат
   - Одна свалка, но через месяц = дубликат
   - Пользователь не может обновить данные

2. **False Negatives**
   - Одна свалка, но фото с разных сторон (>50м) = не дубликат
   - GPS неточность может пропустить дубликат

3. **Нет учета времени**
   - Свалка могла измениться за месяц
   - Но мы все равно блокируем

4. **Нет учета содержимого**
   - Не сравниваем сами фото
   - Только координаты

### Risks ⚠️

1. **GPS неточность**
   - Риск: GPS может врать на 10-50 метров
   - Митигация: Порог 50м учитывает неточность

2. **Динамические свалки**
   - Риск: Свалка растет, нужно обновлять
   - Митигация: `skip_duplicate_check=True` для мониторинга

3. **Множественные свалки рядом**
   - Риск: В одном месте несколько типов мусора
   - Митигация: Увеличить порог или ручная проверка

## Alternatives Considered

### Alternative 1: Perceptual Hash (pHash) фото

**Описание**: Сравнивать хеши изображений

```python
import imagehash
from PIL import Image

hash1 = imagehash.phash(Image.open("photo1.jpg"))
hash2 = imagehash.phash(Image.open("photo2.jpg"))

if hash1 - hash2 < threshold:
    # Дубликат!
```

**Почему не выбрали**:
- ❌ Медленно (нужно хешировать все старые фото)
- ❌ Фото с разных углов = разные хеши
- ❌ Освещение, время суток влияют на хеш
- ❌ Нужно хранить хеши для всех фото

**Когда подходит**:
- ✅ Обнаружение точных дубликатов (копипаст)
- ✅ Защита от спама

**TODO**: Рассмотреть как дополнительную проверку

### Alternative 2: ML Embeddings сравнение

**Описание**: Использовать ML для генерации embeddings фото

```python
embedding1 = model.encode(photo1)
embedding2 = model.encode(photo2)

similarity = cosine_similarity(embedding1, embedding2)
if similarity > 0.9:
    # Похожие фото
```

**Почему не выбрали**:
- ❌ Очень дорого (ML inference для каждой проверки)
- ❌ Нужно хранить embeddings для всех фото
- ❌ Сложная векторная БД (Pinecone, Weaviate)
- ❌ Избыточно для MVP

**Когда подходит**:
- ✅ Поиск похожих свалок
- ✅ Recommendation system

**TODO**: Phase 3 - semantic search

### Alternative 3: Временной порог

**Описание**: Блокировать дубликаты только в течение N дней

```python
# Дубликат только если:
# - Та же локация (<50м)
# - И прошло меньше 30 дней
is_duplicate = (
    distance < 50 and
    (now - last_analysis.created_at).days < 30
)
```

**Почему не выбрали сейчас**:
- ⚠️ Усложняет логику
- ⚠️ Нужно решить: сколько дней?
- ⚠️ Разные свалки растут по-разному

**Будем использовать**:
- ✅ Phase 2 - добавить временной порог
- ✅ Настраиваемый через config

### Alternative 4: Нет дедупликации

**Описание**: Вообще не проверять дубликаты

**Почему не выбрали**:
- ❌ Лишние вычисления ML
- ❌ Дубли в БД
- ❌ Плохой UX (зачем отправлять, если уже есть?)

## Implementation

### Phase 1 (Current) ✅

```python
async def location_already_analyzed(
    self,
    location: Location,
    threshold_meters: float = 50.0,
) -> bool:
    # In-memory проверка с упрощенной формулой
    nearby = await self.find_by_location(location, threshold_meters)
    return len(nearby) > 0
```

### Phase 2 (TODO) - PostGIS

```python
async def location_already_analyzed(
    self,
    location: Location,
    threshold_meters: float = 50.0,
) -> bool:
    query = """
    SELECT EXISTS (
        SELECT 1 FROM photo_analysis
        WHERE ST_DWithin(
            location::geography,
            ST_MakePoint($1, $2)::geography,
            $3
        )
    )
    """
    return await db.fetchval(
        query,
        location.longitude,
        location.latitude,
        threshold_meters,
    )
```

### Phase 3 (TODO) - Временной порог

```python
async def location_already_analyzed(
    self,
    location: Location,
    threshold_meters: float = 50.0,
    time_window_days: int = 30,
) -> bool:
    cutoff_date = datetime.now() - timedelta(days=time_window_days)
    
    query = """
    SELECT EXISTS (
        SELECT 1 FROM photo_analysis
        WHERE ST_DWithin(
            location::geography,
            ST_MakePoint($1, $2)::geography,
            $3
        )
        AND created_at > $4
    )
    """
    return await db.fetchval(
        query,
        location.longitude,
        location.latitude,
        threshold_meters,
        cutoff_date,
    )
```

## User Experience

### Telegram Bot

```
User: Отправляет фото
Bot: ✅ Фото получено!

User: Отправляет локацию
Bot: ⚠️ Эта локация уже была проанализирована ранее!
     
     Отправь фото из другого места (дальше 50 метров).
```

### API

```json
{
  "error": "duplicate_location",
  "detail": "Location (55.7558, 37.6173) was already analyzed",
  "nearest_analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "distance_meters": 12.5,
  "suggestion": "Try a location at least 50 meters away"
}
```

## Configuration

### Per-Environment

```env
# Development - строгая проверка
DUPLICATE_CHECK_THRESHOLD_METERS=10.0

# Production - учитываем GPS неточность
DUPLICATE_CHECK_THRESHOLD_METERS=50.0

# Monitoring mode - для отслеживания динамики
DUPLICATE_CHECK_THRESHOLD_METERS=0.0  # Disabled
```

### Per-Request

```python
# API
POST /webhook/photo?skip_duplicate_check=true

# Service
await service.process_photo(
    ...,
    skip_duplicate_check=True,
)
```

## Monitoring

### Метрики

- `duplicate_checks_total` - количество проверок
- `duplicates_detected_total` - найдено дубликатов
- `duplicate_check_duration_seconds` - время проверки

### Alerts

- High duplicate rate (>50%) - возможно проблема с GPS
- Slow duplicate checks (>1s) - проблема с spatial index

## Testing

### Unit Tests

```python
def test_duplicate_detection():
    # Одна локация дважды
    loc1 = Location(55.7558, 37.6173)
    loc2 = Location(55.7558, 37.6173)
    
    assert loc1.is_duplicate_location(loc2, threshold=50.0)

def test_not_duplicate_far_away():
    # Локации далеко друг от друга
    moscow = Location(55.7558, 37.6173)
    spb = Location(59.9343, 30.3351)
    
    assert not moscow.is_duplicate_location(spb, threshold=50.0)
```

## Related ADRs

- [ADR-001: Clean Architecture](001-clean-architecture.md)
- [ADR-002: Webhook vs Polling](002-webhook-vs-polling.md)

## References

- [PostGIS ST_DWithin](https://postgis.net/docs/ST_DWithin.html)
- [Haversine Formula](https://en.wikipedia.org/wiki/Haversine_formula)
- [Perceptual Hashing](http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html)

## Changelog

- **2024-01-15**: Initial decision (Accepted)
- **Future**: Add temporal threshold (Phase 2)
- **Future**: Add perceptual hash as secondary check (Phase 3)

