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
    time(19, 0)  # 9:50 PM
]

# فایل ذخیره شناسه پیام‌های مربوط به قیمت
PRICE_MESSAGES_FILE = "price_messages.json"
# فایل ذخیره آخرین شناسه پیام
LAST_MESSAGE_ID_FILE = "last_message_id.txt"
# فایل ذخیره آخرین زمان ارسال پیام جدید
LAST_SEND_TIME_FILE = "last_send_time.txt"

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
        # به message_manager اطلاع بدهیم
        save_latest_message_id(message_id)
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

def save_last_send_time():
    """ذخیره آخرین زمان ارسال پیام جدید"""
    try:
        now = get_iran_time_now()
        with open(LAST_SEND_TIME_FILE, 'w') as f:
            f.write(now.strftime("%Y-%m-%d %H:%M:%S"))
        logger.info(f"آخرین زمان ارسال پیام ذخیره شد: {now}")
    except Exception as e:
        logger.error(f"خطا در ذخیره آخرین زمان ارسال پیام: {e}")

def get_last_send_time():
    """دریافت آخرین زمان ارسال پیام جدید"""
    try:
        if os.path.exists(LAST_SEND_TIME_FILE):
            with open(LAST_SEND_TIME_FILE, 'r') as f:
                time_str = f.read().strip()
                if time_str:
                    # تبدیل به datetime با منطقه زمانی ایران (نه UTC)
                    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    return dt.replace(tzinfo=pytz.timezone('Asia/Tehran'))
        return None
    except Exception as e:
        logger.error(f"خطا در خواندن آخرین زمان ارسال پیام: {e}")
        return None

def should_send_new_message():
    """بررسی اینکه آیا باید پیام جدید ارسال شود یا پیام موجود ویرایش شود"""
    now = get_iran_time_now()
    logger.info(f"بررسی نیاز به ارسال پیام جدید - زمان فعلی: {now.strftime('%H:%M:%S')}")
    
    # اگر آخرین پیامی وجود ندارد، پیام جدید ارسال شود
    if get_last_message_id() is None:
        logger.info("هیچ پیام قبلی وجود ندارد، پیام جدید ارسال خواهد شد")
        return True
    
    # دریافت آخرین زمان ارسال پیام
    last_send_time = get_last_send_time()
    if last_send_time:
        logger.info(f"آخرین زمان ارسال پیام: {last_send_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        logger.info("هیچ زمان ارسال قبلی ثبت نشده است")
    
    # بررسی زمان‌های مشخص شده برای ارسال پیام جدید
    current_time = now.time()
    for send_time in SEND_TIMES:
        logger.info(f"بررسی زمان ارسال {send_time.hour}:{send_time.minute}")
        
        # اگر دقیقاً در زمان مشخص شده هستیم (با محدوده 1 دقیقه)
        if (
            send_time.hour == current_time.hour and
            abs(send_time.minute - current_time.minute) <= 1
        ):
            logger.info(f"دقیقاً در زمان ارسال مشخص شده هستیم ({send_time.hour}:{send_time.minute})")
            # در زمان دقیق مشخص شده، همیشه پیام جدید ارسال می‌کنیم
            return True
            
        # اگر در محدوده گسترده‌تر زمان ارسال هستیم (5 دقیقه)
        elif (
            send_time.hour == current_time.hour and
            abs(send_time.minute - current_time.minute) <= 5
        ):
            logger.info(f"در محدوده زمان ارسال هستیم (±5 دقیقه از {send_time.hour}:{send_time.minute})")
            
            # اگر آخرین زمان ارسال ثبت نشده است
            if last_send_time is None:
                logger.info("هیچ زمان ارسال قبلی ثبت نشده است، پیام جدید ارسال خواهد شد")
                return True
                
            # بررسی تفاوت زمانی
            time_diff = now - last_send_time
            logger.info(f"فاصله زمانی از آخرین ارسال: {time_diff.total_seconds()} ثانیه")
            
            # اگر امروز پیام ارسال نشده یا از آخرین ارسال بیش از 10 دقیقه گذشته
            today = now.date()
            last_send_date = last_send_time.date()
            
            if last_send_date < today or time_diff.total_seconds() > 600:
                logger.info("پیام جدید ارسال خواهد شد (زمان کافی از آخرین ارسال گذشته است)")
                return True
            else:
                logger.info("زمان کافی از آخرین ارسال نگذشته است، پیام ویرایش خواهد شد")
            
    logger.info("خارج از زمان‌های ارسال پیام جدید هستیم، پیام ویرایش خواهد شد")
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
    
    # ذخیره شناسه پیام جدید و زمان ارسال
    message_id = sent_message.message_id
    save_price_message_id(message_id)
    save_last_message_id(message_id)
    save_last_send_time()
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
            
        logger.info(f"تلاش برای حذف {len(message_ids)} پیام قدیمی: {message_ids}")
        deleted_count = 0
        
        # حذف تمام پیام‌های قبلی
        for msg_id in message_ids:
            try:
                await bot.delete_message(chat_id=channel_id, message_id=msg_id)
                logger.info(f"پیام قدیمی با ID {msg_id} حذف شد")
                deleted_count += 1
            except TelegramError as e:
                logger.error(f"خطا در حذف پیام {msg_id}: {e}")
                
        # پاک کردن فایل پس از حذف پیام‌ها
        with open(PRICE_MESSAGES_FILE, 'w') as f:
            json.dump([], f)
            
        logger.info(f"تعداد {deleted_count} پیام حذف شد")
    except Exception as e:
        logger.error(f"خطا در حذف پیام‌های قدیمی: {e}")

def main():
    logger.info("شروع ربات قیمت‌ها...")
    asyncio.run(schedule_price_updates())

if __name__ == '__main__':
    main()