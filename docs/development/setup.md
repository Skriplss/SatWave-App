# 💻 Development Setup

Настройка окружения для разработки SatWave.

## Требования

- **Python 3.11+**
- **pip** или **poetry**
- **Git**
- **(Опционально) Docker** для БД

## Quick Start

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Skriplss/SatWave-SaaS.git
cd SatWave-SaaS

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Создать .env файл
cp .env.example .env

# 5. Запустить API
python -m satwave.main

# 6. Запустить Bot (в другом терминале)
python -m satwave.adapters.bot.telegram_bot
```

## Детальная настройка

### 1. Python Environment

#### venv (стандартный)

```bash
python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

#### Poetry (рекомендуется)

```bash
# Установить Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Создать окружение и установить зависимости
poetry install

# Активировать окружение
poetry shell
```

### 2. Конфигурация

#### .env файл

```env
# API
API_HOST=127.0.0.1
API_PORT=8000
DEBUG=true
LOG_LEVEL=DEBUG

# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Database (опционально для начала)
DATABASE_URL=postgresql+asyncpg://satwave:satwave@localhost:5432/satwave

# Storage
PHOTO_STORAGE_TYPE=stub
PHOTO_STORAGE_BASE_URL=http://localhost:8000/photos

# ML
ML_MODEL_TYPE=stub
ML_MODEL_CONFIDENCE_THRESHOLD=0.5

# Deduplication
DUPLICATE_CHECK_THRESHOLD_METERS=50.0
```

### 3. Database Setup (опционально)

#### Docker

```bash
docker run --name satwave-db \
  -e POSTGRES_USER=satwave \
  -e POSTGRES_PASSWORD=satwave \
  -e POSTGRES_DB=satwave \
  -p 5432:5432 \
  -d postgis/postgis:15-3.3
```

#### Локально (macOS)

```bash
brew install postgresql postgis
brew services start postgresql

createdb satwave
psql satwave -c "CREATE EXTENSION postgis;"
```

### 4. Telegram Bot Token

1. Открой `@BotFather` в Telegram
2. Отправь `/newbot`
3. Следуй инструкциям
4. Скопируй токен в `.env`

Подробнее: [Bot Setup](../bot/setup.md)

## Структура проекта

```
SatWave/
├── src/satwave/          # Исходный код
│   ├── core/            # Доменная логика
│   ├── adapters/        # Адаптеры
│   └── config/          # Конфигурация
├── tests/               # Тесты
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/                # Документация
├── .env                 # Конфигурация (не в Git!)
├── requirements.txt     # Зависимости
├── pyproject.toml       # Настройки проекта
└── README.md
```

## Запуск сервисов

### API

```bash
# Development с hot-reload
uvicorn satwave.adapters.api.app:create_app --reload --factory

# Или через main
python -m satwave.main
```

API будет доступен:
- http://localhost:8000
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc

### Telegram Bot

```bash
python -m satwave.adapters.bot.telegram_bot
```

Или через команду:
```bash
satwave-bot
```

### Одновременно (с tmux)

```bash
# Terminal 1
tmux new -s satwave

# Terminal 1: API
python -m satwave.main

# Terminal 2: Bot
tmux split-window -h
python -m satwave.adapters.bot.telegram_bot

# Переключение: Ctrl+B потом стрелка
```

## Качество кода

### Линтер и форматирование

```bash
# Проверить код
ruff check src/ tests/

# Исправить автоматически
ruff check --fix src/ tests/

# Форматирование
ruff format src/ tests/
```

### Type Checking

```bash
mypy src/
```

### Pre-commit hooks (рекомендуется)

```bash
# Установить pre-commit
pip install pre-commit

# Создать .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
EOF

# Установить hooks
pre-commit install

# Теперь ruff будет запускаться перед каждым коммитом
```

## Testing

См. [Testing Guide](testing.md)

## IDE Setup

### VS Code

Установи расширения:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Ruff (charliermarsh.ruff)

`.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

### PyCharm

1. Settings → Project → Python Interpreter
2. Выбери venv interpreter
3. Settings → Tools → Python Integrated Tools
   - Default test runner: pytest
4. Settings → Editor → Inspections
   - Включи все Python inspections

## Git Workflow

### Ветки

- `main` - продакшн (всегда зеленая)
- `dev` - разработка
- `feat/<scope>-<name>` - новая функциональность
- `fix/<scope>-<name>` - исправление

### Коммиты

Используем **Conventional Commits**:

```bash
git commit -m "feat(api): add rate limiting to webhook endpoint"
git commit -m "fix(bot): handle empty photo data"
git commit -m "docs(readme): update installation instructions"
```

Типы:
- `feat` - новая функциональность
- `fix` - исправление
- `docs` - документация
- `test` - тесты
- `refactor` - рефакторинг
- `perf` - оптимизация
- `chore` - инфраструктура

### Pull Requests

1. Создай ветку от `dev`
2. Сделай изменения
3. Запусти тесты: `pytest`
4. Запусти линтер: `ruff check --fix src/ tests/`
5. Коммит с Conventional Commits
6. Push в ветку
7. Создай PR в `dev`

## Troubleshooting

### ModuleNotFoundError

```bash
# Установи проект в editable mode
pip install -e .
```

### Порт 8000 занят

```bash
# Убить процесс на порту 8000
lsof -ti:8000 | xargs kill -9

# Или использовать другой порт
API_PORT=8001 python -m satwave.main
```

### Import errors

```bash
# Проверь PYTHONPATH
echo $PYTHONPATH

# Добавь src/ в PYTHONPATH (или используй pip install -e .)
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Telegram bot не отвечает

1. Проверь токен в `.env`
2. Убедись, что скрипт запущен
3. Отправь `/start` заново
4. Проверь логи (LOG_LEVEL=DEBUG)

## Полезные команды

```bash
# Запустить конкретный тест
pytest tests/unit/test_models.py::test_location_validation

# Запустить с coverage
pytest --cov=satwave --cov-report=html

# Очистить кеш
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Обновить зависимости
pip list --outdated
pip install --upgrade package_name
```

## Ресурсы

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Aiogram Docs](https://docs.aiogram.dev/)
- [Pytest Docs](https://docs.pytest.org/)
- [Ruff Docs](https://docs.astral.sh/ruff/)

## См. также

- [Testing Guide](testing.md)
- [Docker Setup](../deployment/docker.md)
- [Bot Setup](../bot/setup.md)

