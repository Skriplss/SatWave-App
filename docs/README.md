# 📚 SatWave Documentation

Welcome to SatWave documentation!

## 📖 Documentation Structure

### 🤖 Telegram Bot
- [Bot Setup](bot/setup.md) - Creating and configuring Telegram bot
- [User Flows](bot/user-flows.md) - How users interact with bot
- [Development](bot/development.md) - Development and extending bot functionality

### 📡 API
- [API Overview](api/overview.md) - General API information
- [Webhook Endpoints](api/webhook.md) - Webhook API documentation for receiving photos
- [Authentication](api/authentication.md) - Authentication methods (TODO)
- [Usage Examples](api/examples.md) - Integration examples

### 🧠 Algorithms and ML
- [Analysis System Overview](algorithms/overview.md) - How the analysis system works
- [ML Models](algorithms/ml-models.md) - Used ML models (YOLOv8, Detectron2)
- [Waste Classification](algorithms/waste-classification.md) - Waste types and confidence
- [Geo-validation](algorithms/geolocation.md) - Coordinate verification and deduplication

### 🏗️ Architecture
- [Clean Architecture](architecture/clean-architecture.md) - Clean architecture principles
- [System Components](architecture/components.md) - Project structure
- [Ports and Adapters](architecture/ports-adapters.md) - Hexagonal architecture
- [Database](architecture/database.md) - Database schema and PostGIS

### 📝 ADR (Architecture Decision Records)
- [ADR-001: Architecture Style Choice](adr/001-clean-architecture.md)
- [ADR-002: ML Framework Choice](adr/002-ml-framework.md)
- [ADR-003: Deduplication Strategy](adr/003-deduplication-strategy.md)
- [ADR-004: Telegram vs WebApp](adr/004-telegram-bot.md)

### 🚀 Deployment
- [Docker Setup](deployment/docker.md) - Running via Docker
- [Production Guide](deployment/production.md) - Production deployment (TODO)
- [Monitoring](deployment/monitoring.md) - Logging and monitoring (TODO)

### 🧪 Testing
- [Testing Strategy](testing/strategy.md) - Unit, Integration, E2E tests
- [Running Tests](testing/running-tests.md) - How to run tests

### 🤝 Contributing
- [Contributing Guide](../CONTRIBUTING.md) - How to contribute
- [Code Style](contributing/code-style.md) - Code formatting rules
- [Git Workflow](contributing/git-workflow.md) - Working with branches and commits

## 🔍 Quick Search

**I want to...**
- Setup Telegram bot → [bot/setup.md](bot/setup.md)
- Integrate with API → [api/webhook.md](api/webhook.md)
- Understand how ML works → [algorithms/overview.md](algorithms/overview.md)
- Learn about architecture → [architecture/clean-architecture.md](architecture/clean-architecture.md)
- Understand why this choice was made → [adr/](adr/)
- Run project → [Quick Start Guide](../README.md#quick-start)

## 📞 Contacts

- **Dima** — Webhook API, geo-validation, ML analysis, Telegram bot
- **Maxim** — Satellite data, area analysis, database

---

**Documentation is updated as the project evolves**
