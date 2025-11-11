# 🚀 Quick Start - Telegram Bot

## Step 1: Create bot in Telegram

1. Open Telegram and find `@BotFather`
2. Send `/newbot`
3. Enter name: `SatWave Bot` (or any other)
4. Enter username: `satwave_analysis_bot` (or any other, must end with `bot`)
5. **Copy token** — it will look something like:
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-123456789
   ```

## Step 2: Add token to project

Open `.env` file (already created in project root) and replace line:

```bash
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
```

with

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-123456789
```

(Insert your token from BotFather)

## Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Run bot

```bash
python -m satwave.adapters.bot.telegram_bot
```

You should see:
```
INFO - Starting Telegram bot...
INFO - Bot started polling
```

## Step 5: Test

1. Find your bot in Telegram (by username)
2. Send `/start`
3. Send any photo
4. Send geolocation (click paperclip → Location → Share My Location)
5. Get result! 🎉

## What happens inside?

```
Telegram Bot
    ↓ (receives photo + geolocation)
handlers.py
    ↓ (calls)
PhotoAnalysisService
    ↓ (processes)
- Validates coordinates
- Checks duplicates
- Runs ML classifier (currently stub)
- Saves to DB (currently in-memory)
    ↓ (returns result)
Telegram Bot
    ↓
User receives message with waste type
```

## Code Structure

```
src/satwave/adapters/bot/
├── telegram_bot.py     # Main bot class (TelegramBot)
└── handlers.py         # Message handlers:
                        #   - /start, /help
                        #   - handle_photo() - receive photo
                        #   - handle_location() - receive location
                        #   - process_analysis() - run analysis
```

## Configuration (optional)

### Set commands in BotFather

1. Send @BotFather command `/setcommands`
2. Select your bot
3. Send:
```
start - Start working with bot
help - Get help
```

### Set description

```
/setdescription
```

Example:
```
SatWave Bot analyzes waste photos and determines waste types. 
Send photo and geolocation - get analysis result!
```

## Troubleshooting

### Error: "Token is invalid"
- Check that token is correctly copied to `.env`
- Make sure there are no extra spaces

### Bot doesn't respond
- Make sure script is running (`python -m satwave.adapters.bot.telegram_bot`)
- Check console logs

### "Duplicate location error"
- This location has already been used
- Send photo from different location (more than 50 meters away)

### Bot received photo but didn't process
- Send geolocation! Bot is waiting for both photo and location

## Next Steps

After basic test you can:
- Run API in parallel: `python -m satwave.main`
- Run everything via Docker: `docker-compose up`
- View API docs: http://localhost:8000/docs
- Integrate with real ML model (replace stub)
- Connect PostgreSQL (replace in-memory DB)

## Documentation

📚 Full documentation: [docs/](docs/)

- [Bot Setup](docs/bot/setup.md) - Detailed instructions
- [User Flows](docs/bot/user-flows.md) - How to work with bot
- [Development](docs/bot/development.md) - Adding new features
- [API Overview](docs/api/overview.md) - Webhook API
- [ADR](docs/adr/) - Architecture decisions

**Done! Now you have a working Telegram bot for receiving waste photos! 🎉**
