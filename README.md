# Timetable Assistant Bot

> **Automatically convert time mentions into multiple timezones for distributed teams.**

A Discord and Telegram bot that detects time mentions in chat messages and converts them to the timezones of all participants, eliminating confusion when coordinating across Vancouver, Amsterdam, Yerevan, and everywhere in between.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-116%20passing-brightgreen.svg)](tests/)

---

## 🎯 **The Problem**

Your team is distributed across the globe. When someone says:

> "Let's meet at 10:30"

...which timezone do they mean?

Even when they're specific:

> "Next call at 1pm Amsterdam"

...team members in Yerevan still have to do mental math to realize it's **4pm** for them.

**Daylight saving time makes this even worse** — not all countries observe it, and those that do switch on different dates.

## 💡 **The Solution**

This bot automatically detects time mentions and converts them for everyone:

**Input:**
```
👤 Alice: "see you at 10:30 Amsterdam"
```

**Bot Response (Telegram):**
```
🤖 Bot:
10:30 Amsterdam
11:30 Cyprus
13:30 Yerevan
02:30 Vancouver
```

**Bot Response (Discord):**
```
🤖 Bot: 🕒 Time detected. Click the button to convert it for you.
[Convert for me]

👤 Bob clicks button → Receives private message:
10:30 Amsterdam → 13:30 Yerevan
```

---

## ✨ **Features**

### Core Functionality
- ✅ **Automatic time detection** in chat messages
- ✅ **Multi-timezone conversion** with DST handling
- ✅ **Bilingual support**: English and Russian
- ✅ **Smart date handling**: "today", "tomorrow", "next Monday"
- ✅ **Time ranges**: "10:00–11:00" converts both endpoints
- ✅ **Multiple times**: "10:30 or 14:00" converts all mentions

### Platform Support
- ✅ **Discord**: Button-based per-user conversion (ephemeral messages)
- ✅ **Telegram**: Public group replies + optional DMs

### User Experience
- ✅ **Respects user timezone settings**: `/tz set Europe/Amsterdam`
- ✅ **Privacy controls**: `/mute` to opt out, `/dm off` to disable DMs
- ✅ **Feedback system**: `/feedback <message>` for reporting issues
- ✅ **Admin-only monitoring**: Only admins can configure which channels/groups are monitored

### Smart Parsing
- ✅ **Multiple time formats**: `10:30`, `10am`, `22h30`, `noon`, `midnight`
- ✅ **Explicit timezones**: City names, IANA strings, abbreviations, UTC offsets
- ✅ **Ignore rules**: Skips version numbers (`v10.3.0`), dates (`10/11`), code blocks

---

## 🚀 **Quick Start**

### Prerequisites
- Python 3.9 or higher
- Discord bot token and/or Telegram bot token

### Installation

```bash
# Clone the repository
git clone https://github.com/VesleAnne/timetable-assistant-bot.git
cd timetable-assistant-bot

# Install dependencies
pip install -r requirements.txt

# Create configuration file
cp .env.example .env
# Edit .env and add your bot tokens

# Run the bot
python -m src.main telegram
# or
python -m src.main discord
```

**Detailed installation instructions**: See [docs/INSTALL.md](docs/INSTALL.md)


---

## 📋 **Usage Examples**

### Telegram

### Telegram Setup

1. **Create your bot:**
   - Message `@BotFather` on Telegram
   - Send `/newbot` and follow the prompts
   - Copy the bot token

2. **Disable Privacy Mode (IMPORTANT):**
   - Message `@BotFather`
   - Send `/setprivacy`
   - Select your bot
   - Choose `Disable`
   - **Why:** This allows the bot to see all group messages, not just commands

3. **Add bot token to `.env`:**
```bash
   TELEGRAM_BOT_TOKEN=your_token_here
```

4. **Run the bot:**
```bash
   python -m src.main telegram
```

5. **Add bot to a group and enable monitoring:**
```
   /monitor_on
   /tz set Europe/Amsterdam
```

**Daily Use:**
```
👤 "meeting tomorrow at 10:30"

🤖 Bot replies:
Sat, Jan 24 - 10:30 Amsterdam
Sat, Jan 24 - 11:30 Cyprus  
Sat, Jan 24 - 13:30 Yerevan
Sat, Jan 24 - 02:30 Vancouver
```

### Discord

**Admin Setup:**
```
/monitor add     # Select channels to monitor (admin only)
```

**User Setup:**
```
/tz set Asia/Yerevan    # Set your timezone
```

**Daily Use:**
```
👤 "see you at 10:30 Amsterdam"

🤖 Bot posts: 🕒 Time detected. Click the button to convert it for you.
              [Convert for me]

👤 Click button → Receive private message:
   10:30 Amsterdam → 13:30 Yerevan
```

---

## 🗂️ **Project Structure**

```
timetable-assistant-bot/
├── README.md                   # You are here
├── pyproject.toml             # Package configuration
├── requirements.txt           # Core dependencies
├── requirements-dev.txt       # For development 
├── configuration.yaml         # Bot settings
│
├── docs/
│   ├── INSTALL.md            # Detailed installation guide
│   ├── spec.md               # Full specification
│   ├── architecture.md       # System design
│   ├── acceptance_tests.md   # Test scenarios
│   └── onboarding.md         # Developer guide
│
├── src/
│   ├── main.py               # Application entry point
│   ├── engine.py             # Core orchestration logic
│   ├── parser.py             # Time mention detection
│   ├── conversion.py         # Timezone conversion
│   ├── formatting.py         # Output formatting
│   ├── discord_bot.py        # Discord adapter
│   ├── telegram_bot.py       # Telegram adapter
│   ├── storage.py            # SQLite persistence
│   ├── config.py             # Configuration loading
│   └── models.py             # Data structures
│
├── tests/
│   ├── test_parser_en.py     # English parsing tests
│   ├── test_parser_ru.py     # Russian parsing tests
│   ├── test_engine_*.py      # Engine logic tests
│   └── ...                   # 166 tests total
│
└── journal/
    └── PROGRESS.md           # Implementation journal
```

---

## 🧪 **Testing**

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Current test coverage**: 116 tests, all passing ✅

Tests cover:
- Time parsing (English & Russian)
- Timezone conversion
- Date anchor resolution
- Ignore rules
- Engine orchestration
- Storage operations
- Output formatting

---

## ⚙️ **Configuration**

### Environment Variables (`.env`)

```bash
DISCORD_BOT_TOKEN=your_discord_token_here
TELEGRAM_BOT_TOKEN=your_telegram_token_here
SQLITE_PATH=./data/bot.db  # Optional
```

### Configuration File (`configuration.yaml`)

```yaml
platforms:
  discord:
    enabled: true
  telegram:
    enabled: true

behavior:
  respond_to_edited_messages: false
  ignore_bots: true

i18n:
  supported_languages: [en, ru]
  reply_language: match_message

storage:
  sqlite_path: "./data/bot.db"
```

**Full configuration options**: See [docs/spec.md](docs/spec.md)

---

## 🌍 **Supported Timezones**

### Curated City List (MVP)
- **Europe**: Amsterdam, Lisbon, Milan, Belgrade
- **Cyprus**: Limassol, Cyprus
- **Caucasus**: Tbilisi, Yerevan
- **North America**: Vancouver, Miami

### Also Supports
- **IANA timezone strings**: `Europe/Amsterdam`, `America/Vancouver`
- **Timezone abbreviations**: `CET`, `PST`, `EET`
- **UTC offsets**: `UTC+4`, `+04:00`

**Adding more cities**: Edit the city mapping in `src/timezones.py` or use IANA timezone strings.

---

## 🗣️ **Supported Languages**

- **English**: Full detection and response support
- **Russian**: Full detection and response support

The bot automatically detects message language and responds in the same language.

**Examples:**

English:
```
"meeting at 10:30" → Bot responds in English
"tomorrow at 2pm" → Bot responds in English
```

Russian:
```
"встреча в 10:30" → Bot responds in Russian
"завтра в 14:00" → Bot responds in Russian
```

---

## 🛠️ **Development**

### Setting Up Development Environment

```bash
# Clone and install in editable mode
git clone https://github.com/VesleAnne/timetable-assistant-bot.git
cd timetable-assistant-bot
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Linting
ruff check src/
```

### Contributing

See [docs/onboarding.md](docs/onboarding.md) for:
- Development workflow
- Code architecture
- How to add new features
- Testing guidelines

---

## 📚 **Documentation**

- **[INSTALL.md](docs/INSTALL.md)** - Detailed installation guide
- **[spec.md](docs/spec.md)** - Complete feature specification
- **[architecture.md](docs/architecture.md)** - System design and data flow
- **[acceptance_tests.md](docs/acceptance_tests.md)** - Test scenarios
- **[onboarding.md](docs/onboarding.md)** - Developer guide (coming soon)

---

## 🎮 **Commands Reference**

### User Commands (All Platforms)

| Command | Description |
|---------|-------------|
| `/tz set <timezone>` | Set your timezone (e.g., `/tz set Europe/Amsterdam`) |
| `/tz show` | Show your current timezone |
| `/tz clear` | Remove your timezone setting |
| `/feedback <text>` | Send feedback to bot administrators |
| `/mute` | Stop receiving bot conversions |
| `/unmute` | Re-enable bot conversions |
| `/delete_me` | Delete all your stored data |

### Telegram-Specific Commands

| Command | Description |
|---------|-------------|
| `/dm on` | Receive DM conversions (in addition to public replies) |
| `/dm off` | Disable DM conversions |
| `/dm status` | Check your DM delivery setting |

### Admin Commands

**Discord:**
| Command | Description |
|---------|-------------|
| `/monitor add` | Add channels to monitoring (interactive select) |
| `/monitor remove` | Remove channels from monitoring |
| `/monitor list` | Show monitored channels |

**Telegram:**
| Command | Description |
|---------|-------------|
| `/monitor_on` | Enable monitoring in this group |
| `/monitor_off` | Disable monitoring in this group |
| `/monitor_status` | Check monitoring status |

---

## 🔒 **Privacy & Data**

### What Data Is Stored
- User timezone preferences (per platform)
- Telegram DM preferences (opt-in only)
- Discord monitored channel IDs
- Telegram group monitoring status
- Usage metrics (anonymous)

### What Data Is NOT Stored
- Message content (parsed in-memory only)
- User activity timestamps
- Personal information beyond timezone

### Data Deletion
Users can delete their data anytime with `/delete_me`.

---

## 🚦 **Production Deployment**


### Using Docker

```bash
# Build and run
docker-compose up -d telegram
docker-compose up -d discord
```

See [docs/INSTALL.md](docs/INSTALL.md) for complete deployment instructions.

---

## 🐛 **Troubleshooting**

### Bot doesn't respond to time mentions

**Check:**
1. Is monitoring enabled in this channel/group?
   - Discord: Run `/monitor list`
   - Telegram: Run `/monitor_status`
2. Did you set your timezone? Run `/tz show`
3. Is the time format supported? See [Supported Formats](#supported-languages)

### "I don't know your timezone yet"

**Solution:** Set your timezone with `/tz set Europe/Amsterdam`

### Tests fail on installation

**Solution:** 
```bash
# Ensure you're in the project root
cd /path/to/timetable-assistant-bot

# Reinstall in editable mode
pip install -e .

# Run tests
pytest tests/
```

**More troubleshooting**: See [docs/INSTALL.md](docs/INSTALL.md#troubleshooting)

---

## 📊 **Technical Highlights**

- **Architecture**: Clean separation between platform adapters and core logic
- **Testing**: 166 passing tests covering parsers, engine, storage, and formatting
- **Type Safety**: Full type hints with mypy checking
- **Timezone Handling**: IANA-based with proper DST support via `zoneinfo`
- **Async**: Modern async/await for Telegram, discord.py v2.x for Discord
- **Configuration**: Pydantic-validated settings with env variable overrides
- **Storage**: SQLite for simplicity, easy migration to Postgres later
- **Localization**: Template-based i18n for English and Russian

---

## 🗺️ **Roadmap**

### MVP (Current) ✅
- ✅ Discord + Telegram support
- ✅ English + Russian languages
- ✅ Time detection and conversion
- ✅ User timezone management
- ✅ Admin controls

### Future Enhancements
- 🔲 WhatsApp integration
- 🔲 Support for edited messages
- 🔲 Natural language time parsing ("in 2 hours", "next Thursday at 3")
- 🔲 Automatic timezone detection from message metadata
- 🔲 Recurring event detection
- 🔲 Calendar integration
- 🔲 Web dashboard for analytics

---

## 🤝 **Contributing**

Contributions are welcome! Please read [docs/onboarding.md](docs/onboarding.md) for:
- Development setup
- Code style guidelines
- How to submit pull requests
- Testing requirements

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

Built to solve real timezone coordination challenges for distributed teams across:
- 🇨🇦 Vancouver
- 🇺🇸 Miami  
- 🇵🇹 Lisbon
- 🇳🇱 Amsterdam
- 🇮🇹 Milan
- 🇷🇸 Belgrade
- 🇨🇾 Limassol
- 🇬🇪 Tbilisi
- 🇦🇲 Yerevan

---

## 📞 **Support**

- **Issues**: [GitHub Issues](https://github.com/vesleanne/timetable-assistant-bot/issues)
- **Documentation**: [docs/](docs/)
- **Questions**: Use the `/feedback` command in the bot

---

## 🔗 **Links**

- **Documentation**: [docs/spec.md](docs/spec.md)
- **Installation Guide**: [docs/INSTALL.md](docs/INSTALL.md)
- **Architecture**: [docs/architecture.md](docs/architecture.md)
- **Tests**: [tests/](tests/)

---

<div align="center">

**Made with ❤️ for distributed teams everywhere**

[⬆ Back to Top](#timetable-assistant-bot)

</div>
