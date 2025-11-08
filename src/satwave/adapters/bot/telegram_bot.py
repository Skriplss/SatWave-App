"""Telegram bot для приема фото мусора."""

import asyncio
import logging
from typing import NoReturn

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from satwave.adapters.bot.handlers import router
from satwave.config.settings import Settings

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram бот для SatWave."""

    def __init__(self, settings: Settings) -> None:
        """
        Инициализация бота.
        
        Args:
            settings: Настройки приложения
        """
        self.settings = settings
        self.bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()
        
        # Подключаем роутеры
        self.dp.include_router(router)

    async def start(self) -> NoReturn:
        """Запустить бота."""
        logger.info("Starting Telegram bot...")
        
        # Удаляем вебхуки если были
        await self.bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем polling
        await self.dp.start_polling(self.bot)

    async def stop(self) -> None:
        """Остановить бота."""
        logger.info("Stopping Telegram bot...")
        await self.bot.session.close()


async def run_bot(settings: Settings) -> None:
    """
    Запустить бота.
    
    Args:
        settings: Настройки приложения
    """
    bot = TelegramBot(settings)
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.stop()


def main() -> None:
    """Entry point для запуска бота."""
    from satwave.config.settings import get_settings

    settings = get_settings()
    
    # Настройка логирования
    log_level = settings.log_level.upper()
    if settings.debug:
        log_level = "DEBUG"
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Логируем все сообщения от aiogram
    logging.getLogger("aiogram").setLevel(log_level)
    
    # Запуск бота
    asyncio.run(run_bot(settings))


if __name__ == "__main__":
    main()

