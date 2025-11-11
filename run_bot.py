    #!/usr/bin/env python
"""Скрипт для запуска Telegram бота."""

import sys
from pathlib import Path

# Добавляем src в PYTHONPATH
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    from satwave.adapters.bot.telegram_bot import main
    main()

