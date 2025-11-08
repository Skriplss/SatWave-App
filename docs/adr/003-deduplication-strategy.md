# ADR-003: Стратегия дедупликации по геолокации

## Status

**Accepted**

## Date

2024-11-08

## Context

Проблема: пользователи (граждане, IoT-урны) могут отправлять фото одной и той же свалки многократно. Это приводит к:
- Дублированию данных в БД
- Лишним вызовам ML-модели (дорого)
- Искажению статистики для маркетплейса
- Путанице: "Эта свалка уже обработана или нет?"

### Сценарии дублирования

1. **Один пользователь отправляет повторно**
   - Забыл, что уже отправлял
   - Хочет обновить статус

2. **Разные пользователи с одной точки**
   - Несколько граждан фотографируют одну свалку
   - IoT-урна + гражданин

3. **GPS неточность**
   - Координаты могут отличаться на 5-50 метров
   - Но это одна и та же точка

### Требования

- Определить, была ли локация уже проанализирована
- Учитывать неточность GPS
- Не блокировать легитимные запросы
- Возможность обновления данных со временем (опционально)

## Decision

Использовать **географическую дедупликацию** с порогом расстояния (threshold radius).

### Алгоритм

1. При получении фото + координат:
   - Проверить, есть ли анализы в радиусе `threshold_meters` (default: 50m)
   - Если есть → отклонить с ошибкой `DuplicateLocationError`
   - Если нет → продолжить обработку

2. Расчет расстояния:
   ```python
   # Упрощенная формула (для малых расстояний)
   lat_diff = abs(lat1 - lat2)
   lon_diff = abs(lon1 - lon2)
   distance_meters = sqrt(lat_diff² + lon_diff²) * 111000
   
   # Более точная (Haversine)
   # TODO: использовать для продакшна
   ```

3. Для продакшна с PostGIS:
   ```sql
   SELECT * FROM analyses
   WHERE ST_DWithin(
       location::geography,
       ST_SetSRID(ST_Point(lon, lat), 4326)::geography,
       threshold_meters
   );
   ```

### Конфигурация

```bash
# .env
DUPLICATE_CHECK_THRESHOLD_METERS=50.0
```

**Настройка порога**:
- **10m** - очень строго (только точное совпадение)
- **50m** - баланс (default, рекомендуется)
- **100m** - более мягко (для сельской местности)

### Реализация

```python
# core/domain/ports.py
class IAnalysisRepository(ABC):
    async def location_already_analyzed(
        self,
        location: Location,
        threshold_meters: float = 50.0
    ) -> bool:
        """Проверить, было ли место проанализировано."""
        ...

# core/services/photo_analysis_service.py
async def process_photo(self, ...):
    location = Location(latitude, longitude)
    
    # Проверка дубликата
    if await self.repo.location_already_analyzed(location):
        raise DuplicateLocationError(
            f"Location ({lat}, {lon}) was already analyzed"
        )
    
    # Продолжаем обработку...
```

### Опция для пропуска проверки

```python
async def process_photo(
    self,
    photo_data: bytes,
    latitude: float,
    longitude: float,
    skip_duplicate_check: bool = False,  # ← Новый параметр
):
    if not skip_duplicate_check:
        if await self.repo.location_already_analyzed(location):
            raise DuplicateLocationError(...)
```

**Когда использовать**:
- Обновление данных (через N дней/недель)
- Админ-режим
- Тестирование

## Рассмотренные альтернативы

### 1. Дедупликация по хэшу фото

**Идея**: Сравнивать perceptual hash изображений

```python
import imagehash
from PIL import Image

hash1 = imagehash.average_hash(Image.open('photo1.jpg'))
hash2 = imagehash.average_hash(Image.open('photo2.jpg'))
distance = hash1 - hash2  # Hamming distance
```

**Плюсы**:
- ✅ Точное определение одинаковых фото
- ✅ Работает даже с разных устройств

**Минусы**:
- ❌ Не решает проблему: разные фото одной свалки
- ❌ Требует хранения всех хэшей
- ❌ Медленный поиск (O(n) сравнений)

**Вердикт**: Не подходит для нашей задачи

### 2. Дедупликация по user_id

**Идея**: Один пользователь не может отправлять с одной точки повторно

**Плюсы**:
- ✅ Простая реализация

**Минусы**:
- ❌ Не решает проблему разных пользователей
- ❌ Блокирует легитимные обновления
- ❌ Сложно отследить пользователей (анонимные отправки)

**Вердикт**: Слишком ограниченно

### 3. Временная дедупликация

**Идея**: Разрешать повторные анализы через N дней/недель

```python
async def location_already_analyzed(
    location: Location,
    threshold_meters: float,
    time_threshold_days: int = 30,  # ← Временной порог
):
    recent_analyses = await self.find_by_location(
        location,
        radius_meters=threshold_meters,
        created_after=datetime.utcnow() - timedelta(days=time_threshold_days)
    )
    return len(recent_analyses) > 0
```

**Плюсы**:
- ✅ Позволяет обновлять данные
- ✅ Учитывает динамику (свалка может измениться)

**Минусы**:
- ❌ Усложняет логику
- ❌ Нужно хранить timestamp
- ❌ Неоднозначно: сколько дней?

**Вердикт**: Хорошая идея для будущего (Phase 2)

### 4. Кластеризация локаций

**Идея**: Группировать близкие точки в кластеры

```python
# DBSCAN или K-means
clusters = cluster_locations(all_analyses, eps=50)
```

**Плюсы**:
- ✅ Автоматическое объединение
- ✅ Статистика по кластерам

**Минусы**:
- ❌ Сложная реализация
- ❌ Требует пересчета при каждом добавлении
- ❌ Overkill для MVP

**Вердикт**: Для Phase 3+

## Consequences

### Положительные

1. **Предотвращение дубликатов**
   - Экономия ресурсов ML
   - Чистота данных в БД
   - Корректная статистика

2. **Учет GPS неточности**
   - Порог 50м покрывает типичную погрешность GPS (5-20m)
   - Работает для городских условий

3. **Простота реализации**
   - Понятный алгоритм
   - Легко тестировать
   - PostGIS поддержка "из коробки"

4. **Настраиваемость**
   - Порог можно изменить в конфиге
   - Опция skip для особых случаев

5. **Производительность**
   - С PostGIS индексами: O(log n)
   - Быстрый поиск в радиусе

### Отрицательные

1. **Блокирование легитимных обновлений**
   - Если свалка изменилась - нельзя обновить
   - **Решение**: параметр `skip_duplicate_check` или временной порог

2. **Edge cases с границей радиуса**
   - 49m - OK
   - 51m - OK
   - 50m - ?
   - **Решение**: Порог должен быть с запасом

3. **Разные пользователи**
   - Второй пользователь получит ошибку "уже проанализировано"
   - Может быть фрустрация
   - **Решение**: Четкое сообщение в UI

4. **Не учитывает время**
   - Свалка может измениться через месяц
   - **Решение**: Phase 2 - добавить временной порог

### Нейтральные

1. **Зависимость от качества GPS**
   - В туннеле, в здании - GPS неточен
   - Но это проблема не нашей системы

2. **Выбор порога субъективен**
   - 50m - эмпирический выбор
   - Возможно, потребуется подстройка

## Будущие улучшения

### Phase 2: Временная дедупликация

```python
DUPLICATE_CHECK_TIME_THRESHOLD_DAYS=30

# Разрешать повторный анализ через 30 дней
if await self.repo.location_analyzed_recently(
    location,
    threshold_meters=50,
    time_threshold_days=30
):
    raise DuplicateLocationError(...)
```

### Phase 3: Smart Deduplication

```python
# Использовать ML для определения "это та же свалка?"
if await self.ml_deduplicator.is_same_waste_site(
    new_photo,
    old_photo,
    location_distance=30
):
    # Обновить существующий анализ
    await self.repo.update_analysis(...)
else:
    # Создать новый
    await self.repo.create_analysis(...)
```

### Phase 4: User Feedback

```python
# Если пользователь уверен - разрешить
if user_confirmed_different:
    skip_duplicate_check = True
```

## Метрики

**Отслеживать**:
- Количество отклоненных дубликатов в день
- Процент дубликатов от всех запросов
- Распределение расстояний между дубликатами

**Целевые значения**:
- < 10% дубликатов (хорошо)
- 10-20% (нормально)
- \> 20% (нужно пересмотреть стратегию)

## Примеры

### Сценарий 1: GPS неточность

```
User1: (55.7558, 37.6173) → Анализ #1 создан
User2: (55.7560, 37.6175) → 22 метров → Дубликат! ❌
```

### Сценарий 2: Разные свалки

```
User1: (55.7558, 37.6173) → Анализ #1 создан
User2: (55.7600, 37.6200) → 520 метров → OK, новый анализ #2 ✅
```

### Сценарий 3: Skip check

```
Admin: (55.7558, 37.6173, skip=true) → Анализ #3 создан (обновление) ✅
```

## References

- [Haversine formula](https://en.wikipedia.org/wiki/Haversine_formula)
- [PostGIS ST_DWithin](https://postgis.net/docs/ST_DWithin.html)
- [GPS accuracy](https://www.gps.gov/systems/gps/performance/accuracy/)
- [ADR-001: Clean Architecture](001-clean-architecture.md)

