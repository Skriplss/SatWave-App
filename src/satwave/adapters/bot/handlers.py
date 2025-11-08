"""Telegram bot handlers для обработки сообщений."""

import logging
import re
from io import BytesIO

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message

from satwave.core.domain.exceptions import (
    DuplicateLocationError,
    InvalidLocationError,
    PhotoProcessingError,
)
from satwave.core.services.photo_analysis_service import PhotoAnalysisService

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start."""
    welcome_text = (
        "🛰️ Привет! Я бот SatWave.\n\n"
        "📸 Отправь мне фото мусора и геолокацию, "
        "и я проанализирую тип отходов!\n\n"
        "Как использовать:\n"
        "1️⃣ Отправь фото\n"
        "2️⃣ Отправь геолокацию (📍 Location в меню)\n\n"
        "Или используй команду /help для помощи."
    )
    await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help."""
    help_text = (
        "📖 Помощь:\n\n"
        "🔹 /start - Приветствие\n"
        "🔹 /help - Эта справка\n"
        "🔹 /stats - Статистика анализов (TODO)\n"
        "🔹 /reload - Перезагрузить модель\n"
        "🔹 /stop - Остановить бота (только для админов)\n\n"
        "📸 Отправка фото:\n"
        "• Отправь фото мусора\n"
        "• Добавь геолокацию в подписи или отдельным сообщением\n\n"
        "📍 Отправка геолокации:\n"
        "• Нажми на скрепку → Location\n"
        "• Выбери текущее местоположение\n\n"
        "⚠️ Важно: я запоминаю локации и не обрабатываю дубликаты!"
    )
    await message.answer(help_text)


@router.message(Command("reload"))
async def cmd_reload(message: Message) -> None:
    """Перезагрузить ML-модель и очистить кэш."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    logger.info(f"User {user_id} requested model reload")

    try:
        # Очищаем кэш компонентов
        import satwave.adapters.api.dependencies as deps
        
        # Если есть модель в памяти, выгружаем её
        if deps._waste_classifier_cache is not None:
            classifier = deps._waste_classifier_cache
            if hasattr(classifier, "_model") and classifier._model is not None:
                classifier._model = None
                classifier._is_ready = False
                logger.info("Model unloaded from memory")
        
        # Очищаем кэш классификатора
        deps._waste_classifier_cache = None

        await message.answer("✅ Кэш очищен. Модель будет перезагружена при следующем использовании")
        logger.info(f"Model reload requested by user {user_id}")

    except Exception as e:
        logger.exception(f"Error reloading model: {e}")
        await message.answer(f"❌ Ошибка при перезагрузке модели: {e}")


@router.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    """Остановить бота (только для админов)."""
    if not message.from_user:
        return

    user_id = message.from_user.id

    # Получаем список админов из настроек
    from satwave.config.settings import get_settings

    settings = get_settings()
    admin_ids_str = settings.telegram_admin_ids.strip()

    if admin_ids_str:
        try:
            admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip()]
        except ValueError:
            admin_ids = []
    else:
        admin_ids = []

    if admin_ids and user_id not in admin_ids:
        await message.answer("❌ У тебя нет прав для этой команды")
        logger.warning(f"User {user_id} tried to stop bot without admin rights")
        return

    logger.info(f"User {user_id} requested bot stop")
    await message.answer("🛑 Останавливаю бота...")

    # Останавливаем polling через dispatcher
    from aiogram import Bot
    bot = message.bot
    await bot.session.close()
    
    # Останавливаем процесс
    import sys
    import os
    os._exit(0)


class UserSession:
    """Сессия пользователя для хранения промежуточных данных."""

    def __init__(self) -> None:
        """Инициализация сессии."""
        self.photo_data: bytes | None = None
        self.latitude: float | None = None
        self.longitude: float | None = None

    def has_photo(self) -> bool:
        """Проверить, есть ли фото."""
        return self.photo_data is not None

    def has_location(self) -> bool:
        """Проверить, есть ли локация."""
        return self.latitude is not None and self.longitude is not None

    def is_ready(self) -> bool:
        """Проверить, готова ли сессия к обработке."""
        return self.has_photo() and self.has_location()

    def clear(self) -> None:
        """Очистить сессию."""
        self.photo_data = None
        self.latitude = None
        self.longitude = None


# In-memory хранилище сессий пользователей
# TODO: Заменить на Redis для продакшна
user_sessions: dict[int, UserSession] = {}


def get_user_session(user_id: int) -> UserSession:
    """Получить сессию пользователя."""
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession()
    return user_sessions[user_id]


@router.message(lambda message: message.photo is not None)
async def handle_photo(message: Message) -> None:
    """
    Обработчик фото.
    
    Сохраняет фото в сессии пользователя и ждет геолокацию.
    """
    if not message.from_user:
        logger.warning("Message without from_user in handle_photo")
        return

    user_id = message.from_user.id
    session = get_user_session(user_id)

    try:
        # Получаем фото самого большого размера
        photo = message.photo[-1]
        
        logger.info(f"User {user_id} sent photo, file_id: {photo.file_id}, size: {photo.file_size}")
        
        # Скачиваем файл
        bot = message.bot
        file = await bot.get_file(photo.file_id)
        photo_bytes = BytesIO()
        await bot.download_file(file.file_path, photo_bytes)
        
        session.photo_data = photo_bytes.getvalue()
        
        logger.info(f"User {user_id} uploaded photo ({len(session.photo_data)} bytes)")

        # Проверяем, есть ли уже локация
        if session.has_location():
            logger.info(f"User {user_id} has both photo and location, starting analysis")
            await process_analysis(message, session)
        else:
            logger.info(f"User {user_id} sent photo, waiting for location")
            await message.answer(
                "✅ Фото получено!\n\n"
                "📍 Теперь отправь геолокацию (нажми на скрепку → Location)"
            )
    except Exception as e:
        logger.exception(f"Error handling photo from user {user_id}: {e}")
        await message.answer(
            "❌ Ошибка при обработке фото. Попробуй отправить еще раз."
        )


@router.message(lambda message: message.location is not None)
async def handle_location(message: Message) -> None:
    """
    Обработчик геолокации.
    
    Сохраняет координаты в сессии пользователя и запускает анализ, если есть фото.
    """
    if not message.from_user:
        logger.warning("Message without from_user in handle_location")
        return
    
    if not message.location:
        logger.warning("Message with None location")
        return

    user_id = message.from_user.id
    session = get_user_session(user_id)

    try:
        session.latitude = message.location.latitude
        session.longitude = message.location.longitude

        logger.info(f"User {user_id} sent location: {session.latitude}, {session.longitude}")

        # Проверяем, есть ли уже фото
        if session.has_photo():
            logger.info(f"User {user_id} has both photo and location, starting analysis")
            await process_analysis(message, session)
        else:
            logger.info(f"User {user_id} sent location, waiting for photo")
            await message.answer(
                f"✅ Локация получена!\n"
                f"📍 {session.latitude}, {session.longitude}\n\n"
                f"📸 Теперь отправь фото мусора"
            )
    except Exception as e:
        logger.exception(f"Error handling location from user {user_id}: {e}")
        await message.answer(
            "❌ Ошибка при обработке геолокации. Попробуй отправить еще раз."
        )


async def process_analysis(message: Message, session: UserSession) -> None:
    """
    Обработать анализ фото.
    
    Args:
        message: Telegram сообщение
        session: Сессия пользователя с фото и локацией
    """
    if not session.is_ready() or not message.from_user:
        logger.warning("Session not ready or no user")
        return

    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("⏳ Обрабатываю фото...")

    try:
        # Получаем сервис через dependency injection
        from satwave.adapters.api.dependencies import get_photo_analysis_service

        logger.info("Getting photo analysis service...")
        service = get_photo_analysis_service()
        logger.info("Service obtained successfully")

        # Запускаем анализ
        logger.info(
            f"Starting analysis for user {message.from_user.id}, "
            f"photo size: {len(session.photo_data)} bytes, "
            f"location: {session.latitude}, {session.longitude}"
        )
        analysis = await service.process_photo(
            photo_data=session.photo_data,  # type: ignore
            latitude=session.latitude,  # type: ignore
            longitude=session.longitude,  # type: ignore
        )

        # Формируем красивый ответ
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

        emoji = waste_type_emoji.get(analysis.get_dominant_waste_type().value, "♻️")

        result_text = (
            f"✅ Анализ завершен!\n\n"
            f"🗑️ Тип мусора: {emoji} {analysis.get_dominant_waste_type().value.upper()}\n"
            f"📊 Найдено объектов: {len(analysis.detections)}\n"
            f"📍 Локация: {analysis.location.latitude:.6f}, {analysis.location.longitude:.6f}\n"
            f"🆔 ID анализа: `{analysis.id}`\n\n"
        )

        # Детали по каждой детекции
        if analysis.detections:
            result_text += "📋 Детали:\n"
            for i, detection in enumerate(analysis.detections[:5], 1):  # Показываем максимум 5
                det_emoji = waste_type_emoji.get(detection.waste_type.value, "•")
                result_text += (
                    f"{det_emoji} {detection.waste_type.value}: "
                    f"{detection.confidence:.0%}\n"
                )

        await processing_msg.edit_text(result_text, parse_mode="Markdown")

        # Очищаем сессию
        session.clear()

        logger.info(f"Analysis completed for user {message.from_user.id}: {analysis.id}")

    except InvalidLocationError as e:
        await processing_msg.edit_text(
            f"❌ Ошибка: Невалидные координаты\n\n{e}"
        )
        session.clear()

    except DuplicateLocationError:
        await processing_msg.edit_text(
            "⚠️ Эта локация уже была проанализирована ранее!\n\n"
            "Отправь фото из другого места."
        )
        session.clear()

    except PhotoProcessingError as e:
        await processing_msg.edit_text(
            f"❌ Ошибка обработки фото\n\n{e}"
        )
        session.clear()

    except Exception as e:
        logger.exception(f"Unexpected error during analysis: {e}")
        error_details = str(e)
        await processing_msg.edit_text(
            f"❌ Произошла ошибка при обработке.\n\n"
            f"Детали: {error_details}\n\n"
            f"Попробуй еще раз или используй /help"
        )
        session.clear()


def parse_coordinates_from_text(text: str) -> tuple[float, float] | None:
    """
    Парсить координаты из текста.
    
    Поддерживает:
    - Google Maps URL: https://maps.google.com/maps?q=48.033134,23.381406
    - Прямые координаты: 48.033134, 23.381406
    - Координаты в скобках: (48.033134, 23.381406)
    
    Returns:
        (latitude, longitude) или None если не найдено
    """
    if not text:
        return None
    
    # Парсим Google Maps URL
    google_maps_pattern = r'maps\.google\.com.*[?&]q=([+-]?\d+\.?\d*),([+-]?\d+\.?\d*)'
    match = re.search(google_maps_pattern, text)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            logger.info(f"Parsed coordinates from Google Maps URL: {lat}, {lon}")
            return (lat, lon)
        except ValueError:
            pass
    
    # Парсим прямые координаты (lat, lon или lat,lon)
    coord_pattern = r'([+-]?\d+\.?\d*)[,\s]+([+-]?\d+\.?\d*)'
    match = re.search(coord_pattern, text)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            # Проверяем, что это похоже на координаты (широта -90..90, долгота -180..180)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                logger.info(f"Parsed coordinates from text: {lat}, {lon}")
                return (lat, lon)
        except ValueError:
            pass
    
    return None


@router.message(lambda message: message.text and not message.text.startswith("/"))
async def handle_text_with_coordinates(message: Message) -> None:
    """Обработчик текстовых сообщений с координатами."""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    text = message.text or ""
    
    # Пытаемся распарсить координаты из текста
    coords = parse_coordinates_from_text(text)
    
    if coords:
        # Нашли координаты в тексте!
        latitude, longitude = coords
        session = get_user_session(user_id)
        
        try:
            session.latitude = latitude
            session.longitude = longitude
            
            logger.info(f"User {user_id} sent coordinates in text: {latitude}, {longitude}")
            
            # Проверяем, есть ли уже фото
            if session.has_photo():
                logger.info(f"User {user_id} has both photo and location from text, starting analysis")
                await process_analysis(message, session)
            else:
                logger.info(f"User {user_id} sent location from text, waiting for photo")
                await message.answer(
                    f"✅ Локация получена!\n"
                    f"📍 {latitude}, {longitude}\n\n"
                    f"📸 Теперь отправь фото мусора"
                )
        except Exception as e:
            logger.exception(f"Error handling coordinates from text: {e}")
            await message.answer(
                "❌ Ошибка при обработке координат. Попробуй отправить геолокацию через кнопку Location."
            )
    else:
        # Не нашли координаты - это обычный текст
        logger.debug(f"User {user_id} sent text without coordinates: {text[:50]}")
        await message.answer(
            "🤔 Я понимаю только фото и геолокацию.\n\n"
            "Отправь геолокацию через кнопку Location (📍) или используй /help для помощи."
        )


@router.message()
async def handle_other(message: Message) -> None:
    """Обработчик всех остальных сообщений."""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    
    # Логируем, что пришло
    logger.debug(
        f"User {user_id} sent unknown message type: "
        f"text={message.text}, photo={message.photo is not None}, "
        f"location={message.location is not None}, document={message.document is not None}"
    )
    
    # Если это команда, но не обработана
    if message.text and message.text.startswith("/"):
        logger.warning(f"Unhandled command from user {user_id}: {message.text}")
        await message.answer(
            "🤔 Неизвестная команда.\n\n"
            "Используй /help для помощи."
        )
    else:
        # Другой тип сообщения (стикер, документ и т.д.)
        await message.answer(
            "🤔 Я понимаю только фото и геолокацию.\n\n"
            "Используй /help для помощи."
        )

