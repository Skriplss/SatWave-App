"""Конфигурация приложения через pydantic settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Основные настройки
    app_name: str = "SatWave"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, description="Debug режим")
    
    # API настройки
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    
    # Telegram Bot
    telegram_bot_token: str = Field(
        default="YOUR_BOT_TOKEN_HERE",
        description="Telegram Bot API token from @BotFather",
    )
    telegram_admin_ids: str = Field(
        default="",
        description="Telegram user IDs администраторов (через запятую)",
    )
    
    # База данных
    database_url: str = Field(
        default="postgresql+asyncpg://satwave:satwave@localhost:5432/satwave",
        description="PostgreSQL connection URL",
    )
    
    # Хранилище фото
    photo_storage_type: str = Field(
        default="stub", description="Тип хранилища: stub, local, s3"
    )
    photo_storage_base_url: str = Field(
        default="http://localhost:8000/photos",
        description="Базовый URL для фото",
    )
    photo_storage_path: str = Field(
        default="./data/photos",
        description="Путь для локального хранилища",
    )
    
    # ML модель
    ml_model_type: str = Field(
        default="stub", description="Тип модели: stub, yolo, roboflow_inference, detectron2"
    )
    ml_model_path: str = Field(
        default="./models/yolov12n.pt",
        description="Путь к весам модели (YOLOv12n или путь к скачанной модели)",
    )
    ml_model_confidence_threshold: float = Field(
        default=0.25, description="Порог confidence для детекций"
    )
    # Roboflow настройки (для скачивания модели)
    roboflow_api_key: str = Field(
        default="",
        description="Roboflow API ключ (опционально, для скачивания модели)",
    )
    roboflow_workspace: str = Field(
        default="asts31",
        description="Roboflow workspace (для модели Trash Sorter)",
    )
    roboflow_project: str = Field(
        default="trash-sorter-all-classes",
        description="Roboflow project name",
    )
    roboflow_version: int = Field(
        default=1,
        description="Roboflow model version",
    )
    # Roboflow Inference API настройки
    roboflow_inference_model_id: str = Field(
        default="trash-sorter-all-classes/4",
        description="Roboflow Inference API model ID (формат: project/version)",
    )
    roboflow_inference_api_url: str = Field(
        default="https://serverless.roboflow.com",
        description="Roboflow Inference API URL",
    )
    
    # Дедупликация
    duplicate_check_threshold_meters: float = Field(
        default=50.0,
        description="Порог расстояния для проверки дубликатов (метры)",
    )
    
    # Логирование
    log_level: str = Field(default="INFO", description="Уровень логирования")


def get_settings() -> Settings:
    """Получить настройки приложения."""
    return Settings()

