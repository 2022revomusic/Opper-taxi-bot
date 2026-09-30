import os
import json
import hmac
import hashlib
import asyncio
import logging
from pathlib import Path
from datetime import datetime

import aiosqlite
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    BotCommand,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "653914246"))

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
INDEX_FILE = WEB_DIR / "index.html"
DB_FILE = BASE_DIR / "oper_taxi.db"

PORT = int(os.getenv("PORT", "8080"))

RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

if RAILWAY_DOMAIN:
    MINI_APP_URL = (
        RAILWAY_DOMAIN
        if RAILWAY_DOMAIN.startswith("http")
        else f"https://{RAILWAY_DOMAIN}"
    )
else:
    MINI_APP_URL = "https://opper-taxi-bot-production.up.railway.app"

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("opper-taxi")

# =========================================================
# BOT
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

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
        "Olmazor",
        "Sergeli",
        "Shayxontohur",
        "Uchtepa",
        "Yakkasaroy",
        "Yashnobod",
        "Bektemir",
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
        "Yuqori Chirchiq",
        "Toshkent tumani",
        "Zangiota",
        "Qibray",
        "Yangiyo‘l",
    ],
    "Farg‘ona viloyati": [
        "Bag‘dod",
        "Beshariq",
        "Buvayda",
        "Dang‘ara",
        "Farg‘ona",
        "Furqat",
        "Qo‘shtepa",
        "Oltiariq",
        "O‘zbekiston",
        "Rishton",
        "So‘x",
        "Toshloq",
        "Uchko‘prik",
        "Yozyovon",
        "Quva",
        "Marg‘ilon",
        "Qo‘qon",
    ],
    "Andijon viloyati": [
        "Andijon",
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
    "Sirdaryo viloyati": [
        "Guliston",
        "Boyovut",
        "Oqoltin",
        "Sayxunobod",
        "Sardoba",
        "Sirdaryo",
        "Xovos",
        "Mirzaobod",
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
        "Yangiobod",
        "Zarbdor",
        "Zafarobod",
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
        "Payariq",
        "Pastdarg‘om",
        "Urgut",
        "Toyloq",
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
        "Qamashi",
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
        "Sariosiyo",
        "Sherobod",
        "Sho‘rchi",
        "Uzun",
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
    "Navoiy viloyati": [
        "Navoiy",
        "Konimex",
        "Karmana",
        "Qiziltepa",
        "Navbahor",
        "Nurota",
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
        "Yangibozor",
        "Yangiariq",
    ],
    "Qoraqalpog‘iston Respublikasi": [
        "Nukus",
        "Amudaryo",
        "Beruniy",
        "Chimboy",
        "Ellikqal’a",
        "Kegeyli",
        "Mo‘ynoq",
        "Qo‘ng‘irot",
        "Qanliko‘l",
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


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_phone(phone):
    phone = clean(phone)
    return phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")


def route_text(
    from_region="",
    from_district="",
    to_region="",
    to_district="",
):
    a = " → ".join(x for x in [from_region, from_district] if x)
    b = " → ".join(x for x in [to_region, to_district] if x)

    if a and b:
        return f"{a}  →  {b}"

    if a:
        return a

    if b:
        return b

    return ""


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


# =========================================================
# TELEGRAM WEBAPP AUTH
# =========================================================

def validate_init_data(init_data: str):
    if not init_data:
        return None

    try:
        parts = init_data.split("&")
        data = {}

        for item in parts:
            if "=" in item:
                key, value = item.split("=", 1)
                data[key] = value

        received_hash = data.get("hash")

        if not received_hash:
            return None

        auth_data = []

        for key in sorted(data.keys()):
            if key == "hash":
                continue
            auth_data.append(f"{key}={data[key]}")

        data_check_string = "\n".join(auth_data)

        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        user_json = data.get("user")

        if not user_json:
            return None

        from urllib.parse import unquote

        user = json.loads(unquote(user_json))

        return user

    except Exception as e:
        logger.error("initData error: %s", e)
        return None


async def get_web_user(request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    init_data = data.get("init_data") or request.query.get("init_data")

    user = validate_init_data(init_data)

    return user


# =========================================================
# DATABASE
# =========================================================

async def ensure_column(db, table, column, definition):
    cursor = await db.execute(f"PRAGMA table_info({table})")
    rows = await cursor.fetchall()

    columns = [row[1] for row in rows]

    if column not in columns:
        await db.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


async def init_db():

    async with aiosqlite.connect(DB_FILE) as db:

        await db.execute("""
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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                full_name TEXT,
                phone TEXT,
                car_model TEXT,
                car_number TEXT,
                seats INTEGER DEFAULT 1,
                approval_status TEXT DEFAULT 'pending',
                admin_comment TEXT DEFAULT '',
                passport_file TEXT DEFAULT '',
                license_file TEXT DEFAULT '',
                car_document_file TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER,
                driver_telegram_id INTEGER,
                driver_name TEXT,
                driver_phone TEXT,
                from_city TEXT,
                to_city TEXT,
                from_region TEXT DEFAULT '',
                from_district TEXT DEFAULT '',
                to_region TEXT DEFAULT '',
                to_district TEXT DEFAULT '',
                ride_date TEXT,
                ride_time TEXT,
                seats INTEGER DEFAULT 1,
                price INTEGER DEFAULT 0,
                car_model TEXT,
                car_number TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER,
                passenger_telegram_id INTEGER,
                passenger_name TEXT,
                passenger_phone TEXT,
                from_city TEXT,
                to_city TEXT,
                from_region TEXT DEFAULT '',
                from_district TEXT DEFAULT '',
                to_region TEXT DEFAULT '',
                to_district TEXT DEFAULT '',
                ride_date TEXT,
                ride_time TEXT,
                seats INTEGER DEFAULT 1,
                latitude REAL,
                longitude REAL,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # YANGI: yo'lovchining ochiq buyurtmalari
        await db.execute("""
            CREATE TABLE IF NOT EXISTS passenger_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                passenger_telegram_id INTEGER,
                passenger_name TEXT,
                passenger_phone TEXT,
                from_region TEXT DEFAULT '',
                from_district TEXT DEFAULT '',
                to_region TEXT DEFAULT '',
                to_district TEXT DEFAULT '',
                request_date TEXT DEFAULT '',
                request_time TEXT DEFAULT '',
                seats INTEGER DEFAULT 1,
                latitude REAL,
                longitude REAL,
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'open',
                accepted_driver_telegram_id INTEGER,
                accepted_driver_name TEXT,
                accepted_driver_phone TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # eski DB lar uchun migration
        await ensure_column(
            db, "drivers", "approval_status",
            "TEXT DEFAULT 'pending'"
        )
        await ensure_column(
            db, "drivers", "admin_comment",
            "TEXT DEFAULT ''"
        )
        await ensure_column(
            db, "drivers", "passport_file",
            "TEXT DEFAULT ''"
        )
        await ensure_column(
            db, "drivers", "license_file",
            "TEXT DEFAULT ''"
        )
        await ensure_column(
            db, "drivers", "car_document_file",
            "TEXT DEFAULT ''"
        )

        for table in ["rides", "orders"]:
            await ensure_column(
                db, table, "from_region",
                "TEXT DEFAULT ''"
            )
            await ensure_column(
                db, table, "from_district",
                "TEXT DEFAULT ''"
            )
            await ensure_column(
                db, table, "to_region",
                "TEXT DEFAULT ''"
            )
            await ensure_column(
                db, table, "to_district",
                "TEXT DEFAULT ''"
            )

        await db.commit()

    logger.info("DATABASE READY")


async def ensure_user(user):
    telegram_id = int(user["id"])

    username = user.get("username", "")
    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")

    full_name = f"{first_name} {last_name}".strip()

    async with aiosqlite.connect(DB_FILE) as db:

        await db.execute("""
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
                username = excluded.username,
                full_name = excluded.full_name,
                updated_at = excluded.updated_at
        """, (
            telegram_id,
            username,
            full_name,
            now_str(),
            now_str(),
        ))

        await db.commit()


async def get_driver(telegram_id):

    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM drivers
            WHERE telegram_id = ?
        """, (telegram_id,))

        return await cursor.fetchone()


# =========================================================
# WEB RESPONSE
# =========================================================

def json_response(data, status=200):
    return web.json_response(
        data,
        status=status,
        headers={
            "Cache-Control": "no-store",
        },
    )


# =========================================================
# DRIVER STATUS
# =========================================================

async def web_driver_status(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    telegram_id = int(user["id"])

    driver = await get_driver(telegram_id)

    if not driver:
        return json_response({
            "ok": True,
            "registered": False,
            "approval_status": "not_registered",
        })

    return json_response({
        "ok": True,
        "registered": True,
        "approval_status": driver["approval_status"],
        "admin_comment": driver["admin_comment"] or "",
        "driver": dict(driver),
    })


# =========================================================
# DRIVER REGISTER
# =========================================================

async def web_driver_register(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    data = await request.json()

    telegram_id = int(user["id"])

    full_name = clean(data.get("full_name"))
    phone = normalize_phone(data.get("phone"))
    car_model = clean(data.get("car_model"))
    car_number = clean(data.get("car_number"))

    seats = safe_int(data.get("seats"), 1)

    passport_file = clean(data.get("passport_file"))
    license_file = clean(data.get("license_file"))
    car_document_file = clean(data.get("car_document_file"))

    if not full_name:
        return json_response({
            "ok": False,
            "error": "F.I.Sh kiriting"
        }, 400)

    if not phone:
        return json_response({
            "ok": False,
            "error": "Telefon raqam kiriting"
        }, 400)

    if not car_model:
        return json_response({
            "ok": False,
            "error": "Mashina modelini kiriting"
        }, 400)

    if not car_number:
        return json_response({
            "ok": False,
            "error": "Mashina raqamini kiriting"
        }, 400)

    if seats < 1 or seats > 8:
        return json_response({
            "ok": False,
            "error": "O‘rinlar 1-8 oralig‘ida bo‘lishi kerak"
        }, 400)

    async with aiosqlite.connect(DB_FILE) as db:

        await db.execute("""
            INSERT INTO drivers (
                telegram_id,
                full_name,
                phone,
                car_model,
                car_number,
                seats,
                approval_status,
                admin_comment,
                passport_file,
                license_file,
                car_document_file,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending', '', ?, ?, ?, ?, ?)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                full_name = excluded.full_name,
                phone = excluded.phone,
                car_model = excluded.car_model,
                car_number = excluded.car_number,
                seats = excluded.seats,
                passport_file = excluded.passport_file,
                license_file = excluded.license_file,
                car_document_file = excluded.car_document_file,
                approval_status = 'pending',
                updated_at = excluded.updated_at
        """, (
            telegram_id,
            full_name,
            phone,
            car_model,
            car_number,
            seats,
            passport_file,
            license_file,
            car_document_file,
            now_str(),
            now_str(),
        ))

        await db.commit()

    try:
        await bot.send_message(
            ADMIN_ID,
            f"""
🚕 YANGI HAYDOVCHI ARIZASI

👤 {full_name}
📞 {phone}
🚗 {car_model}
🔢 {car_number}
💺 {seats} ta o‘rin

Telegram ID: {telegram_id}

Tasdiqlash:
 /approve_driver {telegram_id}

Rad etish:
 /reject_driver {telegram_id}
            """,
        )
    except Exception as e:
        logger.error("Admin notification error: %s", e)

    return json_response({
        "ok": True,
        "approval_status": "pending",
        "message": "Arizangiz admin tasdig‘iga yuborildi."
    })


# =========================================================
# DRIVER ADD RIDE
# =========================================================

async def web_driver_ride(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    telegram_id = int(user["id"])

    driver = await get_driver(telegram_id)

    if not driver:
        return json_response({
            "ok": False,
            "error": "Avval haydovchi sifatida ro‘yxatdan o‘ting"
        }, 403)

    if driver["approval_status"] != "approved":
        return json_response({
            "ok": False,
            "error": "Haydovchi hali admin tomonidan tasdiqlanmagan"
        }, 403)

    data = await request.json()

    from_region = clean(data.get("from_region"))
    from_district = clean(data.get("from_district"))
    to_region = clean(data.get("to_region"))
    to_district = clean(data.get("to_district"))

    ride_date = clean(data.get("ride_date") or data.get("date"))
    ride_time = clean(data.get("ride_time") or data.get("time"))

    seats = safe_int(data.get("seats"), driver["seats"])
    price = safe_int(data.get("price"), 0)

    if not from_region or not to_region:
        return json_response({
            "ok": False,
            "error": "Yo‘nalishni kiriting"
        }, 400)

    if seats < 1 or seats > 8:
        return json_response({
            "ok": False,
            "error": "O‘rinlar noto‘g‘ri"
        }, 400)

    if price < 0:
        return json_response({
            "ok": False,
            "error": "Narx noto‘g‘ri"
        }, 400)

    from_city = from_district or from_region
    to_city = to_district or to_region

    async with aiosqlite.connect(DB_FILE) as db:

        cursor = await db.execute("""
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
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
            now_str(),
        ))

        ride_id = cursor.lastrowid

        await db.commit()

    return json_response({
        "ok": True,
        "ride_id": ride_id,
        "message": "Safar muvaffaqiyatli qo‘shildi"
    })


# =========================================================
# SEARCH RIDES
# =========================================================

async def web_rides(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    data = await request.json()

    from_region = clean(data.get("from_region"))
    from_district = clean(data.get("from_district"))

    to_region = clean(data.get("to_region"))
    to_district = clean(data.get("to_district"))

    ride_date = clean(
        data.get("ride_date")
        or data.get("date")
    )

    ride_time = clean(
        data.get("ride_time")
        or data.get("time")
    )

    seats = safe_int(data.get("seats"), 0)

    conditions = [
        "r.status = 'active'"
    ]

    params = []

    # MUHIM:
    # faqat to‘ldirilgan filtrlar ishlaydi.

    if from_region:
        conditions.append(
            "(r.from_region = ? OR r.from_region LIKE ?)"
        )
        params.extend([
            from_region,
            f"%{from_region}%"
        ])

    if from_district:
        conditions.append(
            "(r.from_district = ? OR r.from_district LIKE ?)"
        )
        params.extend([
            from_district,
            f"%{from_district}%"
        ])

    if to_region:
        conditions.append(
            "(r.to_region = ? OR r.to_region LIKE ?)"
        )
        params.extend([
            to_region,
            f"%{to_region}%"
        ])

    if to_district:
        conditions.append(
            "(r.to_district = ? OR r.to_district LIKE ?)"
        )
        params.extend([
            to_district,
            f"%{to_district}%"
        ])

    if ride_date:
        conditions.append("r.ride_date = ?")
        params.append(ride_date)

    if ride_time:
        conditions.append("r.ride_time = ?")
        params.append(ride_time)

    async with aiosqlite.connect(DB_FILE) as db:

        db.row_factory = aiosqlite.Row

        query = f"""
            SELECT
                r.*,

                (
                    SELECT COALESCE(SUM(o.seats), 0)
                    FROM orders o
                    WHERE o.ride_id = r.id
                    AND o.status = 'active'
                ) AS booked_seats

            FROM rides r

            WHERE {' AND '.join(conditions)}

            ORDER BY
                CASE
                    WHEN r.ride_date = ? THEN 0
                    ELSE 1
                END,
                r.ride_date ASC,
                r.ride_time ASC,
                r.id DESC
        """

        params.append(ride_date)

        cursor = await db.execute(query, params)

        rows = await cursor.fetchall()

        rides = []

        for row in rows:

            item = dict(row)

            booked = safe_int(item["booked_seats"])
            total = safe_int(item["seats"])

            available = total - booked

            if seats > 0 and available < seats:
                continue

            if available <= 0:
                continue

            item["available_seats"] = available
            item["route"] = route_text(
                item["from_region"],
                item["from_district"],
                item["to_region"],
                item["to_district"],
            )

            rides.append(item)

    return json_response({
        "ok": True,
        "rides": rides
    })


# =========================================================
# PASSENGER ORDER EXISTING RIDE
# =========================================================

async def web_passenger_order(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    data = await request.json()

    telegram_id = int(user["id"])

    ride_id = safe_int(data.get("ride_id"))
    seats = safe_int(data.get("seats"), 1)

    passenger_name = clean(
        data.get("passenger_name")
        or user.get("first_name", "")
    )

    passenger_phone = normalize_phone(
        data.get("passenger_phone")
    )

    latitude = safe_float(data.get("latitude"))
    longitude = safe_float(data.get("longitude"))

    if not ride_id:
        return json_response({
            "ok": False,
            "error": "Safar topilmadi"
        }, 400)

    if seats < 1 or seats > 8:
        return json_response({
            "ok": False,
            "error": "O‘rinlar noto‘g‘ri"
        }, 400)

    if not passenger_phone:
        return json_response({
            "ok": False,
            "error": "Telefon raqamingizni kiriting"
        }, 400)

    async with aiosqlite.connect(DB_FILE) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM rides
            WHERE id = ?
            AND status = 'active'
        """, (ride_id,))

        ride = await cursor.fetchone()

        if not ride:
            return json_response({
                "ok": False,
                "error": "Safar mavjud emas"
            }, 404)

        if int(ride["driver_telegram_id"]) == telegram_id:
            return json_response({
                "ok": False,
                "error": "O‘zingizning safaringizga buyurtma bera olmaysiz"
            }, 400)

        cursor = await db.execute("""
            SELECT COALESCE(SUM(seats), 0)
            FROM orders
            WHERE ride_id = ?
            AND status = 'active'
        """, (ride_id,))

        booked = (await cursor.fetchone())[0]

        available = int(ride["seats"]) - int(booked)

        if available < seats:
            return json_response({
                "ok": False,
                "error": "Yetarli bo‘sh joy yo‘q"
            }, 400)

        cursor = await db.execute("""
            SELECT id
            FROM orders
            WHERE ride_id = ?
            AND passenger_telegram_id = ?
            AND status = 'active'
        """, (
            ride_id,
            telegram_id,
        ))

        duplicate = await cursor.fetchone()

        if duplicate:
            return json_response({
                "ok": False,
                "error": "Bu safarga allaqachon buyurtma bergansiz"
            }, 400)

        cursor = await db.execute("""
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """, (
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
            now_str(),
            now_str(),
        ))

        order_id = cursor.lastrowid

        await db.commit()

    # haydovchiga xabar
    try:
        location_text = ""

        if latitude is not None and longitude is not None:
            location_text = (
                f"\n📍 Lokatsiya: "
                f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
            )

        await bot.send_message(
            int(ride["driver_telegram_id"]),
            f"""
🔔 YANGI BUYURTMA

👤 Yo‘lovchi: {passenger_name}
📞 Telefon: {passenger_phone}

🚕 Yo‘nalish:
{route_text(
    ride["from_region"],
    ride["from_district"],
    ride["to_region"],
    ride["to_district"],
)}

📅 {ride["ride_date"]}
🕐 {ride["ride_time"]}
💺 {seats} ta o‘rin
{location_text}
            """
        )
    except Exception as e:
        logger.error("Driver notification error: %s", e)

    return json_response({
        "ok": True,
        "order_id": order_id,
        "driver_phone": ride["driver_phone"],
        "message": "Buyurtma yuborildi"
    })


# =========================================================
# PASSENGER OPEN REQUEST
# =========================================================

async def web_passenger_request(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    data = await request.json()

    telegram_id = int(user["id"])

    passenger_name = clean(
        data.get("passenger_name")
        or user.get("first_name", "")
    )

    passenger_phone = normalize_phone(
        data.get("passenger_phone")
    )

    from_region = clean(data.get("from_region"))
    from_district = clean(data.get("from_district"))

    to_region = clean(data.get("to_region"))
    to_district = clean(data.get("to_district"))

    request_date = clean(data.get("request_date"))
    request_time = clean(data.get("request_time"))

    seats = safe_int(data.get("seats"), 1)

    latitude = safe_float(data.get("latitude"))
    longitude = safe_float(data.get("longitude"))

    note = clean(data.get("note"))

    if not from_region or not to_region:
        return json_response({
            "ok": False,
            "error": "Qayerdan va qayerga yo‘nalishini kiriting"
        }, 400)

    if not passenger_phone:
        return json_response({
            "ok": False,
            "error": "Telefon raqamingizni kiriting"
        }, 400)

    if seats < 1 or seats > 8:
        return json_response({
            "ok": False,
            "error": "O‘rinlar 1-8 oralig‘ida bo‘lishi kerak"
        }, 400)

    async with aiosqlite.connect(DB_FILE) as db:

        cursor = await db.execute("""
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
        """, (
            telegram_id,
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
            now_str(),
            now_str(),
        ))

        request_id = cursor.lastrowid

        await db.commit()

    # barcha tasdiqlangan haydovchilarga yuborish
    async with aiosqlite.connect(DB_FILE) as db:

        cursor = await db.execute("""
            SELECT telegram_id
            FROM drivers
            WHERE approval_status = 'approved'
        """)

        drivers = await cursor.fetchall()

    for row in drivers:

        driver_id = row[0]

        try:

            location_text = ""

            if latitude is not None and longitude is not None:
                location_text = (
                    f"\n📍 Lokatsiya:"
                    f"\nhttps://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
                )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Buyurtmani olish",
                            callback_data=f"take_request:{request_id}"
                        )
                    ]
                ]
            )

            await bot.send_message(
                int(driver_id),
                f"""
📢 YANGI YO‘LOVCHI BUYURTMASI

👤 {passenger_name}
📞 {passenger_phone}

📍 Qayerdan:
{from_region} / {from_district or 'Aniq tuman kiritilmagan'}

📍 Qayerga:
{to_region} / {to_district or 'Aniq tuman kiritilmagan'}

📅 Sana:
{request_date or 'Istalgan sana'}

🕐 Vaqt:
{request_time or 'Istalgan vaqt'}

💺 O‘rin:
{seats}

📝 Izoh:
{note or '—'}
{location_text}
                """,
                reply_markup=keyboard,
            )

        except Exception as e:
            logger.error(
                "Driver request send error %s: %s",
                driver_id,
                e,
            )

    return json_response({
        "ok": True,
        "request_id": request_id,
        "message": "Buyurtmangiz haydovchilarga yuborildi."
    })


# =========================================================
# DRIVER OPEN REQUESTS
# =========================================================

async def web_driver_requests(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    telegram_id = int(user["id"])

    driver = await get_driver(telegram_id)

    if not driver or driver["approval_status"] != "approved":
        return json_response({
            "ok": False,
            "error": "Haydovchi tasdiqlanmagan"
        }, 403)

    async with aiosqlite.connect(DB_FILE) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM passenger_requests
            WHERE status = 'open'
            ORDER BY id DESC
        """)

        rows = await cursor.fetchall()

    return json_response({
        "ok": True,
        "requests": [dict(row) for row in rows]
    })


# =========================================================
# DRIVER ACCEPT REQUEST
# =========================================================

async def web_driver_accept_request(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    telegram_id = int(user["id"])

    driver = await get_driver(telegram_id)

    if not driver or driver["approval_status"] != "approved":
        return json_response({
            "ok": False,
            "error": "Haydovchi tasdiqlanmagan"
        }, 403)

    data = await request.json()

    request_id = safe_int(data.get("request_id"))

    if not request_id:
        return json_response({
            "ok": False,
            "error": "Buyurtma topilmadi"
        }, 400)

    async with aiosqlite.connect(DB_FILE) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM passenger_requests
            WHERE id = ?
            AND status = 'open'
        """, (request_id,))

        passenger_request = await cursor.fetchone()

        if not passenger_request:
            return json_response({
                "ok": False,
                "error": "Bu buyurtmani boshqa haydovchi olgan yoki buyurtma yopilgan"
            }, 409)

        await db.execute("""
            UPDATE passenger_requests
            SET
                status = 'accepted',
                accepted_driver_telegram_id = ?,
                accepted_driver_name = ?,
                accepted_driver_phone = ?,
                updated_at = ?
            WHERE id = ?
            AND status = 'open'
        """, (
            telegram_id,
            driver["full_name"],
            driver["phone"],
            now_str(),
            request_id,
        ))

        await db.commit()

    # yo'lovchiga xabar
    try:

        await bot.send_message(
            int(passenger_request["passenger_telegram_id"]),
            f"""
✅ BUYURTMANGIZ QABUL QILINDI

🚕 Haydovchi:
{driver["full_name"]}

🚗 Mashina:
{driver["car_model"]}

🔢 Raqami:
{driver["car_number"]}

📞 Telefon:
{driver["phone"]}

📍 Yo‘nalish:
{route_text(
    passenger_request["from_region"],
    passenger_request["from_district"],
    passenger_request["to_region"],
    passenger_request["to_district"],
)}
            """
        )

    except Exception as e:
        logger.error("Passenger notification error: %s", e)

    return json_response({
        "ok": True,
        "message": "Buyurtma sizga biriktirildi."
    })


# =========================================================
# DRIVER ORDERS
# =========================================================

async def web_driver_orders(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    telegram_id = int(user["id"])

    driver = await get_driver(telegram_id)

    if not driver or driver["approval_status"] != "approved":
        return json_response({
            "ok": False,
            "error": "Haydovchi tasdiqlanmagan"
        }, 403)

    async with aiosqlite.connect(DB_FILE) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT
                pr.*,
                r.id AS ride_id
            FROM passenger_requests pr
            LEFT JOIN rides r
                ON r.driver_telegram_id = pr.accepted_driver_telegram_id
                AND r.from_region = pr.from_region
                AND r.to_region = pr.to_region
            WHERE pr.accepted_driver_telegram_id = ?
            AND pr.status = 'accepted'

            UNION ALL

            SELECT
                NULL AS id,
                o.passenger_telegram_id,
                o.passenger_name,
                o.passenger_phone,
                o.from_region,
                o.from_district,
                o.to_region,
                o.to_district,
                o.ride_date AS request_date,
                o.ride_time AS request_time,
                o.seats,
                o.latitude,
                o.longitude,
                o.status,
                o.ride_id AS accepted_driver_telegram_id,
                r.driver_name AS accepted_driver_name,
                r.driver_phone AS accepted_driver_phone,
                o.created_at,
                o.updated_at,
                o.ride_id
            FROM orders o
            JOIN rides r ON r.id = o.ride_id
            WHERE r.driver_telegram_id = ?
            AND o.status = 'active'

            ORDER BY updated_at DESC
        """, (
            telegram_id,
            telegram_id,
        ))

        rows = await cursor.fetchall()

    return json_response({
        "ok": True,
        "orders": [dict(row) for row in rows]
    })


# =========================================================
# PASSENGER ORDERS
# =========================================================

async def web_passenger_orders(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    telegram_id = int(user["id"])

    async with aiosqlite.connect(DB_FILE) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT
                o.*,
                r.driver_name,
                r.driver_phone,
                r.car_model,
                r.car_number,
                r.price
            FROM orders o
            JOIN rides r ON r.id = o.ride_id
            WHERE o.passenger_telegram_id = ?
            AND o.status = 'active'

            UNION ALL

            SELECT
                NULL AS id,
                pr.id AS ride_id,
                pr.passenger_telegram_id,
                pr.passenger_name,
                pr.passenger_phone,
                '' AS from_city,
                '' AS to_city,
                pr.from_region,
                pr.from_district,
                pr.to_region,
                pr.to_district,
                pr.request_date AS ride_date,
                pr.request_time AS ride_time,
                pr.seats,
                pr.latitude,
                pr.longitude,
                pr.status,
                pr.created_at,
                pr.updated_at,
                pr.accepted_driver_name AS driver_name,
                pr.accepted_driver_phone AS driver_phone,
                '' AS car_model,
                '' AS car_number,
                0 AS price
            FROM passenger_requests pr
            WHERE pr.passenger_telegram_id = ?
            AND pr.status IN ('open', 'accepted')

            ORDER BY updated_at DESC
        """, (
            telegram_id,
            telegram_id,
        ))

        rows = await cursor.fetchall()

    return json_response({
        "ok": True,
        "orders": [dict(row) for row in rows]
    })


# =========================================================
# PROFILE
# =========================================================

async def web_profile(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    telegram_id = int(user["id"])

    await ensure_user(user)

    driver = await get_driver(telegram_id)

    async with aiosqlite.connect(DB_FILE) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM users
            WHERE telegram_id = ?
        """, (telegram_id,))

        db_user = await cursor.fetchone()

    return json_response({
        "ok": True,
        "user": dict(db_user) if db_user else {},
        "driver": dict(driver) if driver else None,
    })


# =========================================================
# PROFILE UPDATE
# =========================================================

async def web_profile_update(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    data = await request.json()

    telegram_id = int(user["id"])

    full_name = clean(data.get("full_name"))
    phone = normalize_phone(data.get("phone"))

    async with aiosqlite.connect(DB_FILE) as db:

        await db.execute("""
            UPDATE users
            SET
                full_name = ?,
                phone = ?,
                updated_at = ?
            WHERE telegram_id = ?
        """, (
            full_name,
            phone,
            now_str(),
            telegram_id,
        ))

        await db.execute("""
            UPDATE drivers
            SET
                full_name = ?,
                phone = ?,
                updated_at = ?
            WHERE telegram_id = ?
        """, (
            full_name,
            phone,
            now_str(),
            telegram_id,
        ))

        await db.commit()

    return json_response({
        "ok": True,
        "message": "Profil yangilandi"
    })


# =========================================================
# CANCEL ORDER
# =========================================================

async def web_order_cancel(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    data = await request.json()

    telegram_id = int(user["id"])
    order_id = safe_int(data.get("order_id"))

    async with aiosqlite.connect(DB_FILE) as db:

        cursor = await db.execute("""
            UPDATE orders
            SET
                status = 'cancelled',
                updated_at = ?
            WHERE id = ?
            AND passenger_telegram_id = ?
        """, (
            now_str(),
            order_id,
            telegram_id,
        ))

        await db.commit()

        if cursor.rowcount == 0:
            return json_response({
                "ok": False,
                "error": "Buyurtma topilmadi"
            }, 404)

    return json_response({
        "ok": True,
        "message": "Buyurtma bekor qilindi"
    })


# =========================================================
# CANCEL PASSENGER REQUEST
# =========================================================

async def web_passenger_request_cancel(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    data = await request.json()

    telegram_id = int(user["id"])
    request_id = safe_int(data.get("request_id"))

    async with aiosqlite.connect(DB_FILE) as db:

        cursor = await db.execute("""
            UPDATE passenger_requests
            SET
                status = 'cancelled',
                updated_at = ?
            WHERE id = ?
            AND passenger_telegram_id = ?
            AND status = 'open'
        """, (
            now_str(),
            request_id,
            telegram_id,
        ))

        await db.commit()

    return json_response({
        "ok": True,
        "message": "Buyurtma bekor qilindi"
    })


# =========================================================
# DRIVER CANCEL RIDE
# =========================================================

async def web_ride_cancel(request):

    user = await get_web_user(request)

    if not user:
        return json_response({
            "ok": False,
            "error": "Telegram tasdiqlanmadi"
        }, 401)

    data = await request.json()

    telegram_id = int(user["id"])
    ride_id = safe_int(data.get("ride_id"))

    async with aiosqlite.connect(DB_FILE) as db:

        cursor = await db.execute("""
            UPDATE rides
            SET
                status = 'cancelled',
                updated_at = ?
            WHERE id = ?
            AND driver_telegram_id = ?
        """, (
            now_str(),
            ride_id,
            telegram_id,
        ))

        await db.commit()

    return json_response({
        "ok": True,
        "message": "Safar bekor qilindi"
    })


# =========================================================
# ADMIN
# =========================================================

@dp.message(Command("approve_driver"))
async def approve_driver(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()

    if len(parts) < 2:
        await message.answer(
            "Foydalanish:\n/approve_driver TELEGRAM_ID"
        )
        return

    telegram_id = safe_int(parts[1])

    async with aiosqlite.connect(DB_FILE) as db:

        cursor = await db.execute("""
            UPDATE drivers
            SET
                approval_status = 'approved',
                admin_comment = '',
                updated_at = ?
            WHERE telegram_id = ?
        """, (
            now_str(),
            telegram_id,
        ))

        await db.commit()

    if cursor.rowcount:
        await message.answer("✅ Haydovchi tasdiqlandi.")

        try:
            await bot.send_message(
                telegram_id,
                """
✅ SIZ TASDIQLANDINGIZ!

Sizning haydovchi profilingiz admin tomonidan tasdiqlandi.

Endi OPPER TAXI ilovasida 🚕 Haydovchi rejimidan foydalanishingiz mumkin.
                """
            )
        except Exception:
            pass

    else:
        await message.answer("Haydovchi topilmadi.")


@dp.message(Command("reject_driver"))
async def reject_driver(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 2:
        await message.answer(
            "Foydalanish:\n/reject_driver TELEGRAM_ID sabab"
        )
        return

    telegram_id = safe_int(parts[1])

    comment = parts[2] if len(parts) > 2 else "Hujjatlar tekshiruvdan o‘tmadi."

    async with aiosqlite.connect(DB_FILE) as db:

        cursor = await db.execute("""
            UPDATE drivers
            SET
                approval_status = 'rejected',
                admin_comment = ?,
                updated_at = ?
            WHERE telegram_id = ?
        """, (
            comment,
            now_str(),
            telegram_id,
        ))

        await db.commit()

    if cursor.rowcount:

        await message.answer("❌ Haydovchi rad etildi.")

        try:
            await bot.send_message(
                telegram_id,
                f"""
❌ HAYDOVCHI ARIZASI RAD ETILDI

Sabab:
{comment}

Ma’lumotlarni qayta yuborishingiz mumkin.
                """
            )
        except Exception:
            pass

    else:
        await message.answer("Haydovchi topilmadi.")


# =========================================================
# TELEGRAM CALLBACK
# =========================================================

@dp.callback_query(F.data.startswith("take_request:"))
async def callback_take_request(callback):

    if not callback.from_user:
        return

    telegram_id = callback.from_user.id

    driver = await get_driver(telegram_id)

    if not driver or driver["approval_status"] != "approved":
        await callback.answer(
            "Siz tasdiqlangan haydovchi emassiz.",
            show_alert=True
        )
        return

    request_id = safe_int(
        callback.data.split(":", 1)[1]
    )

    async with aiosqlite.connect(DB_FILE) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM passenger_requests
            WHERE id = ?
            AND status = 'open'
        """, (request_id,))

        passenger_request = await cursor.fetchone()

        if not passenger_request:
            await callback.answer(
                "Buyurtmani boshqa haydovchi olgan.",
                show_alert=True
            )
            return

        await db.execute("""
            UPDATE passenger_requests
            SET
                status = 'accepted',
                accepted_driver_telegram_id = ?,
                accepted_driver_name = ?,
                accepted_driver_phone = ?,
                updated_at = ?
            WHERE id = ?
            AND status = 'open'
        """, (
            telegram_id,
            driver["full_name"],
            driver["phone"],
            now_str(),
            request_id,
        ))

        await db.commit()

    await callback.answer("Buyurtma sizga berildi.")

    try:
        await bot.send_message(
            int(passenger_request["passenger_telegram_id"]),
            f"""
✅ HAYDOVCHI TOPILDI!

👤 {driver["full_name"]}
🚗 {driver["car_model"]}
🔢 {driver["car_number"]}
📞 {driver["phone"]}
            """
        )
    except Exception:
        pass


# =========================================================
# TELEGRAM MENU
# =========================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🚕 OPPER TAXI",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ],
            [
                KeyboardButton(text="🚕 Haydovchi bo‘lish"),
                KeyboardButton(text="👤 Yo‘lovchi bo‘lish"),
            ],
            [
                KeyboardButton(text="📞 Yordam"),
            ],
        ],
        resize_keyboard=True,
    )


@dp.message(CommandStart())
async def start_handler(message: Message):

    await ensure_user({
        "id": message.from_user.id,
        "username": message.from_user.username or "",
        "first_name": message.from_user.first_name or "",
        "last_name": message.from_user.last_name or "",
    })

    await message.answer(
        """
🚕 OPPER TAXI

Toshkent va viloyatlar bo‘ylab
haydovchi va yo‘lovchilarni bog‘lovchi xizmat.

Ilovani ochish uchun:
🚕 OPPER TAXI tugmasini bosing.
        """,
        reply_markup=main_keyboard(),
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
                        web_app=WebAppInfo(url=MINI_APP_URL)
                    )
                ]
            ],
            resize_keyboard=True,
        )
    )


@dp.message(F.text == "🚕 Haydovchi bo‘lish")
async def driver_info(message: Message):

    await message.answer(
        """
🚕 HAYDOVCHI BO‘LISH

Haydovchi bo‘lish uchun OPPER TAXI ilovasiga kiring.

Ilovada:
1️⃣ Ma’lumotlaringizni kiriting
2️⃣ Kerakli hujjatlarni yuboring
3️⃣ Admin tekshiradi
4️⃣ Tasdiqlangandan keyin haydovchi rejimi ochiladi.
        """
    )


@dp.message(F.text == "👤 Yo‘lovchi bo‘lish")
async def passenger_info(message: Message):

    await message.answer(
        """
👤 YO‘LOVCHI

Ilovaga kirib:

🔎 Tayyor safarlarni qidiring

yoki

📢 O‘zingizga kerakli yo‘nalish bo‘yicha buyurtma qoldiring.

Mos haydovchi buyurtmangizni oladi.
        """
    )


@dp.message(F.text == "📞 Yordam")
async def help_handler(message: Message):

    await message.answer(
        """
📞 OPPER TAXI YORDAM

Muammo yoki taklif bo‘lsa admin bilan bog‘laning.
        """
    )


# =========================================================
# WEB
# =========================================================

async def web_index(request):

    if not INDEX_FILE.exists():
        return web.Response(
            status=500,
            text="web/index.html topilmadi"
        )

    response = web.FileResponse(INDEX_FILE)

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )

    return response


async def health_handler(request):

    return json_response({
        "ok": True,
        "service": "OPPER TAXI",
        "time": now_str(),
    })


# =========================================================
# SERVER
# =========================================================

async def start_web_server():

    app = web.Application()

    app.router.add_get("/", web_index)
    app.router.add_get("/app", web_index)
    app.router.add_get("/health", health_handler)

    app.router.add_post(
        "/api/driver/status",
        web_driver_status
    )

    app.router.add_post(
        "/api/driver/register",
        web_driver_register
    )

    app.router.add_post(
        "/api/driver/ride",
        web_driver_ride
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
        "/api/passenger/orders",
        web_passenger_orders
    )

    app.router.add_post(
        "/api/passenger/request/cancel",
        web_passenger_request_cancel
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
        "/api/driver/orders",
        web_driver_orders
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
        web_order_cancel
    )

    app.router.add_post(
        "/api/ride/cancel",
        web_ride_cancel
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    logger.info(
        "WEB SERVER RUNNING: %s",
        PORT
    )

    logger.info(
        "MINI APP: %s",
        MINI_APP_URL
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    logger.info("🚕 OPPER TAXI BOT STARTING...")

    await init_db()

    await start_web_server()

    try:
        await bot.set_my_commands([
            BotCommand(
                command="start",
                description="OPPER TAXI"
            ),
            BotCommand(
                command="help",
                description="Yordam"
            ),
        ])
    except Exception as e:
        logger.error("Bot commands error: %s", e)

    logger.info("🤖 BOT POLLING STARTED")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
