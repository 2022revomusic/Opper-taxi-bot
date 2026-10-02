import os
import re
import json
import base64
import hmac
import hashlib
import asyncio
import logging
from pathlib import Path
from datetime import datetime

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
    CallbackQuery,
)

# =========================================================
# CONFIG
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID = int(os.getenv("ADMIN_ID", "653914246"))

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
INDEX_FILE = WEB_DIR / "index.html"

UPLOAD_DIR = BASE_DIR / "uploads"
DRIVER_DOCS_DIR = UPLOAD_DIR / "drivers"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DRIVER_DOCS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "oper_taxi.db"

PORT = int(os.getenv("PORT", "8080"))

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


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")


# =========================================================
# BOT
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# CITIES / REGIONS
# =========================================================

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


# =========================================================
# HELPERS
# =========================================================

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def safe_filename(name):
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    return name[:100]


def normalize_location(region, district):
    return {
        "region": clean_text(region),
        "district": clean_text(district),
    }


def valid_location(region, district):
    region = clean_text(region)
    district = clean_text(district)

    return (
        region in REGIONS
        and district in REGIONS[region]
    )


# =========================================================
# TELEGRAM INIT DATA VALIDATION
# =========================================================

def validate_init_data(init_data: str):
    if not init_data:
        return None

    try:
        from urllib.parse import parse_qsl

        parsed = dict(parse_qsl(init_data, keep_blank_values=True))

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
        logging.error("INIT DATA ERROR: %s", e)
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

    user = validate_init_data(init_data)

    return user


# =========================================================
# DATABASE
# =========================================================

async def db():
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


async def add_column_if_missing(conn, table, column, definition):
    cursor = await conn.execute(f"PRAGMA table_info({table})")
    columns = await cursor.fetchall()

    existing = {row["name"] for row in columns}

    if column not in existing:
        await conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


async def init_db():

    conn = await db()

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            full_name TEXT,
            phone TEXT,
            car_model TEXT,
            car_number TEXT,
            seats INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            driver_telegram_id INTEGER,
            driver_name TEXT,
            driver_phone TEXT,
            from_city TEXT,
            to_city TEXT,
            ride_date TEXT,
            ride_time TEXT,
            seats INTEGER,
            price INTEGER,
            car_model TEXT,
            car_number TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id INTEGER,
            passenger_telegram_id INTEGER,
            passenger_name TEXT,
            passenger_phone TEXT,
            from_city TEXT,
            to_city TEXT,
            ride_date TEXT,
            ride_time TEXT,
            seats INTEGER,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # New driver verification columns

    await add_column_if_missing(
        conn,
        "drivers",
        "verification_status",
        "TEXT DEFAULT 'none'"
    )

    await add_column_if_missing(
        conn,
        "drivers",
        "passport_file",
        "TEXT"
    )

    await add_column_if_missing(
        conn,
        "drivers",
        "license_file",
        "TEXT"
    )

    await add_column_if_missing(
        conn,
        "drivers",
        "tech_passport_file",
        "TEXT"
    )

    await add_column_if_missing(
        conn,
        "drivers",
        "car_photo_file",
        "TEXT"
    )

    await add_column_if_missing(
        conn,
        "drivers",
        "region",
        "TEXT"
    )

    await add_column_if_missing(
        conn,
        "drivers",
        "district",
        "TEXT"
    )

    await add_column_if_missing(
        conn,
        "drivers",
        "rejection_reason",
        "TEXT"
    )

    # New ride location fields

    for table in ["rides", "orders"]:

        await add_column_if_missing(
            conn,
            table,
            "from_region",
            "TEXT"
        )

        await add_column_if_missing(
            conn,
            table,
            "from_district",
            "TEXT"
        )

        await add_column_if_missing(
            conn,
            table,
            "to_region",
            "TEXT"
        )

        await add_column_if_missing(
            conn,
            table,
            "to_district",
            "TEXT"
        )

    # Passenger requests

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS passenger_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_telegram_id INTEGER,
            passenger_name TEXT,
            passenger_phone TEXT,

            from_region TEXT,
            from_district TEXT,

            to_region TEXT,
            to_district TEXT,

            request_date TEXT,
            request_time TEXT,
            seats INTEGER,

            latitude REAL,
            longitude REAL,

            note TEXT,

            status TEXT DEFAULT 'open',

            accepted_driver_telegram_id INTEGER,

            created_at TEXT,
            updated_at TEXT
        )
    """)

    await conn.commit()
    await conn.close()

    logging.info("DATABASE READY")


# =========================================================
# USER
# =========================================================

async def ensure_user(user):
    telegram_id = int(user["id"])

    username = clean_text(user.get("username"))
    first_name = clean_text(user.get("first_name"))
    last_name = clean_text(user.get("last_name"))

    full_name = " ".join(
        x for x in [first_name, last_name]
        if x
    ).strip()

    conn = await db()

    await conn.execute("""
        INSERT INTO users (
            telegram_id,
            username,
            full_name,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            username=excluded.username,
            full_name=excluded.full_name,
            updated_at=excluded.updated_at
    """, (
        telegram_id,
        username,
        full_name,
        now_str(),
        now_str(),
    ))

    await conn.commit()
    await conn.close()


async def get_driver(telegram_id):
    conn = await db()

    cursor = await conn.execute("""
        SELECT *
        FROM drivers
        WHERE telegram_id=?
    """, (telegram_id,))

    row = await cursor.fetchone()

    await conn.close()

    return dict(row) if row else None


# =========================================================
# SAVE BASE64 FILE
# =========================================================

async def save_base64_file(
    telegram_id,
    field_name,
    value
):
    if not value:
        return None

    try:
        if "," in value:
            value = value.split(",", 1)[1]

        raw = base64.b64decode(value)

        # max 8 MB
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Fayl 8 MB dan katta")

        filename = (
            f"{telegram_id}_"
            f"{field_name}_"
            f"{int(datetime.now().timestamp())}.jpg"
        )

        path = DRIVER_DOCS_DIR / safe_filename(filename)

        with open(path, "wb") as f:
            f.write(raw)

        return str(path)

    except Exception as e:
        logging.error(
            "FILE SAVE ERROR %s: %s",
            field_name,
            e
        )

        return None


# =========================================================
# DRIVER APPLICATION
# =========================================================

async def web_driver_register(request):

    user = await get_telegram_user(request)

    if not user:
        return web.json_response(
            {
                "ok": False,
                "error": "Telegram foydalanuvchisi aniqlanmadi"
            },
            status=401
        )

    data = await request.json()

    telegram_id = int(user["id"])

    full_name = clean_text(data.get("full_name"))
    phone = normalize_phone(data.get("phone"))

    car_model = clean_text(data.get("car_model"))
    car_number = clean_text(data.get("car_number"))

    region = clean_text(data.get("region"))
    district = clean_text(data.get("district"))

    try:
        seats = int(data.get("seats", 0))
    except Exception:
        seats = 0

    if len(full_name) < 3:
        return web.json_response({
            "ok": False,
            "error": "F.I.Sh. to‘liq kiriting"
        }, status=400)

    if not phone:
        return web.json_response({
            "ok": False,
            "error": "Telefon raqami kerak"
        }, status=400)

    if not car_model:
        return web.json_response({
            "ok": False,
            "error": "Mashina rusmini kiriting"
        }, status=400)

    if not car_number:
        return web.json_response({
            "ok": False,
            "error": "Davlat raqamini kiriting"
        }, status=400)

    if seats < 1 or seats > 8:
        return web.json_response({
            "ok": False,
            "error": "O‘rindiqlar soni 1-8 oralig‘ida bo‘lishi kerak"
        }, status=400)

    if not valid_location(region, district):
        return web.json_response({
            "ok": False,
            "error": "Viloyat yoki tuman noto‘g‘ri"
        }, status=400)

    passport_file = data.get("passport_file")
    license_file = data.get("license_file")
    tech_passport_file = data.get("tech_passport_file")
    car_photo_file = data.get("car_photo_file")

    if not passport_file:
        return web.json_response({
            "ok": False,
            "error": "Pasport yoki ID rasmi kerak"
        }, status=400)

    if not license_file:
        return web.json_response({
            "ok": False,
            "error": "Haydovchilik guvohnomasi rasmi kerak"
        }, status=400)

    if not tech_passport_file:
        return web.json_response({
            "ok": False,
            "error": "Texpasport rasmi kerak"
        }, status=400)

    if not car_photo_file:
        return web.json_response({
            "ok": False,
            "error": "Avtomobil rasmi kerak"
        }, status=400)

    await ensure_user(user)

    old_driver = await get_driver(telegram_id)

    if old_driver:
        status = old_driver.get("verification_status")

        if status == "approved":
            return web.json_response({
                "ok": False,
                "error": "Siz allaqachon tasdiqlangan haydovchisiz"
            }, status=400)

    passport_path = await save_base64_file(
        telegram_id,
        "passport",
        passport_file
    )

    license_path = await save_base64_file(
        telegram_id,
        "license",
        license_file
    )

    tech_path = await save_base64_file(
        telegram_id,
        "techpassport",
        tech_passport_file
    )

    car_path = await save_base64_file(
        telegram_id,
        "car",
        car_photo_file
    )

    if not all([
        passport_path,
        license_path,
        tech_path,
        car_path
    ]):
        return web.json_response({
            "ok": False,
            "error": "Hujjatlarni saqlashda xatolik"
        }, status=500)

    conn = await db()

    await conn.execute("""
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
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            full_name=excluded.full_name,
            phone=excluded.phone,
            car_model=excluded.car_model,
            car_number=excluded.car_number,
            seats=excluded.seats,
            verification_status='pending',
            passport_file=excluded.passport_file,
            license_file=excluded.license_file,
            tech_passport_file=excluded.tech_passport_file,
            car_photo_file=excluded.car_photo_file,
            region=excluded.region,
            district=excluded.district,
            rejection_reason=NULL,
            updated_at=excluded.updated_at
    """, (
        telegram_id,
        full_name,
        phone,
        car_model,
        car_number,
        seats,
        "pending",
        passport_path,
        license_path,
        tech_path,
        car_path,
        region,
        district,
        now_str(),
        now_str(),
    ))

    await conn.commit()
    await conn.close()

    # Notify admin

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ TASDIQLASH",
                    callback_data=f"driver_approve:{telegram_id}"
                ),
                InlineKeyboardButton(
                    text="❌ RAD ETISH",
                    callback_data=f"driver_reject:{telegram_id}"
                )
            ]
        ]
    )

    admin_text = f"""
🚕 <b>YANGI HAYDOVCHI ARIZASI</b>

👤 <b>F.I.Sh:</b> {full_name}
📞 <b>Telefon:</b> {phone}

🚗 <b>Mashina:</b> {car_model}
🔢 <b>Davlat raqami:</b> {car_number}
💺 <b>O‘rindiq:</b> {seats}

📍 <b>Hudud:</b>
{region} → {district}

🆔 <b>Telegram ID:</b> <code>{telegram_id}</code>

🟡 <b>Holat:</b> TEKSHIRUVDA
"""

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        await bot.send_document(
            ADMIN_ID,
            document=passport_path
        )

        await bot.send_document(
            ADMIN_ID,
            document=license_path
        )

        await bot.send_document(
            ADMIN_ID,
            document=tech_path
        )

        await bot.send_document(
            ADMIN_ID,
            document=car_path
        )

    except Exception as e:
        logging.error(
            "ADMIN NOTIFICATION ERROR: %s",
            e
        )

    return web.json_response({
        "ok": True,
        "status": "pending",
        "message": "Arizangiz yuborildi. Admin tasdig‘i kutilmoqda."
    })


# =========================================================
# DRIVER STATUS
# =========================================================

async def web_driver_status(request):

    user = await get_telegram_user(request)

    if not user:
        return web.json_response(
            {"ok": False, "error": "Unauthorized"},
            status=401
        )

    driver = await get_driver(int(user["id"]))

    if not driver:
        return web.json_response({
            "ok": True,
            "exists": False,
            "status": "none"
        })

    return web.json_response({
        "ok": True,
        "exists": True,
        "status": driver.get("verification_status") or "none",
        "driver": driver
    })


# =========================================================
# ADMIN APPROVE / REJECT
# =========================================================

@dp.callback_query(F.data.startswith("driver_approve:"))
async def approve_driver(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Siz admin emassiz",
            show_alert=True
        )
        return

    telegram_id = int(
        callback.data.split(":", 1)[1]
    )

    conn = await db()

    await conn.execute("""
        UPDATE drivers
        SET verification_status='approved',
            rejection_reason=NULL,
            updated_at=?
        WHERE telegram_id=?
    """, (
        now_str(),
        telegram_id
    ))

    await conn.commit()
    await conn.close()

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        f"✅ Haydovchi <code>{telegram_id}</code> TASDIQLANDI.",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            telegram_id,
            """
🟢 <b>HAYDOVCHILIK TASDIQLANDI!</b>

Tabriklaymiz! Sizning hujjatlaringiz admin tomonidan tasdiqlandi.

Endi OPPER TAXI ilovasiga kirib, faqat <b>Haydovchi rejimi</b>dan foydalanishingiz mumkin. 🚕
""",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer("Tasdiqlandi")


@dp.callback_query(F.data.startswith("driver_reject:"))
async def reject_driver(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Siz admin emassiz",
            show_alert=True
        )
        return

    telegram_id = int(
        callback.data.split(":", 1)[1]
    )

    conn = await db()

    await conn.execute("""
        UPDATE drivers
        SET verification_status='rejected',
            updated_at=?
        WHERE telegram_id=?
    """, (
        now_str(),
        telegram_id
    ))

    await conn.commit()
    await conn.close()

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        f"❌ Haydovchi <code>{telegram_id}</code> RAD ETILDI.",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            telegram_id,
            """
🔴 <b>HAYDOVCHILIK ARIZASI RAD ETILDI</b>

Hujjatlaringiz admin tomonidan tasdiqlanmadi.

Ma'lumotlarni tekshirib, qaytadan ariza yuborishingiz mumkin.
""",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer("Rad etildi")


# =========================================================
# DRIVER ACCESS CHECK
# =========================================================

async def require_approved_driver(request):

    user = await get_telegram_user(request)

    if not user:
        return None, web.json_response(
            {
                "ok": False,
                "error": "Telegram foydalanuvchisi aniqlanmadi"
            },
            status=401
        )

    driver = await get_driver(int(user["id"]))

    if not driver:
        return None, web.json_response(
            {
                "ok": False,
                "error": "Avval haydovchi sifatida ro‘yxatdan o‘ting"
            },
            status=403
        )

    if driver.get("verification_status") != "approved":
        return None, web.json_response(
            {
                "ok": False,
                "error": "Haydovchilik hali admin tomonidan tasdiqlanmagan",
                "status": driver.get("verification_status")
            },
            status=403
        )

    return user, None


# =========================================================
# ADD RIDE
# =========================================================

async def web_driver_ride(request):

    user, error = await require_approved_driver(request)

    if error:
        return error

    data = await request.json()

    telegram_id = int(user["id"])

    driver = await get_driver(telegram_id)

    from_region = clean_text(data.get("from_region"))
    from_district = clean_text(data.get("from_district"))

    to_region = clean_text(data.get("to_region"))
    to_district = clean_text(data.get("to_district"))

    ride_date = clean_text(data.get("ride_date"))

    ride_time = clean_text(
        data.get("ride_time")
        or data.get("time")
    )

    try:
        seats = int(data.get("seats", 0))
        price = int(data.get("price", 0))
    except Exception:
        seats = 0
        price = -1

    if not valid_location(
        from_region,
        from_district
    ):
        return web.json_response({
            "ok": False,
            "error": "Jo‘nash manzili noto‘g‘ri"
        }, status=400)

    if not valid_location(
        to_region,
        to_district
    ):
        return web.json_response({
            "ok": False,
            "error": "Borish manzili noto‘g‘ri"
        }, status=400)

    if (
        from_region == to_region
        and from_district == to_district
    ):
        return web.json_response({
            "ok": False,
            "error": "Jo‘nash va borish joyi bir xil bo‘lishi mumkin emas"
        }, status=400)

    if not ride_date or not ride_time:
        return web.json_response({
            "ok": False,
            "error": "Sana va vaqtni kiriting"
        }, status=400)

    if seats < 1 or seats > int(driver["seats"]):
        return web.json_response({
            "ok": False,
            "error": f"O‘rindiq 1-{driver['seats']} oralig‘ida bo‘lishi kerak"
        }, status=400)

    if price < 0:
        return web.json_response({
            "ok": False,
            "error": "Narx noto‘g‘ri"
        }, status=400)

    from_city = f"{from_region}, {from_district}"
    to_city = f"{to_region}, {to_district}"

    conn = await db()

    cursor = await conn.execute("""
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
        VALUES (
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            'active',
            ?, ?
        )
    """, (
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

        now_str(),
        now_str()
    ))

    ride_id = cursor.lastrowid

    await conn.commit()
    await conn.close()

    return web.json_response({
        "ok": True,
        "ride_id": ride_id,
        "message": "Safar muvaffaqiyatli qo‘shildi"
    })


# =========================================================
# SEARCH RIDES
# =========================================================

async def web_rides(request):

    user = await get_telegram_user(request)

    if not user:
        return web.json_response(
            {
                "ok": False,
                "error": "Unauthorized"
            },
            status=401
        )

    data = {}

    try:
        if request.method == "POST":
            data = await request.json()
    except Exception:
        pass

    from_region = clean_text(data.get("from_region"))
    from_district = clean_text(data.get("from_district"))

    to_region = clean_text(data.get("to_region"))
    to_district = clean_text(data.get("to_district"))

    ride_date = clean_text(data.get("ride_date"))

    conn = await db()

    query = """
        SELECT
            r.*,

            (
                SELECT COALESCE(SUM(o.seats), 0)
                FROM orders o
                WHERE o.ride_id = r.id
                AND o.status='active'
            ) AS booked_seats

        FROM rides r
        WHERE r.status='active'
    """

    params = []

    if from_region:
        query += " AND r.from_region=?"
        params.append(from_region)

    if from_district:
        query += " AND r.from_district=?"
        params.append(from_district)

    if to_region:
        query += " AND r.to_region=?"
        params.append(to_region)

    if to_district:
        query += " AND r.to_district=?"
        params.append(to_district)

    if ride_date:
        query += " AND r.ride_date=?"
        params.append(ride_date)

    query += " ORDER BY r.ride_date ASC, r.ride_time ASC"

    cursor = await conn.execute(
        query,
        params
    )

    rows = await cursor.fetchall()

    result = []

    for row in rows:

        item = dict(row)

        booked = int(
            item.get("booked_seats") or 0
        )

        total = int(
            item.get("seats") or 0
        )

        available = total - booked

        if available <= 0:
            continue

        item["booked_seats"] = booked
        item["available_seats"] = available

        result.append(item)

    await conn.close()

    return web.json_response({
        "ok": True,
        "rides": result
    })


# =========================================================
# PASSENGER ORDER
# =========================================================

async def web_passenger_order(request):

    user = await get_telegram_user(request)

    if not user:
        return web.json_response(
            {
                "ok": False,
                "error": "Unauthorized"
            },
            status=401
        )

    data = await request.json()

    telegram_id = int(user["id"])

    ride_id = int(data.get("ride_id", 0))

    try:
        seats = int(data.get("seats", 1))
    except Exception:
        seats = 0

    phone = normalize_phone(
        data.get("phone")
    )

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if seats < 1 or seats > 8:
        return web.json_response({
            "ok": False,
            "error": "Yo‘lovchilar soni noto‘g‘ri"
        }, status=400)

    if not phone:
        return web.json_response({
            "ok": False,
            "error": "Telefon raqamingizni kiriting"
        }, status=400)

    conn = await db()

    cursor = await conn.execute("""
        SELECT *
        FROM rides
        WHERE id=?
        AND status='active'
    """, (ride_id,))

    ride = await cursor.fetchone()

    if not ride:
        await conn.close()

        return web.json_response({
            "ok": False,
            "error": "Safar topilmadi"
        }, status=404)

    ride = dict(ride)

    if int(ride["driver_telegram_id"]) == telegram_id:
        await conn.close()

        return web.json_response({
            "ok": False,
            "error": "O‘zingizning safaringizga buyurtma bera olmaysiz"
        }, status=400)

    cursor = await conn.execute("""
        SELECT id
        FROM orders
        WHERE ride_id=?
        AND passenger_telegram_id=?
        AND status='active'
    """, (
        ride_id,
        telegram_id
    ))

    existing = await cursor.fetchone()

    if existing:
        await conn.close()

        return web.json_response({
            "ok": False,
            "error": "Bu safarga allaqachon buyurtma bergansiz"
        }, status=400)

    cursor = await conn.execute("""
        SELECT COALESCE(SUM(seats), 0)
        FROM orders
        WHERE ride_id=?
        AND status='active'
    """, (ride_id,))

    booked = int(
        (await cursor.fetchone())[0] or 0
    )

    available = int(ride["seats"]) - booked

    if seats > available:
        await conn.close()

        return web.json_response({
            "ok": False,
            "error": f"Faqat {available} ta joy qoldi"
        }, status=400)

    passenger_name = clean_text(
        user.get("first_name")
    )

    if user.get("last_name"):
        passenger_name += " " + clean_text(
            user.get("last_name")
        )

    cursor = await conn.execute("""
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
        VALUES (
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            'active',
            ?, ?
        )
    """, (
        ride_id,
        telegram_id,
        passenger_name,
        phone,

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

        now_str(),
        now_str()
    ))

    order_id = cursor.lastrowid

    await conn.commit()
    await conn.close()

    # Notify driver

    location_text = ""

    if latitude and longitude:
        location_text = (
            f"\n📍 <b>Lokatsiya:</b> "
            f"https://www.google.com/maps/search/?api=1&query="
            f"{latitude},{longitude}"
        )

    driver_text = f"""
👤 <b>YANGI YO‘LOVCHI BUYURTMASI</b>

👤 <b>Yo‘lovchi:</b> {passenger_name}
📞 <b>Telefon:</b> {phone}

🛣 <b>Yo‘nalish:</b>
{ride["from_city"]} → {ride["to_city"]}

📅 <b>Sana:</b> {ride["ride_date"]}
🕐 <b>Vaqt:</b> {ride["ride_time"]}

💺 <b>Yo‘lovchilar:</b> {seats}

📞 <a href="tel:{phone}">Yo‘lovchiga qo‘ng‘iroq</a>
{location_text}
"""

    try:
        await bot.send_message(
            int(ride["driver_telegram_id"]),
            driver_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(
            "DRIVER NOTIFY ERROR: %s",
            e
        )

    return web.json_response({
        "ok": True,
        "order_id": order_id,
        "driver_phone": ride["driver_phone"],
        "message": "Buyurtma haydovchiga yuborildi"
    })


# =========================================================
# PASSENGER REQUEST WHEN NO TAXI
# =========================================================

async def web_passenger_request(request):

    user = await get_telegram_user(request)

    if not user:
        return web.json_response(
            {
                "ok": False,
                "error": "Unauthorized"
            },
            status=401
        )

    data = await request.json()

    telegram_id = int(user["id"])

    from_region = clean_text(data.get("from_region"))
    from_district = clean_text(data.get("from_district"))

    to_region = clean_text(data.get("to_region"))
    to_district = clean_text(data.get("to_district"))

    request_date = clean_text(
        data.get("request_date")
    )

    request_time = clean_text(
        data.get("request_time")
        or data.get("time")
    )

    phone = normalize_phone(
        data.get("phone")
    )

    note = clean_text(
        data.get("note")
    )

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    try:
        seats = int(
            data.get("seats", 1)
        )
    except Exception:
        seats = 0

    if not valid_location(
        from_region,
        from_district
    ):
        return web.json_response({
            "ok": False,
            "error": "Jo‘nash manzili noto‘g‘ri"
        }, status=400)

    if not valid_location(
        to_region,
        to_district
    ):
        return web.json_response({
            "ok": False,
            "error": "Borish manzili noto‘g‘ri"
        }, status=400)

    if not request_date or not request_time:
        return web.json_response({
            "ok": False,
            "error": "Sana va vaqt kerak"
        }, status=400)

    if seats < 1 or seats > 8:
        return web.json_response({
            "ok": False,
            "error": "Yo‘lovchilar soni noto‘g‘ri"
        }, status=400)

    if not phone:
        return web.json_response({
            "ok": False,
            "error": "Telefon raqami kerak"
        }, status=400)

    passenger_name = clean_text(
        user.get("first_name")
    )

    if user.get("last_name"):
        passenger_name += " " + clean_text(
            user.get("last_name")
        )

    conn = await db()

    cursor = await conn.execute("""
        INSERT INTO passenger_requests (
            passenger_telegram_id,
            passenger_name,
            passenger_phone,

            from_region,
            from_district,

            to_region,
            to_district,

            request_date,
            request_time,
            seats,

            latitude,
            longitude,

            note,

            status,
            created_at,
            updated_at
        )
        VALUES (
            ?, ?, ?,
            ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?,
            ?,
            'open',
            ?, ?
        )
    """, (
        telegram_id,
        passenger_name,
        phone,

        from_region,
        from_district,

        to_region,
        to_district,

        request_date,
        request_time,
        seats,

        latitude,
        longitude,

        note,

        now_str(),
        now_str()
    ))

    request_id = cursor.lastrowid

    await conn.commit()
    await conn.close()

    return web.json_response({
        "ok": True,
        "request_id": request_id,
        "message": "Buyurtmangiz haydovchilar uchun yuborildi"
    })


# =========================================================
# DRIVER OPEN REQUESTS
# =========================================================

async def web_driver_requests(request):

    user, error = await require_approved_driver(request)

    if error:
        return error

    conn = await db()

    cursor = await conn.execute("""
        SELECT *
        FROM passenger_requests
        WHERE status='open'
        ORDER BY request_date ASC, request_time ASC
    """)

    rows = await cursor.fetchall()

    await conn.close()

    return web.json_response({
        "ok": True,
        "requests": [dict(row) for row in rows]
    })


# =========================================================
# DRIVER ACCEPT PASSENGER REQUEST
# =========================================================

async def web_driver_accept_request(request):

    user, error = await require_approved_driver(request)

    if error:
        return error

    data = await request.json()

    request_id = int(
        data.get("request_id", 0)
    )

    telegram_id = int(user["id"])

    conn = await db()

    cursor = await conn.execute("""
        SELECT *
        FROM passenger_requests
        WHERE id=?
        AND status='open'
    """, (request_id,))

    passenger_request = await cursor.fetchone()

    if not passenger_request:
        await conn.close()

        return web.json_response({
            "ok": False,
            "error": "Buyurtma allaqachon qabul qilingan yoki topilmadi"
        }, status=404)

    driver = await get_driver(telegram_id)

    await conn.execute("""
        UPDATE passenger_requests
        SET status='accepted',
            accepted_driver_telegram_id=?,
            updated_at=?
        WHERE id=?
    """, (
        telegram_id,
        now_str(),
        request_id
    ))

    await conn.commit()
    await conn.close()

    passenger_request = dict(
        passenger_request
    )

    # Notify passenger

    try:
        await bot.send_message(
            int(
                passenger_request[
                    "passenger_telegram_id"
                ]
            ),
            f"""
🟢 <b>BUYURTMANGIZNI HAYDOVCHI QABUL QILDI!</b>

🚕 <b>Haydovchi:</b> {driver["full_name"]}
🚗 <b>Mashina:</b> {driver["car_model"]}
🔢 <b>Raqam:</b> {driver["car_number"]}

📞 <a href="tel:{driver["phone"]}">Haydovchiga qo‘ng‘iroq</a>
""",
            parse_mode="HTML"
        )

    except Exception:
        pass

    return web.json_response({
        "ok": True,
        "message": "Buyurtma qabul qilindi"
    })


# =========================================================
# MY TRIPS
# =========================================================

async def web_orders(request):

    user = await get_telegram_user(request)

    if not user:
        return web.json_response(
            {
                "ok": False,
                "error": "Unauthorized"
            },
            status=401
        )

    telegram_id = int(user["id"])

    conn = await db()

    cursor = await conn.execute("""
        SELECT
            r.*,
            (
                SELECT COALESCE(SUM(o.seats), 0)
                FROM orders o
                WHERE o.ride_id=r.id
                AND o.status='active'
            ) AS booked_seats
        FROM rides r
        WHERE r.driver_telegram_id=?
        ORDER BY r.ride_date DESC, r.ride_time DESC
    """, (telegram_id,))

    driver_rides = [
        dict(row)
        for row in await cursor.fetchall()
    ]

    cursor = await conn.execute("""
        SELECT
            o.*,
            r.driver_name,
            r.driver_phone,
            r.car_model,
            r.car_number,
            r.price
        FROM orders o
        LEFT JOIN rides r
            ON r.id=o.ride_id
        WHERE o.passenger_telegram_id=?
        ORDER BY o.ride_date DESC, o.ride_time DESC
    """, (telegram_id,))

    passenger_orders = [
        dict(row)
        for row in await cursor.fetchall()
    ]

    cursor = await conn.execute("""
        SELECT *
        FROM passenger_requests
        WHERE passenger_telegram_id=?
        ORDER BY created_at DESC
    """, (telegram_id,))

    passenger_requests = [
        dict(row)
        for row in await cursor.fetchall()
    ]

    await conn.close()

    for ride in driver_rides:
        ride["booked_seats"] = int(
            ride.get("booked_seats") or 0
        )
        ride["available_seats"] = (
            int(ride["seats"])
            - ride["booked_seats"]
        )

    return web.json_response({
        "ok": True,

        "driver_rides": driver_rides,

        "passenger_orders": passenger_orders,

        "passenger_requests": passenger_requests,

        # Compatibility
        "rides": driver_rides,
        "orders": passenger_orders
    })


# =========================================================
# PROFILE
# =========================================================

async def web_profile(request):

    user = await get_telegram_user(request)

    if not user:
        return web.json_response(
            {
                "ok": False,
                "error": "Unauthorized"
            },
            status=401
        )

    telegram_id = int(user["id"])

    await ensure_user(user)

    conn = await db()

    cursor = await conn.execute("""
        SELECT *
        FROM users
        WHERE telegram_id=?
    """, (telegram_id,))

    user_row = await cursor.fetchone()

    cursor = await conn.execute("""
        SELECT *
        FROM drivers
        WHERE telegram_id=?
    """, (telegram_id,))

    driver_row = await cursor.fetchone()

    await conn.close()

    return web.json_response({
        "ok": True,
        "user": dict(user_row) if user_row else None,
        "driver": dict(driver_row) if driver_row else None
    })


# =========================================================
# PROFILE UPDATE
# =========================================================

async def web_profile_update(request):

    user = await get_telegram_user(request)

    if not user:
        return web.json_response(
            {
                "ok": False,
                "error": "Unauthorized"
            },
            status=401
        )

    data = await request.json()

    telegram_id = int(user["id"])

    full_name = clean_text(
        data.get("full_name")
    )

    phone = normalize_phone(
        data.get("phone")
    )

    await ensure_user(user)

    conn = await db()

    await conn.execute("""
        UPDATE users
        SET full_name=?,
            phone=?,
            updated_at=?
        WHERE telegram_id=?
    """, (
        full_name,
        phone,
        now_str(),
        telegram_id
    ))

    await conn.execute("""
        UPDATE drivers
        SET full_name=?,
            phone=?,
            updated_at=?
        WHERE telegram_id=?
    """, (
        full_name,
        phone,
        now_str(),
        telegram_id
    ))

    await conn.commit()
    await conn.close()

    return web.json_response({
        "ok": True
    })


# =========================================================
# CANCEL
# =========================================================

async def web_cancel(request):

    user = await get_telegram_user(request)

    if not user:
        return web.json_response(
            {
                "ok": False,
                "error": "Unauthorized"
            },
            status=401
        )

    data = await request.json()

    telegram_id = int(user["id"])

    conn = await db()

    if data.get("order_id"):

        order_id = int(
            data["order_id"]
        )

        cursor = await conn.execute("""
            UPDATE orders
            SET status='cancelled',
                updated_at=?
            WHERE id=?
            AND passenger_telegram_id=?
            AND status='active'
        """, (
            now_str(),
            order_id,
            telegram_id
        ))

    elif data.get("ride_id"):

        ride_id = int(
            data["ride_id"]
        )

        cursor = await conn.execute("""
            UPDATE rides
            SET status='cancelled',
                updated_at=?
            WHERE id=?
            AND driver_telegram_id=?
            AND status='active'
        """, (
            now_str(),
            ride_id,
            telegram_id
        ))

    elif data.get("request_id"):

        request_id = int(
            data["request_id"]
        )

        cursor = await conn.execute("""
            UPDATE passenger_requests
            SET status='cancelled',
                updated_at=?
            WHERE id=?
            AND passenger_telegram_id=?
            AND status='open'
        """, (
            now_str(),
            request_id,
            telegram_id
        ))

    else:
        await conn.close()

        return web.json_response({
            "ok": False,
            "error": "Bekor qilinadigan obyekt topilmadi"
        }, status=400)

    await conn.commit()
    changed = cursor.rowcount

    await conn.close()

    return web.json_response({
        "ok": changed > 0,
        "message": "Bekor qilindi" if changed else "Topilmadi"
    })


# =========================================================
# HEALTH
# =========================================================

async def health_handler(request):

    return web.json_response({
        "ok": True,
        "service": "OPPER TAXI",
        "time": now_str()
    })


# =========================================================
# WEB INDEX
# =========================================================

async def web_index(request):

    if not INDEX_FILE.exists():

        return web.Response(
            status=500,
            text="web/index.html topilmadi"
        )

    response = web.FileResponse(
        INDEX_FILE
    )

    response.headers[
        "Cache-Control"
    ] = "no-store, no-cache, must-revalidate, max-age=0"

    return response


# =========================================================
# TELEGRAM KEYBOARD
# =========================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🚕 OPPER TAXI"
                )
            ],
            [
                KeyboardButton(
                    text="🚕 Haydovchi bo‘lish"
                ),
                KeyboardButton(
                    text="👤 Yo‘lovchi bo‘lish"
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


@dp.message(CommandStart())
async def start_handler(message: Message):

    await message.answer(
        """
🚕 <b>OPPER TAXI</b>

Toshkent va viloyatlar bo‘ylab qulay taksi xizmati.

Ilovani ochib, Haydovchi yoki Yo‘lovchi rejimini tanlang.
""",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "🚕 OPPER TAXI")
async def app_handler(message: Message):

    await message.answer(
        "🚕 OPPER TAXI ilovasini oching:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="🚕 Ilovani ochish",
                        web_app=WebAppInfo(
                            url=MINI_APP_URL
                        )
                    )
                ]
            ],
            resize_keyboard=True
        )
    )


@dp.message(F.text == "🚕 Haydovchi bo‘lish")
async def driver_button(message: Message):

    await message.answer(
        "🚕 Haydovchi rejimini oching:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="🚕 Haydovchi ilovasi",
                        web_app=WebAppInfo(
                            url=MINI_APP_URL + "?mode=driver"
                        )
                    )
                ]
            ],
            resize_keyboard=True
        )
    )


@dp.message(F.text == "👤 Yo‘lovchi bo‘lish")
async def passenger_button(message: Message):

    await message.answer(
        "👤 Yo‘lovchi rejimini oching:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="👤 Yo‘lovchi ilovasi",
                        web_app=WebAppInfo(
                            url=MINI_APP_URL + "?mode=passenger"
                        )
                    )
                ]
            ],
            resize_keyboard=True
        )
    )


@dp.message(F.text == "📞 Yordam")
async def help_handler(message: Message):

    await message.answer(
        """
📞 <b>OPPER TAXI Yordam</b>

Muammo bo‘lsa administratorga murojaat qiling.

🚕 Haydovchi hujjatlari admin tomonidan tekshiriladi.
""",
        parse_mode="HTML"
    )


# =========================================================
# STARTUP
# =========================================================

async def setup_bot():

    await bot.set_my_commands([
        BotCommand(
            command="start",
            description="OPPER TAXI"
        )
    ])

    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🚕 Ilova",
            web_app=WebAppInfo(
                url=MINI_APP_URL
            )
        )
    )

    logging.info(
        "Telegram Mini App menu button o‘rnatildi."
    )


# =========================================================
# WEB SERVER
# =========================================================

async def start_web_server():

    app = web.Application(
        client_max_size=12 * 1024 * 1024
    )

    app.router.add_get(
        "/",
        web_index
    )

    app.router.add_get(
        "/app",
        web_index
    )

    app.router.add_get(
        "/health",
        health_handler
    )

    app.router.add_post(
        "/api/driver/register",
        web_driver_register
    )

    app.router.add_post(
        "/api/driver/status",
        web_driver_status
    )

    app.router.add_post(
        "/api/driver/ride",
        web_driver_ride
    )

    app.router.add_post(
        "/api/driver/requests",
        web_driver_requests
    )

    app.router.add_post(
        "/api/driver/request/accept",
        web_driver_accept_request
    )

    app.router.add_post(
        "/api/rides",
        web_rides
    )

    app.router.add_post(
        "/api/passenger/order",
        web_passenger_order
    )

    app.router.add_post(
        "/api/passenger/request",
        web_passenger_request
    )

    app.router.add_post(
        "/api/orders",
        web_orders
    )

    app.router.add_post(
        "/api/profile",
        web_profile
    )

    app.router.add_post(
        "/api/profile/update",
        web_profile_update
    )

    app.router.add_post(
        "/api/order/cancel",
        web_cancel
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    logging.info(
        "WEB SERVER RUNNING: %s",
        PORT
    )

    logging.info(
        "MINI APP: %s",
        MINI_APP_URL
    )

    return runner


# =========================================================
# MAIN
# =========================================================

async def main():

    logging.info(
        "🚕 OPPER TAXI BOT STARTING..."
    )

    await init_db()

    await setup_bot()

    await start_web_server()

    logging.info(
        "🤖 BOT POLLING STARTED"
    )

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logging.info(
            "BOT STOPPED"
        )
