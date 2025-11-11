"""Application configuration via pydantic settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Main settings
    app_name: str = "SatWave"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, description="Debug mode")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    
    # Telegram Bot
    telegram_bot_token: str = Field(
        default="YOUR_BOT_TOKEN_HERE",
        description="Telegram Bot API token from @BotFather",
    )
    telegram_admin_ids: str = Field(
        default="",
        description="Telegram user IDs of administrators (comma-separated)",
    )
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://satwave:satwave@localhost:5432/satwave",
        description="PostgreSQL connection URL",
    )
    
    # Photo storage
    photo_storage_type: str = Field(
        default="stub", description="Storage type: stub, local, s3"
    )
    photo_storage_base_url: str = Field(
        default="http://localhost:8000/photos",
        description="Base URL for photos",
    )
    photo_storage_path: str = Field(
        default="./data/photos",
        description="Path for local storage",
    )
    
    # ML model
    ml_model_type: str = Field(
        default="stub",
        description="Model type: stub, yolo (Waste-Classification-using-YOLOv8), roboflow_inference, detectron2",
    )
    ml_model_path: str = Field(
        default="./models/waste-classification-yolov8.pt",
        description="Path to YOLOv8 model weights (e.g., Waste-Classification-using-YOLOv8 model from teamsmcorg)",
    )
    ml_model_confidence_threshold: float = Field(
        default=0.25, description="Confidence threshold for detections"
    )
    # Roboflow settings (for downloading model)
    roboflow_api_key: str = Field(
        default="",
        description="Roboflow API key (optional, for downloading model)",
    )
    roboflow_workspace: str = Field(
        default="asts31",
        description="Roboflow workspace (for Trash Sorter model)",
    )
    roboflow_project: str = Field(
        default="trash-sorter-all-classes",
        description="Roboflow project name",
    )
    roboflow_version: int = Field(
        default=1,
        description="Roboflow model version",
    )
    # Roboflow Inference API settings
    roboflow_inference_model_id: str = Field(
        default="trash-sorter-all-classes/4",
        description="Roboflow Inference API model ID (format: project/version)",
    )
    roboflow_inference_api_url: str = Field(
        default="https://serverless.roboflow.com",
        description="Roboflow Inference API URL",
    )
    
    # Deduplication
    duplicate_check_threshold_meters: float = Field(
        default=50.0,
        description="Distance threshold for duplicate check (meters)",
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Supabase настройки
    supabase_url: str = Field(
        default="",
        description="Supabase project URL (https://<ref>.supabase.co)",
    )
    supabase_anon_key: str = Field(
        default="",
        description="Supabase anon public key (для клиента)",
    )
    supabase_service_role_key: str = Field(
        default="",
        description="Supabase service role key (использовать только на бэкенде)",
    )
    supabase_jwks_url: str = Field(
        default="",
        description="Supabase JWKS URL (обычно https://<ref>.supabase.co/auth/v1/jwks)",
    )

    # SMTP (отправка почты)
    smtp_host: str = Field(default="", description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port (обычно 587)")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password / API key")
    smtp_from: str = Field(default="", description="From email, например no-reply@example.com")


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()

