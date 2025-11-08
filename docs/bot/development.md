# 🛠️ Разработка Telegram бота

## Архитектура бота

### Структура файлов

```
src/satwave/adapters/bot/
├── __init__.py
├── telegram_bot.py     # Основной класс TelegramBot
└── handlers.py         # Обработчики сообщений и команд
```

### Компоненты

#### telegram_bot.py

```python
class TelegramBot:
    """Главный класс бота."""
    
    def __init__(self, settings: Settings):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.dp = Dispatcher()
        self.dp.include_router(router)  # Подключаем handlers
    
    async def start(self) -> NoReturn:
        """Запуск polling."""
        await self.dp.start_polling(self.bot)
    
    async def stop(self) -> None:
        """Остановка бота."""
        await self.bot.session.close()
```

#### handlers.py

```python
router = Router()  # Aiogram Router

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик /start."""
    ...

@router.message(lambda m: m.photo is not None)
async def handle_photo(message: Message):
    """Обработчик фото."""
    ...

@router.message(lambda m: m.location is not None)
async def handle_location(message: Message):
    """Обработчик геолокации."""
    ...
```

### UserSession

Для хранения промежуточных данных пользователя:

```python
class UserSession:
    photo_data: bytes | None = None
    latitude: float | None = None
    longitude: float | None = None
    
    def is_ready(self) -> bool:
        return self.has_photo() and self.has_location()

# In-memory хранилище (TODO: заменить на Redis)
user_sessions: dict[int, UserSession] = {}
```

## Добавление новых команд

### Простая команда

```python
@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Показать статистику пользователя."""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    
    # Получаем статистику из БД
    # stats = await get_user_stats(user_id)
    
    await message.answer(
        f"📊 Твоя статистика:\n\n"
        f"Отправлено фото: ?\n"
        f"Проанализировано: ?"
    )
```

### Команда с аргументами

```python
@router.message(Command("search"))
async def cmd_search(message: Message) -> None:
    """Поиск анализов по типу мусора."""
    # Извлекаем аргументы
    args = message.text.split()[1:] if message.text else []
    
    if not args:
        await message.answer("Использование: /search <тип_мусора>")
        return
    
    waste_type = args[0].lower()
    # Поиск в БД...
```

## Middleware

### Chat Action (показывает "typing...")

```python
from aiogram.utils.chat_action import ChatActionMiddleware

dp.message.middleware(ChatActionMiddleware())
```

### Rate Limiting

```python
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 5):
        self.rate_limit = rate_limit
        self.user_requests: Dict[int, int] = {}
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        
        # Проверка лимита
        if self.user_requests.get(user_id, 0) >= self.rate_limit:
            await event.answer("⚠️ Слишком много запросов. Подожди немного.")
            return
        
        self.user_requests[user_id] = self.user_requests.get(user_id, 0) + 1
        return await handler(event, data)

# Подключение
dp.message.middleware(RateLimitMiddleware(rate_limit=10))
```

## Работа с кнопками

### Inline кнопки

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@router.message(Command("menu"))
async def show_menu(message: Message) -> None:
    """Показать меню с кнопками."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="📜 История", callback_data="history")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ])
    
    await message.answer("Выбери действие:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "stats")
async def process_stats_callback(callback: CallbackQuery) -> None:
    """Обработка нажатия кнопки."""
    await callback.answer()  # Убрать "часики"
    await callback.message.answer("📊 Твоя статистика...")
```

### Reply кнопки

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить локацию", request_location=True)],
            [KeyboardButton(text="📸 Отправить фото")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    
    await message.answer("Привет! Выбери действие:", reply_markup=keyboard)
```

## Интеграция с сервисами

### Dependency Injection

Текущая реализация:

```python
from satwave.adapters.api.dependencies import get_photo_analysis_service

service = get_photo_analysis_service()
analysis = await service.process_photo(...)
```

### Улучшенный вариант (через контекст)

```python
# В telegram_bot.py
async def lifespan():
    # Setup
    service = get_photo_analysis_service()
    dp["photo_service"] = service
    
    yield
    
    # Cleanup
    ...

# В handlers.py
@router.message(lambda m: m.photo)
async def handle_photo(message: Message, photo_service: PhotoAnalysisService):
    analysis = await photo_service.process_photo(...)
```

## Работа с файлами

### Скачивание фото

```python
from io import BytesIO

@router.message(lambda m: m.photo)
async def handle_photo(message: Message):
    # Получаем самое большое фото
    photo = message.photo[-1]
    
    # Скачиваем
    bot = message.bot
    file = await bot.get_file(photo.file_id)
    
    photo_bytes = BytesIO()
    await bot.download_file(file.file_path, photo_bytes)
    
    photo_data = photo_bytes.getvalue()
    # Обработка...
```

### Отправка файлов

```python
from aiogram.types import FSInputFile, BufferedInputFile

# Из файловой системы
photo = FSInputFile("path/to/photo.jpg")
await message.answer_photo(photo, caption="Результат анализа")

# Из памяти
photo_bytes = b"..."  # Бинарные данные
photo = BufferedInputFile(photo_bytes, filename="result.jpg")
await message.answer_photo(photo)
```

## Тестирование

### Unit тесты для handlers

```python
import pytest
from aiogram.types import Message, User
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_cmd_start():
    """Тест команды /start."""
    # Создаем mock объекты
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.answer = AsyncMock()
    
    # Вызываем handler
    await cmd_start(message)
    
    # Проверяем
    message.answer.assert_called_once()
    assert "Привет" in message.answer.call_args[0][0]
```

### Integration тесты

```python
from aiogram.methods import SendMessage
from aiogram.client.session.base import BaseSession

class MockSession(BaseSession):
    """Mock для Telegram API."""
    
    async def make_request(self, bot, method, data):
        if isinstance(method, SendMessage):
            return {"ok": True, "result": {"message_id": 1}}

@pytest.fixture
async def bot():
    """Фикстура для тестового бота."""
    return Bot(token="TEST_TOKEN", session=MockSession())
```

## Логирование

### Настройка логов

```python
import logging

logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    logger.info(f"User {message.from_user.id} started bot")
    ...
```

### Структурное логирование

```python
import structlog

logger = structlog.get_logger()

@router.message(lambda m: m.photo)
async def handle_photo(message: Message):
    logger.info(
        "photo_received",
        user_id=message.from_user.id,
        photo_size=len(photo_data),
        has_location=session.has_location()
    )
```

## Продакшн настройки

### Webhook вместо Polling

```python
from aiohttp import web

async def webhook_handler(request):
    """Обработчик webhook от Telegram."""
    data = await request.json()
    await dp.feed_update(bot, Update(**data))
    return web.Response()

async def start_webhook():
    """Запуск webhook."""
    await bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook/telegram",
        secret_token=SECRET_TOKEN
    )
    
    app = web.Application()
    app.router.add_post("/webhook/telegram", webhook_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
```

### Redis для сессий

```python
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

redis = Redis(host="localhost", port=6379)
storage = RedisStorage(redis)
dp = Dispatcher(storage=storage)
```

### Graceful Shutdown

```python
import signal
import asyncio

async def shutdown(signal, loop, bot):
    """Корректная остановка."""
    logger.info(f"Received exit signal {signal.name}...")
    
    # Останавливаем бота
    await bot.session.close()
    
    # Завершаем задачи
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

# В main()
loop = asyncio.get_event_loop()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(
        sig,
        lambda s=sig: asyncio.create_task(shutdown(s, loop, bot))
    )
```

## Best Practices

### 1. Асинхронность

```python
# ❌ Плохо - блокирующий вызов
def process_photo(data):
    time.sleep(5)  # Блокирует event loop

# ✅ Хорошо - асинхронный вызов
async def process_photo(data):
    await asyncio.sleep(5)  # Не блокирует
```

### 2. Обработка ошибок

```python
@router.message(Command("analyze"))
async def cmd_analyze(message: Message):
    try:
        result = await service.process_photo(...)
        await message.answer(f"Результат: {result}")
    except InvalidLocationError as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.warning(f"Invalid location: {e}")
    except Exception as e:
        await message.answer("❌ Произошла ошибка")
        logger.exception(f"Unexpected error: {e}")
```

### 3. Валидация данных

```python
from pydantic import BaseModel, validator

class AnalysisRequest(BaseModel):
    photo_data: bytes
    latitude: float
    longitude: float
    
    @validator("latitude")
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("Invalid latitude")
        return v
```

### 4. Документация

```python
@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """
    Показать статистику пользователя.
    
    Отображает:
    - Количество отправленных фото
    - Количество проанализированных локаций
    - Распределение по типам мусора
    
    Args:
        message: Входящее сообщение от пользователя
    """
    ...
```

## См. также

- [Настройка бота](setup.md)
- [Пользовательские сценарии](user-flows.md)
- [Clean Architecture](../architecture/clean-architecture.md)
- [Aiogram Documentation](https://docs.aiogram.dev/)

