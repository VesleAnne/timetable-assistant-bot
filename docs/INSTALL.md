# Installation Guide

This guide covers installing and running the Timetable Assistant Bot locally or in production.

## Prerequisites

- **Python 3.9 or higher** (3.11+ recommended)
- **pip** (Python package installer)
- **Git** (to clone the repository)
- **Discord and/or Telegram bot token(s)** 

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/VesleAnne/timetable-assistant-bot.git
cd timetable-assistant-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env and add your bot tokens

# 4. Run the bot (Telegram or Discord or both)
python -m src.main telegram
# or
python -m src.main discord

```

## Detailed Installation

### Option 1: Using pip (Recommended)

```bash
# Install core dependencies
pip install -r requirements.txt

# For development (includes testing and linting tools)
pip install -r requirements-dev.txt
```

### Option 2: Using pyproject.toml 

```bash
# Install in editable mode (for development)
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Option 3: Using a Virtual Environment (Recommended for Production)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# Discord bot token (get from https://discord.com/developers/applications)

DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Telegram bot token (get from @BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Database path (optional, defaults to ./data/bot.db)
SQLITE_PATH=./data/bot.db
```
### 2. Configuration File

The bot uses `configuration.yaml` for settings. The default configuration works for most cases:

```yaml
platforms:
  discord:
    enabled: true
  telegram:
    enabled: true

storage:
  sqlite_path: "./data/bot.db"

telegram:
  dm_delivery:
    enabled: true
```

Environment variables **override** YAML settings, so you can keep tokens in `.env` for security.

## Getting Bot Tokens

### Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Give it a name (e.g., "Timetable Assistant")
4. Go to **Bot** tab → Click **"Add Bot"**
5. Under **Token**, click **"Copy"**
6. Paste into your `.env` file as `DISCORD_BOT_TOKEN`

**Required Bot Permissions:**
- Read Messages/View Channels
- Send Messages
- Use Slash Commands
- Embed Links
- Read Message History

**Required Intents:**
- Server Members Intent (for tracking users)
- Message Content Intent (to read time mentions)

### Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow the prompts to choose a name and username
4. Copy the token BotFather gives you
5. Paste into your `.env` file as `TELEGRAM_BOT_TOKEN`

## Running the Bot

### Run Telegram Bot

```bash
python -m src.main telegram
```

### Run Discord Bot

```bash
python -m src.main discord
```

### Run with Custom Configuration

```bash
python -m src.main telegram --config /path/to/config.yaml --log-level DEBUG
```

### Available Options

```bash
python -m src.main --help

usage: main.py [-h] [--config CONFIG] [--log-level LOG_LEVEL]
               {discord,telegram}

positional arguments:
  {discord,telegram}    Which platform bot to run

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to configuration.yaml
  --log-level LOG_LEVEL
                        Logging level (DEBUG, INFO, WARNING, ERROR)
```

## Database Setup

The bot uses SQLite for storage. The database is created automatically on first run.

**Default location**: `./data/bot.db`

To use a different location:
1. Set `SQLITE_PATH` in `.env`, OR
2. Edit `storage.sqlite_path` in `configuration.yaml`

The bot will create the `data/` directory if it doesn't exist.

## Testing the Installation

### 1. Verify Imports

```bash
python -c "from src.main import main; print('✅ Imports successful')"
```

### 2. Run Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

Expected output:
```
============================== 166 passed in 2.35s ==============================
```

### 3. Test Bot Locally

**For Discord**:
1. Invite your bot to a test server
2. Run `python -m src.main discord`
3. In Discord, use `/monitor add` to add a channel
4. Send a message like "see you at 10:30"
5. Click the "Convert for me" button

**For Telegram**:
1. Add your bot to a test group
2. Run `python -m src.main telegram`
3. In the group, send `/monitor_on` (as admin)
4. Send `/tz set Europe/Amsterdam`
5. Send a message like "meeting at 10:30"
6. Bot should reply with timezone conversions

## Troubleshooting

### "No module named 'discord'" or "No module named 'telegram'"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### "DISCORD_BOT_TOKEN is missing"

**Solution**: Create `.env` file with your bot tokens (see [Configuration](#configuration))

### "Permission denied" when running the bot

**Solution**: Ensure the bot has proper permissions in Discord/Telegram. See [Getting Bot Tokens](#getting-bot-tokens).

### Database errors on first run

**Solution**: Ensure the `data/` directory is writable:
```bash
mkdir -p data
chmod 755 data
```

### Tests fail with "No module named 'src'"

**Solution**: Run tests from the project root:
```bash
cd /path/to/timetable-assistant-bot
pytest tests/
```

Or install in editable mode:
```bash
pip install -e .
```

### "Message content intent not enabled" (Discord)

**Solution**: Enable Message Content Intent in Discord Developer Portal:
1. Go to your application
2. Bot tab → Privileged Gateway Intents
3. Enable "Message Content Intent"
4. Save changes and restart the bot

## Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/timetable-bot-telegram.service`:

```ini
[Unit]
Description=Timetable Assistant Bot (Telegram)
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/timetable-assistant-bot
Environment="PATH=/opt/timetable-assistant-bot/venv/bin"
ExecStart=/opt/timetable-assistant-bot/venv/bin/python -m src.main telegram
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable timetable-bot-telegram
sudo systemctl start timetable-bot-telegram
sudo systemctl status timetable-bot-telegram
```

### Using Docker (Recommended)

See `Dockerfile` and `docker-compose.yml` for containerized deployment.

```bash
docker-compose up -d telegram
# or
docker-compose up -d discord
```

### Environment Variables in Production

Never hardcode tokens! Use environment variables:

```bash
export DISCORD_BOT_TOKEN="your_token_here"
export TELEGRAM_BOT_TOKEN="your_token_here"
python -m src.main telegram
```

## Updating the Bot

```bash
git pull
pip install -r requirements.txt --upgrade
# Restart the bot service
```

## Logs and Monitoring

Logs are written to stdout by default. To save logs:

```bash
python -m src.main telegram 2>&1 | tee -a bot.log
```

To increase verbosity:
```bash
python -m src.main telegram --log-level DEBUG
```

## Next Steps

- Read [docs/onboarding.md](docs/onboarding.md) for development setup
- See [docs/architecture.md](docs/architecture.md) for system design
- Check [docs/spec.md](docs/spec.md) for feature specifications
- Review [docs/acceptance_tests.md](docs/acceptance_tests.md) for testing

## Getting Help

- Check the [FAQ](#troubleshooting)
- Review logs with `--log-level DEBUG`
- Open an issue on GitHub
- Read the documentation in `docs/`

## Dependencies

**Core Runtime Dependencies:**
- `pyyaml>=6.0` - Configuration file parsing
- `pydantic>=2.0` - Data validation
- `discord.py>=2.3.0` - Discord API wrapper
- `python-telegram-bot>=20.0` - Telegram API wrapper
- `tzdata>=2023.3` - Timezone database
- `pyyaml>=6.0` - 

**Development Dependencies:**
- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `black>=23.0.0` - Code formatting
- `mypy>=1.5.0` - Static type checking
- `ruff>=0.1.0` - Fast linter

See `requirements.txt` and `requirements-dev.txt` for full lists.