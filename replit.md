# SRRD Bot

## Overview
A Discord bot application imported from GitHub (https://github.com/getthemtoes1/srrd-bot).

**Current State**: Bot is online and connected to Discord.

## Recent Changes
- **December 1, 2025**: Initial setup in Replit environment
  - Installed Python 3.11 with discord.py library
  - Created Discord bot with basic commands
  - Set up workflow for running the bot
  - Configured DISCORD_BOT_TOKEN secret

## Project Architecture
- **Language**: Python 3.11
- **Framework**: discord.py
- **Entry Point**: main.py
- **Type**: Discord Bot

## Structure
```
.
├── main.py           # Discord bot application
├── requirements.txt  # Python dependencies (discord.py)
└── README.md         # Original repository README
```

## Bot Commands
- `!ping` - Check bot latency
- `!hello` - Get a greeting from the bot
- `!info` - Display bot information

## Secrets Required
- `DISCORD_BOT_TOKEN` - Your Discord bot token from the Developer Portal

## How to Run
The bot runs automatically via the "Run Bot" workflow. It connects to Discord and responds to commands with the `!` prefix.
