"""Entry point для запуска приложения."""

import uvicorn

from satwave.adapters.api.app import create_app
from satwave.config.settings import get_settings


def main() -> None:
    """Запустить сервер."""
    settings = get_settings()
    app = create_app()
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

