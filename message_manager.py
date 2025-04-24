import os
from datetime import datetime
import pytz
import logging

PRICE_MESSAGE_KEYWORD = "قیمت‌های لحظه‌ای"
LATEST_MESSAGE_FILE = "latest_message_id.txt"
IRAN_TZ = pytz.timezone('Asia/Tehran')


def get_iran_time_now():
    return datetime.now(IRAN_TZ)


def is_send_time(current_time, send_times):
    for send_time in send_times:
        if (
            send_time.hour == current_time.hour and
            abs(send_time.minute - current_time.minute) <= 5
        ):
            return True
    return False


def format_price_message(prices):
    now = get_iran_time_now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    text = f"💵 {PRICE_MESSAGE_KEYWORD} 💵\n\n"
    if 'currencies' in prices:
        for name, data in prices['currencies'].items():
            text += f"📊 {name}: {data.get('price', 'N/A')} تومان\n"
    if 'gold' in prices:
        text += "\n"
        for name, data in prices['gold'].items():
            text += f"📊 {name}: {data.get('price', 'N/A')} تومان\n"
    if 'coin' in prices:
        text += "\n"
        for name, data in prices['coin'].items():
            text += f"📊 {name}: {data.get('price', 'N/A')} تومان\n"
    text += f"\n🔄 <b>قیمت‌ها هر یک دقیقه یکبار به‌روز می‌شوند</b>\n"
    text += f"⏰ آخرین به‌روزرسانی: {date_str}"
    return text


def save_latest_message_id(message_id):
    with open(LATEST_MESSAGE_FILE, 'w') as f:
        f.write(str(message_id))


def get_latest_message_id_from_file():
    if not os.path.exists(LATEST_MESSAGE_FILE):
        return None
    with open(LATEST_MESSAGE_FILE, 'r') as f:
        message_id = f.read().strip()
        return int(message_id) if message_id else None


async def find_and_delete_old_price_messages(bot, channel_id):
    from telegram.error import TelegramError
    try:
        # get_chat_history is not available in Bot API, so we use get_updates workaround
        updates = await bot.get_updates(limit=100)
        for update in updates:
            msg = getattr(update, 'channel_post', None)
            if msg and hasattr(msg, 'chat') and hasattr(msg.chat, 'username') and msg.chat.username == channel_id[1:]:
                if msg.text and (
                    PRICE_MESSAGE_KEYWORD in msg.text or
                    any(k in msg.text for k in ['قیمت', 'دلار', 'یورو', 'سکه', 'طلا', 'به روز رسانی'])
                ):
                    try:
                        await bot.delete_message(chat_id=channel_id, message_id=msg.message_id)
                    except TelegramError as e:
                        logging.error(f"Error deleting message {msg.message_id}: {e}")
    except Exception as e:
        logging.error(f"Error in find_and_delete_old_price_messages: {e}") 