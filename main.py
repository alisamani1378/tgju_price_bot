import os
import asyncio
from datetime import datetime, time, timedelta
import pytz
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
import logging
import json

from price_extractor_v2 import get_all_prices
from message_manager import (
    format_price_message,
    save_latest_message_id,
    get_latest_message_id_from_file,
    is_send_time,
    get_iran_time_now
)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# بارگذاری متغیرهای محیطی
load_dotenv(override=True)
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = "@testdigitallvpn"
PRICE_MESSAGE_KEYWORD = "قیمت‌های به‌روز شده"

# زمان‌های ارسال پیام جدید (به جای ویرایش)
SEND_TIMES = [
    time(9, 0),   # 9:00 AM
    time(18, 0)   # 6:00 PM
]

# فایل ذخیره شناسه پیام‌های مربوط به قیمت
PRICE_MESSAGES_FILE = "price_messages.json"
# فایل ذخیره آخرین شناسه پیام
LAST_MESSAGE_ID_FILE = "last_message_id.txt"

def save_price_message_id(message_id):
    """ذخیره شناسه پیام قیمت در فایل"""
    try:
        # خواندن شناسه‌های قبلی
        message_ids = []
        if os.path.exists(PRICE_MESSAGES_FILE):
            with open(PRICE_MESSAGES_FILE, 'r') as f:
                message_ids = json.load(f)
        
        # اضافه کردن شناسه جدید
        if message_id not in message_ids:
            message_ids.append(message_id)
        
        # ذخیره در فایل
        with open(PRICE_MESSAGES_FILE, 'w') as f:
            json.dump(message_ids, f)
            
        logger.info(f"شناسه پیام {message_id} ذخیره شد")
    except Exception as e:
        logger.error(f"خطا در ذخیره شناسه پیام: {e}")

def get_saved_price_message_ids():
    """دریافت شناسه‌های پیام‌های قیمت ذخیره شده"""
    try:
        if os.path.exists(PRICE_MESSAGES_FILE):
            with open(PRICE_MESSAGES_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"خطا در خواندن شناسه‌های پیام: {e}")
        return []

def save_last_message_id(message_id):
    """ذخیره آخرین شناسه پیام برای ویرایش"""
    try:
        with open(LAST_MESSAGE_ID_FILE, 'w') as f:
            f.write(str(message_id))
        logger.info(f"آخرین شناسه پیام {message_id} ذخیره شد")
    except Exception as e:
        logger.error(f"خطا در ذخیره آخرین شناسه پیام: {e}")

def get_last_message_id():
    """دریافت آخرین شناسه پیام برای ویرایش"""
    try:
        if os.path.exists(LAST_MESSAGE_ID_FILE):
            with open(LAST_MESSAGE_ID_FILE, 'r') as f:
                message_id = f.read().strip()
                return int(message_id) if message_id else None
        return None
    except Exception as e:
        logger.error(f"خطا در خواندن آخرین شناسه پیام: {e}")
        return None

def should_send_new_message():
    """بررسی اینکه آیا باید پیام جدید ارسال شود یا پیام موجود ویرایش شود"""
    now = get_iran_time_now()
    
    # اگر آخرین پیامی وجود ندارد، پیام جدید ارسال شود
    if get_last_message_id() is None:
        return True
        
    # بررسی زمان‌های مشخص شده برای ارسال پیام جدید
    for send_time in SEND_TIMES:
        current_time = now.time()
        if (
            send_time.hour == current_time.hour and
            abs(send_time.minute - current_time.minute) <= 5
        ):
            return True
            
    return False

async def send_new_price_message(bot, prices):
    """ارسال پیام قیمت جدید"""
    # حذف پیام‌های قبلی
    await find_and_delete_old_price_messages(bot, CHANNEL_ID)

    # ارسال پیام جدید
    message = format_price_message(prices)
    sent_message = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=message,
        parse_mode=ParseMode.HTML
    )
    
    # ذخیره شناسه پیام جدید
    message_id = sent_message.message_id
    save_price_message_id(message_id)
    save_last_message_id(message_id)
    logger.info(f"پیام جدید قیمت با ID {message_id} ارسال شد")
    return True

async def edit_price_message(bot, prices):
    """ویرایش آخرین پیام قیمت"""
    message_id = get_last_message_id()
    if message_id is None:
        logger.warning("هیچ پیام قبلی برای ویرایش یافت نشد")
        return await send_new_price_message(bot, prices)
        
    try:
        # ویرایش پیام موجود
        message = format_price_message(prices)
        await bot.edit_message_text(
            chat_id=CHANNEL_ID,
            message_id=message_id,
            text=message,
            parse_mode=ParseMode.HTML
        )
        logger.info(f"پیام قیمت با ID {message_id} ویرایش شد")
        return True
    except Exception as e:
        logger.error(f"خطا در ویرایش پیام {message_id}: {e}")
        # در صورت خطا، پیام جدید ارسال می‌کنیم
        return await send_new_price_message(bot, prices)

async def update_price_message(bot: Bot):
    """به‌روزرسانی پیام قیمت (ارسال یا ویرایش)"""
    prices = get_all_prices()
    if not prices:
        logger.warning("هیچ قیمتی برای به‌روزرسانی دریافت نشد")
        return False

    # تصمیم‌گیری بین ارسال پیام جدید یا ویرایش پیام قبلی
    if should_send_new_message():
        return await send_new_price_message(bot, prices)
    else:
        return await edit_price_message(bot, prices)

async def schedule_price_updates():
    """زمان‌بندی به‌روزرسانی قیمت‌ها"""
    bot = Bot(token=BOT_TOKEN)
    while True:
        try:
            await update_price_message(bot)
            await asyncio.sleep(60)  # هر یک دقیقه
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی قیمت‌ها: {e}")
            await asyncio.sleep(60)

async def find_and_delete_old_price_messages(bot, channel_id):
    from telegram.error import TelegramError
    try:
        # دریافت شناسه‌های پیام‌های قبلی
        message_ids = get_saved_price_message_ids()
        
        if not message_ids:
            logger.info("هیچ پیام قبلی برای حذف یافت نشد")
            return
            
        logger.info(f"تلاش برای حذف {len(message_ids)} پیام قدیمی...")
        deleted_count = 0
        
        # حذف پیام‌های قبلی به جز آخرین پیام
        last_id = get_last_message_id()
        for msg_id in message_ids:
            if last_id is not None and msg_id == last_id:
                continue  # آخرین پیام را حذف نمی‌کنیم
                
            try:
                await bot.delete_message(chat_id=channel_id, message_id=msg_id)
                logger.info(f"پیام قدیمی با ID {msg_id} حذف شد")
                deleted_count += 1
            except TelegramError as e:
                logger.error(f"خطا در حذف پیام {msg_id}: {e}")
                
        # پاک کردن فایل پس از حذف پیام‌ها (به جز آخرین پیام)
        new_message_ids = []
        if last_id is not None:
            new_message_ids = [last_id]
            
        with open(PRICE_MESSAGES_FILE, 'w') as f:
            json.dump(new_message_ids, f)
            
        logger.info(f"تعداد {deleted_count} پیام حذف شد")
    except Exception as e:
        logger.error(f"خطا در حذف پیام‌های قدیمی: {e}")

def main():
    logger.info("شروع ربات قیمت‌ها...")
    asyncio.run(schedule_price_updates())

if __name__ == '__main__':
    main()