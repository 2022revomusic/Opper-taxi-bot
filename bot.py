import os
import re
import json
import hmac
import hashlib
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone

import aiosqlite
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    FSInputFile,
    MenuButtonWebApp,
)

# =========================================================
# OPPER TAXI
# Professional Telegram Bot + Mini App API
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("opper_taxi")


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID = int(os.getenv("ADMIN_ID", "653914246"))

PORT = int(os.getenv("PORT", "8080"))

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "oper_taxi.db"

UPLOAD_DIR = BASE_DIR / "uploads"
DRIVER_DOCS_DIR = UPLOAD_DIR / "drivers"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DRIVER_DOCS_DIR.mkdir(parents=True, exist_ok=True)


RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

if os.getenv("MINI_APP_URL"):
    MINI_APP_URL = os.getenv("MINI_APP_URL").strip()
elif RAILWAY_DOMAIN:
    MINI_APP_URL = f"https://{RAILWAY_DOMAIN}"
else:
    MINI_APP_URL = "https://opper-taxi-bot-production.up.railway.app"


# =========================================================
# CONSTANTS
# =========================================================

MIN_SEATS = 1
MAX_SEATS = 4

DRIVER_PENDING = "pending"
DRIVER_APPROVED = "approved"
DRIVER_REJECTED = "rejected"

RIDE_ACTIVE = "active"
RIDE_FULL = "full"
RIDE_CANCELLED = "cancelled"
RIDE_FINISHED = "finished"

ORDER_PENDING = "pending"
ORDER_ACCEPTED = "accepted"
ORDER_REJECTED = "rejected"
ORDER_CANCELLED = "cancelled"
ORDER_FINISHED = "finished"


# =========================================================
# REGIONS
# =========================================================

REGIONS = {
    "Toshkent shahri": [
        "Bektemir",
        "Chilonzor",
        "Mirobod",
        "Mirzo Ulug‘bek",
        "Olmazor",
        "Sergeli",
        "Shayxontohur",
        "Uchtepa",
        "Yakkasaroy",
        "Yashnobod",
        "Yunusobod",
        "Yangihayot",
    ],
    "Toshkent viloyati": [
        "Bekobod",
        "Bo‘ka",
        "Chinoz",
        "Ohangaron",
        "Olmaliq",
        "Oqqo‘rg‘on",
        "Parkent",
        "Piskent",
        "Quyi Chirchiq",
        "Toshkent tumani",
        "Yuqori Chirchiq",
        "Zangiota",
    ],
    "Andijon viloyati": [
        "Andijon",
        "Asaka",
        "Baliqchi",
        "Bo‘ston",
        "Buloqboshi",
        "Izboskan",
        "Jalaquduq",
        "Marhamat",
        "Paxtaobod",
        "Qo‘rg‘ontepa",
        "Shahrixon",
        "Ulug‘nor",
        "Xo‘jaobod",
    ],
    "Farg‘ona viloyati": [
        "Farg‘ona",
        "Bag‘dod",
        "Beshariq",
        "Dang‘ara",
        "Furqat",
        "Oltiariq",
        "Qo‘shtepa",
        "Quva",
        "Rishton",
        "So‘x",
        "Toshloq",
        "Uchko‘prik",
        "Yozyovon",
    ],
    "Namangan viloyati": [
        "Namangan",
        "Chortoq",
        "Chust",
        "Kosonsoy",
        "Mingbuloq",
        "Norin",
        "Pop",
        "To‘raqo‘rg‘on",
        "Uchqo‘rg‘on",
        "Uychi",
        "Yangiqo‘rg‘on",
    ],
    "Samarqand viloyati": [
        "Samarqand",
        "Bulung‘ur",
        "Ishtixon",
        "Jomboy",
        "Kattaqo‘rg‘on",
        "Narpay",
        "Nurobod",
        "Oqdaryo",
        "Paxtachi",
        "Pastdarg‘om",
        "Payariq",
        "Urgut",
    ],
    "Buxoro viloyati": [
        "Buxoro",
        "G‘ijduvon",
        "Jondor",
        "Kogon",
        "Olot",
        "Peshku",
        "Qorako‘l",
        "Qorovulbozor",
        "Romitan",
        "Shofirkon",
        "Vobkent",
    ],
    "Qashqadaryo viloyati": [
        "Qarshi",
        "Chiroqchi",
        "Dehqonobod",
        "G‘uzor",
        "Kasbi",
        "Kitob",
        "Koson",
        "Mirishkor",
        "Muborak",
        "Nishon",
        "Shahrisabz",
        "Yakkabog‘",
    ],
    "Surxondaryo viloyati": [
        "Termiz",
        "Angor",
        "Boysun",
        "Denov",
        "Jarqo‘rg‘on",
        "Muzrabot",
        "Oltinsoy",
        "Qiziriq",
        "Qumqo‘rg‘on",
        "Sherobod",
        "Sho‘rchi",
        "Uzun",
    ],
    "Jizzax viloyati": [
        "Jizzax",
        "Arnasoy",
        "Baxmal",
        "Do‘stlik",
        "Forish",
        "G‘allaorol",
        "Mirzacho‘l",
        "Paxtakor",
        "Sharof Rashidov",
        "Zafarobod",
        "Zarbdor",
    ],
    "Sirdaryo viloyati": [
        "Guliston",
        "Boyovut",
        "Oqoltin",
        "Sayxunobod",
        "Sardoba",
        "Sirdaryo",
        "Xovos",
    ],
    "Navoiy viloyati": [
        "Navoiy",
        "Karmana",
        "Konimex",
        "Navbahor",
        "Nurota",
        "Qiziltepa",
        "Tomdi",
        "Uchquduq",
        "Xatirchi",
    ],
    "Xorazm viloyati": [
        "Urganch",
        "Bog‘ot",
        "Gurlan",
        "Hazorasp",
        "Qo‘shko‘pir",
        "Shovot",
        "Tuproqqal’a",
        "Urganch tumani",
        "Xiva",
        "Xonqa",
        "Yangiariq",
        "Yangibozor",
    ],
    "Qoraqalpog‘iston Respublikasi": [
        "Nukus",
        "Amudaryo",
        "Beruniy",
        "Chimboy",
        "Ellikqal’a",
        "Kegeyli",
        "Mo‘ynoq",
        "Qanliko‘l",
        "Qo‘ng‘irot",
        "Shumanay",
        "Taxtako‘pir",
        "To‘rtko‘l",
        "Xo‘jayli",
    ],
}


# =========================================================
# GLOBAL OBJECTS
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# HELPERS
# =========================================================

def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def clean_text(value, max_length=500):
    if value is None:
        return ""

    value = str(value).strip()

    return value[:max_length]


def safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def valid_seats(value):
    seats = safe_int(value, 0)
    return MIN_SEATS <= seats <= MAX_SEATS


def normalize_phone(phone):
    if not phone:
        return ""

    phone = str(phone).strip()

    phone = re.sub(r"[^\d+]", "", phone)

    if phone.startswith("998"):
        phone = "+" + phone

    if not phone.startswith("+"):
        if len(phone) == 9:
            phone = "+998" + phone

    return phone


def safe_filename(name):
    name = str(name or "file")
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    return name[:150]


def json_ok(data=None):
    result = {
        "success": True
    }

    if data:
        result.update(data)

    return web.json_response(result)


def json_error(message, status=400):
    return web.json_response(
        {
            "success": False,
            "error": message
        },
        status=status
    )


async def request_json(request):
    try:
        return await request.json()
    except Exception:
        return {}


# =========================================================
# TELEGRAM WEB APP AUTH
# =========================================================

def validate_telegram_webapp(init_data: str):
    if not init_data:
        return None

    try:
        pairs = []

        for item in init_data.split("&"):
            if "=" not in item:
                continue

            key, value = item.split("=", 1)

            if key == "hash":
                received_hash = value
            else:
                pairs.append((key, value))

        if not received_hash:
            return None

        pairs.sort(key=lambda x: x[0])

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in pairs
        )

        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None

        user_data = dict(pairs)

        if "user" in user_data:
            try:
                user_data["user"] = json.loads(
                    user_data["user"]
                )
            except Exception:
                pass

        return user_data

    except Exception as e:
        logger.exception(
            "Telegram auth error: %s",
            e
        )

        return None


async def get_web_user(request):
    init_data = request.headers.get(
        "X-Telegram-Init-Data",
        ""
    )

    if not init_data:
        init_data = request.query.get(
            "initData",
            ""
        )

    user_data = validate_telegram_webapp(
        init_data
    )

    if not user_data:
        return None

    user = user_data.get("user")

    if not isinstance(user, dict):
        return None

    telegram_id = user.get("id")

    if not telegram_id:
        return None

    return user


async def require_web_user(request):
    user = await get_web_user(request)

    if not user:
        return None, json_error(
            "Telegram foydalanuvchisini tasdiqlash imkoni bo‘lmadi.",
            401
        )

    return user, None


# =========================================================
# DATABASE
# =========================================================

async def db_execute(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, params)
        await db.commit()


async def db_fetchone(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            query,
            params
        )

        row = await cursor.fetchone()

        await cursor.close()

        return row


async def db_fetchall(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            query,
            params
        )

        rows = await cursor.fetchall()

        await cursor.close()

        return rows


async def init_db():

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                car_model TEXT DEFAULT '',
                car_number TEXT DEFAULT '',
                seats INTEGER DEFAULT 1,
                verification_status TEXT DEFAULT 'pending',
                passport_file TEXT DEFAULT '',
                license_file TEXT DEFAULT '',
                tech_passport_file TEXT DEFAULT '',
                car_photo_file TEXT DEFAULT '',
                region TEXT DEFAULT '',
                district TEXT DEFAULT '',
                rejection_reason TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER NOT NULL,
                model TEXT DEFAULT '',
                car_number TEXT DEFAULT '',
                seats INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER NOT NULL,
                driver_telegram_id INTEGER NOT NULL,
                driver_name TEXT DEFAULT '',
                driver_phone TEXT DEFAULT '',
                from_city TEXT DEFAULT '',
                to_city TEXT DEFAULT '',
                from_region TEXT DEFAULT '',
                from_district TEXT DEFAULT '',
                to_region TEXT DEFAULT '',
                to_district TEXT DEFAULT '',
                ride_date TEXT DEFAULT '',
                ride_time TEXT DEFAULT '',
                seats INTEGER DEFAULT 1,
                price INTEGER DEFAULT 0,
                car_model TEXT DEFAULT '',
                car_number TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER NOT NULL,
                passenger_telegram_id INTEGER NOT NULL,
                passenger_name TEXT DEFAULT '',
                passenger_phone TEXT DEFAULT '',
                from_city TEXT DEFAULT '',
                to_city TEXT DEFAULT '',
                from_region TEXT DEFAULT '',
                from_district TEXT DEFAULT '',
                to_region TEXT DEFAULT '',
                to_district TEXT DEFAULT '',
                ride_date TEXT DEFAULT '',
                ride_time TEXT DEFAULT '',
                seats INTEGER DEFAULT 1,
                latitude REAL,
                longitude REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                from_telegram_id INTEGER NOT NULL,
                to_telegram_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(order_id, from_telegram_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                title TEXT DEFAULT '',
                message TEXT DEFAULT '',
                type TEXT DEFAULT '',
                related_id INTEGER DEFAULT 0,
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS passenger_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                passenger_telegram_id INTEGER NOT NULL,
                passenger_name TEXT DEFAULT '',
                passenger_phone TEXT DEFAULT '',
                from_city TEXT DEFAULT '',
                to_city TEXT DEFAULT '',
                from_region TEXT DEFAULT '',
                from_district TEXT DEFAULT '',
                to_region TEXT DEFAULT '',
                to_district TEXT DEFAULT '',
                ride_date TEXT DEFAULT '',
                ride_time TEXT DEFAULT '',
                seats INTEGER DEFAULT 1,
                price INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_telegram_id INTEGER NOT NULL,
                target_telegram_id INTEGER DEFAULT 0,
                order_id INTEGER DEFAULT 0,
                reason TEXT DEFAULT '',
                status TEXT DEFAULT 'new',
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_telegram_id INTEGER NOT NULL,
                action TEXT DEFAULT '',
                target_telegram_id INTEGER DEFAULT 0,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rides_route
            ON rides(from_city, to_city, status)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_passenger
            ON orders(passenger_telegram_id, status)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_ride
            ON orders(ride_id, status)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_user
            ON notifications(telegram_id, is_read)
        """)

        await db.commit()

    logger.info("Database initialized")


# =========================================================
# USER
# =========================================================

async def ensure_user(
    telegram_id,
    username="",
    full_name="",
    phone=""
):

    telegram_id = safe_int(telegram_id)

    old = await db_fetchone(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    current_time = now_str()

    if old:

        await db_execute(
            """
            UPDATE users
            SET
                username = ?,
                full_name = ?,
                phone = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                username,
                full_name,
                phone,
                current_time,
                telegram_id
            )
        )

    else:

        await db_execute(
            """
            INSERT INTO users (
                telegram_id,
                username,
                full_name,
                phone,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                username,
                full_name,
                phone,
                current_time,
                current_time
            )
        )


# =========================================================
# NOTIFICATIONS
# =========================================================

async def create_notification(
    telegram_id,
    title,
    message,
    notification_type="system",
    related_id=0
):

    await db_execute(
        """
        INSERT INTO notifications (
            telegram_id,
            title,
            message,
            type,
            related_id,
            is_read,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, 0, ?)
        """,
        (
            telegram_id,
            title,
            message,
            notification_type,
            related_id,
            now_str()
        )
    )


async def send_notification(
    telegram_id,
    text
):

    try:
        await bot.send_message(
            telegram_id,
            text
        )

    except Exception as e:
        logger.warning(
            "Telegram notification error %s: %s",
            telegram_id,
            e
        )


# =========================================================
# FILE SAVE
# =========================================================

async def save_base64_file(
    telegram_id,
    file_type,
    filename,
    base64_data
):

    try:

        if not base64_data:
            return ""

        if "," in base64_data:
            base64_data = base64_data.split(
                ",",
                1
            )[1]

        import base64

        data = base64.b64decode(
            base64_data
        )

        safe_name = safe_filename(
            filename
        )

        timestamp = int(
            datetime.now().timestamp()
        )

        final_name = (
            f"{telegram_id}_"
            f"{file_type}_"
            f"{timestamp}_"
            f"{safe_name}"
        )

        file_path = (
            DRIVER_DOCS_DIR /
            final_name
        )

        with open(
            file_path,
            "wb"
        ) as f:
            f.write(data)

        return str(file_path)

    except Exception as e:

        logger.exception(
            "File save error: %s",
            e
        )

        return ""


# =========================================================
# BOT KEYBOARD
# =========================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🚕 OPPER TAXI",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    )
                )
            ],
            [
                KeyboardButton(
                    text="🚗 Haydovchi bo‘lish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL + "?mode=driver"
                    )
                ),
                KeyboardButton(
                    text="👤 Yo‘lovchi bo‘lish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL + "?mode=passenger"
                    )
                )
            ],
            [
                KeyboardButton(
                    text="📞 Yordam"
                )
            ]
        ],
        resize_keyboard=True
    )


# =========================================================
# START
# =========================================================

@dp.message(Command("start"))
async def start_handler(message: Message):

    username = (
        message.from_user.username
        if message.from_user
        else ""
    )

    full_name = (
        message.from_user.full_name
        if message.from_user
        else ""
    )

    await ensure_user(
        message.from_user.id,
        username,
        full_name
    )

    text = (
        "🚕 <b>OPPER TAXI</b>\n\n"
        "Shaharlar orasida ishonchli safar toping.\n\n"
        "🚗 Haydovchi sifatida safar joylang\n"
        "👤 Yo‘lovchi sifatida safar toping\n"
        "📱 Barchasini Mini App ichida boshqaring.\n\n"
        "Quyidagi <b>OPPER TAXI</b> tugmasini bosing."
    )

    await message.answer(
        text,
        reply_markup=main_keyboard()
    )


@dp.message(Command("help"))
async def help_handler(message: Message):

    await message.answer(
        "📞 <b>OPPER TAXI yordam</b>\n\n"
        "🚕 Mini App — asosiy xizmat\n"
        "🚗 Haydovchi — safar joylash\n"
        "👤 Yo‘lovchi — safar qidirish\n\n"
        "Muammo bo‘lsa administratorga murojaat qiling.",
        reply_markup=main_keyboard()
    )


@dp.message(F.text == "📞 Yordam")
async def help_button(message: Message):

    await help_handler(message)


# =========================================================
# API: HEALTH
# =========================================================

async def health(request):

    return json_ok({
        "service": "OPPER TAXI",
        "status": "online",
        "time": now_str()
    })


# =========================================================
# API: PROFILE
# =========================================================

async def api_profile(request):

    user, error = await require_web_user(request)

    if error:
        return error

    telegram_id = safe_int(
        user.get("id")
    )

    await ensure_user(
        telegram_id,
        user.get("username", ""),
        (
            f"{user.get('first_name', '')} "
            f"{user.get('last_name', '')}"
        ).strip()
    )

    profile = await db_fetchone(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    rating_row = await db_fetchone(
        """
        SELECT
            AVG(rating) AS avg_rating,
            COUNT(*) AS rating_count
        FROM ratings
        WHERE to_telegram_id = ?
        """,
        (telegram_id,)
    )

    return json_ok({
        "profile": dict(profile) if profile else None,
        "driver": dict(driver) if driver else None,
        "rating": {
            "average": round(
                float(
                    rating_row["avg_rating"] or 0
                ),
                2
            ),
            "count": rating_row["rating_count"] or 0
        }
    })


# =========================================================
# API: PROFILE UPDATE
# =========================================================

async def api_profile_update(request):

    user, error = await require_web_user(request)

    if error:
        return error

    data = await request_json(request)

    telegram_id = safe_int(
        user.get("id")
    )

    full_name = clean_text(
        data.get("full_name"),
        100
    )

    phone = normalize_phone(
        data.get("phone")
    )

    await ensure_user(
        telegram_id,
        user.get("username", ""),
        full_name,
        phone
    )

    return json_ok({
        "message": "Profil yangilandi."
    })


# =========================================================
# API: DRIVER STATUS
# =========================================================

async def api_driver_status(request):

    user, error = await require_web_user(request)

    if error:
        return error

    telegram_id = safe_int(
        user.get("id")
    )

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    if not driver:

        return json_ok({
            "registered": False,
            "driver": None
        })

    return json_ok({
        "registered": True,
        "driver": dict(driver)
    })


# =========================================================
# API: DRIVER REGISTER
# =========================================================

async def api_driver_register(request):

    user, error = await require_web_user(request)

    if error:
        return error

    data = await request_json(request)

    telegram_id = safe_int(
        user.get("id")
    )

    full_name = clean_text(
        data.get("full_name")
        or (
            f"{user.get('first_name', '')} "
            f"{user.get('last_name', '')}"
        ).strip(),
        100
    )

    phone = normalize_phone(
        data.get("phone")
    )

    car_model = clean_text(
        data.get("car_model"),
        100
    )

    car_number = clean_text(
        data.get("car_number"),
        50
    )

    seats = safe_int(
        data.get("seats"),
        0
    )

    region = clean_text(
        data.get("region"),
        100
    )

    district = clean_text(
        data.get("district"),
        100
    )

    if not phone:
        return json_error(
            "Telefon raqamni kiriting."
        )

    if not car_model:
        return json_error(
            "Avtomobil modelini kiriting."
        )

    if not car_number:
        return json_error(
            "Avtomobil raqamini kiriting."
        )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    if region and region not in REGIONS:
        return json_error(
            "Viloyat noto‘g‘ri."
        )

    if region and district:
        if district not in REGIONS.get(
            region,
            []
        ):
            return json_error(
                "Tuman noto‘g‘ri."
            )

    await ensure_user(
        telegram_id,
        user.get("username", ""),
        full_name,
        phone
    )

    existing = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    passport_file = ""

    license_file = ""

    tech_passport_file = ""

    car_photo_file = ""

    if data.get("passport_file"):
        passport_file = await save_base64_file(
            telegram_id,
            "passport",
            data.get(
                "passport_filename",
                "passport.jpg"
            ),
            data.get("passport_file")
        )

    if data.get("license_file"):
        license_file = await save_base64_file(
            telegram_id,
            "license",
            data.get(
                "license_filename",
                "license.jpg"
            ),
            data.get("license_file")
        )

    if data.get("tech_passport_file"):
        tech_passport_file = await save_base64_file(
            telegram_id,
            "tech_passport",
            data.get(
                "tech_passport_filename",
                "tech_passport.jpg"
            ),
            data.get("tech_passport_file")
        )

    if data.get("car_photo_file"):
        car_photo_file = await save_base64_file(
            telegram_id,
            "car",
            data.get(
                "car_photo_filename",
                "car.jpg"
            ),
            data.get("car_photo_file")
        )

    if existing:

        await db_execute(
            """
            UPDATE drivers
            SET
                full_name = ?,
                phone = ?,
                car_model = ?,
                car_number = ?,
                seats = ?,
                region = ?,
                district = ?,
                passport_file =
                    CASE
                        WHEN ? != '' THEN ?
                        ELSE passport_file
                    END,
                license_file =
                    CASE
                        WHEN ? != '' THEN ?
                        ELSE license_file
                    END,
                tech_passport_file =
                    CASE
                        WHEN ? != '' THEN ?
                        ELSE tech_passport_file
                    END,
                car_photo_file =
                    CASE
                        WHEN ? != '' THEN ?
                        ELSE car_photo_file
                    END,
                verification_status = 'pending',
                rejection_reason = '',
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                full_name,
                phone,
                car_model,
                car_number,
                seats,
                region,
                district,

                passport_file,
                passport_file,

                license_file,
                license_file,

                tech_passport_file,
                tech_passport_file,

                car_photo_file,
                car_photo_file,

                now_str(),
                telegram_id
            )
        )

    else:

        await db_execute(
            """
            INSERT INTO drivers (
                telegram_id,
                full_name,
                phone,
                car_model,
                car_number,
                seats,
                verification_status,
                passport_file,
                license_file,
                tech_passport_file,
                car_photo_file,
                region,
                district,
                rejection_reason,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                full_name,
                phone,
                car_model,
                car_number,
                seats,
                DRIVER_PENDING,
                passport_file,
                license_file,
                tech_passport_file,
                car_photo_file,
                region,
                district,
                "",
                now_str(),
                now_str()
            )
        )

    # Admin notification
    try:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Tasdiqlash",
                        callback_data=(
                            f"driver_approve:{telegram_id}"
                        )
                    ),
                    InlineKeyboardButton(
                        text="❌ Rad etish",
                        callback_data=(
                            f"driver_reject:{telegram_id}"
                        )
                    )
                ]
            ]
        )

        await bot.send_message(
            ADMIN_ID,
            (
                "🚗 <b>Yangi haydovchi arizasi</b>\n\n"
                f"👤 {full_name}\n"
                f"📞 {phone}\n"
                f"🚘 {car_model}\n"
                f"🔢 {car_number}\n"
                f"💺 O‘rindiq: {seats}\n"
                f"📍 {region} / {district}\n"
                f"🆔 {telegram_id}"
            ),
            reply_markup=keyboard
        )

        # Documents
        driver = await db_fetchone(
            """
            SELECT *
            FROM drivers
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        if driver:

            files = [
                (
                    driver["passport_file"],
                    "📄 Pasport"
                ),
                (
                    driver["license_file"],
                    "🪪 Haydovchilik guvohnomasi"
                ),
                (
                    driver["tech_passport_file"],
                    "📘 Tex pasport"
                ),
                (
                    driver["car_photo_file"],
                    "🚘 Avtomobil rasmi"
                )
            ]

            for file_path, title in files:

                if file_path and Path(
                    file_path
                ).exists():

                    try:

                        await bot.send_document(
                            ADMIN_ID,
                            FSInputFile(
                                file_path
                            ),
                            caption=title
                        )

                    except Exception as e:

                        logger.warning(
                            "Document send error: %s",
                            e
                        )

    except Exception as e:

        logger.warning(
            "Admin notification error: %s",
            e
        )

    await create_notification(
        telegram_id,
        "Haydovchi arizasi",
        "Arizangiz administratorga yuborildi.",
        "driver"
    )

    return json_ok({
        "message":
            "Arizangiz qabul qilindi. "
            "Administrator tasdiqlashini kuting."
    })


# =========================================================
# API: DRIVER RIDE CREATE
# =========================================================

async def api_driver_ride(request):

    user, error = await require_web_user(request)

    if error:
        return error

    data = await request_json(request)

    telegram_id = safe_int(
        user.get("id")
    )

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    if not driver:
        return json_error(
            "Avval haydovchi sifatida ro‘yxatdan o‘ting."
        )

    if driver["verification_status"] != DRIVER_APPROVED:
        return json_error(
            "Haydovchilik profilingiz hali tasdiqlanmagan."
        )

    seats = safe_int(
        data.get("seats"),
        0
    )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    # Haydovchining mashina sig'imidan oshmasin
    if seats > safe_int(
        driver["seats"],
        1
    ):
        return json_error(
            "O‘rindiqlar soni avtomobilingizdagi "
            "o‘rindiqlar sonidan oshmasligi kerak."
        )

    from_city = clean_text(
        data.get("from_city"),
        100
    )

    to_city = clean_text(
        data.get("to_city"),
        100
    )

    from_region = clean_text(
        data.get("from_region"),
        100
    )

    from_district = clean_text(
        data.get("from_district"),
        100
    )

    to_region = clean_text(
        data.get("to_region"),
        100
    )

    to_district = clean_text(
        data.get("to_district"),
        100
    )

    ride_date = clean_text(
        data.get("ride_date"),
        30
    )

    ride_time = clean_text(
        data.get("ride_time"),
        20
    )

    price = safe_int(
        data.get("price"),
        0
    )

    if not from_city or not to_city:
        return json_error(
            "Qayerdan va qayerga borishingizni kiriting."
        )

    if not ride_date or not ride_time:
        return json_error(
            "Sana va vaqtni kiriting."
        )

    if price <= 0:
        return json_error(
            "Narxni to‘g‘ri kiriting."
        )

    await db_execute(
        """
        INSERT INTO rides (
            driver_id,
            driver_telegram_id,
            driver_name,
            driver_phone,
            from_city,
            to_city,
            from_region,
            from_district,
            to_region,
            to_district,
            ride_date,
            ride_time,
            seats,
            price,
            car_model,
            car_number,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            driver["id"],
            telegram_id,
            driver["full_name"],
            driver["phone"],
            from_city,
            to_city,
            from_region,
            from_district,
            to_region,
            to_district,
            ride_date,
            ride_time,
            seats,
            price,
            driver["car_model"],
            driver["car_number"],
            RIDE_ACTIVE,
            now_str(),
            now_str()
        )
    )

    return json_ok({
        "message": "Safar muvaffaqiyatli joylandi."
    })


# =========================================================
# API: RIDES SEARCH
# =========================================================

async def api_rides(request):

    from_city = clean_text(
        request.query.get(
            "from_city",
            ""
        ),
        100
    )

    to_city = clean_text(
        request.query.get(
            "to_city",
            ""
        ),
        100
    )

    ride_date = clean_text(
        request.query.get(
            "ride_date",
            ""
        ),
        30
    )

    seats = safe_int(
        request.query.get(
            "seats",
            "1"
        ),
        1
    )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    query = """
        SELECT
            r.*,
            (
                SELECT COALESCE(
                    SUM(o.seats),
                    0
                )
                FROM orders o
                WHERE
                    o.ride_id = r.id
                    AND o.status IN ('pending', 'accepted')
            ) AS booked_seats
        FROM rides r
        WHERE r.status = 'active'
    """

    params = []

    if from_city:
        query += """
            AND r.from_city = ?
        """
        params.append(from_city)

    if to_city:
        query += """
            AND r.to_city = ?
        """
        params.append(to_city)

    if ride_date:
        query += """
            AND r.ride_date = ?
        """
        params.append(ride_date)

    query += """
        ORDER BY
            r.ride_date ASC,
            r.ride_time ASC,
            r.id DESC
        LIMIT 100
    """

    rows = await db_fetchall(
        query,
        params
    )

    rides = []

    for row in rows:

        item = dict(row)

        available = (
            safe_int(
                item["seats"]
            )
            -
            safe_int(
                item["booked_seats"]
            )
        )

        item["available_seats"] = max(
            available,
            0
        )

        item["can_order"] = (
            item["available_seats"] >= seats
        )

        rides.append(item)

    return json_ok({
        "rides": rides
    })


# =========================================================
# API: PASSENGER ORDER
# =========================================================

async def api_passenger_order(request):

    user, error = await require_web_user(request)

    if error:
        return error

    data = await request_json(request)

    telegram_id = safe_int(
        user.get("id")
    )

    passenger_name = clean_text(
        data.get("passenger_name")
        or (
            f"{user.get('first_name', '')} "
            f"{user.get('last_name', '')}"
        ).strip(),
        100
    )

    passenger_phone = normalize_phone(
        data.get("passenger_phone")
    )

    ride_id = safe_int(
        data.get("ride_id"),
        0
    )

    seats = safe_int(
        data.get("seats"),
        0
    )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    if not ride_id:
        return json_error(
            "Safar tanlanmagan."
        )

    if not passenger_phone:
        return json_error(
            "Telefon raqamingizni kiriting."
        )

    ride = await db_fetchone(
        """
        SELECT *
        FROM rides
        WHERE id = ?
        """,
        (ride_id,)
    )

    if not ride:
        return json_error(
            "Safar topilmadi."
        )

    if ride["status"] != RIDE_ACTIVE:
        return json_error(
            "Bu safar faol emas."
        )

    if ride["driver_telegram_id"] == telegram_id:
        return json_error(
            "O‘zingizning safaringizga buyurtma bera olmaysiz."
        )

    booked = await db_fetchone(
        """
        SELECT COALESCE(
            SUM(seats),
            0
        ) AS total
        FROM orders
        WHERE
            ride_id = ?
            AND status IN ('pending', 'accepted')
        """,
        (ride_id,)
    )

    booked_seats = safe_int(
        booked["total"],
        0
    )

    available_seats = (
        safe_int(ride["seats"])
        -
        booked_seats
    )

    if seats > available_seats:
        return json_error(
            f"Faqat {max(available_seats, 0)} ta "
            f"bo‘sh o‘rindiq qoldi."
        )

    duplicate = await db_fetchone(
        """
        SELECT *
        FROM orders
        WHERE
            ride_id = ?
            AND passenger_telegram_id = ?
            AND status IN ('pending', 'accepted')
        """,
        (
            ride_id,
            telegram_id
        )
    )

    if duplicate:
        return json_error(
            "Bu safarga allaqachon buyurtma bergansiz."
        )

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    await db_execute(
        """
        INSERT INTO orders (
            ride_id,
            passenger_telegram_id,
            passenger_name,
            passenger_phone,
            from_city,
            to_city,
            from_region,
            from_district,
            to_region,
            to_district,
            ride_date,
            ride_time,
            seats,
            latitude,
            longitude,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ride_id,
            telegram_id,
            passenger_name,
            passenger_phone,
            ride["from_city"],
            ride["to_city"],
            ride["from_region"],
            ride["from_district"],
            ride["to_region"],
            ride["to_district"],
            ride["ride_date"],
            ride["ride_time"],
            seats,
            latitude,
            longitude,
            ORDER_PENDING,
            now_str(),
            now_str()
        )
    )

    order = await db_fetchone(
        """
        SELECT *
        FROM orders
        WHERE
            ride_id = ?
            AND passenger_telegram_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            ride_id,
            telegram_id
        )
    )

    order_id = (
        order["id"]
        if order
        else 0
    )

    await create_notification(
        ride["driver_telegram_id"],
        "Yangi buyurtma",
        (
            f"👤 {passenger_name}\n"
            f"📍 {ride['from_city']} → {ride['to_city']}\n"
            f"💺 {seats} ta o‘rindiq\n"
            f"📞 {passenger_phone}"
        ),
        "order",
        order_id
    )

    await send_notification(
        ride["driver_telegram_id"],
        (
            "🚕 <b>Yangi yo‘lovchi buyurtmasi!</b>\n\n"
            f"👤 {passenger_name}\n"
            f"📍 {ride['from_city']} → {ride['to_city']}\n"
            f"💺 {seats} ta\n"
            f"📞 {passenger_phone}"
        )
    )

    return json_ok({
        "message": "Buyurtma haydovchiga yuborildi.",
        "order_id": order_id
    })


# =========================================================
# API: DRIVER ORDERS
# =========================================================

async def api_driver_orders(request):

    user, error = await require_web_user(request)

    if error:
        return error

    telegram_id = safe_int(
        user.get("id")
    )

    rows = await db_fetchall(
        """
        SELECT
            o.*,
            r.driver_name,
            r.driver_phone,
            r.car_model,
            r.car_number
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        WHERE
            r.driver_telegram_id = ?
        ORDER BY o.id DESC
        LIMIT 100
        """,
        (telegram_id,)
    )

    return json_ok({
        "orders": [
            dict(row)
            for row in rows
        ]
    })


# =========================================================
# API: ACCEPT ORDER
# =========================================================

async def accept_order(request):

    user, error = await require_web_user(request)

    if error:
        return error

    data = await request_json(request)

    telegram_id = safe_int(
        user.get("id")
    )

    order_id = safe_int(
        data.get("order_id"),
        0
    )

    if not order_id:
        return json_error(
            "Buyurtma topilmadi."
        )

    order = await db_fetchone(
        """
        SELECT
            o.*,
            r.driver_telegram_id,
            r.seats AS ride_seats
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        WHERE o.id = ?
        """,
        (order_id,)
    )

    if not order:
        return json_error(
            "Buyurtma topilmadi."
        )

    if order["driver_telegram_id"] != telegram_id:
        return json_error(
            "Bu buyurtmani boshqarish huquqingiz yo‘q.",
            403
        )

    if order["status"] != ORDER_PENDING:
        return json_error(
            "Bu buyurtma endi faol emas."
        )

    booked = await db_fetchone(
        """
        SELECT COALESCE(
            SUM(seats),
            0
        ) AS total
        FROM orders
        WHERE
            ride_id = ?
            AND status = 'accepted'
        """,
        (order["ride_id"],)
    )

    booked_seats = safe_int(
        booked["total"],
        0
    )

    if (
        booked_seats
        +
        safe_int(order["seats"])
        >
        safe_int(order["ride_seats"])
    ):
        return json_error(
            "Bu safarda yetarli o‘rindiq qolmagan."
        )

    await db_execute(
        """
        UPDATE orders
        SET
            status = 'accepted',
            updated_at = ?
        WHERE id = ?
        """,
        (
            now_str(),
            order_id
        )
    )

    await create_notification(
        order["passenger_telegram_id"],
        "Buyurtma qabul qilindi",
        (
            f"🚕 Haydovchi buyurtmangizni qabul qildi.\n"
            f"📍 {order['from_city']} → "
            f"{order['to_city']}"
        ),
        "order",
        order_id
    )

    await send_notification(
        order["passenger_telegram_id"],
        (
            "✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
            f"📍 {order['from_city']} → "
            f"{order['to_city']}\n"
            f"💺 {order['seats']} ta"
        )
    )

    return json_ok({
        "message": "Buyurtma qabul qilindi."
    })


# =========================================================
# API: REJECT ORDER
# =========================================================

async def reject_order(request):

    user, error = await require_web_user(request)

    if error:
        return error

    data = await request_json(request)

    telegram_id = safe_int(
        user.get("id")
    )

    order_id = safe_int(
        data.get("order_id"),
        0
    )

    order = await db_fetchone(
        """
        SELECT
            o.*,
            r.driver_telegram_id
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        WHERE o.id = ?
        """,
        (order_id,)
    )

    if not order:
        return json_error(
            "Buyurtma topilmadi."
        )

    if order["driver_telegram_id"] != telegram_id:
        return json_error(
            "Ruxsat yo‘q.",
            403
        )

    if order["status"] != ORDER_PENDING:
        return json_error(
            "Buyurtma faol emas."
        )

    await db_execute(
        """
        UPDATE orders
        SET
            status = 'rejected',
            updated_at = ?
        WHERE id = ?
        """,
        (
            now_str(),
            order_id
        )
    )

    await create_notification(
        order["passenger_telegram_id"],
        "Buyurtma rad etildi",
        (
            f"❌ Haydovchi buyurtmangizni rad etdi.\n"
            f"📍 {order['from_city']} → "
            f"{order['to_city']}"
        ),
        "order",
        order_id
    )

    await send_notification(
        order["passenger_telegram_id"],
        (
            "❌ <b>Buyurtma rad etildi.</b>\n\n"
            "Boshqa safarni qidirishingiz mumkin."
        )
    )

    return json_ok({
        "message": "Buyurtma rad etildi."
    })


# =========================================================
# API: MY ORDERS
# =========================================================

async def api_my_orders(request):

    user, error = await require_web_user(request)

    if error:
        return error

    telegram_id = safe_int(
        user.get("id")
    )

    rows = await db_fetchall(
        """
        SELECT
            o.*,
            r.driver_name,
            r.driver_phone,
            r.car_model,
            r.car_number,
            r.price
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        WHERE
            o.passenger_telegram_id = ?
        ORDER BY o.id DESC
        LIMIT 100
        """,
        (telegram_id,)
    )

    return json_ok({
        "orders": [
            dict(row)
            for row in rows
        ]
    })


# =========================================================
# API: CANCEL ORDER
# =========================================================

async def api_cancel_order(request):

    user, error = await require_web_user(request)

    if error:
        return error

    data = await request_json(request)

    telegram_id = safe_int(
        user.get("id")
    )

    order_id = safe_int(
        data.get("order_id"),
        0
    )

    order = await db_fetchone(
        """
        SELECT *
        FROM orders
        WHERE id = ?
        """,
        (order_id,)
    )

    if not order:
        return json_error(
            "Buyurtma topilmadi."
        )

    if order["passenger_telegram_id"] != telegram_id:
        return json_error(
            "Bu buyurtmani bekor qilish huquqingiz yo‘q.",
            403
        )

    if order["status"] not in (
        ORDER_PENDING,
        ORDER_ACCEPTED
    ):
        return json_error(
            "Bu buyurtmani bekor qilib bo‘lmaydi."
        )

    await db_execute(
        """
        UPDATE orders
        SET
            status = 'cancelled',
            updated_at = ?
        WHERE id = ?
        """,
        (
            now_str(),
            order_id
        )
    )

    ride = await db_fetchone(
        """
        SELECT driver_telegram_id
        FROM rides
        WHERE id = ?
        """,
        (order["ride_id"],)
    )

    if ride:

        await create_notification(
            ride["driver_telegram_id"],
            "Buyurtma bekor qilindi",
            (
                f"Yo‘lovchi buyurtmani bekor qildi.\n"
                f"📍 {order['from_city']} → "
                f"{order['to_city']}"
            ),
            "order",
            order_id
        )

        await send_notification(
            ride["driver_telegram_id"],
            "❌ Yo‘lovchi buyurtmani bekor qildi."
        )

    return json_ok({
        "message": "Buyurtma bekor qilindi."
    })


# =========================================================
# API: NOTIFICATIONS
# =========================================================

async def api_notifications(request):

    user, error = await require_web_user(request)

    if error:
        return error

    telegram_id = safe_int(
        user.get("id")
    )

    rows = await db_fetchall(
        """
        SELECT *
        FROM notifications
        WHERE telegram_id = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        (telegram_id,)
    )

    unread = await db_fetchone(
        """
        SELECT COUNT(*) AS total
        FROM notifications
        WHERE
            telegram_id = ?
            AND is_read = 0
        """,
        (telegram_id,)
    )

    return json_ok({
        "notifications": [
            dict(row)
            for row in rows
        ],
        "unread": (
            unread["total"]
            if unread
            else 0
        )
    })


# =========================================================
# API: MARK NOTIFICATIONS READ
# =========================================================

async def api_notifications_read(request):

    user, error = await require_web_user(request)

    if error:
        return error

    telegram_id = safe_int(
        user.get("id")
    )

    await db_execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    return json_ok({
        "message": "Bildirishnomalar o‘qilgan deb belgilandi."
    })


# =========================================================
# API: RATING
# =========================================================

async def api_rating(request):

    user, error = await require_web_user(request)

    if error:
        return error

    data = await request_json(request)

    telegram_id = safe_int(
        user.get("id")
    )

    order_id = safe_int(
        data.get("order_id"),
        0
    )

    rating = safe_int(
        data.get("rating"),
        0
    )

    comment = clean_text(
        data.get("comment"),
        500
    )

    if rating < 1 or rating > 5:
        return json_error(
            "Reyting 1–5 oralig‘ida bo‘lishi kerak."
        )

    order = await db_fetchone(
        """
        SELECT *
        FROM orders
        WHERE id = ?
        """,
        (order_id,)
    )

    if not order:
        return json_error(
            "Buyurtma topilmadi."
        )

    if order["passenger_telegram_id"] != telegram_id:
        return json_error(
            "Bu buyurtmaga reyting bera olmaysiz.",
            403
        )

    if order["status"] != ORDER_ACCEPTED:
        return json_error(
            "Faqat qabul qilingan buyurtmaga reyting berish mumkin."
        )

    ride = await db_fetchone(
        """
        SELECT driver_telegram_id
        FROM rides
        WHERE id = ?
        """,
        (order["ride_id"],)
    )

    if not ride:
        return json_error(
            "Haydovchi topilmadi."
        )

    try:

        await db_execute(
            """
            INSERT INTO ratings (
                order_id,
                from_telegram_id,
                to_telegram_id,
                rating,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                telegram_id,
                ride["driver_telegram_id"],
                rating,
                comment,
                now_str()
            )
        )

    except Exception:

        return json_error(
            "Bu buyurtmaga allaqachon reyting bergansiz."
        )

    await create_notification(
        ride["driver_telegram_id"],
        "Yangi reyting",
        f"⭐ Sizga {rating}/5 reyting berildi.",
        "rating",
        order_id
    )

    return json_ok({
        "message": "Reyting qabul qilindi."
    })


# =========================================================
# API: PASSENGER REQUEST
# =========================================================

async def api_passenger_request(request):

    user, error = await require_web_user(request)

    if error:
        return error

    data = await request_json(request)

    telegram_id = safe_int(
        user.get("id")
    )

    passenger_name = clean_text(
        data.get("passenger_name")
        or (
            f"{user.get('first_name', '')} "
            f"{user.get('last_name', '')}"
        ).strip(),
        100
    )

    passenger_phone = normalize_phone(
        data.get("passenger_phone")
    )

    seats = safe_int(
        data.get("seats"),
        0
    )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    if not passenger_phone:
        return json_error(
            "Telefon raqamingizni kiriting."
        )

    from_city = clean_text(
        data.get("from_city"),
        100
    )

    to_city = clean_text(
        data.get("to_city"),
        100
    )

    if not from_city or not to_city:
        return json_error(
            "Qayerdan va qayerga borishingizni kiriting."
        )

    price = safe_int(
        data.get("price"),
        0
    )

    await ensure_user(
        telegram_id,
        user.get("username", ""),
        passenger_name,
        passenger_phone
    )

    await db_execute(
        """
        INSERT INTO passenger_requests (
            passenger_telegram_id,
            passenger_name,
            passenger_phone,
            from_city,
            to_city,
            from_region,
            from_district,
            to_region,
            to_district,
            ride_date,
            ride_time,
            seats,
            price,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            passenger_name,
            passenger_phone,
            from_city,
            to_city,
            clean_text(
                data.get("from_region"),
                100
            ),
            clean_text(
                data.get("from_district"),
                100
            ),
            clean_text(
                data.get("to_region"),
                100
            ),
            clean_text(
                data.get("to_district"),
                100
            ),
            clean_text(
                data.get("ride_date"),
                30
            ),
            clean_text(
                data.get("ride_time"),
                20
            ),
            seats,
            price,
            "active",
            now_str(),
            now_str()
        )
    )

    return json_ok({
        "message": "Yo‘lovchi so‘rovi joylandi."
    })


# =========================================================
# API: DRIVER REQUESTS
# =========================================================

async def api_driver_requests(request):

    user, error = await require_web_user(request)

    if error:
        return error

    telegram_id = safe_int(
        user.get("id")
    )

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    if not driver:
        return json_error(
            "Haydovchi topilmadi."
        )

    if driver["verification_status"] != DRIVER_APPROVED:
        return json_error(
            "Haydovchi profilingiz tasdiqlanmagan."
        )

    rows = await db_fetchall(
        """
        SELECT *
        FROM passenger_requests
        WHERE status = 'active'
        ORDER BY id DESC
        LIMIT 100
        """
    )

    return json_ok({
        "requests": [
            dict(row)
            for row in rows
        ]
    })


# =========================================================
# API: ADMIN STATS
# =========================================================

async def api_admin_stats(request):

    user, error = await require_web_user(request)

    if error:
        return error

    telegram_id = safe_int(
        user.get("id")
    )

    if telegram_id != ADMIN_ID:
        return json_error(
            "Admin huquqi talab qilinadi.",
            403
        )

    users = await db_fetchone(
        "SELECT COUNT(*) AS total FROM users"
    )

    drivers = await db_fetchone(
        "SELECT COUNT(*) AS total FROM drivers"
    )

    pending_drivers = await db_fetchone(
        """
        SELECT COUNT(*) AS total
        FROM drivers
        WHERE verification_status = 'pending'
        """
    )

    rides = await db_fetchone(
        "SELECT COUNT(*) AS total FROM rides"
    )

    orders = await db_fetchone(
        "SELECT COUNT(*) AS total FROM orders"
    )

    active_orders = await db_fetchone(
        """
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status IN ('pending', 'accepted')
        """
    )

    return json_ok({
        "users": users["total"],
        "drivers": drivers["total"],
        "pending_drivers": pending_drivers["total"],
        "rides": rides["total"],
        "orders": orders["total"],
        "active_orders": active_orders["total"]
    })


# =========================================================
# ADMIN CALLBACKS
# =========================================================

@dp.callback_query(
    F.data.startswith("driver_approve:")
)
async def admin_driver_approve(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Sizda ruxsat yo‘q.",
            show_alert=True
        )

        return

    telegram_id = safe_int(
        callback.data.split(
            ":",
            1
        )[1],
        0
    )

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    if not driver:

        await callback.answer(
            "Haydovchi topilmadi.",
            show_alert=True
        )

        return

    await db_execute(
        """
        UPDATE drivers
        SET
            verification_status = 'approved',
            rejection_reason = '',
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            now_str(),
            telegram_id
        )
    )

    await db_execute(
        """
        INSERT INTO admin_actions (
            admin_telegram_id,
            action,
            target_telegram_id,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            ADMIN_ID,
            "driver_approve",
            telegram_id,
            "Driver approved",
            now_str()
        )
    )

    await create_notification(
        telegram_id,
        "Haydovchi tasdiqlandi",
        "🎉 Haydovchilik profilingiz tasdiqlandi.",
        "driver"
    )

    await send_notification(
        telegram_id,
        (
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Sizning haydovchilik profilingiz "
            "administrator tomonidan tasdiqlandi.\n\n"
            "Endi OPPER TAXI orqali safar joylashingiz mumkin."
        )
    )

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:
        pass

    await callback.answer(
        "Haydovchi tasdiqlandi."
    )


@dp.callback_query(
    F.data.startswith("driver_reject:")
)
async def admin_driver_reject(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Sizda ruxsat yo‘q.",
            show_alert=True
        )

        return

    telegram_id = safe_int(
        callback.data.split(
            ":",
            1
        )[1],
        0
    )

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    if not driver:

        await callback.answer(
            "Haydovchi topilmadi.",
            show_alert=True
        )

        return

    await db_execute(
        """
        UPDATE drivers
        SET
            verification_status = 'rejected',
            rejection_reason = 'Administrator tomonidan rad etildi',
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            now_str(),
            telegram_id
        )
    )

    await db_execute(
        """
        INSERT INTO admin_actions (
            admin_telegram_id,
            action,
            target_telegram_id,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            ADMIN_ID,
            "driver_reject",
            telegram_id,
            "Driver rejected",
            now_str()
        )
    )

    await create_notification(
        telegram_id,
        "Haydovchi arizasi",
        (
            "❌ Haydovchi arizangiz rad etildi.\n"
            "Ma’lumotlarni tekshirib qayta yuborishingiz mumkin."
        ),
        "driver"
    )

    await send_notification(
        telegram_id,
        (
            "❌ <b>Haydovchi arizangiz rad etildi.</b>\n\n"
            "Ma’lumotlarni tekshirib, Mini App orqali "
            "qayta yuborishingiz mumkin."
        )
    )

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:
        pass

    await callback.answer(
        "Haydovchi rad etildi."
    )


# =========================================================
# WEB: INDEX
# =========================================================

async def index_handler(request):

    index_file = BASE_DIR / "index.html"

    if not index_file.exists():

        return web.Response(
            text=(
                "OPPER TAXI Mini App index.html topilmadi."
            ),
            status=404
        )

    return web.FileResponse(
        index_file
    )


# =========================================================
# WEB APP SETUP
# =========================================================

def setup_routes(app):

    # Frontend
    app.router.add_get(
        "/",
        index_handler
    )

    app.router.add_get(
        "/app",
        index_handler
    )

    # Health
    app.router.add_get(
        "/health",
        health
    )

    # Profile
    app.router.add_get(
        "/api/profile",
        api_profile
    )

    app.router.add_post(
        "/api/profile/update",
        api_profile_update
    )

    # Driver
    app.router.add_get(
        "/api/driver/status",
        api_driver_status
    )

    app.router.add_post(
        "/api/driver/register",
        api_driver_register
    )

    app.router.add_post(
        "/api/driver/ride",
        api_driver_ride
    )

    app.router.add_get(
        "/api/driver/orders",
        api_driver_orders
    )

    app.router.add_get(
        "/api/driver/requests",
        api_driver_requests
    )

    # Rides
    app.router.add_get(
        "/api/rides",
        api_rides
    )

    # Passenger
    app.router.add_post(
        "/api/passenger/order",
        api_passenger_order
    )

    app.router.add_post(
        "/api/passenger/request",
        api_passenger_request
    )

    # Orders
    app.router.add_get(
        "/api/orders",
        api_my_orders
    )

    # IMPORTANT:
    # Old xato shu yerda edi.
    # Endi to'g'ri:
    app.router.add_post(
        "/api/order/accept",
        accept_order
    )

    app.router.add_post(
        "/api/order/reject",
        reject_order
    )

    app.router.add_post(
        "/api/order/cancel",
        api_cancel_order
    )

    # Notifications
    app.router.add_get(
        "/api/notifications",
        api_notifications
    )

    app.router.add_post(
        "/api/notifications/read",
        api_notifications_read
    )

    # Rating
    app.router.add_post(
        "/api/rating",
        api_rating
    )

    # Admin
    app.router.add_get(
        "/api/admin/stats",
        api_admin_stats
    )


# =========================================================
# START WEB SERVER
# =========================================================

async def start_web_server():

    app = web.Application()

    setup_routes(app)

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=PORT
    )

    await site.start()

    logger.info(
        "Web server started on port %s",
        PORT
    )

    logger.info(
        "Mini App URL: %s",
        MINI_APP_URL
    )

    return runner


# =========================================================
# BOT MENU
# =========================================================

async def setup_bot():

    try:

        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🚕 OPPER TAXI",
                web_app=WebAppInfo(
                    url=MINI_APP_URL
                )
            )
        )

    except Exception as e:

        logger.warning(
            "Menu button error: %s",
            e
        )


# =========================================================
# MAIN
# =========================================================

async def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN topilmadi. "
            "Railway Variables ichiga BOT_TOKEN qo‘ying."
        )

    logger.info(
        "Starting OPPER TAXI..."
    )

    await init_db()

    await setup_bot()

    runner = await start_web_server()

    try:

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        logger.info(
            "Bot polling started."
        )

        await dp.start_polling(
            bot
        )

    finally:

        await runner.cleanup()

        await bot.session.close()

        logger.info(
            "OPPER TAXI stopped."
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "Stopped by user."
        )

    except Exception as e:

        logger.exception(
            "Fatal error: %s",
            e
        )
