# Telegram Clash API Dashboard

A lightweight asynchronous Telegram bot designed to monitor and manage a local Sing-box (or Clash) instance via its Clash-compatible REST API.

## Features

- 📈 **Traffic Monitoring**: Capture real-time traffic speeds and generate a line chart.
- 🌐 **Connection Summaries**: View active connections, total throughput, and top destination hosts.
- 📊 **Rule Visualization**: Pie charts showing how your traffic is distributed across routing rules.
- 📍 **Proxy Management**: Check the status of your proxy groups and currently selected nodes.
- 📄 **Log Capture**: Stream logs for a specified duration and receive a formatted JSON file.
- 🔄 **Config Reload**: Trigger a hot-reload of your Sing-box configuration.
- 🔒 **Security**: Whitelist specific Telegram Chat IDs to prevent unauthorized access.
- ⌨️ **Command Hints**: Automatically registers commands with Telegram for easy access.

## Prerequisites

- Python 3.9 or higher
- A running Sing-box instance with the `clash_api` enabled in the `experimental` section.

## Configuration

1.  **Copy the environment template:**
    ```bash
    cp .env.example .env
    ```

2.  **Edit `.env` and fill in your details:**
    - `BOT_TOKEN`: Your bot token from [@BotFather](https://t.me/BotFather).
    - `CLASH_API_URL`: The external controller address (e.g., `http://127.0.0.1:9090`).
    - `CLASH_API_SECRET`: The secret set in your Sing-box config (leave empty if none).
    - `ALLOWED_CHAT_ID`: Your Telegram Chat ID to secure the bot.
    - `HTTP_TELEGRAM_PROXY`: (Optional) HTTP proxy for the bot to connect to Telegram (e.g., `http://127.0.0.1:7890`).

## Usage

Start the bot by running:
```bash
python bot.py
```

## Bot Commands

- `/start` - Show help message and command list.
- `/traffic [sec]` - Capture and plot real-time traffic (default 10s).
- `/connections` - Show a text summary of active connections.
- `/connections_plot` - Generate a pie chart of connections by routing rule.
- `/proxies` - List status of all proxy groups.
- `/logs [min]` - Capture logs for X minutes and send as a document.
- `/rules` - View current routing rules.
- `/config` - View current configuration.
- `/reload` - Trigger a hot-reload of the Sing-box configuration.
