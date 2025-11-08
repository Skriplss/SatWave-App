# 🤖 Telegram Bot - Архитектура

Техническая документация Telegram бота.

## Обзор

Telegram бот - это альтернативный интерфейс для граждан для отправки фото мусора. Использует ту же доменную логику, что и Webhook API.

## Технологии

- **Aiogram 3.x** - асинхронный фреймворк для Telegram Bot API
- **Asyncio** - асинхронное программирование
- **PhotoAnalysisService** - интеграция с core логикой

## Структура

```
src/satwave/adapters/bot/
├── __init__.py
├── telegram_bot.py    # Класс бота, запуск polling
└── handlers.py        # Обработчики сообщений
```

## Компоненты

### TelegramBot (telegram_bot.py)

Основной класс бота.

```python
class TelegramBot:
    def __init__(self, settings: Settings):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.dp = Dispatcher()
        self.dp.include_router(router)
    
    async def start(self) -> NoReturn:
        """Запуск polling"""
    
    async def stop(self) -> None:
        """Остановка бота"""
```

**Ответственность**:
- Инициализация Bot и Dispatcher
- Управление lifecycle (start/stop)
- Подключение handlers

### Handlers (handlers.py)

Обработчики команд и сообщений.

#### Команды

```python
@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Приветствие и инструкция"""

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Подробная помощь"""
```

#### Прием фото

```python
@router.message(lambda message: message.photo is not None)
async def handle_photo(message: Message) -> None:
    """
    1. Получить фото (самого большого размера)
    2. Скачать через bot.download_file()
    3. Сохранить в UserSession
    4. Если есть локация → запустить анализ
    """
```

#### Прием геолокации

```python
@router.message(lambda message: message.location is not None)
async def handle_location(message: Message) -> None:
    """
    1. Получить координаты
    2. Сохранить в UserSession
    3. Если есть фото → запустить анализ
    """
```

#### Обработка анализа

```python
async def process_analysis(message: Message, session: UserSession) -> None:
    """
    1. Проверить, что есть и фото, и локация
    2. Вызвать PhotoAnalysisService
    3. Обработать результат или ошибки
    4. Отправить пользователю красивое сообщение
    5. Очистить сессию
    """
```

## User Sessions

Для хранения промежуточных данных используются сессии пользователей.

```python
class UserSession:
    photo_data: bytes | None = None
    latitude: float | None = None
    longitude: float | None = None
    
    def has_photo(self) -> bool
    def has_location(self) -> bool
    def is_ready(self) -> bool
    def clear(self) -> None
```

**Хранилище** (текущее):
```python
user_sessions: dict[int, UserSession] = {}
```

**TODO**: Использовать Redis для персистентности:
```python
from aiogram.fsm.storage.redis import RedisStorage
storage = RedisStorage(redis)
```

## Флоу пользователя

```
User opens bot
    ↓
/start command
    ↓
Bot sends welcome message
    ↓
User sends photo
    ↓
Bot: "✅ Фото получено! Отправь геолокацию"
Session: photo_data = <bytes>
    ↓
User sends location
    ↓
Bot: "⏳ Обрабатываю..."
Session: latitude, longitude = <coords>
    ↓
PhotoAnalysisService.process_photo()
    ↓
Bot: "✅ Анализ завершен! 🗑️ Тип: PLASTIC..."
Session.clear()
```

## Интеграция с PhotoAnalysisService

```python
from satwave.adapters.api.dependencies import get_photo_analysis_service

service = get_photo_analysis_service()

analysis = await service.process_photo(
    photo_data=session.photo_data,
    latitude=session.latitude,
    longitude=session.longitude,
)
```

**Преимущество**: Используется та же бизнес-логика, что и в API!

## Обработка ошибок

### InvalidLocationError

```python
try:
    analysis = await service.process_photo(...)
except InvalidLocationError as e:
    await message.answer(
        f"❌ Ошибка: Невалидные координаты\n\n{e}"
    )
```

### DuplicateLocationError

```python
except DuplicateLocationError:
    await message.answer(
        "⚠️ Эта локация уже была проанализирована ранее!\n\n"
        "Отправь фото из другого места."
    )
```

### PhotoProcessingError

```python
except PhotoProcessingError as e:
    await message.answer(f"❌ Ошибка обработки фото\n\n{e}")
```

### Общие ошибки

```python
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    await message.answer(
        "❌ Произошла ошибка. Попробуй еще раз."
    )
```

## Форматирование ответа

### Эмодзи для типов мусора

```python
waste_type_emoji = {
    "plastic": "🥤",
    "metal": "🔩",
    "paper": "📄",
    "glass": "🍾",
    "organic": "🍎",
    "textile": "👕",
    "electronics": "💻",
    "mixed": "♻️",
    "unknown": "❓",
}
```

### Красивое сообщение с результатом

```python
emoji = waste_type_emoji.get(analysis.get_dominant_waste_type().value, "♻️")

result_text = (
    f"✅ Анализ завершен!\n\n"
    f"🗑️ Тип мусора: {emoji} {analysis.get_dominant_waste_type().value.upper()}\n"
    f"📊 Найдено объектов: {len(analysis.detections)}\n"
    f"📍 Локация: {analysis.location.latitude:.6f}, {analysis.location.longitude:.6f}\n"
    f"🆔 ID анализа: `{analysis.id}`\n\n"
)

# Добавляем детали
if analysis.detections:
    result_text += "📋 Детали:\n"
    for detection in analysis.detections[:5]:
        det_emoji = waste_type_emoji.get(detection.waste_type.value, "•")
        result_text += (
            f"{det_emoji} {detection.waste_type.value}: "
            f"{detection.confidence:.0%}\n"
        )

await message.answer(result_text, parse_mode="Markdown")
```

## Конфигурация

### Settings

```python
class Settings(BaseSettings):
    telegram_bot_token: str = Field(
        default="YOUR_BOT_TOKEN_HERE",
        description="Telegram Bot API token",
    )
```

### Переменные окружения

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
LOG_LEVEL=INFO
```

## Запуск

### Локально

```bash
python -m satwave.adapters.bot.telegram_bot
```

### Docker

```yaml
# docker-compose.yml
services:
  bot:
    build: .
    command: python -m satwave.adapters.bot.telegram_bot
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    restart: unless-stopped
```

```bash
docker-compose up bot
```

## Логирование

```python
logger = logging.getLogger(__name__)

logger.info(f"User {user_id} uploaded photo ({len(photo_data)} bytes)")
logger.info(f"User {user_id} sent location: {lat}, {lon}")
logger.info(f"Analysis completed: {analysis.id}")
logger.error(f"Error during analysis: {e}")
```

## Мониторинг (TODO)

### Метрики

- Количество пользователей
- Количество анализов
- Время обработки
- Распределение типов мусора
- Ошибки и исключения

### Prometheus

```python
from prometheus_client import Counter, Histogram

photo_received = Counter('bot_photo_received_total', 'Photos received')
analysis_duration = Histogram('bot_analysis_duration_seconds', 'Analysis duration')

@photo_received.count()
async def handle_photo(...):
    ...
```

## Тестирование

### Unit тесты

```python
def test_user_session():
    session = UserSession()
    assert not session.is_ready()
    
    session.photo_data = b"test"
    assert not session.is_ready()
    
    session.latitude = 55.0
    session.longitude = 37.0
    assert session.is_ready()
```

### Integration тесты

```python
from aiogram.test_utils.mocked_bot import MockedBot

async def test_start_command():
    bot = MockedBot()
    # ...
```

## Расширения (TODO)

### Inline кнопки

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
    [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
])
```

### FSM (Finite State Machine)

```python
from aiogram.fsm.state import State, StatesGroup

class AnalysisStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_location = State()
    processing = State()
```

### Админ-панель

```python
ADMIN_USERS = [12345678]

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_USERS:
        return
    
    # Статистика, управление
```

### Мультиязычность

```python
from aiogram.utils.i18n import I18n

i18n = I18n(path="locales", default_locale="ru", domain="messages")
```

## Best Practices

1. **Асинхронность** - все операции async/await
2. **Обработка ошибок** - try/except для всех операций
3. **Логирование** - логировать важные события
4. **User-friendly** - понятные сообщения с эмодзи
5. **Безопасность** - не логировать токены и чувствительные данные

## См. также

- [Bot Setup](setup.md)
- [Quick Start](../../QUICK_START_BOT.md)
- [PhotoAnalysisService](../architecture/services.md)
- [Aiogram Docs](https://docs.aiogram.dev/)

