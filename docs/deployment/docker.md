# 🐳 Docker Deployment

Развертывание SatWave через Docker и Docker Compose.

## Требования

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM минимум
- 10GB свободного места

## Quick Start

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Skriplss/SatWave-SaaS.git
cd SatWave-SaaS

# 2. Создать .env файл
cp .env.example .env

# 3. Добавить Telegram токен (опционально)
nano .env  # TELEGRAM_BOT_TOKEN=...

# 4. Запустить
docker-compose up --build
```

##Структура

```yaml
services:
  api:       # FastAPI REST API
  bot:       # Telegram Bot
  db:        # PostgreSQL + PostGIS
```

## Сервисы

### API Service

**Порт**: 8000

**Endpoints**:
- `http://localhost:8000/docs` - Swagger UI
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/webhook/photo` - Photo upload

**Конфигурация**:
```yaml
api:
  build: .
  ports:
    - "8000:8000"
  environment:
    - API_HOST=0.0.0.0
    - API_PORT=8000
    - ML_MODEL_TYPE=stub
    - PHOTO_STORAGE_TYPE=stub
```

### Bot Service

**Конфигурация**:
```yaml
bot:
  build: .
  command: python -m satwave.adapters.bot.telegram_bot
  environment:
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  restart: unless-stopped
```

### Database Service

**Порт**: 5432

**Image**: `postgis/postgis:15-3.3`

**Volumes**: Данные персистентны в `postgres_data`

## Команды

### Запуск всех сервисов

```bash
docker-compose up
```

### Запуск в фоне

```bash
docker-compose up -d
```

### Запуск только API

```bash
docker-compose up api
```

### Запуск только Bot

```bash
docker-compose up bot
```

### Остановка

```bash
docker-compose down
```

### Пересборка образов

```bash
docker-compose up --build
```

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Только API
docker-compose logs -f api

# Только Bot
docker-compose logs -f bot
```

### Очистка

```bash
# Остановить и удалить контейнеры
docker-compose down

# Удалить volumes (БД будет очищена!)
docker-compose down -v

# Удалить images
docker-compose down --rmi all
```

## Production Setup

### Environment Variables

Создай `.env` файл для продакшна:

```env
# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Telegram
TELEGRAM_BOT_TOKEN=your_production_token

# Database
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/satwave

# Storage
PHOTO_STORAGE_TYPE=s3
S3_BUCKET=satwave-photos-prod
S3_REGION=eu-west-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=yyy

# ML
ML_MODEL_TYPE=yolo
ML_MODEL_PATH=/app/models/yolov8.pt

# Security
API_KEY=your_secret_api_key
```

### HTTPS с Nginx

`docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api

  api:
    # ... same as before
    expose:
      - "8000"
    # Don't expose ports directly
```

`nginx.conf`:
```nginx
upstream api {
    server api:8000;
}

server {
    listen 80;
    server_name api.satwave.io;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.satwave.io;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Healthchecks

Добавь healthchecks в `docker-compose.yml`:

```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U satwave"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Resource Limits

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  bot:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

## Мониторинг

### Docker Stats

```bash
docker stats
```

### Логи с timestamps

```bash
docker-compose logs -f --timestamps
```

### Container inspect

```bash
docker inspect satwave_api_1
```

## Troubleshooting

### API не запускается

**Проблема**: `Connection refused`

```bash
# Проверить логи
docker-compose logs api

# Проверить healthcheck
docker ps

# Зайти внутрь контейнера
docker-compose exec api bash
```

### База данных не подключается

**Проблема**: `Could not connect to database`

```bash
# Проверить, что БД запущена
docker-compose ps db

# Проверить логи БД
docker-compose logs db

# Проверить connection string
docker-compose exec api env | grep DATABASE
```

### Bot не отвечает

**Проблема**: Бот не реагирует на сообщения

```bash
# Проверить токен
docker-compose exec bot env | grep TELEGRAM

# Проверить логи
docker-compose logs bot

# Перезапустить бота
docker-compose restart bot
```

### Нехватка памяти

**Проблема**: `OOMKilled`

```bash
# Увеличить лимиты в docker-compose.yml
# Или увеличить Docker Desktop memory limit
```

## Backup & Restore

### Backup БД

```bash
docker-compose exec db pg_dump -U satwave satwave > backup.sql
```

### Restore БД

```bash
cat backup.sql | docker-compose exec -T db psql -U satwave satwave
```

### Backup volumes

```bash
docker run --rm \
  -v satwave_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz /data
```

## CI/CD Integration

### GitHub Actions

`.github/workflows/docker-build.yml`:
```yaml
name: Docker Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build image
        run: docker-compose build
      
      - name: Run tests
        run: docker-compose run api pytest
      
      - name: Push to registry
        run: |
          docker tag satwave_api ghcr.io/satwave/api:latest
          docker push ghcr.io/satwave/api:latest
```

## См. также

- [Development Setup](../development/setup.md)
- [docker-compose.yml](../../docker-compose.yml)
- [Dockerfile](../../Dockerfile)

