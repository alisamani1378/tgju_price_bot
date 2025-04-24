# TGJU Price Bot

A Telegram bot that provides real-time prices for gold, coins, and currencies from [TGJU.org](https://www.tgju.org).

## Features

- Real-time price updates for gold, coins, USD, and Euro
- Automatic price updates every minute
- Updates existing messages instead of creating new ones to avoid channel clutter
- Scheduled full refreshes twice daily (8 AM and 8 PM Iran time)

## Setup

1. Create a `.env` file with your Telegram bot token and channel ID:
   ```
   BOT_TOKEN=your_telegram_bot_token
   CHANNEL_ID=@your_channel_name (or channel ID)
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the bot:
   ```
   python main.py
   ```

## How It Works

The bot scrapes price data from TGJU.org and sends it to your Telegram channel. It intelligently manages messages by:

1. First checking if there's an existing price message to update
2. If found, updates that message instead of creating a new one
3. If not found, creates a new message
4. Cleans up old messages to avoid cluttering the channel

## Files

- `main.py` - Main bot code that handles sending updates to Telegram and extracting price data
- `requirements.txt` - Project dependencies

## Data Source

All price data is sourced from [TGJU.org](https://www.tgju.org). 