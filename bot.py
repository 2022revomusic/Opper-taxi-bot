import os
import re
import json
import hmac
import hashlib
import time
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import parse_qsl

import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    BotCommand,
    MenuButtonWebApp,
)

# =========================================================
# OPPER TAXI
# PROFESSIONAL BOT + TELEGRAM MINI APP BACKEND
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("OPPER-TAXI")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN Railway Variables ichida topilmadi.")

ADMIN_ID = int(os.getenv("ADMIN_ID", "653914246"))

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
INDEX_FILE = WEB_DIR / "index.html"

DB_PATH = BASE_DIR / "oper_taxi.db"

UPLOAD_DIR = BASE_DIR / "uploads" / "drivers"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PORT = int(os.getenv("PORT", "8080"))

RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()

if not MINI_APP_URL:
    if RAILWAY_DOMAIN:
        if RAILWAY_DOMAIN.startswith("http"):
            MINI_APP_URL = RAILWAY_DOMAIN
        else:
            MINI_APP_URL = f"https://{RAILWAY_DOMAIN}"

if not MINI_APP_URL:
    MINI_APP_URL = (
        "https://opper-taxi-bot-production.up.railway.app"
    )

# =========================================================
# BOT
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# GENERAL HELPERS
# =========================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def clean_phone(value):
    value = clean_text(value)
    value = re.sub(r"[^\d+]", "", value)

    if value.startswith("00"):
        value = "+" + value[2:]

    return value


def valid_phone(value):
    digits = re.sub(r"\D", "", value or "")
    return 9 <= len(digits) <= 15


def normalize_city(value):
    value = clean_text(value)

    variants = {
        "Farg'ona": "Farg‘ona",
        "Fargʻona": "Farg‘ona",
        "Fargona": "Farg‘ona",

        "Qo'qon": "Qo‘qon",
        "Qoʻqon": "Qo‘qon",
        "Qoqon": "Qo‘qon",

        "Marg'ilon": "Marg‘ilon",
        "Margʻilon": "Marg‘ilon",
        "Margilon": "Marg‘ilon",
    }

    return variants.get(value, value)


CITIES = [
    "Toshkent",
    "Namangan",
    "Andijon",
    "Farg‘ona",
    "Qo‘qon",
    "Marg‘ilon",
]


# =========================================================
# REGION / DISTRICT
# =========================================================

REGIONS = {
    "Toshkent shahri": [
        "Chilonzor",
        "Yunusobod",
        "Mirzo Ulug‘bek",
        "Yakkasaroy",
        "Shayxontohur",
        "Olmazor",
        "Sergeli",
        "Bektemir",
    ],

    "Toshkent viloyati": [
        "Chirchiq",
        "Olmaliq",
        "Angren",
        "Bekobod",
        "Zangiota",
        "Qibray",
        "Yangiyo‘l",
        "Parkent",
    ],

    "Farg‘ona": [
        "Farg‘ona shahri",
        "Bag‘dod",
        "Beshariq",
        "Buvayda",
        "Dang‘ara",
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
        "Quvasoy",
        "Marg‘ilon",
        "Qo‘qon",
    ],

    "Andijon": [
        "Andijon shahri",
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
        "Namangan shahri",
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

    "Samarqand": [
        "Samarqand shahri",
        "Bulung‘ur",
        "Ishtixon",
        "Jomboy",
        "Kattaqo‘rg‘on",
        "Narpay",
        "Nurobod",
        "Oqdaryo",
        "Pastdarg‘om",
        "Paxtachi",
        "Payariq",
        "Urgut",
    ],

    "Buxoro": [
        "Buxoro shahri",
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

    "Qashqadaryo": [
        "Qarshi shahri",
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

    "Surxondaryo": [
        "Termiz shahri",
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
    ],

    "Jizzax": [
        "Jizzax shahri",
        "Arnasoy",
        "Baxmal",
        "Do‘stlik",
        "Forish",
        "G‘allaorol",
        "Mirzacho‘l",
        "Paxtakor",
        "Yangiobod",
        "Zomin",
    ],

    "Sirdaryo": [
        "Guliston shahri",
        "Boyovut",
        "Guliston",
        "Mirzaobod",
        "Oqoltin",
        "Sayxunobod",
        "Sardoba",
        "Sirdaryo",
        "Xovos",
    ],

    "Navoiy": [
        "Navoiy shahri",
        "Karmana",
        "Konimex",
        "Navbahor",
        "Nurota",
        "Qiziltepa",
        "Tomdi",
        "Uchquduq",
        "Xatirchi",
    ],

    "Xorazm": [
        "Urganch shahri",
        "Bog‘ot",
        "Gurlan",
        "Hazorasp",
        "Qo‘shko‘pir",
        "Shovot",
        "Tuproqqal’a",
        "Urganch",
        "Xonqa",
        "Yangiariq",
        "Yangibozor",
    ],

    "Qoraqalpog‘iston": [
        "Nukus shahri",
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
# TELEGRAM INIT DATA VALIDATION
# =========================================================

def validate_init_data(init_data: str):
    """
    Telegram Mini App initData HMAC tekshiruvi.
    """

    if not init_data:
        return None

    try:
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
            f"{key}={value}"
            for key, value in sorted(parsed.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode("utf-8"),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            log.warning("Telegram initData HASH mismatch")
            return None

        auth_date = parsed.get("auth_date")

        if auth_date:

            try:
                age = time.time() - int(auth_date)

                if age > 86400:
                    log.warning(
                        "Telegram initData expired: %s seconds",
                        int(age)
                    )
                    return None

            except ValueError:
                return None

        raw_user = parsed.get("user")

        if not raw_user:
            return None

        return json.loads(raw_user)

    except Exception:

        log.exception(
            "Telegram initData validation error"
        )

        return None


async def get_telegram_user(request):

    try:

        if request.method == "GET":

            init_data = request.query.get(
                "init_data",
                ""
            )

        else:

            if request.content_type == "application/json":

                data = await request.json()

                init_data = data.get(
                    "init_data",
                    ""
                )

            else:

                return None

        return validate_init_data(init_data)

    except Exception:

        log.exception(
            "get_telegram_user error"
        )

        return None


# =========================================================
# DATABASE
# =========================================================

async def column_exists(
    db,
    table,
    column
):

    cur = await db.execute(
        f"PRAGMA table_info({table})"
    )

    rows = await cur.fetchall()

    return any(
        row[1] == column
        for row in rows
    )


async def add_column_if_missing(
    db,
    table,
    column,
    definition
):

    if not await column_exists(
        db,
        table,
        column
    ):

        await db.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


async def init_db():

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        # USERS
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # DRIVERS
        await db.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                car_model TEXT DEFAULT '',
                car_number TEXT DEFAULT '',
                seats INTEGER DEFAULT 1,

                approval_status TEXT DEFAULT 'pending',
                admin_comment TEXT DEFAULT '',

                passport_file TEXT DEFAULT '',
                license_file TEXT DEFAULT '',
                car_registration_file TEXT DEFAULT '',
                car_photo_file TEXT DEFAULT '',

                created_at TEXT,
                updated_at TEXT
            )
        """)

        # RIDES
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

                from_address TEXT DEFAULT '',
                to_address TEXT DEFAULT '',

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

        # ORDERS
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ride_id INTEGER,

                passenger_telegram_id INTEGER,
                passenger_name TEXT,
                passenger_phone TEXT,

                from_city TEXT,
                to_city TEXT,

                from_address TEXT DEFAULT '',
                to_address TEXT DEFAULT '',

                ride_date TEXT,
                ride_time TEXT,

                seats INTEGER,

                latitude REAL,
                longitude REAL,

                status TEXT DEFAULT 'pending',

                created_at TEXT,
                updated_at TEXT
            )
        """)

        # OPEN PASSENGER REQUESTS
        await db.execute("""
            CREATE TABLE IF NOT EXISTS passenger_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                passenger_telegram_id INTEGER,
                passenger_name TEXT,
                passenger_phone TEXT,

                from_region TEXT DEFAULT '',
                from_district TEXT DEFAULT '',
                from_address TEXT DEFAULT '',

                to_region TEXT DEFAULT '',
                to_district TEXT DEFAULT '',
                to_address TEXT DEFAULT '',

                request_date TEXT DEFAULT '',
                request_time TEXT DEFAULT '',

                seats INTEGER DEFAULT 1,

                latitude REAL,
                longitude REAL,

                note TEXT DEFAULT '',

                status TEXT DEFAULT 'open',

                accepted_driver_telegram_id INTEGER,

                created_at TEXT,
                updated_at TEXT
            )
        """)

        # -------------------------------------------------
        # OLD DB MIGRATION
        # -------------------------------------------------

        driver_columns = [

            (
                "approval_status",
                "TEXT DEFAULT 'pending'"
            ),

            (
                "admin_comment",
                "TEXT DEFAULT ''"
            ),

            (
                "passport_file",
                "TEXT DEFAULT ''"
            ),

            (
                "license_file",
                "TEXT DEFAULT ''"
            ),

            (
                "car_registration_file",
                "TEXT DEFAULT ''"
            ),

            (
                "car_photo_file",
                "TEXT DEFAULT ''"
            ),
        ]

        for column, definition in driver_columns:

            await add_column_if_missing(
                db,
                "drivers",
                column,
                definition
            )

        ride_columns = [

            (
                "from_region",
                "TEXT DEFAULT ''"
            ),

            (
                "from_district",
                "TEXT DEFAULT ''"
            ),

            (
                "to_region",
                "TEXT DEFAULT ''"
            ),

            (
                "to_district",
                "TEXT DEFAULT ''"
            ),

            (
                "from_address",
                "TEXT DEFAULT ''"
            ),

            (
                "to_address",
                "TEXT DEFAULT ''"
            ),
        ]

        for column, definition in ride_columns:

            await add_column_if_missing(
                db,
                "rides",
                column,
                definition
            )

        order_columns = [

            (
                "from_address",
                "TEXT DEFAULT ''"
            ),

            (
                "to_address",
                "TEXT DEFAULT ''"
            ),
        ]

        for column, definition in order_columns:

            await add_column_if_missing(
                db,
                "orders",
                column,
                definition
            )

        await db.commit()

    log.info("DATABASE READY")


# =========================================================
# USER
# =========================================================

async def ensure_user(tg_user):

    if not tg_user:
        return

    telegram_id = int(
        tg_user["id"]
    )

    username = clean_text(
        tg_user.get("username", "")
    )

    full_name = " ".join(
        x
        for x in [
            tg_user.get("first_name", ""),
            tg_user.get("last_name", "")
        ]
        if x
    ).strip()

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(
            """
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
                updated_at=excluded.updated_at
            """,

            (
                telegram_id,
                username,
                full_name,
                now(),
                now()
            )
        )

        await db.commit()


async def require_user(request):

    user = await get_telegram_user(
        request
    )

    if not user:

        return (
            None,
            web.json_response(
                {
                    "ok": False,
                    "error":
                        "Telegram tasdiqlamadi. "
                        "Ilovani Telegram ichidan qayta oching."
                },
                status=401
            )
        )

    await ensure_user(user)

    return user, None


# =========================================================
# DRIVER HELPERS
# =========================================================

async def get_driver(telegram_id):

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM drivers
            WHERE telegram_id=?
            """,
            (telegram_id,)
        )

        row = await cur.fetchone()

        if not row:
            return None

        return dict(row)


async def require_approved_driver(request):

    user, error = await require_user(
        request
    )

    if error:
        return None, None, error

    driver = await get_driver(
        int(user["id"])
    )

    if not driver:

        return (
            user,
            None,
            web.json_response(
                {
                    "ok": False,
                    "error":
                        "Siz hali haydovchi sifatida ro‘yxatdan o‘tmagansiz."
                },
                status=403
            )
        )

    if driver["approval_status"] != "approved":

        status_text = {
            "pending":
                "Haydovchilik arizangiz admin tomonidan tekshirilmoqda.",

            "rejected":
                "Haydovchilik arizangiz rad etilgan."
        }.get(
            driver["approval_status"],
            "Haydovchi profilingiz tasdiqlanmagan."
        )

        return (
            user,
            driver,
            web.json_response(
                {
                    "ok": False,
                    "error": status_text,
                    "approval_status":
                        driver["approval_status"],
                    "admin_comment":
                        driver["admin_comment"]
                },
                status=403
            )
        )

    return user, driver, None


# =========================================================
# WEB
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
    ] = (
        "no-store, no-cache, "
        "must-revalidate, max-age=0"
    )

    return response


async def health(request):

    return web.json_response(
        {
            "ok": True,
            "service": "OPPER TAXI",
            "time": now()
        }
    )


async def api_config(request):

    return web.json_response(
        {
            "ok": True,
            "cities": CITIES,
            "regions": REGIONS,
            "mini_app_url": MINI_APP_URL
        }
    )


# =========================================================
# PROFILE
# =========================================================

async def api_profile(request):

    user, error = await require_user(
        request
    )

    if error:
        return error

    telegram_id = int(
        user["id"]
    )

    driver = await get_driver(
        telegram_id
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM users
            WHERE telegram_id=?
            """,
            (telegram_id,)
        )

        db_user = await cur.fetchone()

    role = "passenger"

    if driver:

        if driver["approval_status"] == "approved":
            role = "driver"

        else:
            role = "driver_pending"

    return web.json_response(
        {
            "ok": True,
            "user":
                dict(db_user)
                if db_user else {},

            "driver":
                driver,

            "role":
                role
        }
    )


async def api_profile_update(request):

    user, error = await require_user(
        request
    )

    if error:
        return error

    data = await request.json()

    telegram_id = int(
        user["id"]
    )

    full_name = clean_text(
        data.get("full_name")
    )

    phone = clean_phone(
        data.get("phone")
    )

    if len(full_name) < 3:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Ism familiyangizni kiriting."
            },
            status=400
        )

    if not valid_phone(phone):

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Telefon raqami noto‘g‘ri."
            },
            status=400
        )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(
            """
            UPDATE users
            SET
                full_name=?,
                phone=?,
                updated_at=?
            WHERE telegram_id=?
            """,
            (
                full_name,
                phone,
                now(),
                telegram_id
            )
        )

        await db.commit()

    return web.json_response(
        {
            "ok": True
        }
    )


# =========================================================
# DRIVER REGISTRATION
# =========================================================

async def api_driver_status(request):

    user, error = await require_user(
        request
    )

    if error:
        return error

    driver = await get_driver(
        int(user["id"])
    )

    return web.json_response(
        {
            "ok": True,
            "driver":
                driver
        }
    )


async def api_driver_register(request):

    # multipart/form-data
    # sababli init_data ham shu form ichidan olinadi.

    try:

        fields = {}
        files = {}

        reader = await request.multipart()

        async for part in reader:

            if part.filename:

                content = await part.read()

                files[
                    part.name
                ] = (
                    part.filename,
                    content
                )

            else:

                fields[
                    part.name
                ] = await part.text()

    except Exception:

        log.exception(
            "Driver multipart error"
        )

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Hujjatlarni yuklashda xatolik."
            },
            status=400
        )

    init_data = fields.get(
        "init_data",
        ""
    )

    verified_user = validate_init_data(
        init_data
    )

    if not verified_user:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Telegram tasdiqlamadi. "
                    "Ilovani Telegram ichidan qayta oching."
            },
            status=401
        )

    telegram_id = int(
        verified_user["id"]
    )

    full_name = clean_text(
        fields.get("full_name")
    )

    phone = clean_phone(
        fields.get("phone")
    )

    car_model = clean_text(
        fields.get("car_model")
    )

    car_number = clean_text(
        fields.get("car_number")
    ).upper()

    try:

        seats = int(
            fields.get(
                "seats",
                "1"
            )
        )

    except ValueError:

        seats = 0

    # Hujjatlar
    required_files = [
        "passport_file",
        "license_file",
        "car_registration_file",
        "car_photo_file"
    ]

    for file_key in required_files:

        if file_key not in files:

            return web.json_response(
                {
                    "ok": False,
                    "error":
                        "Barcha hujjatlarni yuklash majburiy."
                },
                status=400
            )

    if len(full_name) < 3:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "To‘liq ism familiyani kiriting."
            },
            status=400
        )

    if not valid_phone(phone):

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Telefon raqami noto‘g‘ri."
            },
            status=400
        )

    if not car_model:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Mashina modelini kiriting."
            },
            status=400
        )

    if not car_number:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Mashina raqamini kiriting."
            },
            status=400
        )

    if seats < 1 or seats > 8:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "O‘rinlar 1–8 oralig‘ida bo‘lishi kerak."
            },
            status=400
        )

    # User yaratish
    await ensure_user(
        verified_user
    )

    driver_dir = (
        UPLOAD_DIR /
        str(telegram_id)
    )

    driver_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    saved_files = {}

    for file_key in required_files:

        filename, content = files[
            file_key
        ]

        if len(content) > 10 * 1024 * 1024:

            return web.json_response(
                {
                    "ok": False,
                    "error":
                        "Har bir fayl 10 MB dan oshmasin."
                },
                status=400
            )

        safe_name = re.sub(
            r"[^a-zA-Z0-9._-]",
            "_",
            filename
        )

        final_path = (
            driver_dir /
            f"{file_key}_{safe_name}"
        )

        final_path.write_bytes(
            content
        )

        saved_files[
            file_key
        ] = str(
            final_path.relative_to(
                BASE_DIR
            )
        )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(
            """
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
                car_registration_file,
                car_photo_file,

                created_at,
                updated_at
            )

            VALUES (
                ?, ?, ?, ?, ?, ?,
                'pending', '',
                ?, ?, ?, ?,
                ?, ?
            )

            ON CONFLICT(telegram_id)
            DO UPDATE SET

                full_name=excluded.full_name,
                phone=excluded.phone,
                car_model=excluded.car_model,
                car_number=excluded.car_number,
                seats=excluded.seats,

                approval_status='pending',
                admin_comment='',

                passport_file=
                    excluded.passport_file,

                license_file=
                    excluded.license_file,

                car_registration_file=
                    excluded.car_registration_file,

                car_photo_file=
                    excluded.car_photo_file,

                updated_at=
                    excluded.updated_at
            """,

            (
                telegram_id,
                full_name,
                phone,
                car_model,
                car_number,
                seats,

                saved_files[
                    "passport_file"
                ],

                saved_files[
                    "license_file"
                ],

                saved_files[
                    "car_registration_file"
                ],

                saved_files[
                    "car_photo_file"
                ],

                now(),
                now()
            )
        )

        await db.execute(
            """
            UPDATE users
            SET
                full_name=?,
                phone=?,
                updated_at=?
            WHERE telegram_id=?
            """,
            (
                full_name,
                phone,
                now(),
                telegram_id
            )
        )

        await db.commit()

    # Admin notification
    try:

        await bot.send_message(
            ADMIN_ID,

            (
                "🆕 <b>YANGI HAYDOVCHI ARIZASI</b>\n\n"

                f"👤 {full_name}\n"
                f"📞 {phone}\n"
                f"🚗 {car_model}\n"
                f"🔢 {car_number}\n"
                f"💺 {seats}\n"
                f"🆔 <code>{telegram_id}</code>\n\n"

                f"✅ Tasdiqlash:\n"
                f"/approve_driver {telegram_id}\n\n"

                f"❌ Rad etish:\n"
                f"/reject_driver {telegram_id} sabab"
            ),

            parse_mode="HTML"
        )

    except Exception:

        log.exception(
            "Admin notification error"
        )

    return web.json_response(
        {
            "ok": True,
            "status": "pending",
            "message":
                "Arizangiz qabul qilindi. "
                "Admin tekshiruvini kuting."
        }
    )


# =========================================================
# DRIVER ADD RIDE
# =========================================================

async def api_driver_ride(request):

    user, driver, error = (
        await require_approved_driver(
            request
        )
    )

    if error:
        return error

    data = await request.json()

    from_city = normalize_city(
        data.get("from_city")
    )

    to_city = normalize_city(
        data.get("to_city")
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

    from_address = clean_text(
        data.get("from_address")
    )

    to_address = clean_text(
        data.get("to_address")
    )

    ride_date = clean_text(
        data.get("ride_date")
    )

    ride_time = clean_text(
        data.get("ride_time")
        or data.get("time")
    )

    try:

        seats = int(
            data.get(
                "seats",
                driver["seats"]
            )
        )

        price = int(
            data.get(
                "price",
                0
            )
        )

    except ValueError:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "O‘rin yoki narx noto‘g‘ri."
            },
            status=400
        )

    if not from_city or not to_city:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Qayerdan va qayerga kiriting."
            },
            status=400
        )

    if from_city == to_city:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Qayerdan va qayerga bir xil bo‘lmasin."
            },
            status=400
        )

    if not ride_date:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Safar sanasini kiriting."
            },
            status=400
        )

    if not ride_time:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Safar vaqtini kiriting."
            },
            status=400
        )

    if seats < 1 or seats > 8:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "O‘rinlar 1–8 oralig‘ida."
            },
            status=400
        )

    if price < 0:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Narx noto‘g‘ri."
            },
            status=400
        )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cur = await db.execute(
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

                from_address,
                to_address,

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

                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                'active',
                ?, ?
            )
            """,

            (
                driver["id"],
                int(user["id"]),

                driver["full_name"],
                driver["phone"],

                from_city,
                to_city,

                from_region,
                from_district,

                to_region,
                to_district,

                from_address,
                to_address,

                ride_date,
                ride_time,

                seats,
                price,

                driver["car_model"],
                driver["car_number"],

                now(),
                now()
            )
        )

        ride_id = cur.lastrowid

        await db.commit()

    return web.json_response(
        {
            "ok": True,
            "ride_id": ride_id
        }
    )


# =========================================================
# SEARCH RIDES
# =========================================================

async def api_rides(request):

    user, error = await require_user(
        request
    )

    if error:
        return error

    q_from = normalize_city(
        request.query.get(
            "from",
            ""
        )
    )

    q_to = normalize_city(
        request.query.get(
            "to",
            ""
        )
    )

    q_date = clean_text(
        request.query.get(
            "date",
            ""
        )
    )

    q_from_district = clean_text(
        request.query.get(
            "from_district",
            ""
        )
    )

    q_to_district = clean_text(
        request.query.get(
            "to_district",
            ""
        )
    )

    conditions = [
        "r.status='active'"
    ]

    params = []

    # MUHIM:
    # Hech qaysi filter majburiy emas.

    if q_from:

        conditions.append(
            """
            (
                r.from_city=?
                OR r.from_region=?
                OR r.from_district=?
            )
            """
        )

        params.extend(
            [
                q_from,
                q_from,
                q_from
            ]
        )

    if q_to:

        conditions.append(
            """
            (
                r.to_city=?
                OR r.to_region=?
                OR r.to_district=?
            )
            """
        )

        params.extend(
            [
                q_to,
                q_to,
                q_to
            ]
        )

    if q_date:

        conditions.append(
            "r.ride_date=?"
        )

        params.append(
            q_date
        )

    if q_from_district:

        conditions.append(
            "r.from_district=?"
        )

        params.append(
            q_from_district
        )

    if q_to_district:

        conditions.append(
            "r.to_district=?"
        )

        params.append(
            q_to_district
        )

    where_sql = " AND ".join(
        conditions
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            f"""
            SELECT

                r.*,

                COALESCE(
                    (
                        SELECT SUM(o.seats)
                        FROM orders o
                        WHERE
                            o.ride_id=r.id
                            AND o.status
                                IN ('pending','accepted')
                    ),
                    0
                ) AS booked_seats

            FROM rides r

            WHERE {where_sql}

            ORDER BY
                r.ride_date ASC,
                r.ride_time ASC,
                r.created_at DESC

            LIMIT 300
            """,

            params
        )

        rows = await cur.fetchall()

    rides = []

    for row in rows:

        item = dict(row)

        booked = int(
            item.get(
                "booked_seats",
                0
            ) or 0
        )

        total = int(
            item.get(
                "seats",
                0
            ) or 0
        )

        available = max(
            0,
            total - booked
        )

        item[
            "available_seats"
        ] = available

        if available > 0:

            rides.append(
                item
            )

    return web.json_response(
        {
            "ok": True,
            "rides": rides,
            "count": len(rides)
        }
    )


# =========================================================
# PASSENGER ORDER
# =========================================================

async def api_passenger_order(request):

    user, error = await require_user(
        request
    )

    if error:
        return error

    data = await request.json()

    telegram_id = int(
        user["id"]
    )

    try:

        ride_id = int(
            data.get("ride_id")
        )

        seats = int(
            data.get(
                "seats",
                1
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Buyurtma ma’lumotlari noto‘g‘ri."
            },
            status=400
        )

    phone = clean_phone(
        data.get("phone")
    )

    if not valid_phone(phone):

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Telefon raqamingizni kiriting."
            },
            status=400
        )

    if seats < 1 or seats > 8:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "O‘rinlar 1–8 oralig‘ida."
            },
            status=400
        )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        # Safar
        cur = await db.execute(
            """
            SELECT *
            FROM rides
            WHERE
                id=?
                AND status='active'
            """,
            (ride_id,)
        )

        ride = await cur.fetchone()

        if not ride:

            return web.json_response(
                {
                    "ok": False,
                    "error":
                        "Safar topilmadi."
                },
                status=404
            )

        if int(
            ride["driver_telegram_id"]
        ) == telegram_id:

            return web.json_response(
                {
                    "ok": False,
                    "error":
                        "O‘zingizning safaringizga buyurtma bera olmaysiz."
                },
                status=400
            )

        # Band o‘rinlar
        cur = await db.execute(
            """
            SELECT
                COALESCE(
                    SUM(seats),
                    0
                ) AS booked
            FROM orders
            WHERE
                ride_id=?
                AND status
                    IN ('pending','accepted')
            """,
            (ride_id,)
        )

        booked_row = await cur.fetchone()

        booked = int(
            booked_row["booked"]
            or 0
        )

        if booked + seats > int(
            ride["seats"]
        ):

            return web.json_response(
                {
                    "ok": False,
                    "error":
                        "Bo‘sh o‘rin yetarli emas."
                },
                status=400
            )

        # Takroriy buyurtma
        cur = await db.execute(
            """
            SELECT id
            FROM orders
            WHERE
                ride_id=?
                AND passenger_telegram_id=?
                AND status
                    IN ('pending','accepted')
            """,
            (
                ride_id,
                telegram_id
            )
        )

        if await cur.fetchone():

            return web.json_response(
                {
                    "ok": False,
                    "error":
                        "Bu safarga allaqachon buyurtma bergansiz."
                },
                status=400
            )

        full_name = " ".join(
            x
            for x in [
                user.get(
                    "first_name",
                    ""
                ),
                user.get(
                    "last_name",
                    ""
                )
            ]
            if x
        ).strip()

        if not full_name:
            full_name = "Yo‘lovchi"

        cur = await db.execute(
            """
            INSERT INTO orders (

                ride_id,

                passenger_telegram_id,
                passenger_name,
                passenger_phone,

                from_city,
                to_city,

                from_address,
                to_address,

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
                ?, ?,
                ?, ?,
                ?,
                ?, ?,
                'pending',
                ?, ?
            )
            """,

            (
                ride_id,

                telegram_id,
                full_name,
                phone,

                ride["from_city"],
                ride["to_city"],

                data.get(
                    "from_address",
                    ""
                ),

                data.get(
                    "to_address",
                    ""
                ),

                ride["ride_date"],
                ride["ride_time"],

                seats,

                data.get(
                    "latitude"
                ),

                data.get(
                    "longitude"
                ),

                now(),
                now()
            )
        )

        order_id = cur.lastrowid

        await db.commit()

    # Haydovchiga Telegram xabari
    try:

        await bot.send_message(
            int(
                ride[
                    "driver_telegram_id"
                ]
            ),

            (
                "🔔 <b>YANGI BUYURTMA</b>\n\n"

                f"👤 {full_name}\n"
                f"📞 {phone}\n\n"

                f"🛣 {ride['from_city']} → "
                f"{ride['to_city']}\n"

                f"📅 {ride['ride_date']}\n"
                f"⏰ {ride['ride_time']}\n"
                f"💺 {seats} ta o‘rin\n\n"

                "📋 Buyurtmani ilovadagi "
                "<b>Buyurtmalarim</b> bo‘limidan ko‘ring."
            ),

            parse_mode="HTML"
        )

    except Exception:

        log.exception(
            "Driver notification error"
        )

    return web.json_response(
        {
            "ok": True,
            "order_id": order_id,
            "status": "pending",
            "message":
                "Buyurtma haydovchiga yuborildi."
        }
    )


# =========================================================
# DRIVER ORDERS
# =========================================================

async def api_driver_orders(request):

    user, driver, error = (
        await require_approved_driver(
            request
        )
    )

    if error:
        return error

    telegram_id = int(
        user["id"]
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT

                o.*,

                r.driver_name,
                r.driver_phone,

                r.from_city AS ride_from_city,
                r.to_city AS ride_to_city,

                r.ride_date,
                r.ride_time,

                r.price AS ride_price,

                r.car_model,
                r.car_number

            FROM orders o

            JOIN rides r
                ON r.id=o.ride_id

            WHERE
                r.driver_telegram_id=?
                AND o.status
                    IN ('pending','accepted')

            ORDER BY

                CASE
                    WHEN o.status='pending'
                    THEN 0
                    ELSE 1
                END,

                o.created_at DESC
            """,

            (telegram_id,)
        )

        rows = await cur.fetchall()

    return web.json_response(
        {
            "ok": True,
            "orders": [
                dict(row)
                for row in rows
            ]
        }
    )


# =========================================================
# DRIVER ACCEPT / REJECT ORDER
# =========================================================

async def api_driver_order_action(request):

    user, driver, error = (
        await require_approved_driver(
            request
        )
    )

    if error:
        return error

    data = await request.json()

    try:

        order_id = int(
            data.get("order_id")
        )

    except (
        ValueError,
        TypeError
    ):

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Buyurtma ID noto‘g‘ri."
            },
            status=400
        )

    action = data.get(
        "action"
    )

    if action not in (
        "accept",
        "reject"
    ):

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Amal noto‘g‘ri."
            },
            status=400
        )

    new_status = (
        "accepted"
        if action == "accept"
        else "rejected"
    )

    telegram_id = int(
        user["id"]
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT

                o.*,

                r.driver_telegram_id

            FROM orders o

            JOIN rides r
                ON r.id=o.ride_id

            WHERE
                o.id=?
                AND r.driver_telegram_id=?
            """,
            (
                order_id,
                telegram_id
            )
        )

        order = await cur.fetchone()

        if not order:

            return web.json_response(
                {
                    "ok": False,
                    "error":
                        "Buyurtma topilmadi."
                },
                status=404
            )

        await db.execute(
            """
            UPDATE orders
            SET
                status=?,
                updated_at=?
            WHERE id=?
            """,
            (
                new_status,
                now(),
                order_id
            )
        )

        await db.commit()

    # Yo‘lovchiga xabar
    try:

        if action == "accept":

            message = (
                "✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
                "Haydovchi buyurtmani tasdiqladi."
            )

        else:

            message = (
                "❌ <b>Buyurtma rad etildi.</b>\n\n"
                "Boshqa taksi tanlashingiz mumkin."
            )

        await bot.send_message(
            int(
                order[
                    "passenger_telegram_id"
                ]
            ),
            message,
            parse_mode="HTML"
        )

    except Exception:

        pass

    return web.json_response(
        {
            "ok": True,
            "status": new_status
        }
    )


# =========================================================
# MY ORDERS / MY RIDES
# =========================================================

async def api_orders(request):

    user, error = await require_user(
        request
    )

    if error:
        return error

    telegram_id = int(
        user["id"]
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        # Haydovchi safarlari
        cur = await db.execute(
            """
            SELECT

                r.*,

                COALESCE(
                    (
                        SELECT SUM(o.seats)
                        FROM orders o
                        WHERE
                            o.ride_id=r.id
                            AND o.status
                                IN ('pending','accepted')
                    ),
                    0
                ) AS booked_seats

            FROM rides r

            WHERE
                r.driver_telegram_id=?

            ORDER BY
                r.created_at DESC
            """,

            (telegram_id,)
        )

        driver_rides = []

        for row in await cur.fetchall():

            item = dict(row)

            item[
                "available_seats"
            ] = max(
                0,
                int(
                    item["seats"]
                )
                -
                int(
                    item[
                        "booked_seats"
                    ]
                    or 0
                )
            )

            driver_rides.append(
                item
            )

        # Yo‘lovchi buyurtmalari
        cur = await db.execute(
            """
            SELECT

                o.*,

                r.driver_name,
                r.driver_phone,

                r.car_model,
                r.car_number,

                r.price,

                r.from_city
                    AS ride_from_city,

                r.to_city
                    AS ride_to_city

            FROM orders o

            JOIN rides r
                ON r.id=o.ride_id

            WHERE
                o.passenger_telegram_id=?

            ORDER BY
                o.created_at DESC
            """,

            (telegram_id,)
        )

        passenger_orders = [
            dict(row)
            for row in await cur.fetchall()
        ]

    return web.json_response(
        {
            "ok": True,

            "driver_rides":
                driver_rides,

            "passenger_orders":
                passenger_orders
        }
    )


# =========================================================
# OPEN PASSENGER REQUEST
# =========================================================

async def api_passenger_request(request):

    user, error = await require_user(
        request
    )

    if error:
        return error

    data = await request.json()

    phone = clean_phone(
        data.get("phone")
    )

    if not valid_phone(phone):

        return web.json_response(
            {
                "ok": False,
                "error":
                    "Telefon raqamingizni kiriting."
            },
            status=400
        )

    try:

        seats = int(
            data.get(
                "seats",
                1
            )
        )

    except ValueError:

        seats = 1

    if seats < 1 or seats > 8:

        return web.json_response(
            {
                "ok": False,
                "error":
                    "O‘rinlar 1–8 oralig‘ida."
            },
            status=400
        )

    full_name = " ".join(
        x
        for x in [
            user.get(
                "first_name",
                ""
            ),
            user.get(
                "last_name",
                ""
            )
        ]
        if x
    ).strip()

    if not full_name:
        full_name = "Yo‘lovchi"

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cur = await db.execute(
            """
            INSERT INTO passenger_requests (

                passenger_telegram_id,
                passenger_name,
                passenger_phone,

                from_region,
                from_district,
                from_address,

                to_region,
                to_district,
                to_address,

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

                ?, ?, ?,

                ?, ?, ?,

                ?, ?,

                ?,

                ?, ?,

                ?,

                'open',

                ?, ?
            )
            """,

            (
                int(user["id"]),
                full_name,
                phone,

                data.get(
                    "from_region",
                    ""
                ),

                data.get(
                    "from_district",
                    ""
                ),

                data.get(
                    "from_address",
                    ""
                ),

                data.get(
                    "to_region",
                    ""
                ),

                data.get(
                    "to_district",
                    ""
                ),

                data.get(
                    "to_address",
                    ""
                ),

                data.get(
                    "request_date",
                    ""
                ),

                data.get(
                    "request_time",
                    ""
                ),

                seats,

                data.get(
                    "latitude"
                ),

                data.get(
                    "longitude"
                ),

                data.get(
                    "note",
                    ""
                ),

                now(),
                now()
            )
        )

        request_id = cur.lastrowid

        await db.commit()

    # Admin xabari
    try:

        await bot.send_message(

            ADMIN_ID,

            (
                "📢 <b>OCHIQ YO‘LOVCHI BUYURTMASI</b>\n\n"

                f"👤 {full_name}\n"
                f"📞 {phone}\n\n"

                f"📍 {data.get('from_region','')} "
                f"{data.get('from_district','')}\n"

                f"🏁 {data.get('to_region','')} "
                f"{data.get('to_district','')}\n"

                f"📅 {data.get('request_date','') or 'Istalgan sana'}\n"
                f"⏰ {data.get('request_time','') or 'Istalgan vaqt'}\n"
                f"💺 {seats}\n"

                f"\n🆔 {request_id}"
            ),

            parse_mode="HTML"
        )

    except Exception:

        pass

    return web.json_response(
        {
            "ok": True,
            "request_id":
                request_id,

            "status":
                "open",

            "message":
                "Ochiq buyurtmangiz qabul qilindi."
        }
    )


# =========================================================
# PASSENGER REQUESTS
# =========================================================

async def api_passenger_requests(request):

    user, error = await require_user(
        request
    )

    if error:
        return error

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM passenger_requests

            WHERE
                passenger_telegram_id=?

            ORDER BY
                created_at DESC
            """,

            (
                int(user["id"]),
            )
        )

        rows = await cur.fetchall()

    return web.json_response(
        {
            "ok": True,
            "requests": [
                dict(row)
                for row in rows
            ]
        }
    )


# =========================================================
# CANCEL ORDER
# =========================================================

async def api_order_cancel(request):

    user, error = await require_user(
        request
    )

    if error:
        return error

    data = await request.json()

    telegram_id = int(
        user["id"]
    )

    if data.get("order_id"):

        try:
            order_id = int(
                data["order_id"]
            )
        except:
            return web.json_response(
                {
                    "ok": False,
                    "error":
                        "Order ID noto‘g‘ri."
                },
                status=400
            )

        async with aiosqlite.connect(
            DB_PATH
        ) as db:

            cur = await db.execute(
                """
                UPDATE orders

                SET
                    status='cancelled',
                    updated_at=?

                WHERE
                    id=?
                    AND passenger_telegram_id=?
                """,

                (
                    now(),
                    order_id,
                    telegram_id
                )
            )

            await db.commit()

            if cur.rowcount == 0:

                return web.json_response(
                    {
                        "ok": False,
                        "error":
                            "Buyurtma topilmadi."
                    },
                    status=404
                )

        return web.json_response(
            {
                "ok": True
            }
        )

    if data.get("ride_id"):

        try:
            ride_id = int(
                data["ride_id"]
            )
        except:
            return web.json_response(
                {
                    "ok": False,
                    "error":
                        "Ride ID noto‘g‘ri."
                },
                status=400
            )

        async with aiosqlite.connect(
            DB_PATH
        ) as db:

            cur = await db.execute(
                """
                UPDATE rides

                SET
                    status='cancelled',
                    updated_at=?

                WHERE
                    id=?
                    AND driver_telegram_id=?
                """,

                (
                    now(),
                    ride_id,
                    telegram_id
                )
            )

            await db.commit()

            if cur.rowcount == 0:

                return web.json_response(
                    {
                        "ok": False,
                        "error":
                            "Safar topilmadi."
                    },
                    status=404
                )

        return web.json_response(
            {
                "ok": True
            }
        )

    return web.json_response(
        {
            "ok": False,
            "error":
                "order_id yoki ride_id kerak."
        },
        status=400
    )


# =========================================================
# ADMIN
# =========================================================

def admin_only(message: Message):

    return (
        message.from_user
        and
        message.from_user.id
        == ADMIN_ID
    )


@dp.message(
    Command("approve_driver")
)
async def approve_driver(
    message: Message
):

    if not admin_only(message):
        return

    parts = (
        message.text or ""
    ).split()

    if len(parts) < 2:

        await message.answer(
            "Foydalanish:\n"
            "/approve_driver TELEGRAM_ID"
        )

        return

    try:

        telegram_id = int(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "Telegram ID noto‘g‘ri."
        )

        return

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cur = await db.execute(
            """
            UPDATE drivers

            SET
                approval_status='approved',
                admin_comment='',
                updated_at=?

            WHERE
                telegram_id=?
            """,

            (
                now(),
                telegram_id
            )
        )

        await db.commit()

        if cur.rowcount == 0:

            await message.answer(
                "Haydovchi topilmadi."
            )

            return

    try:

        await bot.send_message(
            telegram_id,

            (
                "🎉 <b>TABRIKLAYMIZ!</b>\n\n"
                "Haydovchilik arizangiz admin "
                "tomonidan tasdiqlandi.\n\n"
                "Endi OPPER TAXI ilovasida "
                "Haydovchi rejimidan foydalanishingiz mumkin."
            ),

            parse_mode="HTML"
        )

    except Exception:

        pass

    await message.answer(
        "✅ Haydovchi tasdiqlandi."
    )


@dp.message(
    Command("reject_driver")
)
async def reject_driver(
    message: Message
):

    if not admin_only(message):
        return

    parts = (
        message.text or ""
    ).split(
        maxsplit=2
    )

    if len(parts) < 2:

        await message.answer(
            "Foydalanish:\n"
            "/reject_driver TELEGRAM_ID sabab"
        )

        return

    try:

        telegram_id = int(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "Telegram ID noto‘g‘ri."
        )

        return

    reason = (
        parts[2]
        if len(parts) >= 3
        else "Hujjatlar yoki ma’lumotlar talabga javob bermadi."
    )

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        cur = await db.execute(
            """
            UPDATE drivers

            SET
                approval_status='rejected',
                admin_comment=?,
                updated_at=?

            WHERE
                telegram_id=?
            """,

            (
                reason,
                now(),
                telegram_id
            )
        )

        await db.commit()

        if cur.rowcount == 0:

            await message.answer(
                "Haydovchi topilmadi."
            )

            return

    try:

        await bot.send_message(
            telegram_id,

            (
                "❌ <b>Haydovchilik arizasi rad etildi.</b>\n\n"
                f"Sabab: {reason}\n\n"
                "Ma’lumotlaringizni tuzatib, qayta ariza yuborishingiz mumkin."
            ),

            parse_mode="HTML"
        )

    except Exception:

        pass

    await message.answer(
        "❌ Haydovchi arizasi rad etildi."
    )


@dp.message(
    Command("pending_drivers")
)
async def pending_drivers(
    message: Message
):

    if not admin_only(message):
        return

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM drivers

            WHERE
                approval_status='pending'

            ORDER BY
                created_at ASC
            """
        )

        rows = await cur.fetchall()

    if not rows:

        await message.answer(
            "⏳ Kutilayotgan haydovchi yo‘q."
        )

        return

    text = (
        "⏳ <b>KUTILAYOTGAN HAYDOVCHILAR</b>\n\n"
    )

    for row in rows:

        text += (
            f"👤 {row['full_name']}\n"
            f"📞 {row['phone']}\n"
            f"🚗 {row['car_model']}\n"
            f"🔢 {row['car_number']}\n"
            f"🆔 <code>{row['telegram_id']}</code>\n"
            f"/approve_driver {row['telegram_id']}\n"
            f"/reject_driver {row['telegram_id']} sabab\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# TELEGRAM BOT UI
# =========================================================

MAIN_KEYBOARD = ReplyKeyboardMarkup(
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


@dp.message(
    CommandStart()
)
async def start(
    message: Message
):

    await message.answer(
        (
            "🚕 <b>OPPER TAXI</b>\n\n"
            "Shaharlararo taksi xizmatiga xush kelibsiz.\n\n"
            "Ilovani ochib kerakli rejimni tanlang."
        ),
        reply_markup=MAIN_KEYBOARD,
        parse_mode="HTML"
    )


@dp.message(
    F.text == "🚕 Haydovchi bo‘lish"
)
async def driver_button(
    message: Message
):

    await message.answer(
        (
            "🚕 <b>HAYDOVCHI REJIMI</b>\n\n"
            "Haydovchi bo‘lish uchun ilovadagi "
            "Haydovchi bo‘lish bo‘limidan ariza yuboring.\n\n"
            "📄 Hujjatlar tekshiriladi.\n"
            "⏳ Admin tasdig‘idan keyin haydovchi rejimi ochiladi."
        ),
        reply_markup=MAIN_KEYBOARD,
        parse_mode="HTML"
    )


@dp.message(
    F.text == "👤 Yo‘lovchi bo‘lish"
)
async def passenger_button(
    message: Message
):

    await message.answer(
        (
            "👤 <b>YO‘LOVCHI REJIMI</b>\n\n"
            "Ilovani ochib mavjud taksilarni qidiring "
            "yoki ochiq buyurtma qoldiring."
        ),
        reply_markup=MAIN_KEYBOARD,
        parse_mode="HTML"
    )


@dp.message(
    F.text == "📞 Yordam"
)
async def help_button(
    message: Message
):

    await message.answer(
        (
            "📞 <b>OPPER TAXI YORDAM</b>\n\n"
            "Muammo bo‘lsa administratorga murojaat qiling."
        ),
        reply_markup=MAIN_KEYBOARD,
        parse_mode="HTML"
    )


# =========================================================
# STARTUP
# =========================================================

async def setup_bot():

    await bot.set_my_commands(
        [
            BotCommand(
                command="start",
                description="OPPER TAXI"
            ),

            BotCommand(
                command="pending_drivers",
                description="Admin: kutilayotgan haydovchilar"
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

        log.info(
            "Telegram Mini App menu button o‘rnatildi."
        )

    except Exception:

        log.exception(
            "Menu button error"
        )


# =========================================================
# WEB SERVER
# =========================================================

async def create_web_app():

    app = web.Application(
        client_max_size=50 * 1024 * 1024
    )

    # Main
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
        health
    )

    # Config
    app.router.add_get(
        "/api/config",
        api_config
    )

    # Profile
    app.router.add_post(
        "/api/profile",
        api_profile
    )

    app.router.add_post(
        "/api/profile/update",
        api_profile_update
    )

    # Driver
    app.router.add_post(
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

    app.router.add_post(
        "/api/driver/orders",
        api_driver_orders
    )

    app.router.add_post(
        "/api/driver/order/action",
        api_driver_order_action
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

    app.router.add_post(
        "/api/passenger/requests",
        api_passenger_requests
    )

    # Orders
    app.router.add_post(
        "/api/orders",
        api_orders
    )

    app.router.add_post(
        "/api/order/cancel",
        api_order_cancel
    )

    return app


# =========================================================
# MAIN
# =========================================================

async def main():

    log.info(
        "🚕 OPPER TAXI BOT STARTING..."
    )

    await init_db()

    await setup_bot()

    app = await create_web_app()

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

    log.info(
        "🌐 WEB SERVER RUNNING: %s",
        PORT
    )

    log.info(
        "📱 MINI APP: %s",
        MINI_APP_URL
    )

    log.info(
        "🤖 BOT POLLING STARTED"
    )

    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    finally:

        await bot.session.close()

        await runner.cleanup()


if __name__ == "__main__":

    import asyncio

    asyncio.run(
        main()
    )
