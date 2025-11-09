"""FastAPI приложение."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from satwave.adapters.api.webhook import router as webhook_router
from satwave.adapters.api.auth import router as auth_router
from satwave.adapters.api.coupons import router as coupons_router
from satwave.config.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle events для приложения."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Startup
    # TODO: Инициализация БД, ML-моделей и т.д.
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """Создать FastAPI приложение."""
    settings = get_settings()
    
    # Настройка логирования
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Платформа для обнаружения, классификации и коммерциализации вторсырья",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Настроить правильные origins для продакшна
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Подключаем роутеры
    app.include_router(webhook_router)
    app.include_router(auth_router)
    app.include_router(coupons_router)
    
    @app.get("/", tags=["health"])
    async def root() -> dict[str, str]:
        """Health check endpoint."""
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "ok",
        }
    
    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Health check."""
        return {"status": "ok"}
    
    return app

