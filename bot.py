import os
import json
import hmac
import hashlib
import asyncio
import logging
from pathlib import Path
from datetime import datetime, date

import aiosqlite
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    MenuButtonWebApp,
    BotCommand,
)
from aiogram.filters import CommandStart, Command


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

ADMIN_ID = int(os.getenv("ADMIN_ID", "653914246"))

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
INDEX_FILE = WEB_DIR / "index.html"

DB_FILE = BASE_DIR / "oper_taxi.db"

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


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("opper_taxi")


# =========================================================
# TELEGRAM
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# CITIES / DISTRICTS
# =========================================================

REGIONS = {
    "Toshkent shahri": [
        "Bektemir",
        "Chilonzor",
        "Yashnobod",
        "Mirobod",
        "Mirzo Ulug‘bek",
        "Olmazor",
        "Sergeli",
        "Shayxontohur",
        "Uchtepa",
        "Yakkasaroy",
        "Yunusobod",
        "Yangihayot",
    ],

    "Toshkent viloyati": [
        "Bekobod",
        "Bo‘ka",
        "Bo‘stonliq",
        "Chinoz",
        "Ohangaron",
        "Oqqo‘rg‘on",
        "Parkent",
        "Piskent",
        "Quyi Chirchiq",
        "Toshkent tumani",
        "Uchko‘prik",
        "Yuqori Chirchiq",
        "Zangiota",
        "Yangiyo‘l",
    ],

    "Farg‘ona": [
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
    ],

    "Andijon": [
        "Andijon tumani",
        "Asaka",
        "Baliqchi",
        "Bo‘ston",
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

    "Namangan": [
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
    ],

    "Samarqand": [
        "Bulung‘ur",
        "Ishtixon",
        "Jomboy",
        "Kattaqo‘rg‘on",
        "Kattaqo‘rg‘on tumani",
        "Narpay",
        "Nurobod",
        "Oqdaryo",
        "Paxtachi",
        "Payariq",
        "Pastdarg‘om",
        "Qo‘shrabot",
        "Samarqand tumani",
        "Toyloq",
        "Urgut",
    ],

    "Buxoro": [
        "Buxoro tumani",
        "G‘ijduvon",
        "Jondor",
        "Kogon",
        "Kogon tumani",
        "Olot",
        "Peshku",
        "Qorako‘l",
        "Qorovulbozor",
        "Romitan",
        "Shofirkon",
        "Vobkent",
    ],

    "Qashqadaryo": [
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
        "Shahrisabz",
        "Shahrisabz tumani",
        "Yakkabog‘",
    ],

    "Surxondaryo": [
        "Angor",
        "Bandixon",
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
        "Uzun",
    ],

    "Jizzax": [
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

    "Sirdaryo": [
        "Boyovut",
        "Guliston tumani",
        "Mirzaobod",
        "Oqoltin",
        "Sayxunobod",
        "Sardoba",
        "Sirdaryo tumani",
        "Xovos",
    ],

    "Navoiy": [
        "Karmana",
        "Konimex",
        "Navbahor",
        "Navoiy tumani",
        "Nurota",
        "Qiziltepa",
        "Tomdi",
        "Uchquduq",
        "Xatirchi",
    ],

    "Xorazm": [
        "Bog‘ot",
        "Gurlan",
        "Hazorasp",
        "Xiva tumani",
        "Qo‘shko‘pir",
        "Shovot",
        "Urganch tumani",
        "Yangiariq",
        "Yangibozor",
    ],

    "Qoraqalpog‘iston": [
        "Amudaryo",
        "Beruniy",
        "Bo‘zatov",
        "Chimboy",
        "Ellikqal’a",
        "Kegeyli",
        "Mo‘ynoq",
        "Nukus tumani",
        "Qanliko‘l",
        "Qo‘ng‘irot",
        "Qorao‘zak",
        "Shumanay",
        "Taxtako‘pir",
        "To‘rtko‘l",
        "Xo‘jayli",
    ],
}


REGION_ALIASES = {
    "Toshkent": "Toshkent shahri",
    "Fargona": "Farg‘ona",
    "Farg'ona": "Farg‘ona",
    "Andijon": "Andijon",
    "Namangan": "Namangan",
    "Samarqand": "Samarqand",
    "Buxoro": "Buxoro",
    "Qashqadaryo": "Qashqadaryo",
    "Surxondaryo": "Surxondaryo",
    "Jizzax": "Jizzax",
    "Sirdaryo": "Sirdaryo",
    "Navoiy": "Navoiy",
    "Xorazm": "Xorazm",
    "Qoraqalpog‘iston": "Qoraqalpog‘iston",
}


def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip()

    replacements = {
        "ʻ": "'",
        "ʼ": "'",
        "’": "'",
        "`": "'",
        "‘": "'",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return " ".join(value.split()).lower()


def normalize_region(value):
    value = normalize_text(value)

    for original, normalized in REGION_ALIASES.items():
        if normalize_text(original) == value:
            return normalized

    for region in REGIONS:
        if normalize_text(region) == value:
            return region

    return str(value).strip()


def normalize_district(value):
    if not value:
        return ""

    normalized = normalize_text(value)

    for region, districts in REGIONS.items():
        for district in districts:
            if normalize_text(district) == normalized:
                return district

    return str(value).strip()


def valid_region(value):
    region = normalize_region(value)
    return region in REGIONS


def valid_district(region, district):
    region = normalize_region(region)
    district = normalize_district(district)

    if region not in REGIONS:
        return False

    return any(
        normalize_text(x) == normalize_text(district)
        for x in REGIONS[region]
    )


# =========================================================
# HELPERS
# =========================================================

def clean_text(value, max_len=500):
    if value is None:
        return ""

    value = str(value).strip()

    return value[:max_len]


def clean_phone(value):
    value = clean_text(value, 30)

    allowed = "+0123456789()- "

    return "".join(ch for ch in value if ch in allowed)


def today_string():
    return date.today().isoformat()


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


def json_response(data, status=200):
    return web.json_response(
        data,
        status=status,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


async def request_json(request):
    try:
        return await request.json()
    except Exception:
        return {}


# =========================================================
# DATABASE
# =========================================================

async def db_execute(query, params=()):
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(query, params)
        await db.commit()

        return cursor


async def db_fetchone(query, params=()):
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(query, params)
        return await cursor.fetchone()


async def db_fetchall(query, params=()):
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(query, params)
        return await cursor.fetchall()


async def column_exists(db, table, column):
    cursor = await db.execute(f"PRAGMA table_info({table})")
    rows = await cursor.fetchall()

    return any(row[1] == column for row in rows)


async def add_column_if_missing(db, table, column, definition):
    if not await column_exists(db, table, column):
        await db.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


async def init_db():

    async with aiosqlite.connect(DB_FILE) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER,
                driver_telegram_id INTEGER,
                driver_name TEXT DEFAULT '',
                driver_phone TEXT DEFAULT '',

                from_city TEXT DEFAULT '',
                from_district TEXT DEFAULT '',

                to_city TEXT DEFAULT '',
                to_district TEXT DEFAULT '',

                ride_date TEXT DEFAULT '',
                ride_time TEXT DEFAULT '',

                seats INTEGER DEFAULT 1,
                price INTEGER DEFAULT 0,

                car_model TEXT DEFAULT '',
                car_number TEXT DEFAULT '',

                status TEXT DEFAULT 'active',

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ride_id INTEGER,

                passenger_telegram_id INTEGER,
                passenger_name TEXT DEFAULT '',
                passenger_phone TEXT DEFAULT '',

                from_city TEXT DEFAULT '',
                from_district TEXT DEFAULT '',

                to_city TEXT DEFAULT '',
                to_district TEXT DEFAULT '',

                ride_date TEXT DEFAULT '',
                ride_time TEXT DEFAULT '',

                seats INTEGER DEFAULT 1,

                latitude REAL,
                longitude REAL,

                location_text TEXT DEFAULT '',

                status TEXT DEFAULT 'active',

                accepted_driver_telegram_id INTEGER,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Existing old database migration
        ride_columns = [
            ("from_district", "TEXT DEFAULT ''"),
            ("to_district", "TEXT DEFAULT ''"),
        ]

        for column, definition in ride_columns:
            await add_column_if_missing(
                db,
                "rides",
                column,
                definition,
            )

        order_columns = [
            ("from_district", "TEXT DEFAULT ''"),
            ("to_district", "TEXT DEFAULT ''"),
            ("latitude", "REAL"),
            ("longitude", "REAL"),
            ("location_text", "TEXT DEFAULT ''"),
            ("accepted_driver_telegram_id", "INTEGER"),
        ]

        for column, definition in order_columns:
            await add_column_if_missing(
                db,
                "orders",
                column,
                definition,
            )

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rides_search
            ON rides(
                status,
                from_city,
                from_district,
                to_city,
                to_district,
                ride_date
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_status
            ON orders(status)
        """)

        await db.commit()

    logger.info("DATABASE READY")


# =========================================================
# TELEGRAM INIT DATA
# =========================================================

def validate_init_data(init_data: str):
    if not init_data:
        return None

    try:
        from urllib.parse import parse_qsl
        import time

        pairs = dict(parse_qsl(init_data, keep_blank_values=True))

        received_hash = pairs.pop("hash", None)

        if not received_hash:
            return None

        auth_date = pairs.get("auth_date")

        if auth_date:
            try:
                if time.time() - int(auth_date) > 86400:
                    return None
            except Exception:
                return None

        data_check_string = "\n".join(
            f"{key}={pairs[key]}"
            for key in sorted(pairs.keys())
        )

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

        if not hmac.compare_digest(
            calculated_hash,
            received_hash,
        ):
            return None

        user_json = pairs.get("user")

        if not user_json:
            return None

        return json.loads(user_json)

    except Exception as e:
        logger.warning("INIT DATA ERROR: %s", e)
        return None


async def get_telegram_user(request, data=None):

    init_data = ""

    if data:
        init_data = data.get("init_data", "")

    if not init_data:
        init_data = request.query.get("init_data", "")

    user = validate_init_data(init_data)

    if not user:
        return None

    return user


# =========================================================
# USER
# =========================================================

async def ensure_user(tg_user):

    telegram_id = int(tg_user["id"])

    username = clean_text(
        tg_user.get("username", ""),
        100,
    )

    full_name = clean_text(
        (
            tg_user.get("first_name", "")
            + " "
            + tg_user.get("last_name", "")
        ).strip(),
        150,
    )

    existing = await db_fetchone(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    if existing:
        await db_execute(
            """
            UPDATE users
            SET username = ?,
                full_name = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """,
            (
                username,
                full_name,
                telegram_id,
            ),
        )
    else:
        await db_execute(
            """
            INSERT INTO users(
                telegram_id,
                username,
                full_name
            )
            VALUES (?, ?, ?)
            """,
            (
                telegram_id,
                username,
                full_name,
            ),
        )


# =========================================================
# TELEGRAM NOTIFICATION
# =========================================================

async def notify_user(telegram_id, text, reply_markup=None):

    try:
        await bot.send_message(
            telegram_id,
            text,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.warning(
            "Telegram notification failed %s: %s",
            telegram_id,
            e,
        )


# =========================================================
# WEB
# =========================================================

async def web_index(request):

    if not INDEX_FILE.exists():
        return web.Response(
            status=500,
            text="web/index.html topilmadi",
        )

    response = web.FileResponse(INDEX_FILE)

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )

    response.headers["Pragma"] = "no-cache"

    return response


async def health_handler(request):

    return json_response({
        "ok": True,
        "service": "OPPER TAXI",
        "database": DB_FILE.exists(),
    })


async def api_regions(request):

    return json_response({
        "ok": True,
        "regions": REGIONS,
    })


# =========================================================
# DRIVER REGISTER
# =========================================================

async def web_driver_register(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    full_name = clean_text(data.get("full_name"), 150)
    phone = clean_phone(data.get("phone"))
    car_model = clean_text(data.get("car_model"), 100)
    car_number = clean_text(data.get("car_number"), 30)
    seats = safe_int(data.get("seats"), 0)

    if not full_name:
        return json_response({
            "ok": False,
            "error": "Ism familiya kiriting",
        }, 400)

    if not phone:
        return json_response({
            "ok": False,
            "error": "Telefon raqam kiriting",
        }, 400)

    if not car_model:
        return json_response({
            "ok": False,
            "error": "Mashina modelini kiriting",
        }, 400)

    if not car_number:
        return json_response({
            "ok": False,
            "error": "Mashina raqamini kiriting",
        }, 400)

    if seats < 1 or seats > 8:
        return json_response({
            "ok": False,
            "error": "O‘rindiqlar soni 1-8 oralig‘ida bo‘lishi kerak",
        }, 400)

    telegram_id = int(tg_user["id"])

    await ensure_user(tg_user)

    await db_execute(
        """
        INSERT INTO drivers(
            telegram_id,
            full_name,
            phone,
            car_model,
            car_number,
            seats
        )
        VALUES (?, ?, ?, ?, ?, ?)

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            full_name = excluded.full_name,
            phone = excluded.phone,
            car_model = excluded.car_model,
            car_number = excluded.car_number,
            seats = excluded.seats,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            telegram_id,
            full_name,
            phone,
            car_model,
            car_number,
            seats,
        ),
    )

    await db_execute(
        """
        UPDATE users
        SET full_name = ?,
            phone = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE telegram_id = ?
        """,
        (
            full_name,
            phone,
            telegram_id,
        ),
    )

    await notify_user(
        telegram_id,
        "✅ Haydovchi profilingiz muvaffaqiyatli saqlandi.\n\n"
        "Endi safar qo‘shishingiz yoki yo‘lovchi zakazlarini qabul qilishingiz mumkin.",
    )

    return json_response({
        "ok": True,
        "message": "Haydovchi profili saqlandi",
    })


# =========================================================
# ADD DRIVER RIDE
# =========================================================

async def web_driver_ride(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    telegram_id = int(tg_user["id"])

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    if not driver:
        return json_response({
            "ok": False,
            "error": "Avval haydovchi sifatida ro‘yxatdan o‘ting",
        }, 400)

    from_city = normalize_region(data.get("from_city"))
    from_district = normalize_district(data.get("from_district"))

    to_city = normalize_region(data.get("to_city"))
    to_district = normalize_district(data.get("to_district"))

    ride_date = clean_text(data.get("ride_date"), 20)

    ride_time = clean_text(
        data.get("ride_time")
        or data.get("time"),
        20,
    )

    seats = safe_int(data.get("seats"), 0)
    price = safe_int(data.get("price"), -1)

    if not valid_region(from_city):
        return json_response({
            "ok": False,
            "error": "Jo‘nab ketish viloyati noto‘g‘ri",
        }, 400)

    if not valid_district(from_city, from_district):
        return json_response({
            "ok": False,
            "error": "Jo‘nab ketish tumani noto‘g‘ri",
        }, 400)

    if not valid_region(to_city):
        return json_response({
            "ok": False,
            "error": "Borish viloyati noto‘g‘ri",
        }, 400)

    if not valid_district(to_city, to_district):
        return json_response({
            "ok": False,
            "error": "Borish tumani noto‘g‘ri",
        }, 400)

    if (
        normalize_text(from_city) == normalize_text(to_city)
        and normalize_text(from_district)
        == normalize_text(to_district)
    ):
        return json_response({
            "ok": False,
            "error": "Jo‘nash va borish joyi bir xil bo‘lishi mumkin emas",
        }, 400)

    if not ride_date:
        return json_response({
            "ok": False,
            "error": "Sana tanlang",
        }, 400)

    if not ride_time:
        return json_response({
            "ok": False,
            "error": "Vaqt tanlang",
        }, 400)

    if seats < 1 or seats > 8:
        return json_response({
            "ok": False,
            "error": "O‘rindiqlar soni noto‘g‘ri",
        }, 400)

    if seats > int(driver["seats"]):
        return json_response({
            "ok": False,
            "error": "Sizning mashinangizdagi o‘rindiqlardan ko‘p joy ko‘rsatilgan",
        }, 400)

    if price < 0:
        return json_response({
            "ok": False,
            "error": "Narx noto‘g‘ri",
        }, 400)

    await db_execute(
        """
        INSERT INTO rides(
            driver_id,
            driver_telegram_id,
            driver_name,
            driver_phone,
            from_city,
            from_district,
            to_city,
            to_district,
            ride_date,
            ride_time,
            seats,
            price,
            car_model,
            car_number,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """,
        (
            driver["id"],
            telegram_id,
            driver["full_name"],
            driver["phone"],
            from_city,
            from_district,
            to_city,
            to_district,
            ride_date,
            ride_time,
            seats,
            price,
            driver["car_model"],
            driver["car_number"],
        ),
    )

    return json_response({
        "ok": True,
        "message": "Safar muvaffaqiyatli qo‘shildi",
    })


# =========================================================
# SEARCH DRIVER RIDES
# =========================================================

async def web_search_rides(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    from_city = normalize_region(data.get("from_city"))
    from_district = normalize_district(data.get("from_district"))

    to_city = normalize_region(data.get("to_city"))
    to_district = normalize_district(data.get("to_district"))

    ride_date = clean_text(data.get("ride_date"), 20)

    query = """
        SELECT
            r.*,

            (
                SELECT COALESCE(SUM(o.seats), 0)
                FROM orders o
                WHERE o.ride_id = r.id
                AND o.status = 'active'
            ) AS booked_seats

        FROM rides r

        WHERE r.status = 'active'
    """

    params = []

    if from_city:
        query += " AND r.from_city = ?"
        params.append(from_city)

    if from_district:
        query += " AND r.from_district = ?"
        params.append(from_district)

    if to_city:
        query += " AND r.to_city = ?"
        params.append(to_city)

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

    rows = await db_fetchall(query, tuple(params))

    rides = []

    for row in rows:

        booked = int(row["booked_seats"] or 0)
        total = int(row["seats"] or 0)

        available = total - booked

        if available <= 0:
            continue

        rides.append({
            "id": row["id"],
            "driver_name": row["driver_name"],
            "driver_phone": row["driver_phone"],
            "from_city": row["from_city"],
            "from_district": row["from_district"],
            "to_city": row["to_city"],
            "to_district": row["to_district"],
            "ride_date": row["ride_date"],
            "ride_time": row["ride_time"],
            "seats": total,
            "booked_seats": booked,
            "available_seats": available,
            "price": row["price"],
            "car_model": row["car_model"],
            "car_number": row["car_number"],
            "status": row["status"],
        })

    return json_response({
        "ok": True,
        "rides": rides,
    })


# =========================================================
# PASSENGER ORDER
# =========================================================

async def web_passenger_order(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    telegram_id = int(tg_user["id"])

    await ensure_user(tg_user)

    from_city = normalize_region(data.get("from_city"))
    from_district = normalize_district(data.get("from_district"))

    to_city = normalize_region(data.get("to_city"))
    to_district = normalize_district(data.get("to_district"))

    ride_date = clean_text(data.get("ride_date"), 20)

    ride_time = clean_text(
        data.get("ride_time")
        or data.get("time"),
        20,
    )

    phone = clean_phone(data.get("phone"))

    seats = safe_int(data.get("seats"), 0)

    latitude = safe_float(data.get("latitude"))
    longitude = safe_float(data.get("longitude"))

    location_text = clean_text(
        data.get("location_text"),
        300,
    )

    ride_id = safe_int(data.get("ride_id"), 0)

    if not valid_region(from_city):
        return json_response({
            "ok": False,
            "error": "Jo‘nash viloyati noto‘g‘ri",
        }, 400)

    if not valid_district(from_city, from_district):
        return json_response({
            "ok": False,
            "error": "Jo‘nash tumani noto‘g‘ri",
        }, 400)

    if not valid_region(to_city):
        return json_response({
            "ok": False,
            "error": "Borish viloyati noto‘g‘ri",
        }, 400)

    if not valid_district(to_city, to_district):
        return json_response({
            "ok": False,
            "error": "Borish tumani noto‘g‘ri",
        }, 400)

    if not ride_date or not ride_time:
        return json_response({
            "ok": False,
            "error": "Sana va vaqtni kiriting",
        }, 400)

    if seats < 1 or seats > 8:
        return json_response({
            "ok": False,
            "error": "Yo‘lovchilar soni 1-8 oralig‘ida bo‘lishi kerak",
        }, 400)

    if not phone:
        return json_response({
            "ok": False,
            "error": "Telefon raqamingizni kiriting",
        }, 400)

    if latitude is None or longitude is None:
        return json_response({
            "ok": False,
            "error": "Avval lokatsiyangizni yuboring",
        }, 400)

    passenger_name = clean_text(
        (
            tg_user.get("first_name", "")
            + " "
            + tg_user.get("last_name", "")
        ).strip(),
        150,
    )

    # -----------------------------------------------------
    # 1. If ride_id exists, order specific driver ride
    # -----------------------------------------------------

    if ride_id:

        ride = await db_fetchone(
            """
            SELECT *
            FROM rides
            WHERE id = ?
            AND status = 'active'
            """,
            (ride_id,),
        )

        if not ride:
            return json_response({
                "ok": False,
                "error": "Bu safar topilmadi yoki bekor qilingan",
            }, 404)

        if int(ride["driver_telegram_id"]) == telegram_id:
            return json_response({
                "ok": False,
                "error": "O‘zingizning safaringizga buyurtma bera olmaysiz",
            }, 400)

        duplicate = await db_fetchone(
            """
            SELECT id
            FROM orders
            WHERE ride_id = ?
            AND passenger_telegram_id = ?
            AND status = 'active'
            """,
            (
                ride_id,
                telegram_id,
            ),
        )

        if duplicate:
            return json_response({
                "ok": False,
                "error": "Siz bu safarga allaqachon buyurtma bergansiz",
            }, 400)

        booked_row = await db_fetchone(
            """
            SELECT COALESCE(SUM(seats), 0) AS booked
            FROM orders
            WHERE ride_id = ?
            AND status = 'active'
            """,
            (ride_id,),
        )

        booked = int(booked_row["booked"] or 0)

        if booked + seats > int(ride["seats"]):
            return json_response({
                "ok": False,
                "error": "Bu safarda yetarli bo‘sh joy qolmagan",
            }, 400)

        cursor = await db_execute(
            """
            INSERT INTO orders(
                ride_id,
                passenger_telegram_id,
                passenger_name,
                passenger_phone,
                from_city,
                from_district,
                to_city,
                to_district,
                ride_date,
                ride_time,
                seats,
                latitude,
                longitude,
                location_text,
                status,
                accepted_driver_telegram_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                ride_id,
                telegram_id,
                passenger_name,
                phone,
                from_city,
                from_district,
                to_city,
                to_district,
                ride_date,
                ride_time,
                seats,
                latitude,
                longitude,
                location_text,
                ride["driver_telegram_id"],
            ),
        )

        order_id = cursor.lastrowid

        map_url = (
            f"https://www.google.com/maps/search/"
            f"?api=1&query={latitude},{longitude}"
        )

        driver_text = (
            "📢 YANGI YO‘LOVCHI BUYURTMASI\n\n"
            f"👤 {passenger_name}\n"
            f"📞 {phone}\n"
            f"📍 {from_city}, {from_district}\n"
            f"🏁 {to_city}, {to_district}\n"
            f"📅 {ride_date}\n"
            f"🕐 {ride_time}\n"
            f"👥 {seats} kishi\n\n"
            f"📍 Yo‘lovchi lokatsiyasi:\n{map_url}"
        )

        await notify_user(
            int(ride["driver_telegram_id"]),
            driver_text,
        )

        return json_response({
            "ok": True,
            "message": "Buyurtma haydovchiga yuborildi",
            "order_id": order_id,
            "driver": {
                "name": ride["driver_name"],
                "phone": ride["driver_phone"],
                "car_model": ride["car_model"],
                "car_number": ride["car_number"],
            },
        })

    # -----------------------------------------------------
    # 2. Search suitable rides
    # -----------------------------------------------------

    matching_rides = await db_fetchall(
        """
        SELECT
            r.*,

            (
                SELECT COALESCE(SUM(o.seats), 0)
                FROM orders o
                WHERE o.ride_id = r.id
                AND o.status = 'active'
            ) AS booked_seats

        FROM rides r

        WHERE r.status = 'active'
        AND r.from_city = ?
        AND r.from_district = ?
        AND r.to_city = ?
        AND r.to_district = ?
        AND r.ride_date = ?

        ORDER BY r.ride_time ASC
        LIMIT 20
        """,
        (
            from_city,
            from_district,
            to_city,
            to_district,
            ride_date,
        ),
    )

    available_rides = []

    for ride in matching_rides:

        booked = int(ride["booked_seats"] or 0)
        available = int(ride["seats"]) - booked

        if available >= seats:
            available_rides.append({
                "id": ride["id"],
                "driver_name": ride["driver_name"],
                "driver_phone": ride["driver_phone"],
                "from_city": ride["from_city"],
                "from_district": ride["from_district"],
                "to_city": ride["to_city"],
                "to_district": ride["to_district"],
                "ride_date": ride["ride_date"],
                "ride_time": ride["ride_time"],
                "price": ride["price"],
                "car_model": ride["car_model"],
                "car_number": ride["car_number"],
                "available_seats": available,
            })

    if available_rides:

        return json_response({
            "ok": True,
            "mode": "rides_found",
            "rides": available_rides,
        })

    # -----------------------------------------------------
    # 3. No taxi found -> create open order
    # -----------------------------------------------------

    cursor = await db_execute(
        """
        INSERT INTO orders(
            ride_id,
            passenger_telegram_id,
            passenger_name,
            passenger_phone,
            from_city,
            from_district,
            to_city,
            to_district,
            ride_date,
            ride_time,
            seats,
            latitude,
            longitude,
            location_text,
            status,
            accepted_driver_telegram_id
        )
        VALUES (
            NULL,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?,
            'open',
            NULL
        )
        """,
        (
            telegram_id,
            passenger_name,
            phone,
            from_city,
            from_district,
            to_city,
            to_district,
            ride_date,
            ride_time,
            seats,
            latitude,
            longitude,
            location_text,
        ),
    )

    order_id = cursor.lastrowid

    # Notify admin
    map_url = (
        f"https://www.google.com/maps/search/"
        f"?api=1&query={latitude},{longitude}"
    )

    await notify_user(
        ADMIN_ID,
        (
            "📢 YANGI OCHIQ TAKSI ZAKAZI\n\n"
            f"👤 {passenger_name}\n"
            f"📞 {phone}\n"
            f"📍 {from_city}, {from_district}\n"
            f"🏁 {to_city}, {to_district}\n"
            f"📅 {ride_date}\n"
            f"🕐 {ride_time}\n"
            f"👥 {seats} kishi\n\n"
            f"🗺 Lokatsiya:\n{map_url}"
        ),
    )

    return json_response({
        "ok": True,
        "mode": "order_created",
        "order_id": order_id,
        "message": (
            "Hozircha bu yo‘nalishda taksi topilmadi. "
            "Buyurtmangiz taksistlarga yuborildi."
        ),
    })


# =========================================================
# OPEN ORDERS FOR DRIVER
# =========================================================

async def web_open_orders(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    telegram_id = int(tg_user["id"])

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    if not driver:
        return json_response({
            "ok": False,
            "error": "Haydovchi profili topilmadi",
        }, 400)

    rows = await db_fetchall(
        """
        SELECT *
        FROM orders
        WHERE status = 'open'
        ORDER BY created_at DESC
        LIMIT 100
        """
    )

    orders = []

    for row in rows:

        map_url = ""

        if row["latitude"] is not None and row["longitude"] is not None:
            map_url = (
                "https://www.google.com/maps/search/"
                "?api=1&query="
                f"{row['latitude']},{row['longitude']}"
            )

        orders.append({
            "id": row["id"],
            "passenger_name": row["passenger_name"],
            "passenger_phone": row["passenger_phone"],
            "from_city": row["from_city"],
            "from_district": row["from_district"],
            "to_city": row["to_city"],
            "to_district": row["to_district"],
            "ride_date": row["ride_date"],
            "ride_time": row["ride_time"],
            "seats": row["seats"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "location_text": row["location_text"],
            "map_url": map_url,
            "status": row["status"],
        })

    return json_response({
        "ok": True,
        "orders": orders,
    })


# =========================================================
# DRIVER ACCEPT OPEN ORDER
# =========================================================

async def web_accept_order(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    telegram_id = int(tg_user["id"])

    order_id = safe_int(data.get("order_id"), 0)

    if not order_id:
        return json_response({
            "ok": False,
            "error": "Zakaz ID topilmadi",
        }, 400)

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    if not driver:
        return json_response({
            "ok": False,
            "error": "Avval haydovchi bo‘lib ro‘yxatdan o‘ting",
        }, 400)

    # Atomic acceptance
    async with aiosqlite.connect(DB_FILE) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            UPDATE orders
            SET status = 'accepted',
                accepted_driver_telegram_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            AND status = 'open'
            """,
            (
                telegram_id,
                order_id,
            ),
        )

        await db.commit()

        if cursor.rowcount == 0:
            return json_response({
                "ok": False,
                "error": "Bu zakazni boshqa haydovchi olib bo‘lgan yoki zakaz yopilgan",
            }, 409)

        cursor = await db.execute(
            """
            SELECT *
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        )

        order = await cursor.fetchone()

    if not order:
        return json_response({
            "ok": False,
            "error": "Zakaz topilmadi",
        }, 404)

    map_url = ""

    if order["latitude"] is not None and order["longitude"] is not None:
        map_url = (
            "https://www.google.com/maps/search/"
            "?api=1&query="
            f"{order['latitude']},{order['longitude']}"
        )

    passenger_text = (
        "🚕 HAYDOVCHI ZAKAZINGIZNI QABUL QILDI!\n\n"
        f"👤 Haydovchi: {driver['full_name']}\n"
        f"📞 Telefon: {driver['phone']}\n"
        f"🚗 Mashina: {driver['car_model']}\n"
        f"🔢 Raqami: {driver['car_number']}\n\n"
        f"📍 Sizning manzilingiz:\n{map_url}"
    )

    await notify_user(
        int(order["passenger_telegram_id"]),
        passenger_text,
    )

    return json_response({
        "ok": True,
        "message": "Zakaz sizga biriktirildi",
        "order": {
            "id": order["id"],
            "passenger_name": order["passenger_name"],
            "passenger_phone": order["passenger_phone"],
            "latitude": order["latitude"],
            "longitude": order["longitude"],
            "map_url": map_url,
        },
    })


# =========================================================
# MY TRIPS / ORDERS
# =========================================================

async def web_orders(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    telegram_id = int(tg_user["id"])

    driver_rides_rows = await db_fetchall(
        """
        SELECT
            r.*,

            (
                SELECT COALESCE(SUM(o.seats), 0)
                FROM orders o
                WHERE o.ride_id = r.id
                AND o.status = 'active'
            ) AS booked_seats

        FROM rides r

        WHERE r.driver_telegram_id = ?

        ORDER BY r.created_at DESC
        LIMIT 100
        """,
        (telegram_id,),
    )

    driver_rides = []

    for row in driver_rides_rows:

        booked = int(row["booked_seats"] or 0)

        driver_rides.append({
            "id": row["id"],
            "from_city": row["from_city"],
            "from_district": row["from_district"],
            "to_city": row["to_city"],
            "to_district": row["to_district"],
            "ride_date": row["ride_date"],
            "ride_time": row["ride_time"],
            "seats": row["seats"],
            "booked_seats": booked,
            "available_seats": int(row["seats"]) - booked,
            "price": row["price"],
            "car_model": row["car_model"],
            "car_number": row["car_number"],
            "status": row["status"],
        })

    passenger_rows = await db_fetchall(
        """
        SELECT
            o.*,
            r.driver_name,
            r.driver_phone,
            r.car_model,
            r.car_number,
            r.price

        FROM orders o

        LEFT JOIN rides r
        ON r.id = o.ride_id

        WHERE o.passenger_telegram_id = ?

        ORDER BY o.created_at DESC
        LIMIT 100
        """,
        (telegram_id,),
    )

    passenger_orders = []

    for row in passenger_rows:

        map_url = ""

        if row["latitude"] is not None and row["longitude"] is not None:
            map_url = (
                "https://www.google.com/maps/search/"
                "?api=1&query="
                f"{row['latitude']},{row['longitude']}"
            )

        passenger_orders.append({
            "id": row["id"],
            "ride_id": row["ride_id"],
            "from_city": row["from_city"],
            "from_district": row["from_district"],
            "to_city": row["to_city"],
            "to_district": row["to_district"],
            "ride_date": row["ride_date"],
            "ride_time": row["ride_time"],
            "seats": row["seats"],
            "status": row["status"],
            "driver_name": row["driver_name"],
            "driver_phone": row["driver_phone"],
            "car_model": row["car_model"],
            "car_number": row["car_number"],
            "price": row["price"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "map_url": map_url,
        })

    # Orders accepted by this driver
    accepted_rows = await db_fetchall(
        """
        SELECT *
        FROM orders
        WHERE accepted_driver_telegram_id = ?
        ORDER BY created_at DESC
        LIMIT 100
        """,
        (telegram_id,),
    )

    accepted_orders = []

    for row in accepted_rows:

        map_url = ""

        if row["latitude"] is not None and row["longitude"] is not None:
            map_url = (
                "https://www.google.com/maps/search/"
                "?api=1&query="
                f"{row['latitude']},{row['longitude']}"
            )

        accepted_orders.append({
            "id": row["id"],
            "passenger_name": row["passenger_name"],
            "passenger_phone": row["passenger_phone"],
            "from_city": row["from_city"],
            "from_district": row["from_district"],
            "to_city": row["to_city"],
            "to_district": row["to_district"],
            "ride_date": row["ride_date"],
            "ride_time": row["ride_time"],
            "seats": row["seats"],
            "status": row["status"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "map_url": map_url,
        })

    return json_response({
        "ok": True,

        "driver_rides": driver_rides,
        "rides": driver_rides,

        "passenger_orders": passenger_orders,
        "orders": passenger_orders,

        "accepted_orders": accepted_orders,
    })


# =========================================================
# PROFILE
# =========================================================

async def web_profile(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    telegram_id = int(tg_user["id"])

    user = await db_fetchone(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    return json_response({
        "ok": True,

        "user": dict(user) if user else None,

        "driver": dict(driver) if driver else None,
    })


# =========================================================
# PROFILE UPDATE
# =========================================================

async def web_profile_update(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    telegram_id = int(tg_user["id"])

    full_name = clean_text(
        data.get("full_name"),
        150,
    )

    phone = clean_phone(
        data.get("phone")
    )

    await db_execute(
        """
        UPDATE users
        SET full_name = ?,
            phone = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE telegram_id = ?
        """,
        (
            full_name,
            phone,
            telegram_id,
        ),
    )

    await db_execute(
        """
        UPDATE drivers
        SET full_name = ?,
            phone = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE telegram_id = ?
        """,
        (
            full_name,
            phone,
            telegram_id,
        ),
    )

    return json_response({
        "ok": True,
        "message": "Profil yangilandi",
    })


# =========================================================
# CANCEL ORDER / RIDE
# =========================================================

async def web_cancel(request):

    data = await request_json(request)

    tg_user = await get_telegram_user(request, data)

    if not tg_user:
        return json_response({
            "ok": False,
            "error": "Telegram foydalanuvchisi aniqlanmadi",
        }, 401)

    telegram_id = int(tg_user["id"])

    order_id = safe_int(data.get("order_id"), 0)
    ride_id = safe_int(data.get("ride_id"), 0)

    # Cancel passenger order
    if order_id:

        order = await db_fetchone(
            """
            SELECT *
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        )

        if not order:
            return json_response({
                "ok": False,
                "error": "Zakaz topilmadi",
            }, 404)

        if int(order["passenger_telegram_id"]) != telegram_id:
            return json_response({
                "ok": False,
                "error": "Bu zakaz sizga tegishli emas",
            }, 403)

        await db_execute(
            """
            UPDATE orders
            SET status = 'cancelled',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (order_id,),
        )

        if order["accepted_driver_telegram_id"]:
            await notify_user(
                int(order["accepted_driver_telegram_id"]),
                "❌ Yo‘lovchi buyurtmasini bekor qildi.",
            )

        return json_response({
            "ok": True,
            "message": "Buyurtma bekor qilindi",
        })

    # Cancel driver ride
    if ride_id:

        ride = await db_fetchone(
            """
            SELECT *
            FROM rides
            WHERE id = ?
            """,
            (ride_id,),
        )

        if not ride:
            return json_response({
                "ok": False,
                "error": "Safar topilmadi",
            }, 404)

        if int(ride["driver_telegram_id"]) != telegram_id:
            return json_response({
                "ok": False,
                "error": "Bu safar sizga tegishli emas",
            }, 403)

        await db_execute(
            """
            UPDATE rides
            SET status = 'cancelled',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (ride_id,),
        )

        await db_execute(
            """
            UPDATE orders
            SET status = 'cancelled',
                updated_at = CURRENT_TIMESTAMP
            WHERE ride_id = ?
            AND status = 'active'
            """,
            (ride_id,),
        )

        return json_response({
            "ok": True,
            "message": "Safar bekor qilindi",
        })

    return json_response({
        "ok": False,
        "error": "order_id yoki ride_id kerak",
    }, 400)


# =========================================================
# TELEGRAM BOT KEYBOARD
# =========================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🚕 OPPER TAXI",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    ),
                )
            ],
            [
                KeyboardButton(text="🚕 Haydovchi bo‘lish"),
                KeyboardButton(text="👤 Yo‘lovchi bo‘lish"),
            ],
            [
                KeyboardButton(text="🔎 Safar qidirish"),
                KeyboardButton(text="📢 Taksi chaqirish"),
            ],
            [
                KeyboardButton(text="📋 Mening safarlarim"),
                KeyboardButton(text="👤 Profilim"),
            ],
            [
                KeyboardButton(text="📞 Yordam"),
            ],
        ],
        resize_keyboard=True,
    )


# =========================================================
# BOT COMMANDS
# =========================================================

@dp.message(CommandStart())
async def start_handler(message: Message):

    await ensure_user({
        "id": message.from_user.id,
        "username": message.from_user.username or "",
        "first_name": message.from_user.first_name or "",
        "last_name": message.from_user.last_name or "",
    })

    await message.answer(
        "🚕 OPPER TAXI\n\n"
        "Yo‘lovchi sifatida taksi chaqiring yoki "
        "haydovchi sifatida safar qo‘shing.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "🚕 OPPER TAXI")
async def app_handler(message: Message):

    await message.answer(
        "🚕 OPPER TAXI ilovasini ochish uchun yuqoridagi tugmani bosing.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "🚕 Haydovchi bo‘lish")
async def driver_handler(message: Message):

    await message.answer(
        "🚕 Haydovchi bo‘lish uchun OPPER TAXI ilovasini oching "
        "va «Haydovchi» bo‘limidan ro‘yxatdan o‘ting.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "👤 Yo‘lovchi bo‘lish")
async def passenger_handler(message: Message):

    await message.answer(
        "👤 Yo‘lovchi sifatida taksi chaqirish uchun "
        "OPPER TAXI ilovasini oching.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text.in_({
    "🔎 Safar qidirish",
    "📢 Taksi chaqirish",
}))
async def taxi_handler(message: Message):

    await message.answer(
        "🚕 OPPER TAXI ilovasini ochib, "
        "«Taksi chaqirish» bo‘limidan foydalaning.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "📋 Mening safarlarim")
async def trips_handler(message: Message):

    await message.answer(
        "📋 Safarlar va buyurtmalaringizni "
        "OPPER TAXI ilovasidagi «Mening safarlarim» bo‘limidan ko‘ring.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "👤 Profilim")
async def profile_handler(message: Message):

    await message.answer(
        "👤 Profilingizni OPPER TAXI ilovasida ko‘rishingiz va "
        "o‘zgartirishingiz mumkin.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "📞 Yordam")
async def help_handler(message: Message):

    await message.answer(
        "📞 OPPER TAXI Yordam\n\n"
        "Ilovada muammo yuzaga kelsa administrator bilan bog‘laning.",
        reply_markup=main_keyboard(),
    )


# =========================================================
# WEB APP ROUTES
# =========================================================

app = web.Application(
    client_max_size=5 * 1024 * 1024,
)

app.router.add_get("/", web_index)
app.router.add_get("/app", web_index)
app.router.add_get("/health", health_handler)

app.router.add_get("/api/regions", api_regions)

app.router.add_post(
    "/api/driver/register",
    web_driver_register,
)

app.router.add_post(
    "/api/driver/ride",
    web_driver_ride,
)

app.router.add_post(
    "/api/rides",
    web_search_rides,
)

app.router.add_post(
    "/api/passenger/order",
    web_passenger_order,
)

app.router.add_post(
    "/api/orders",
    web_orders,
)

app.router.add_post(
    "/api/open-orders",
    web_open_orders,
)

app.router.add_post(
    "/api/order/accept",
    web_accept_order,
)

app.router.add_post(
    "/api/profile",
    web_profile,
)

app.router.add_post(
    "/api/profile/update",
    web_profile_update,
)

app.router.add_post(
    "/api/order/cancel",
    web_cancel,
)


# =========================================================
# SETUP BOT
# =========================================================

async def setup_bot():

    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🚕 Ilova",
            web_app=WebAppInfo(
                url=MINI_APP_URL,
            ),
        )
    )

    await bot.set_my_commands([
        BotCommand(
            command="start",
            description="OPPER TAXI ni ochish",
        ),
        BotCommand(
            command="help",
            description="Yordam",
        ),
    ])

    logger.info(
        "Telegram Mini App menu button o‘rnatildi."
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    logger.info("🚕 OPPER TAXI BOT STARTING...")

    await init_db()

    await setup_bot()

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    logger.info(
        "🌐 WEB SERVER RUNNING: %s",
        PORT,
    )

    logger.info(
        "📱 MINI APP: %s",
        MINI_APP_URL,
    )

    logger.info(
        "🤖 BOT POLLING STARTED",
    )

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    finally:

        await runner.cleanup()

        await bot.session.close()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("BOT STOPPED")

    except Exception as e:
        logger.exception(
            "FATAL ERROR: %s",
            e,
        )
