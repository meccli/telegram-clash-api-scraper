import asyncio
import os
import io
import json
import logging
from datetime import datetime
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from dotenv import load_dotenv

from clash_api import ClashAPI

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLASH_API_URL = os.getenv("CLASH_API_URL")
CLASH_API_SECRET = os.getenv("CLASH_API_SECRET")
ALLOWED_CHAT_ID = os.getenv("ALLOWED_CHAT_ID")

# Convert ALLOWED_CHAT_ID to int if it exists
if ALLOWED_CHAT_ID:
    try:
        ALLOWED_CHAT_ID = int(ALLOWED_CHAT_ID)
    except ValueError:
        logging.warning("ALLOWED_CHAT_ID is not a valid integer. Security filter might not work as expected.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
clash = ClashAPI(CLASH_API_URL, CLASH_API_SECRET)

# Authorization Middleware
@dp.message.outer_middleware()
async def auth_middleware(handler, event: types.Message, data):
    if ALLOWED_CHAT_ID and event.chat.id != ALLOWED_CHAT_ID:
        logger.warning(f"Unauthorized access attempt from chat ID: {event.chat.id}")
        return # Ignore message
    return await handler(event, data)

def format_bytes(size: int) -> str:
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B/s"

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Clash API Dashboard Bot is active!\nCommands:\n"
                         "/traffic [sec] - Real-time traffic plot\n"
                         "/connections - Connection summary\n"
                         "/connections_plot - Rule distribution pie chart\n"
                         "/proxies - Proxy group status\n"
                         "/logs [min] - Capture and send logs\n"
                         "/rules - Routing rules\n"
                         "/config - Current configuration\n"
                         "/reload - Reload configuration")

@dp.message(Command("traffic"))
async def cmd_traffic(message: types.Message):
    args = message.text.split()
    duration = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
    duration = min(max(duration, 5), 60) # Limit between 5 and 60 seconds

    sent_msg = await message.answer(f"Capturing traffic for {duration}s...")
    
    times = []
    up_speeds = []
    down_speeds = []
    
    start_time = datetime.now()
    try:
        count = 0
        async for data in clash.stream_traffic():
            times.append(count)
            up_speeds.append(data.get('up', 0) / 1024) # KB/s
            down_speeds.append(data.get('down', 0) / 1024) # KB/s
            count += 1
            if count >= duration:
                break
    except Exception as e:
        await message.answer(f"Error capturing traffic: {e}")
        return

    plt.figure(figsize=(10, 5))
    plt.plot(times, up_speeds, label='Upload (KB/s)', color='red')
    plt.plot(times, down_speeds, label='Download (KB/s)', color='blue')
    plt.title(f"Traffic Usage over {duration}s")
    plt.xlabel("Seconds")
    plt.ylabel("Speed (KB/s)")
    plt.legend()
    plt.grid(True)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    await bot.send_photo(message.chat.id, photo=BufferedInputFile(buf.read(), filename="traffic.png"))
    await sent_msg.delete()

@dp.message(Command("connections"))
async def cmd_connections(message: types.Message):
    try:
        data = await clash.get_connections()
        conns = data.get('connections', [])
        total = len(conns)
        upload_total = data.get('uploadTotal', 0)
        download_total = data.get('downloadTotal', 0)

        # Get top hosts
        hosts = {}
        for c in conns:
            host = c.get('metadata', {}).get('host') or c.get('metadata', {}).get('destinationIP')
            hosts[host] = hosts.get(host, 0) + 1
        
        top_hosts = sorted(hosts.items(), key=lambda x: x[1], reverse=True)[:5]
        hosts_str = "\n".join([f"• {h}: {c}" for h, c in top_hosts])

        text = (f"🌐 **Connections Summary**\n"
                f"Total Active: {total}\n"
                f"Total Up: {format_bytes(upload_total)}\n"
                f"Total Down: {format_bytes(download_total)}\n\n"
                f"**Top Hosts:**\n{hosts_str}")
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Error: {e}")

@dp.message(Command("connections_plot"))
async def cmd_connections_plot(message: types.Message):
    try:
        data = await clash.get_connections()
        conns = data.get('connections', [])
        
        rules = {}
        for c in conns:
            rule = c.get('rule', 'Unknown')
            rules[rule] = rules.get(rule, 0) + 1

        if not rules:
            await message.answer("No active connections to plot.")
            return

        plt.figure(figsize=(8, 8))
        plt.pie(rules.values(), labels=rules.keys(), autopct='%1.1f%%', startangle=140)
        plt.title("Connection Distribution by Rule")

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        await bot.send_photo(message.chat.id, photo=BufferedInputFile(buf.read(), filename="connections.png"))
    except Exception as e:
        await message.answer(f"Error: {e}")

@dp.message(Command("proxies"))
async def cmd_proxies(message: types.Message):
    try:
        data = await clash.get_proxies()
        proxies = data.get('proxies', {})
        
        output = ["📍 **Proxy Groups Status**"]
        for name, info in proxies.items():
            if info.get('type') in ['Selector', 'URLTest', 'Fallback']:
                selected = info.get('now', 'N/A')
                output.append(f"• **{name}**: {selected}")
        
        await message.answer("\n".join(output), parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Error: {e}")

@dp.message(Command("logs"))
async def cmd_logs(message: types.Message):
    args = message.text.split()
    duration_min = int(args[1]) if len(args) > 1 and args[1].isdigit() else 2
    duration_sec = duration_min * 60
    duration_sec = min(max(duration_sec, 10), 600) # 10s to 10m

    sent_msg = await message.answer(f"Capturing logs for {duration_min}m...")
    
    logs = []
    try:
        async def capture():
            async for log in clash.stream_logs():
                logs.append(log)
                if len(logs) > 5000: # Safety break
                    break

        try:
            await asyncio.wait_for(capture(), timeout=duration_sec)
        except asyncio.TimeoutError:
            pass # Expected

        if not logs:
            await message.answer("No logs captured.")
            return

        formatted_logs = json.dumps(logs, indent=2)
        buf = io.BytesIO(formatted_logs.encode())
        
        await bot.send_document(message.chat.id, 
                               document=BufferedInputFile(buf.read(), filename=f"logs_{datetime.now().strftime('%H%M%S')}.json"),
                               caption=f"Captured {len(logs)} log entries.")
    except Exception as e:
        await message.answer(f"Error: {e}")
    finally:
        await sent_msg.delete()

@dp.message(Command("rules", "config"))
async def cmd_json_data(message: types.Message):
    endpoint = message.text.replace('/', '')
    try:
        if endpoint == 'rules':
            data = await clash.get_rules()
        else:
            data = await clash.get_configs()

        formatted = json.dumps(data, indent=2)
        if len(formatted) < 4000:
            await message.answer(f"```json\n{formatted}\n```", parse_mode="MarkdownV2")
        else:
            buf = io.BytesIO(formatted.encode())
            await bot.send_document(message.chat.id, 
                                   document=BufferedInputFile(buf.read(), filename=f"{endpoint}.json"))
    except Exception as e:
        await message.answer(f"Error: {e}")

@dp.message(Command("reload"))
async def cmd_reload(message: types.Message):
    sent_msg = await message.answer("🔄 Reloading configuration...")
    try:
        await clash.reload_config()
        await sent_msg.edit_text("✅ Configuration reloaded successfully!")
    except Exception as e:
        await sent_msg.edit_text(f"❌ Error reloading configuration: {e}")

async def main():
    # Set bot commands for hints
    commands = [
        types.BotCommand(command="traffic", description="Real-time traffic plot"),
        types.BotCommand(command="connections", description="Connection summary"),
        types.BotCommand(command="connections_plot", description="Rule distribution pie chart"),
        types.BotCommand(command="proxies", description="Proxy group status"),
        types.BotCommand(command="logs", description="Capture and send logs"),
        types.BotCommand(command="rules", description="Routing rules"),
        types.BotCommand(command="config", description="Current configuration"),
        types.BotCommand(command="reload", description="Reload Sing-box configuration"),
    ]
    await bot.set_my_commands(commands)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
