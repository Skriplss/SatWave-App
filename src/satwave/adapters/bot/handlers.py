"""Telegram bot handlers for message processing."""

import logging
import re
from io import BytesIO

from PIL import Image
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


def validate_image(photo_data: bytes) -> tuple[bool, str]:
    """
    Validate image before processing.
    
    Checks:
    - File type (must be an image)
    - Minimum image size
    - Aspect ratio
    - File size
    
    Args:
        photo_data: Binary image data
        
    Returns:
        Tuple[bool, str]: (is image valid, error message)
    """
    try:
        # Check file size (minimum 1KB, maximum 20MB)
        if len(photo_data) < 1024:
            return False, "File is too small. Please send a full photo."
        
        if len(photo_data) > 20 * 1024 * 1024:
            return False, "File is too large. Maximum size: 20MB."
        
        # Try to open image
        try:
            image = Image.open(BytesIO(photo_data))
        except Exception as e:
            logger.warning(f"Failed to open image: {e}")
            return False, "This is not an image. Please send a photo in JPEG or PNG format."
        
        # Check format (must be JPEG, PNG, WebP)
        if image.format not in ("JPEG", "PNG", "WEBP"):
            return False, f"Unsupported format: {image.format}. Please use JPEG or PNG."
        
        # Check image size (minimum 100x100 pixels)
        width, height = image.size
        min_size = 100
        if width < min_size or height < min_size:
            return False, (
                f"Image is too small ({width}x{height}). "
                f"Minimum size: {min_size}x{min_size} pixels."
            )
        
        # Check aspect ratio (should not be too extreme)
        # For example, not 1:10 or 10:1 (might be file icon or preview)
        aspect_ratio = width / height if height > 0 else 0
        max_aspect_ratio = 10.0
        min_aspect_ratio = 0.1
        
        if aspect_ratio > max_aspect_ratio or aspect_ratio < min_aspect_ratio:
            return False, (
                f"Strange aspect ratio ({width}x{height}). "
                "This might be a file preview, not a photo. Please send a full photo."
            )
        
        # Check that this is not too small image (might be icon)
        # Minimum area: 10,000 pixels (100x100)
        min_area = 10000
        area = width * height
        if area < min_area:
            return False, (
                f"Image is too small (area: {area} pixels). "
                f"Minimum area: {min_area} pixels."
            )
        
        logger.info(
            f"Image validated: {width}x{height}, format={image.format}, "
            f"size={len(photo_data)} bytes, aspect_ratio={aspect_ratio:.2f}"
        )
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Error validating image: {e}")
        return False, f"Error checking image: {str(e)}"


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Handler for /start command."""
    welcome_text = (
        "🛰️ Hello! I'm SatWave bot.\n\n"
        "📸 Send me a photo of waste and geolocation, "
        "and I'll analyze the waste type!\n\n"
        "How to use:\n"
        "1️⃣ Send a photo\n"
        "2️⃣ Send geolocation (📍 Location in menu)\n\n"
        "Or use /help for help."
    )
    await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handler for /help command."""
    help_text = (
        "📖 Help:\n\n"
        "🔹 /start - Welcome message\n"
        "🔹 /help - This help\n"
        "🔹 /stats - Analysis statistics (TODO)\n"
        "🔹 /reload - Reload model\n"
        "🔹 /stop - Stop bot (admin only)\n\n"
        "📸 Sending photos:\n"
        "• Send a photo of waste\n"
        "• Add geolocation in caption or as separate message\n\n"
        "📍 Sending geolocation:\n"
        "• Click on paperclip → Location\n"
        "• Select current location\n\n"
        "⚠️ Important: I remember locations and don't process duplicates!"
    )
    await message.answer(help_text)


@router.message(Command("reload"))
async def cmd_reload(message: Message) -> None:
    """Reload ML model and clear cache."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    logger.info(f"User {user_id} requested model reload")

    try:
        # Clear component cache
        import satwave.adapters.api.dependencies as deps
        
        # If model is in memory, unload it
        if deps._waste_classifier_cache is not None:
            classifier = deps._waste_classifier_cache
            if hasattr(classifier, "_model") and classifier._model is not None:
                classifier._model = None
                classifier._is_ready = False
                logger.info("Model unloaded from memory")
        
        # Clear classifier cache
        deps._waste_classifier_cache = None

        await message.answer("✅ Cache cleared. Model will be reloaded on next use")
        logger.info(f"Model reload requested by user {user_id}")

    except Exception as e:
        logger.exception(f"Error reloading model: {e}")
        await message.answer(f"❌ Error reloading model: {e}")


@router.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    """Stop bot (admin only)."""
    if not message.from_user:
        return

    user_id = message.from_user.id

    # Get admin list from settings
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
        await message.answer("❌ You don't have permission for this command")
        logger.warning(f"User {user_id} tried to stop bot without admin rights")
        return

    logger.info(f"User {user_id} requested bot stop")
    await message.answer("🛑 Stopping bot...")

    # Stop polling via dispatcher
    from aiogram import Bot
    bot = message.bot
    await bot.session.close()
    
    # Stop process
    import sys
    import os
    os._exit(0)


class UserSession:
    """User session for storing intermediate data."""

    def __init__(self) -> None:
        """Initialize session."""
        self.photo_data: bytes | None = None
        self.latitude: float | None = None
        self.longitude: float | None = None

    def has_photo(self) -> bool:
        """Check if photo exists."""
        return self.photo_data is not None

    def has_location(self) -> bool:
        """Check if location exists."""
        return self.latitude is not None and self.longitude is not None

    def is_ready(self) -> bool:
        """Check if session is ready for processing."""
        return self.has_photo() and self.has_location()

    def clear(self) -> None:
        """Clear session."""
        self.photo_data = None
        self.latitude = None
        self.longitude = None


# In-memory storage for user sessions
# TODO: Replace with Redis for production
user_sessions: dict[int, UserSession] = {}


def get_user_session(user_id: int) -> UserSession:
    """Get user session."""
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession()
    return user_sessions[user_id]


@router.message(lambda message: message.photo is not None)
async def handle_photo(message: Message) -> None:
    """
    Photo handler.
    
    Saves photo in user session and waits for geolocation.
    """
    if not message.from_user:
        logger.warning("Message without from_user in handle_photo")
        return

    user_id = message.from_user.id
    session = get_user_session(user_id)

    try:
        # Get largest photo size
        photo = message.photo[-1]
        
        logger.info(f"User {user_id} sent photo, file_id: {photo.file_id}, size: {photo.file_size}")
        
        # Download file
        bot = message.bot
        file = await bot.get_file(photo.file_id)
        photo_bytes = BytesIO()
        await bot.download_file(file.file_path, photo_bytes)
        
        photo_data = photo_bytes.getvalue()
        
        logger.info(f"User {user_id} uploaded photo ({len(photo_data)} bytes)")
        
        # Validate image
        is_valid, error_message = validate_image(photo_data)
        if not is_valid:
            logger.warning(f"User {user_id} sent invalid image: {error_message}")
            await message.answer(
                f"❌ {error_message}\n\n"
                "📸 Please send a full photo of waste (not a file preview or icon)."
            )
            return
        
        # Save valid image
        session.photo_data = photo_data

        # Check if location already exists
        if session.has_location():
            logger.info(f"User {user_id} has both photo and location, starting analysis")
            await process_analysis(message, session)
        else:
            logger.info(f"User {user_id} sent photo, waiting for location")
            await message.answer(
                "✅ Photo received!\n\n"
                "📍 Now send geolocation (click on paperclip → Location)"
            )
    except Exception as e:
        logger.exception(f"Error handling photo from user {user_id}: {e}")
        await message.answer(
            "❌ Error processing photo. Please try again."
        )


@router.message(lambda message: message.location is not None)
async def handle_location(message: Message) -> None:
    """
    Geolocation handler.
    
    Saves coordinates in user session and starts analysis if photo exists.
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

        # Check if photo already exists
        if session.has_photo():
            logger.info(f"User {user_id} has both photo and location, starting analysis")
            await process_analysis(message, session)
        else:
            logger.info(f"User {user_id} sent location, waiting for photo")
            await message.answer(
                f"✅ Location received!\n"
                f"📍 {session.latitude}, {session.longitude}\n\n"
                f"📸 Now send a photo of waste"
            )
    except Exception as e:
        logger.exception(f"Error handling location from user {user_id}: {e}")
        await message.answer(
            "❌ Error processing geolocation. Please try again."
        )


async def process_analysis(message: Message, session: UserSession) -> None:
    """
    Process photo analysis.
    
    Args:
        message: Telegram message
        session: User session with photo and location
    """
    if not session.is_ready() or not message.from_user:
        logger.warning("Session not ready or no user")
        return

    # Send processing message
    processing_msg = await message.answer("⏳ Processing photo...")

    try:
        # Get service via dependency injection
        from satwave.adapters.api.dependencies import get_photo_analysis_service

        logger.info("Getting photo analysis service...")
        service = get_photo_analysis_service()
        logger.info("Service obtained successfully")

        # Start analysis
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

        # Format response
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
            "hazardous_waste": "☢️",
            "household_waste": "🏠",
            "waste_separation_facilities": "♻️",
            "mixed_waste": "♻️",
            "construction_waste": "🏗️",
        }

        emoji = waste_type_emoji.get(analysis.get_dominant_waste_type().value, "♻️")

        result_text = (
            f"✅ Analysis completed!\n\n"
            f"🗑️ Waste type: {emoji} {analysis.get_dominant_waste_type().value.upper()}\n"
            f"📊 Objects found: {len(analysis.detections)}\n"
            f"📍 Location: {analysis.location.latitude:.6f}, {analysis.location.longitude:.6f}\n"
            f"🆔 Analysis ID: `{analysis.id}`\n\n"
        )

        # Details for each detection
        if analysis.detections:
            result_text += "📋 Details:\n"
            for i, detection in enumerate(analysis.detections[:5], 1):  # Show max 5
                det_emoji = waste_type_emoji.get(detection.waste_type.value, "•")
                result_text += (
                    f"{det_emoji} {detection.waste_type.value}: "
                    f"{detection.confidence:.0%}\n"
                )

        await processing_msg.edit_text(result_text, parse_mode="Markdown")

        # Clear session
        session.clear()

        logger.info(f"Analysis completed for user {message.from_user.id}: {analysis.id}")

    except InvalidLocationError as e:
        await processing_msg.edit_text(
            f"❌ Error: Invalid coordinates\n\n{e}"
        )
        session.clear()

    except DuplicateLocationError:
        await processing_msg.edit_text(
            "⚠️ This location was already analyzed!\n\n"
            "Send a photo from a different location."
        )
        session.clear()

    except PhotoProcessingError as e:
        await processing_msg.edit_text(
            f"❌ Photo processing error\n\n{e}"
        )
        session.clear()

    except Exception as e:
        logger.exception(f"Unexpected error during analysis: {e}")
        error_details = str(e)
        await processing_msg.edit_text(
            f"❌ An error occurred during processing.\n\n"
            f"Details: {error_details}\n\n"
            f"Please try again or use /help"
        )
        session.clear()


def parse_coordinates_from_text(text: str) -> tuple[float, float] | None:
    """
    Parse coordinates from text.
    
    Supports:
    - Google Maps URL: https://maps.google.com/maps?q=48.033134,23.381406
    - Direct coordinates: 48.033134, 23.381406
    - Coordinates in brackets: (48.033134, 23.381406)
    
    Returns:
        (latitude, longitude) or None if not found
    """
    if not text:
        return None
    
    # Parse Google Maps URL
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
    
    # Parse direct coordinates (lat, lon or lat,lon)
    coord_pattern = r'([+-]?\d+\.?\d*)[,\s]+([+-]?\d+\.?\d*)'
    match = re.search(coord_pattern, text)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            # Check if this looks like coordinates (latitude -90..90, longitude -180..180)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                logger.info(f"Parsed coordinates from text: {lat}, {lon}")
                return (lat, lon)
        except ValueError:
            pass
    
    return None


@router.message(lambda message: message.text and not message.text.startswith("/"))
async def handle_text_with_coordinates(message: Message) -> None:
    """Handler for text messages with coordinates."""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    text = message.text or ""
    
    # Try to parse coordinates from text
    coords = parse_coordinates_from_text(text)
    
    if coords:
        # Found coordinates in text!
        latitude, longitude = coords
        session = get_user_session(user_id)
        
        try:
            session.latitude = latitude
            session.longitude = longitude
            
            logger.info(f"User {user_id} sent coordinates in text: {latitude}, {longitude}")
            
            # Check if photo already exists
            if session.has_photo():
                logger.info(f"User {user_id} has both photo and location from text, starting analysis")
                await process_analysis(message, session)
            else:
                logger.info(f"User {user_id} sent location from text, waiting for photo")
                await message.answer(
                    f"✅ Location received!\n"
                    f"📍 {latitude}, {longitude}\n\n"
                    f"📸 Now send a photo of waste"
                )
        except Exception as e:
            logger.exception(f"Error handling coordinates from text: {e}")
            await message.answer(
                "❌ Error processing coordinates. Please send geolocation via Location button."
            )
    else:
        # Didn't find coordinates - this is regular text
        logger.debug(f"User {user_id} sent text without coordinates: {text[:50]}")
        await message.answer(
            "🤔 I only understand photos and geolocation.\n\n"
            "Send geolocation via Location button (📍) or use /help for help."
        )


@router.message()
async def handle_other(message: Message) -> None:
    """Handler for all other messages."""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    
    # Log what came in
    logger.debug(
        f"User {user_id} sent unknown message type: "
        f"text={message.text}, photo={message.photo is not None}, "
        f"location={message.location is not None}, document={message.document is not None}"
    )
    
    # If this is a command but not handled
    if message.text and message.text.startswith("/"):
        logger.warning(f"Unhandled command from user {user_id}: {message.text}")
        await message.answer(
            "🤔 Unknown command.\n\n"
            "Use /help for help."
        )
    else:
        # Other message type (sticker, document, etc.)
        await message.answer(
            "🤔 I only understand photos and geolocation.\n\n"
            "Use /help for help."
        )
