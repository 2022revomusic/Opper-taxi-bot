import os
import re
import json
import hmac
import hashlib
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timezone

import aiosqlite
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    MenuButtonWebApp,
    BotCommand,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.types import FSInputFile


# ============================================================
# OPPER TAXI
# Professional Telegram Mini App Backend
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "653914246"))
except Exception:
    ADMIN_ID = 653914246

PORT = int(os.getenv("PORT", "8080"))

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
DB_PATH = BASE_DIR / "oper_taxi.db"

UPLOAD_DIR = BASE_DIR / "uploads"
DRIVER_DOCS_DIR = UPLOAD_DIR / "drivers"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DRIVER_DOCS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# MINI APP URL
# ============================================================

MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()

if not MINI_APP_URL:
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

    if railway_domain:
        if railway_domain.startswith("http"):
            MINI_APP_URL = railway_domain
        else:
            MINI_APP_URL = f"https://{railway_domain}"

if not MINI_APP_URL:
    MINI_APP_URL = "https://opper-taxi-bot-production.up.railway.app"


# ============================================================
# TELEGRAM
# ============================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# CONSTANTS
# ============================================================

MIN_SEATS = 1
MAX_SEATS = 4

RIDE_ACTIVE = "active"
RIDE_CANCELLED = "cancelled"
RIDE_COMPLETED = "completed"

ORDER_PENDING = "pending"
ORDER_ACCEPTED = "accepted"
ORDER_REJECTED = "rejected"
ORDER_CANCELLED = "cancelled"
ORDER_COMPLETED = "completed"

DRIVER_PENDING = "pending"
DRIVER_APPROVED = "approved"
DRIVER_REJECTED = "rejected"
DRIVER_BLOCKED = "blocked"


# ============================================================
# REGIONS / DISTRICTS
# ============================================================

REGIONS = {
    "Toshkent shahri": [
        "Chilonzor",
        "Yunusobod",
        "Mirzo Ulug‘bek",
        "Mirobod",
        "Shayxontohur",
        "Olmazor",
        "Sergeli",
        "Bektemir",
        "Yakkasaroy",
        "Uchtepa",
        "Yashnobod",
        "Yangihayot",
    ],

    "Toshkent viloyati": [
        "Bekobod",
        "Bo‘ka",
        "Chinoz",
        "Ohangaron",
        "Oqqo‘rg‘on",
        "Parkent",
        "Piskent",
        "Quyi Chirchiq",
        "Toshkent tumani",
        "Yangiyo‘l",
        "Yuqori Chirchiq",
        "Zangiota",
        "Qibray",
    ],

    "Farg‘ona viloyati": [
        "Bag‘dod",
        "Beshariq",
        "Buvayda",
        "Dang‘ara",
        "Farg‘ona tumani",
        "Furqat",
        "Oltiariq",
        "Qo‘shtepa",
        "Quva",
        "Rishton",
        "So‘x",
        "Toshloq",
        "Uchko‘prik",
        "Yozyovon",
        "Marg‘ilon shahri",
        "Farg‘ona shahri",
        "Qo‘qon shahri",
    ],

    "Andijon viloyati": [
        "Andijon tumani",
        "Asaka",
        "Baliqchi",
        "Bo‘z",
        "Buloqboshi",
        "Izboskan",
        "Jalaquduq",
        "Marhamat",
        "Oltinko‘l",
        "Paxtaobod",
        "Qo‘rg‘ontepa",
        "Shahrixon",
        "Ulug‘nor",
        "Xo‘jaobod",
        "Andijon shahri",
    ],

    "Namangan viloyati": [
        "Chortoq",
        "Chust",
        "Kosonsoy",
        "Mingbuloq",
        "Namangan tumani",
        "Norin",
        "Pop",
        "To‘raqo‘rg‘on",
        "Uchqo‘rg‘on",
        "Uychi",
        "Yangiqo‘rg‘on",
        "Namangan shahri",
    ],

    "Sirdaryo viloyati": [
        "Boyovut",
        "Guliston",
        "Mirzaobod",
        "Oqoltin",
        "Sayxunobod",
        "Sardoba",
        "Sirdaryo tumani",
        "Xovos",
    ],

    "Jizzax viloyati": [
        "Arnasoy",
        "Baxmal",
        "Do‘stlik",
        "Forish",
        "G‘allaorol",
        "Jizzax tumani",
        "Mirzacho‘l",
        "Paxtakor",
        "Yangiobod",
        "Zafarobod",
        "Zarbdor",
    ],

    "Samarqand viloyati": [
        "Bulung‘ur",
        "Ishtixon",
        "Jomboy",
        "Kattaqo‘rg‘on",
        "Kattaqo‘rg‘on shahri",
        "Narpay",
        "Nurobod",
        "Oqdaryo",
        "Pastdarg‘om",
        "Paxtachi",
        "Payariq",
        "Qo‘shrabot",
        "Samarqand tumani",
        "Samarqand shahri",
        "Toyloq",
        "Urgut",
    ],

    "Qashqadaryo viloyati": [
        "Chiroqchi",
        "Dehqonobod",
        "G‘uzor",
        "Kasbi",
        "Kitob",
        "Koson",
        "Mirishkor",
        "Muborak",
        "Nishon",
        "Qamashi",
        "Qarshi tumani",
        "Qarshi shahri",
        "Shahrisabz",
        "Yakkabog‘",
    ],

    "Surxondaryo viloyati": [
        "Angor",
        "Boysun",
        "Denov",
        "Jarqo‘rg‘on",
        "Muzrabot",
        "Oltinsoy",
        "Qiziriq",
        "Qumqo‘rg‘on",
        "Sariosiyo",
        "Sherobod",
        "Sho‘rchi",
        "Termiz tumani",
        "Termiz shahri",
        "Uzun",
    ],

    "Buxoro viloyati": [
        "Buxoro tumani",
        "Buxoro shahri",
        "G‘ijduvon",
        "Jondor",
        "Kogon",
        "Kogon shahri",
        "Olot",
        "Peshku",
        "Qorako‘l",
        "Qorovulbozor",
        "Romitan",
        "Shofirkon",
        "Vobkent",
    ],

    "Navoiy viloyati": [
        "Karmana",
        "Konimex",
        "Navbahor",
        "Navoiy shahri",
        "Nurota",
        "Qiziltepa",
        "Tomdi",
        "Uchquduq",
        "Xatirchi",
    ],

    "Xorazm viloyati": [
        "Bog‘ot",
        "Gurlan",
        "Hazorasp",
        "Honqa",
        "Qo‘shko‘pir",
        "Shovot",
        "Tuproqqal’a",
        "Urganch tumani",
        "Urganch shahri",
        "Xiva",
        "Xiva shahri",
        "Yangiariq",
        "Yangibozor",
    ],

    "Qoraqalpog‘iston Respublikasi": [
        "Amudaryo",
        "Beruniy",
        "Chimboy",
        "Ellikqal’a",
        "Kegeyli",
        "Mo‘ynoq",
        "Nukus tumani",
        "Nukus shahri",
        "Qanliko‘l",
        "Qo‘ng‘irot",
        "Shumanay",
        "Taxtako‘pir",
        "To‘rtko‘l",
        "Xo‘jayli",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_phone(phone):
    phone = clean_text(phone)
    digits = re.sub(r"\D", "", phone)

    if digits.startswith("998"):
        return "+" + digits

    if len(digits) == 9:
        return "+998" + digits

    return phone


def safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except Exception:
        return default


def valid_seats(value):
    seats = safe_int(value, 0)
    return MIN_SEATS <= seats <= MAX_SEATS


def valid_location(region, district):
    region = clean_text(region)
    district = clean_text(district)

    return (
        region in REGIONS
        and district in REGIONS[region]
    )


def safe_filename(name):
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(name))
    return name[:100]


def json_ok(data=None):
    result = {"ok": True}

    if data:
        result.update(data)

    return web.json_response(result)


def json_error(message, status=400):
    return web.json_response(
        {
            "ok": False,
            "error": message
        },
        status=status
    )


# ============================================================
# TELEGRAM MINI APP AUTHENTICATION
# ============================================================

def validate_init_data(init_data):
    if not init_data:
        return None

    try:
        from urllib.parse import parse_qsl

        parsed = dict(
            parse_qsl(
                init_data,
                keep_blank_values=True
            )
        )

        received_hash = parsed.pop("hash", None)

        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{key}={parsed[key]}"
            for key in sorted(parsed)
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

        user_json = parsed.get("user")

        if not user_json:
            return None

        return json.loads(user_json)

    except Exception as e:
        logging.error(
            "INIT DATA ERROR: %s",
            e
        )

        return None


async def get_telegram_user(request):
    data = {}

    try:
        if request.method == "POST":
            data = await request.json()
        else:
            data = dict(request.query)
    except Exception:
        data = {}

    init_data = (
        data.get("init_data")
        or request.headers.get("X-Telegram-Init-Data")
        or request.headers.get("X-Telegram-InitData")
    )

    return validate_init_data(init_data)


async def ensure_user(telegram_user):
    if not telegram_user:
        return None

    telegram_id = int(telegram_user["id"])

    username = clean_text(
        telegram_user.get("username")
    )

    first_name = clean_text(
        telegram_user.get("first_name")
    )

    last_name = clean_text(
        telegram_user.get("last_name")
    )

    full_name = (
        f"{first_name} {last_name}"
    ).strip()

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT INTO users
            (
                telegram_id,
                username,
                full_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                updated_at = excluded.updated_at
            """,
            (
                telegram_id,
                username,
                full_name,
                now_str(),
                now_str()
            )
        )

        await db.commit()

    return telegram_id


# ============================================================
# DATABASE
# ============================================================

async def init_db():

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("PRAGMA journal_mode=WAL")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                is_blocked INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                region TEXT DEFAULT '',
                district TEXT DEFAULT '',
                verification_status TEXT DEFAULT 'pending',
                verification_reason TEXT DEFAULT '',
                passport_file TEXT DEFAULT '',
                license_file TEXT DEFAULT '',
                tech_passport_file TEXT DEFAULT '',
                car_photo_file TEXT DEFAULT '',
                rating REAL DEFAULT 5.0,
                rating_count INTEGER DEFAULT 0,
                trips_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_telegram_id INTEGER UNIQUE NOT NULL,
                model TEXT DEFAULT '',
                number TEXT DEFAULT '',
                seats INTEGER DEFAULT 4,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER,
                driver_telegram_id INTEGER NOT NULL,
                from_region TEXT NOT NULL,
                from_district TEXT NOT NULL,
                to_region TEXT NOT NULL,
                to_district TEXT NOT NULL,
                ride_date TEXT NOT NULL,
                ride_time TEXT NOT NULL,
                seats INTEGER NOT NULL,
                price INTEGER NOT NULL,
                car_model TEXT DEFAULT '',
                car_number TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER NOT NULL,
                passenger_telegram_id INTEGER NOT NULL,
                passenger_name TEXT DEFAULT '',
                passenger_phone TEXT DEFAULT '',
                seats INTEGER NOT NULL,
                latitude REAL,
                longitude REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER NOT NULL,
                order_id INTEGER,
                driver_telegram_id INTEGER NOT NULL,
                passenger_telegram_id INTEGER NOT NULL,
                stars INTEGER NOT NULL,
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(order_id)
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                title TEXT DEFAULT '',
                message TEXT DEFAULT '',
                type TEXT DEFAULT '',
                related_id INTEGER,
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS passenger_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                passenger_telegram_id INTEGER NOT NULL,
                passenger_name TEXT DEFAULT '',
                passenger_phone TEXT DEFAULT '',
                from_region TEXT NOT NULL,
                from_district TEXT NOT NULL,
                to_region TEXT NOT NULL,
                to_district TEXT NOT NULL,
                ride_date TEXT NOT NULL,
                ride_time TEXT NOT NULL,
                seats INTEGER NOT NULL,
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'open',
                accepted_driver_telegram_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_telegram_id INTEGER NOT NULL,
                target_telegram_id INTEGER,
                order_id INTEGER,
                reason TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_telegram_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_telegram_id INTEGER,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_rides_route
            ON rides(
                from_region,
                from_district,
                to_region,
                to_district
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_orders_ride
            ON orders(ride_id)
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notifications_user
            ON notifications(telegram_id, is_read)
            """
        )

        await db.commit()

    logging.info("DATABASE READY")


# ============================================================
# NOTIFICATIONS
# ============================================================

async def create_notification(
    telegram_id,
    title,
    message,
    notification_type="system",
    related_id=None
):

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT INTO notifications
            (
                telegram_id,
                title,
                message,
                type,
                related_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
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

        await db.commit()


async def send_telegram_notification(
    telegram_id,
    text,
    keyboard=None
):
    try:
        await bot.send_message(
            telegram_id,
            text,
            reply_markup=keyboard
        )
    except Exception as e:
        logging.warning(
            "Telegram notification failed %s: %s",
            telegram_id,
            e
        )


# ============================================================
# BOT KEYBOARD
# ============================================================

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
                        url=f"{MINI_APP_URL}?mode=driver"
                    )
                ),
                KeyboardButton(
                    text="👤 Yo‘lovchi bo‘lish",
                    web_app=WebAppInfo(
                        url=f"{MINI_APP_URL}?mode=passenger"
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


# ============================================================
# /START
# ============================================================

@dp.message(CommandStart())
async def start_handler(message: Message):

    user = message.from_user

    if user:

        await ensure_user(
            {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        )

    await message.answer(
        "🚕 <b>OPPER TAXI</b>\n\n"
        "Manzilingizga birga boramiz.\n\n"
        "Shaharlar orasida ishonchli safar toping "
        "yoki o‘zingizga yo‘lovchi toping.\n\n"
        "📱 OPPER TAXI ilovasini ochish uchun "
        "pastdagi tugmani bosing.",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@dp.message(Command("help"))
async def help_handler(message: Message):

    await message.answer(
        "🆘 <b>OPPER TAXI YORDAM</b>\n\n"
        "🚕 Safar topish — mavjud safarlarni qidirish\n"
        "🚗 Safar joylash — haydovchi sifatida safar qo‘yish\n"
        "📋 Buyurtmalar — buyurtmalaringiz\n"
        "👤 Profil — shaxsiy ma’lumotlar\n"
        "🔔 Bildirishnomalar — yangi buyurtmalar\n\n"
        "Muammo bo‘lsa administratorga murojaat qiling.",
        parse_mode="HTML"
    )


@dp.message(F.text == "📞 Yordam")
async def help_button(message: Message):
    await help_handler(message)


# ============================================================
# DRIVER REGISTER
# ============================================================

async def driver_register(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = await ensure_user(telegram_user)

    try:
        data = await request.json()
    except Exception:
        return json_error("Noto‘g‘ri ma'lumot.")

    full_name = clean_text(data.get("full_name"))
    phone = normalize_phone(data.get("phone"))
    region = clean_text(data.get("region"))
    district = clean_text(data.get("district"))

    car_model = clean_text(
        data.get("car_model")
        or data.get("model")
    )

    car_number = clean_text(
        data.get("car_number")
        or data.get("number")
    )

    seats = safe_int(
        data.get("seats"),
        0
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not full_name:
        return json_error(
            "F.I.Sh. kiritilmagan."
        )

    if not phone:
        return json_error(
            "Telefon raqami kiritilmagan."
        )

    if not valid_location(
        region,
        district
    ):
        return json_error(
            "Viloyat yoki tuman noto‘g‘ri."
        )

    if not car_model:
        return json_error(
            "Avtomobil modeli kiritilmagan."
        )

    if not car_number:
        return json_error(
            "Avtomobil raqami kiritilmagan."
        )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT INTO users
            (
                telegram_id,
                full_name,
                phone,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                full_name = excluded.full_name,
                phone = excluded.phone,
                updated_at = excluded.updated_at
            """,
            (
                telegram_id,
                full_name,
                phone,
                now_str(),
                now_str()
            )
        )

        await db.execute(
            """
            INSERT INTO drivers
            (
                telegram_id,
                full_name,
                phone,
                region,
                district,
                verification_status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                full_name = excluded.full_name,
                phone = excluded.phone,
                region = excluded.region,
                district = excluded.district,
                verification_status = 'pending',
                updated_at = excluded.updated_at
            """,
            (
                telegram_id,
                full_name,
                phone,
                region,
                district,
                DRIVER_PENDING,
                now_str(),
                now_str()
            )
        )

        await db.execute(
            """
            INSERT INTO cars
            (
                driver_telegram_id,
                model,
                number,
                seats,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(driver_telegram_id)
            DO UPDATE SET
                model = excluded.model,
                number = excluded.number,
                seats = excluded.seats,
                updated_at = excluded.updated_at
            """,
            (
                telegram_id,
                car_model,
                car_number,
                seats,
                now_str(),
                now_str()
            )
        )

        await db.commit()

    # --------------------------------------------------------
    # ADMIN NOTIFICATION
    # --------------------------------------------------------

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"driver_approve:{telegram_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"driver_reject:{telegram_id}"
                )
            ]
        ]
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            "🚗 <b>YANGI HAYDOVCHI</b>\n\n"
            f"👤 {full_name}\n"
            f"📞 {phone}\n"
            f"📍 {region}, {district}\n"
            f"🚘 {car_model}\n"
            f"🔢 {car_number}\n"
            f"🪑 {seats} ta o‘rindiq\n\n"
            "Tasdiqlashni tanlang.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(
            "ADMIN NOTIFY ERROR: %s",
            e
        )

    return json_ok(
        {
            "message": "Haydovchi ma'lumotlari qabul qilindi. Admin tasdig‘i kutilmoqda.",
            "verification_status": DRIVER_PENDING
        }
    )


# ============================================================
# DRIVER STATUS
# ============================================================

async def driver_status(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = int(
        telegram_user["id"]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                d.*,
                c.model AS car_model,
                c.number AS car_number,
                c.seats AS car_seats
            FROM drivers d
            LEFT JOIN cars c
                ON c.driver_telegram_id = d.telegram_id
            WHERE d.telegram_id = ?
            """,
            (telegram_id,)
        )

        row = await cursor.fetchone()

    if not row:
        return json_ok(
            {
                "registered": False
            }
        )

    return json_ok(
        {
            "registered": True,
            "driver": dict(row)
        }
    )


# ============================================================
# DRIVER CREATE RIDE
# ============================================================

async def driver_create_ride(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = int(
        telegram_user["id"]
    )

    try:
        data = await request.json()
    except Exception:
        return json_error(
            "Noto‘g‘ri ma'lumot."
        )

    from_region = clean_text(
        data.get("from_region")
    )

    from_district = clean_text(
        data.get("from_district")
    )

    to_region = clean_text(
        data.get("to_region")
    )

    to_district = clean_text(
        data.get("to_district")
    )

    ride_date = clean_text(
        data.get("ride_date")
    )

    ride_time = clean_text(
        data.get("ride_time")
    )

    seats = safe_int(
        data.get("seats"),
        0
    )

    price = safe_int(
        data.get("price"),
        -1
    )

    if not valid_location(
        from_region,
        from_district
    ):
        return json_error(
            "Jo‘nash joyi noto‘g‘ri."
        )

    if not valid_location(
        to_region,
        to_district
    ):
        return json_error(
            "Borish joyi noto‘g‘ri."
        )

    if (
        from_region == to_region
        and from_district == to_district
    ):
        return json_error(
            "Jo‘nash va borish joyi bir xil bo‘lishi mumkin emas."
        )

    if not ride_date:
        return json_error(
            "Safar sanasi kiritilmagan."
        )

    if not ride_time:
        return json_error(
            "Safar vaqti kiritilmagan."
        )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    if price <= 0:
        return json_error(
            "Narx noto‘g‘ri."
        )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                d.*,
                c.model AS car_model,
                c.number AS car_number,
                c.seats AS car_seats
            FROM drivers d
            LEFT JOIN cars c
                ON c.driver_telegram_id = d.telegram_id
            WHERE d.telegram_id = ?
            """,
            (telegram_id,)
        )

        driver = await cursor.fetchone()

        if not driver:
            return json_error(
                "Avval haydovchi sifatida ro‘yxatdan o‘ting."
            )

        if driver["verification_status"] != DRIVER_APPROVED:
            return json_error(
                "Haydovchi profilingiz hali admin tomonidan tasdiqlanmagan."
            )

        driver_seats = safe_int(
            driver["car_seats"],
            0
        )

        if not valid_seats(driver_seats):
            return json_error(
                "Haydovchi profilidagi o‘rindiqlar soni noto‘g‘ri. Profilni yangilang."
            )

        if seats > driver_seats:
            return json_error(
                f"Sizning avtomobilingizda {driver_seats} ta joy bor. "
                f"Safarga {driver_seats} tagacha joy qo‘yishingiz mumkin."
            )

        cursor = await db.execute(
            """
            INSERT INTO rides
            (
                driver_id,
                driver_telegram_id,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                driver["id"],
                telegram_id,
                from_region,
                from_district,
                to_region,
                to_district,
                ride_date,
                ride_time,
                seats,
                price,
                driver["car_model"] or "",
                driver["car_number"] or "",
                RIDE_ACTIVE,
                now_str(),
                now_str()
            )
        )

        ride_id = cursor.lastrowid

        await db.commit()

    await create_notification(
        telegram_id,
        "Safar joylashtirildi",
        f"{from_district} → {to_district} safaringiz yaratildi.",
        "ride",
        ride_id
    )

    return json_ok(
        {
            "ride_id": ride_id,
            "message": "Safar muvaffaqiyatli joylashtirildi."
        }
    )


# ============================================================
# SEARCH RIDES
# ============================================================

async def search_rides(request):

    try:
        data = dict(request.query)
    except Exception:
        data = {}

    from_region = clean_text(
        data.get("from_region")
    )

    from_district = clean_text(
        data.get("from_district")
    )

    to_region = clean_text(
        data.get("to_region")
    )

    to_district = clean_text(
        data.get("to_district")
    )

    ride_date = clean_text(
        data.get("ride_date")
    )

    seats = safe_int(
        data.get("seats"),
        1
    )

    if not valid_seats(seats):
        return json_error(
            "Yo‘lovchilar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    query = """
        SELECT
            r.*,
            d.full_name AS driver_name,
            d.rating AS driver_rating,
            d.rating_count AS driver_rating_count
        FROM rides r
        LEFT JOIN drivers d
            ON d.telegram_id = r.driver_telegram_id
        WHERE r.status = 'active'
    """

    params = []

    if from_region:
        query += " AND r.from_region = ?"
        params.append(from_region)

    if from_district:
        query += " AND r.from_district = ?"
        params.append(from_district)

    if to_region:
        query += " AND r.to_region = ?"
        params.append(to_region)

    if to_district:
        query += " AND r.to_district = ?"
        params.append(to_district)

    if ride_date:
        query += " AND r.ride_date = ?"
        params.append(ride_date)

    query += """
        ORDER BY
            r.ride_date ASC,
            r.ride_time ASC,
            r.id DESC
        LIMIT 100
    """

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            query,
            params
        )

        rides = await cursor.fetchall()

        result = []

        for ride in rides:

            cursor2 = await db.execute(
                """
                SELECT COALESCE(
                    SUM(seats),
                    0
                )
                FROM orders
                WHERE ride_id = ?
                AND status IN (?, ?)
                """,
                (
                    ride["id"],
                    ORDER_PENDING,
                    ORDER_ACCEPTED
                )
            )

            booked = (
                await cursor2.fetchone()
            )[0] or 0

            available = (
                ride["seats"] - booked
            )

            if available < seats:
                continue

            item = dict(ride)

            item["booked_seats"] = booked
            item["available_seats"] = available

            result.append(item)

    return json_ok(
        {
            "rides": result,
            "count": len(result)
        }
    )


# ============================================================
# PASSENGER ORDER
# ============================================================

async def passenger_order(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    passenger_id = int(
        telegram_user["id"]
    )

    try:
        data = await request.json()
    except Exception:
        return json_error(
            "Noto‘g‘ri ma'lumot."
        )

    ride_id = safe_int(
        data.get("ride_id"),
        0
    )

    seats = safe_int(
        data.get("seats"),
        0
    )

    phone = normalize_phone(
        data.get("phone")
    )

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if ride_id <= 0:
        return json_error(
            "Safar tanlanmagan."
        )

    if not valid_seats(seats):
        return json_error(
            "Yo‘lovchilar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    if not phone:
        return json_error(
            "Telefon raqamingizni kiriting."
        )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM rides
            WHERE id = ?
            """,
            (ride_id,)
        )

        ride = await cursor.fetchone()

        if not ride:
            return json_error(
                "Safar topilmadi."
            )

        if ride["status"] != RIDE_ACTIVE:
            return json_error(
                "Bu safar faol emas."
            )

        if ride["driver_telegram_id"] == passenger_id:
            return json_error(
                "O‘zingizning safaringizga buyurtma bera olmaysiz."
            )

        cursor = await db.execute(
            """
            SELECT *
            FROM orders
            WHERE ride_id = ?
            AND passenger_telegram_id = ?
            AND status IN (?, ?)
            """,
            (
                ride_id,
                passenger_id,
                ORDER_PENDING,
                ORDER_ACCEPTED
            )
        )

        duplicate = await cursor.fetchone()

        if duplicate:
            return json_error(
                "Bu safarga siz allaqachon buyurtma bergansiz."
            )

        cursor = await db.execute(
            """
            SELECT COALESCE(
                SUM(seats),
                0
            )
            FROM orders
            WHERE ride_id = ?
            AND status IN (?, ?)
            """,
            (
                ride_id,
                ORDER_PENDING,
                ORDER_ACCEPTED
            )
        )

        booked = (
            await cursor.fetchone()
        )[0] or 0

        available = (
            ride["seats"] - booked
        )

        if seats > available:
            return json_error(
                f"Bu safarda faqat {available} ta joy qoldi."
            )

        first_name = clean_text(
            telegram_user.get("first_name")
        )

        last_name = clean_text(
            telegram_user.get("last_name")
        )

        passenger_name = (
            f"{first_name} {last_name}"
        ).strip()

        cursor = await db.execute(
            """
            INSERT INTO orders
            (
                ride_id,
                passenger_telegram_id,
                passenger_name,
                passenger_phone,
                seats,
                latitude,
                longitude,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ride_id,
                passenger_id,
                passenger_name,
                phone,
                seats,
                latitude,
                longitude,
                ORDER_PENDING,
                now_str(),
                now_str()
            )
        )

        order_id = cursor.lastrowid

        await db.commit()

    await create_notification(
        ride["driver_telegram_id"],
        "🔔 Yangi buyurtma",
        f"{passenger_name} sizning safaringizga "
        f"{seats} ta joy uchun buyurtma berdi.",
        "order",
        order_id
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Buyurtmalarni ko‘rish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    )
                )
            ]
        ]
    )

    await send_telegram_notification(
        ride["driver_telegram_id"],
        "🔔 <b>Yangi OPPER TAXI buyurtmasi</b>\n\n"
        f"👤 {passenger_name}\n"
        f"🪑 {seats} ta joy\n"
        f"📍 {ride['from_district']} → {ride['to_district']}\n"
        f"📅 {ride['ride_date']}\n"
        f"⏰ {ride['ride_time']}\n\n"
        "Buyurtmani Mini App orqali boshqaring.",
        keyboard
    )

    return json_ok(
        {
            "order_id": order_id,
            "message": "Buyurtma yuborildi."
        }
    )


# ============================================================
# DRIVER ORDERS
# ============================================================

async def driver_orders(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = int(
        telegram_user["id"]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                o.*,
                r.from_region,
                r.from_district,
                r.to_region,
                r.to_district,
                r.ride_date,
                r.ride_time,
                r.price,
                r.car_model,
                r.car_number
            FROM orders o
            JOIN rides r
                ON r.id = o.ride_id
            WHERE r.driver_telegram_id = ?
            ORDER BY o.created_at DESC
            """,
            (telegram_id,)
        )

        rows = await cursor.fetchall()

    return json_ok(
        {
            "orders": [
                dict(row)
                for row in rows
            ]
        }
    )


# ============================================================
# ACCEPT ORDER
# ============================================================

async def accept_order(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    driver_id = int(
        telegram_user["id"]
    )

    try:
        data = await request.json()
    except Exception:
        return json_error(
            "Noto‘g‘ri ma'lumot."
        )

    order_id = safe_int(
        data.get("order_id"),
        0
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                o.*,
                r.driver_telegram_id,
                r.seats AS ride_seats,
                r.from_district,
                r.to_district,
                r.ride_date,
                r.ride_time
            FROM orders o
            JOIN rides r
                ON r.id = o.ride_id
            WHERE o.id = ?
            """,
            (order_id,)
        )

        order = await cursor.fetchone()

        if not order:
            return json_error(
                "Buyurtma topilmadi."
            )

        if order["driver_telegram_id"] != driver_id:
            return json_error(
                "Bu buyurtma sizga tegishli emas.",
                403
            )

        if order["status"] != ORDER_PENDING:
            return json_error(
                "Bu buyurtma allaqachon ko‘rib chiqilgan."
            )

        await db.execute(
            """
            UPDATE orders
            SET
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                ORDER_ACCEPTED,
                now_str(),
                order_id
            )
        )

        await db.commit()

    await create_notification(
        order["passenger_telegram_id"],
        "✅ Buyurtma qabul qilindi",
        f"Haydovchi buyurtmangizni qabul qildi.\n"
        f"{order['from_district']} → {order['to_district']}",
        "order",
        order_id
    )

    await send_telegram_notification(
        order["passenger_telegram_id"],
        "✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
        f"📍 {order['from_district']} → {order['to_district']}\n"
        f"📅 {order['ride_date']}\n"
        f"⏰ {order['ride_time']}\n\n"
        "OPPER TAXI orqali buyurtmangizni kuzatishingiz mumkin.",
    )

    return json_ok(
        {
            "message": "Buyurtma qabul qilindi."
        }
    )


# ============================================================
# REJECT ORDER
# ============================================================

async def reject_order(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    driver_id = int(
        telegram_user["id"]
    )

    try:
        data = await request.json()
    except Exception:
        return json_error(
            "Noto‘g‘ri ma'lumot."
        )

    order_id = safe_int(
        data.get("order_id"),
        0
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
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

        order = await cursor.fetchone()

        if not order:
            return json_error(
                "Buyurtma topilmadi."
            )

        if order["driver_telegram_id"] != driver_id:
            return json_error(
                "Bu buyurtma sizga tegishli emas.",
                403
            )

        await db.execute(
            """
            UPDATE orders
            SET
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                ORDER_REJECTED,
                now_str(),
                order_id
            )
        )

        await db.commit()

    await create_notification(
        order["passenger_telegram_id"],
        "❌ Buyurtma rad etildi",
        "Haydovchi buyurtmangizni qabul qilmadi.",
        "order",
        order_id
    )

    await send_telegram_notification(
        order["passenger_telegram_id"],
        "❌ Haydovchi buyurtmangizni qabul qilmadi.\n\n"
        "Boshqa safarni qidirib ko‘rishingiz mumkin."
    )

    return json_ok(
        {
            "message": "Buyurtma rad etildi."
        }
    )


# ============================================================
# MY ORDERS
# ============================================================

async def my_orders(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = int(
        telegram_user["id"]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                o.*,
                r.driver_telegram_id,
                r.from_region,
                r.from_district,
                r.to_region,
                r.to_district,
                r.ride_date,
                r.ride_time,
                r.price,
                r.car_model,
                r.car_number,
                d.full_name AS driver_name,
                d.phone AS driver_phone,
                d.rating AS driver_rating
            FROM orders o
            JOIN rides r
                ON r.id = o.ride_id
            LEFT JOIN drivers d
                ON d.telegram_id = r.driver_telegram_id
            WHERE o.passenger_telegram_id = ?

            ORDER BY o.created_at DESC
            """,
            (telegram_id,)
        )

        passenger_orders = await cursor.fetchall()

        cursor = await db.execute(
            """
            SELECT *
            FROM rides
            WHERE driver_telegram_id = ?
            ORDER BY created_at DESC
            """,
            (telegram_id,)
        )

        driver_rides = await cursor.fetchall()

    return json_ok(
        {
            "passenger_orders": [
                dict(row)
                for row in passenger_orders
            ],
            "driver_rides": [
                dict(row)
                for row in driver_rides
            ]
        }
    )


# ============================================================
# PROFILE
# ============================================================

async def profile(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = int(
        telegram_user["id"]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        user = await cursor.fetchone()

        cursor = await db.execute(
            """
            SELECT
                d.*,
                c.model AS car_model,
                c.number AS car_number,
                c.seats AS car_seats
            FROM drivers d
            LEFT JOIN cars c
                ON c.driver_telegram_id = d.telegram_id
            WHERE d.telegram_id = ?
            """,
            (telegram_id,)
        )

        driver = await cursor.fetchone()

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM rides
            WHERE driver_telegram_id = ?
            AND status = ?
            """,
            (
                telegram_id,
                RIDE_COMPLETED
            )
        )

        completed_trips = (
            await cursor.fetchone()
        )[0]

        cursor = await db.execute(
            """
            SELECT *
            FROM notifications
            WHERE telegram_id = ?
            ORDER BY created_at DESC
            LIMIT 30
            """,
            (telegram_id,)
        )

        notifications = await cursor.fetchall()

    return json_ok(
        {
            "user": dict(user) if user else None,
            "driver": dict(driver) if driver else None,
            "completed_trips": completed_trips,
            "notifications": [
                dict(row)
                for row in notifications
            ]
        }
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

async def notifications(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = int(
        telegram_user["id"]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM notifications
            WHERE telegram_id = ?
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (telegram_id,)
        )

        rows = await cursor.fetchall()

    return json_ok(
        {
            "notifications": [
                dict(row)
                for row in rows
            ]
        }
    )


async def mark_notifications_read(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = int(
        telegram_user["id"]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        await db.commit()

    return json_ok()


# ============================================================
# RATING
# ============================================================

async def add_rating(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    passenger_id = int(
        telegram_user["id"]
    )

    try:
        data = await request.json()
    except Exception:
        return json_error(
            "Noto‘g‘ri ma'lumot."
        )

    order_id = safe_int(
        data.get("order_id"),
        0
    )

    stars = safe_int(
        data.get("stars"),
        0
    )

    comment = clean_text(
        data.get("comment")
    )

    if stars < 1 or stars > 5:
        return json_error(
            "Reyting 1–5 oralig‘ida bo‘lishi kerak."
        )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM orders
            WHERE id = ?
            AND passenger_telegram_id = ?
            """,
            (
                order_id,
                passenger_id
            )
        )

        order = await cursor.fetchone()

        if not order:
            return json_error(
                "Buyurtma topilmadi."
            )

        if order["status"] != ORDER_COMPLETED:
            return json_error(
                "Faqat yakunlangan safarga reyting berish mumkin."
            )

        cursor = await db.execute(
            """
            SELECT id
            FROM ratings
            WHERE order_id = ?
            """,
            (order_id,)
        )

        existing = await cursor.fetchone()

        if existing:
            return json_error(
                "Bu safarga allaqachon reyting bergansiz."
            )

        cursor = await db.execute(
            """
            SELECT driver_telegram_id
            FROM rides
            WHERE id = ?
            """,
            (order["ride_id"],)
        )

        ride = await cursor.fetchone()

        if not ride:
            return json_error(
                "Safar topilmadi."
            )

        driver_id = ride["driver_telegram_id"]

        await db.execute(
            """
            INSERT INTO ratings
            (
                ride_id,
                order_id,
                driver_telegram_id,
                passenger_telegram_id,
                stars,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order["ride_id"],
                order_id,
                driver_id,
                passenger_id,
                stars,
                comment,
                now_str()
            )
        )

        cursor = await db.execute(
            """
            SELECT
                COALESCE(
                    SUM(stars),
                    0
                ) AS total,
                COUNT(*) AS count
            FROM ratings
            WHERE driver_telegram_id = ?
            """,
            (driver_id,)
        )

        rating_data = await cursor.fetchone()

        total = rating_data[0]
        count = rating_data[1]

        average = (
            round(total / count, 2)
            if count
            else 5.0
        )

        await db.execute(
            """
            UPDATE drivers
            SET
                rating = ?,
                rating_count = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                average,
                count,
                now_str(),
                driver_id
            )
        )

        await db.commit()

    await create_notification(
        driver_id,
        "⭐ Yangi reyting",
        f"Sizga {stars}/5 reyting berildi.",
        "rating",
        order_id
    )

    return json_ok(
        {
            "rating": average,
            "message": "Rahmat! Reytingingiz saqlandi."
        }
    )


# ============================================================
# CANCEL ORDER / RIDE
# ============================================================

async def cancel_order(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = int(
        telegram_user["id"]
    )

    try:
        data = await request.json()
    except Exception:
        return json_error(
            "Noto‘g‘ri ma'lumot."
        )

    order_id = safe_int(
        data.get("order_id"),
        0
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
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

        order = await cursor.fetchone()

        if not order:
            return json_error(
                "Buyurtma topilmadi."
            )

        if (
            order["passenger_telegram_id"] != telegram_id
            and order["driver_telegram_id"] != telegram_id
        ):
            return json_error(
                "Siz bu buyurtmani boshqara olmaysiz.",
                403
            )

        await db.execute(
            """
            UPDATE orders
            SET
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                ORDER_CANCELLED,
                now_str(),
                order_id
            )
        )

        await db.commit()

    other_user = (
        order["driver_telegram_id"]
        if order["passenger_telegram_id"] == telegram_id
        else order["passenger_telegram_id"]
    )

    await create_notification(
        other_user,
        "⚠️ Buyurtma bekor qilindi",
        "Buyurtma ishtirokchilardan biri tomonidan bekor qilindi.",
        "order",
        order_id
    )

    await send_telegram_notification(
        other_user,
        "⚠️ OPPER TAXI buyurtmasi bekor qilindi."
    )

    return json_ok(
        {
            "message": "Buyurtma bekor qilindi."
        }
    )


# ============================================================
# DRIVER REQUESTS
# ============================================================

async def passenger_request(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    passenger_id = int(
        telegram_user["id"]
    )

    try:
        data = await request.json()
    except Exception:
        return json_error(
            "Noto‘g‘ri ma'lumot."
        )

    from_region = clean_text(
        data.get("from_region")
    )

    from_district = clean_text(
        data.get("from_district")
    )

    to_region = clean_text(
        data.get("to_region")
    )

    to_district = clean_text(
        data.get("to_district")
    )

    ride_date = clean_text(
        data.get("ride_date")
    )

    ride_time = clean_text(
        data.get("ride_time")
    )

    phone = normalize_phone(
        data.get("phone")
    )

    seats = safe_int(
        data.get("seats"),
        0
    )

    note = clean_text(
        data.get("note")
    )

    if not valid_location(
        from_region,
        from_district
    ):
        return json_error(
            "Jo‘nash joyi noto‘g‘ri."
        )

    if not valid_location(
        to_region,
        to_district
    ):
        return json_error(
            "Borish joyi noto‘g‘ri."
        )

    if not valid_seats(seats):
        return json_error(
            "Yo‘lovchilar soni 1–4 oralig‘ida bo‘lishi kerak."
        )

    if not ride_date or not ride_time:
        return json_error(
            "Sana va vaqtni kiriting."
        )

    if not phone:
        return json_error(
            "Telefon raqamingizni kiriting."
        )

    passenger_name = (
        f"{clean_text(telegram_user.get('first_name'))} "
        f"{clean_text(telegram_user.get('last_name'))}"
    ).strip()

    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute(
            """
            INSERT INTO passenger_requests
            (
                passenger_telegram_id,
                passenger_name,
                passenger_phone,
                from_region,
                from_district,
                to_region,
                to_district,
                ride_date,
                ride_time,
                seats,
                note,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                passenger_id,
                passenger_name,
                phone,
                from_region,
                from_district,
                to_region,
                to_district,
                ride_date,
                ride_time,
                seats,
                note,
                "open",
                now_str(),
                now_str()
            )
        )

        request_id = cursor.lastrowid

        await db.commit()

    return json_ok(
        {
            "request_id": request_id,
            "message": "Yo‘lovchi so‘rovi joylashtirildi."
        }
    )


async def driver_requests(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401
        )

    telegram_id = int(
        telegram_user["id"]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM passenger_requests
            WHERE status = 'open'
            ORDER BY created_at DESC
            LIMIT 100
            """
        )

        rows = await cursor.fetchall()

    return json_ok(
        {
            "requests": [
                dict(row)
                for row in rows
            ]
        }
    )


# ============================================================
# ADMIN DRIVER APPROVAL
# ============================================================

@dp.callback_query(
    F.data.startswith("driver_approve:")
)
async def approve_driver(callback):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Ruxsat yo‘q.",
            show_alert=True
        )
        return

    telegram_id = safe_int(
        callback.data.split(":")[1]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            UPDATE drivers
            SET
                verification_status = ?,
                verification_reason = '',
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                DRIVER_APPROVED,
                now_str(),
                telegram_id
            )
        )

        await db.execute(
            """
            INSERT INTO admin_actions
            (
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
                "driver_approved",
                telegram_id,
                "",
                now_str()
            )
        )

        await db.commit()

    await create_notification(
        telegram_id,
        "✅ Haydovchi tasdiqlandi",
        "Tabriklaymiz! Haydovchi profilingiz tasdiqlandi.",
        "verification"
    )

    await send_telegram_notification(
        telegram_id,
        "✅ <b>Haydovchi profilingiz tasdiqlandi!</b>\n\n"
        "Endi OPPER TAXI orqali safar joylashtirishingiz mumkin.",
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.answer(
        "Haydovchi tasdiqlandi."
    )


@dp.callback_query(
    F.data.startswith("driver_reject:")
)
async def reject_driver(callback):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Ruxsat yo‘q.",
            show_alert=True
        )
        return

    telegram_id = safe_int(
        callback.data.split(":")[1]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            UPDATE drivers
            SET
                verification_status = ?,
                verification_reason = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                DRIVER_REJECTED,
                "Admin tomonidan rad etildi",
                now_str(),
                telegram_id
            )
        )

        await db.commit()

    await create_notification(
        telegram_id,
        "❌ Haydovchi tasdiqlanmadi",
        "Haydovchi profilingiz admin tomonidan rad etildi.",
        "verification"
    )

    await send_telegram_notification(
        telegram_id,
        "❌ <b>Haydovchi profilingiz tasdiqlanmadi.</b>\n\n"
        "Ma'lumotlarni tekshirib, qayta yuborishingiz mumkin.",
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.answer(
        "Haydovchi rad etildi."
    )


# ============================================================
# ADMIN STATISTICS
# ============================================================

async def admin_stats(request):

    telegram_user = await get_telegram_user(request)

    if not telegram_user:
        return json_error(
            "Authentication kerak.",
            401
        )

    if int(telegram_user["id"]) != ADMIN_ID:
        return json_error(
            "Admin ruxsati kerak.",
            403
        )

    async with aiosqlite.connect(DB_PATH) as db:

        async def count(table, where="", params=()):
            query = f"SELECT COUNT(*) FROM {table}"

            if where:
                query += " WHERE " + where

            cursor = await db.execute(
                query,
                params
            )

            return (
                await cursor.fetchone()
            )[0]

        users = await count(
            "users"
        )

        drivers = await count(
            "drivers"
        )

        approved_drivers = await count(
            "drivers",
            "verification_status = ?",
            (DRIVER_APPROVED,)
        )

        pending_drivers = await count(
            "drivers",
            "verification_status = ?",
            (DRIVER_PENDING,)
        )

        rides = await count(
            "rides"
        )

        active_rides = await count(
            "rides",
            "status = ?",
            (RIDE_ACTIVE,)
        )

        orders = await count(
            "orders"
        )

        reports = await count(
            "reports",
            "status = 'open'"
        )

    return json_ok(
        {
            "statistics": {
                "users": users,
                "drivers": drivers,
                "approved_drivers": approved_drivers,
                "pending_drivers": pending_drivers,
                "rides": rides,
                "active_rides": active_rides,
                "orders": orders,
                "open_reports": reports
            }
        }
    )


# ============================================================
# HEALTH
# ============================================================

async def health(request):

    return json_ok(
        {
            "service": "OPPER TAXI",
            "status": "online",
            "version": "2.0",
            "seats": {
                "min": MIN_SEATS,
                "max": MAX_SEATS
            },
            "mini_app": MINI_APP_URL
        }
    )


# ============================================================
# SERVE MINI APP
# ============================================================

async def index(request):

    if not INDEX_FILE.exists():

        return web.Response(
            text="""
            <h1>OPPER TAXI</h1>
            <p>index.html topilmadi.</p>
            """,
            content_type="text/html"
        )

    return web.FileResponse(
        INDEX_FILE,
        headers={
            "Cache-Control": "no-store"
        }
    )


# ============================================================
# ROUTES
# ============================================================

def setup_routes(app):

    app.router.add_get(
        "/",
        index
    )

    app.router.add_get(
        "/app",
        index
    )

    app.router.add_get(
        "/health",
        health
    )

    # Driver
    app.router.add_post(
        "/api/driver/register",
        driver_register
    )

    app.router.add_get(
        "/api/driver/status",
        driver_status
    )

    app.router.add_post(
        "/api/driver/ride",
        driver_create_ride
    )

    app.router.add_get(
        "/api/driver/requests",
        driver_requests
    )

    # Rides
    app.router.add_get(
        "/api/rides",
        search_rides
    )

    # Orders
    app.router.add_post(
        "/api/passenger/order",
        passenger_order
    )

    app.router.add_get(
        "/api/orders",
        my_orders
    )

    app.router.add-get if False else app.router.add_post(
        "/api/order/accept",
        accept_order
    )

    app.router.add_post(
        "/api/order/reject",
        reject_order
    )

    app.router.add_post(
        "/api/order/cancel",
        cancel_order
    )

    # Passenger request
    app.router.add_post(
        "/api/passenger/request",
        passenger_request
    )

    # Profile
    app.router.add_get(
        "/api/profile",
        profile
    )

    # Notifications
    app.router.add_get(
        "/api/notifications",
        notifications
    )

    app.router.add_post(
        "/api/notifications/read",
        mark_notifications_read
    )

    # Ratings
    app.router.add_post(
        "/api/rating",
        add_rating
    )

    # Admin
    app.router.add_get(
        "/api/admin/stats",
        admin_stats
    )


# ============================================================
# BOT SETUP
# ============================================================

async def setup_bot():

    await bot.set_my_commands(
        [
            BotCommand(
                command="start",
                description="OPPER TAXI'ni ochish"
            ),
            BotCommand(
                command="help",
                description="Yordam"
            ),
        ]
    )

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

        logging.warning(
            "MENU BUTTON ERROR: %s",
            e
        )


# ============================================================
# WEB SERVER
# ============================================================

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

    logging.info(
        "OPPER TAXI WEB SERVER: http://0.0.0.0:%s",
        PORT
    )

    return runner


# ============================================================
# MAIN
# ============================================================

async def main():

    logging.info(
        "========================================"
    )

    logging.info(
        "OPPER TAXI STARTING..."
    )

    logging.info(
        "MINI APP: %s",
        MINI_APP_URL
    )

    logging.info(
        "PORT: %s",
        PORT
    )

    logging.info(
        "ADMIN ID: %s",
        ADMIN_ID
    )

    logging.info(
        "SEATS: %s-%s",
        MIN_SEATS,
        MAX_SEATS
    )

    logging.info(
        "========================================"
    )

    await init_db()

    await setup_bot()

    runner = await start_web_server()

    try:

        await dp.start_polling(
            bot
        )

    finally:

        await runner.cleanup()

        await bot.session.close()


if __name__ == "__main__":

    try:
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logging.info(
            "OPPER TAXI STOPPED"
        )
