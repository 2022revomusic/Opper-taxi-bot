import os
import re
import json
import hmac
import hashlib
import logging
import asyncio
from pathlib import Path
from datetime import datetime

import aiosqlite
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    MenuButtonWebApp,
    BotCommand,
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

PORT = int(os.getenv("PORT", "8080"))

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
INDEX_FILE = WEB_DIR / "index.html"
DB_PATH = BASE_DIR / "oper_taxi.db"

MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()

if not MINI_APP_URL:
    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

    if domain:
        if domain.startswith("http"):
            MINI_APP_URL = domain
        else:
            MINI_APP_URL = "https://" + domain

if not MINI_APP_URL:
    MINI_APP_URL = "https://opper-taxi-bot-production.up.railway.app"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

WEB_DIR.mkdir(parents=True, exist_ok=True)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# REGIONS
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
        "Yangihayot"
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
        "Qibray"
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
        "Qo‘qon shahri"
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
        "Andijon shahri"
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
        "Namangan shahri"
    ],

    "Sirdaryo viloyati": [
        "Boyovut",
        "Guliston",
        "Mirzaobod",
        "Oqoltin",
        "Sayxunobod",
        "Sardoba",
        "Sirdaryo tumani",
        "Xovos"
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
        "Zarbdor"
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
        "Urgut"
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
        "Yakkabog‘"
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
        "Uzun"
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
        "Vobkent"
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
        "Xatirchi"
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
        "Yangibozor"
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
        "Xo‘jayli"
    ]
}


# =========================================================
# HELPERS
# =========================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def normalize_phone(phone):
    phone = clean(phone)

    digits = re.sub(r"\D", "", phone)

    if digits.startswith("998"):
        return "+" + digits

    if len(digits) == 9:
        return "+998" + digits

    return phone


def valid_location(region, district):
    region = clean(region)
    district = clean(district)

    return (
        region in REGIONS
        and district in REGIONS[region]
    )


# =========================================================
# TELEGRAM MINI APP AUTH
# =========================================================

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


async def get_user(request):

    try:

        if request.method == "POST":
            data = await request.json()
        else:
            data = dict(request.query)

    except Exception:
        data = {}

    init_data = (
        data.get("init_data")
        or request.headers.get(
            "X-Telegram-Init-Data"
        )
        or request.headers.get(
            "X-Telegram-InitData"
        )
    )

    return validate_init_data(init_data)


# =========================================================
# DATABASE
# =========================================================

async def init_db():

    async with aiosqlite.connect(DB_PATH) as db:

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
            seats INTEGER DEFAULT 4,
            region TEXT,
            district TEXT,
            verification_status TEXT DEFAULT 'approved',
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
            from_region TEXT,
            from_district TEXT,
            to_region TEXT,
            to_district TEXT,
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

        await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id INTEGER,
            passenger_telegram_id INTEGER,
            passenger_name TEXT,
            passenger_phone TEXT,
            seats INTEGER,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT
        )
        """)

        await db.commit()


async def get_driver(telegram_id):

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM drivers
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        row = await cursor.fetchone()

        return dict(row) if row else None


async def save_user(user):

    telegram_id = int(user["id"])

    username = clean(
        user.get("username")
    )

    full_name = clean(
        (
            user.get("first_name", "")
            + " "
            + user.get("last_name", "")
        )
    )

    async with aiosqlite.connect(DB_PATH) as db:

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
                username = excluded.username,
                full_name = excluded.full_name,
                updated_at = excluded.updated_at
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


# =========================================================
# API RESPONSE
# =========================================================

def ok(data=None, message="OK"):

    result = {
        "ok": True,
        "message": message
    }

    if data:
        result.update(data)

    return web.json_response(result)


def error(message, status=400):

    return web.json_response(
        {
            "ok": False,
            "error": message
        },
        status=status
    )


# =========================================================
# PROFILE
# =========================================================

async def api_profile(request):

    user = await get_user(request)

    if not user:
        return error(
            "Telegram foydalanuvchisi aniqlanmadi",
            401
        )

    await save_user(user)

    driver = await get_driver(
        int(user["id"])
    )

    return ok(
        {
            "user": {
                "id": user["id"],
                "username": user.get("username", ""),
                "full_name": (
                    user.get("first_name", "")
                    + " "
                    + user.get("last_name", "")
                ).strip()
            },
            "driver": driver
        }
    )


# =========================================================
# DRIVER REGISTER
# =========================================================

async def api_driver_register(request):

    user = await get_user(request)

    if not user:
        return error(
            "Telegram foydalanuvchisi aniqlanmadi",
            401
        )

    try:
        data = await request.json()
    except Exception:
        return error("Ma'lumot noto‘g‘ri")

    telegram_id = int(user["id"])

    full_name = clean(
        data.get("full_name")
    )

    phone = normalize_phone(
        data.get("phone")
    )

    car_model = clean(
        data.get("car_model")
    )

    car_number = clean(
        data.get("car_number")
    )

    region = clean(
        data.get("region")
    )

    district = clean(
        data.get("district")
    )

    try:
        seats = int(
            str(
                data.get("seats", "")
            ).strip()
        )
    except (TypeError, ValueError):
        seats = 0

    if not full_name:
        return error(
            "F.I.Sh. kiriting"
        )

    if not phone:
        return error(
            "Telefon raqam kiriting"
        )

    if not car_model:
        return error(
            "Avtomobil rusumini kiriting"
        )

    if not car_number:
        return error(
            "Avtomobil raqamini kiriting"
        )

    if not valid_location(
        region,
        district
    ):
        return error(
            "Viloyat yoki tuman noto‘g‘ri"
        )

    # MUHIM: FAQAT 1-4
    if seats < 1 or seats > 4:
        return error(
            "O‘rindiqlar soni 1–4 oralig‘ida bo‘lishi kerak"
        )

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT INTO drivers (
                telegram_id,
                full_name,
                phone,
                car_model,
                car_number,
                seats,
                region,
                district,
                verification_status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?, ?)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                full_name = excluded.full_name,
                phone = excluded.phone,
                car_model = excluded.car_model,
                car_number = excluded.car_number,
                seats = excluded.seats,
                region = excluded.region,
                district = excluded.district,
                updated_at = excluded.updated_at
            """,
            (
                telegram_id,
                full_name,
                phone,
                car_model,
                car_number,
                seats,
                region,
                district,
                now(),
                now()
            )
        )

        await db.commit()

    return ok(
        message="Haydovchi profili saqlandi"
    )


# =========================================================
# DRIVER STATUS
# =========================================================

async def api_driver_status(request):

    user = await get_user(request)

    if not user:
        return error(
            "Telegram foydalanuvchisi aniqlanmadi",
            401
        )

    driver = await get_driver(
        int(user["id"])
    )

    if not driver:
        return ok(
            {
                "registered": False,
                "driver": None
            }
        )

    return ok(
        {
            "registered": True,
            "driver": driver
        }
    )


# =========================================================
# ADD RIDE
# =========================================================

async def api_driver_ride(request):

    user = await get_user(request)

    if not user:
        return error(
            "Telegram foydalanuvchisi aniqlanmadi",
            401
        )

    driver = await get_driver(
        int(user["id"])
    )

    if not driver:
        return error(
            "Avval haydovchi profilini yarating"
        )

    try:
        data = await request.json()
    except Exception:
        return error("Ma'lumot noto‘g‘ri")

    from_region = clean(
        data.get("from_region")
    )

    from_district = clean(
        data.get("from_district")
    )

    to_region = clean(
        data.get("to_region")
    )

    to_district = clean(
        data.get("to_district")
    )

    ride_date = clean(
        data.get("ride_date")
    )

    ride_time = clean(
        data.get("ride_time")
    )

    try:
        seats = int(
            str(
                data.get("seats", "")
            ).strip()
        )
    except (TypeError, ValueError):
        seats = 0

    try:
        price = int(
            str(
                data.get("price", "")
            ).strip()
        )
    except (TypeError, ValueError):
        price = 0

    if not valid_location(
        from_region,
        from_district
    ):
        return error(
            "Qayerdan manzili noto‘g‘ri"
        )

    if not valid_location(
        to_region,
        to_district
    ):
        return error(
            "Qayerga manzili noto‘g‘ri"
        )

    if (
        from_region == to_region
        and from_district == to_district
    ):
        return error(
            "Qayerdan va Qayerga bir xil bo‘lmasin"
        )

    if not ride_date:
        return error(
            "Safar sanasini kiriting"
        )

    if not ride_time:
        return error(
            "Safar vaqtini kiriting"
        )

    # GLOBAL LIMIT
    if seats < 1 or seats > 4:
        return error(
            "O‘rindiqlar soni 1–4 oralig‘ida bo‘lishi kerak"
        )

    driver_seats = int(
        driver["seats"] or 0
    )

    if driver_seats < 1 or driver_seats > 4:
        return error(
            "Haydovchi profilidagi o‘rindiqlar soni noto‘g‘ri. Profilni yangilang."
        )

    if seats > driver_seats:
        return error(
            f"Sizning avtomobilingizda {driver_seats} ta o‘rindiq ko‘rsatilgan. "
            f"Safarga {driver_seats} tagacha joy qo‘yishingiz mumkin."
        )

    if price < 0:
        return error(
            "Narx noto‘g‘ri"
        )

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT INTO rides (
                driver_id,
                driver_telegram_id,
                driver_name,
                driver_phone,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                driver["id"],
                driver["telegram_id"],
                driver["full_name"],
                driver["phone"],
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
                now(),
                now()
            )
        )

        await db.commit()

    return ok(
        message="Safar muvaffaqiyatli qo‘shildi"
    )


# =========================================================
# SEARCH RIDES
# =========================================================

async def api_rides(request):

    user = await get_user(request)

    try:
        data = await request.json()
    except Exception:
        data = {}

    from_region = clean(
        data.get("from_region")
    )

    from_district = clean(
        data.get("from_district")
    )

    to_region = clean(
        data.get("to_region")
    )

    to_district = clean(
        data.get("to_district")
    )

    query = """
        SELECT *
        FROM rides
        WHERE status = 'active'
    """

    params = []

    if from_region:
        query += " AND from_region = ?"
        params.append(from_region)

    if from_district:
        query += " AND from_district = ?"
        params.append(from_district)

    if to_region:
        query += " AND to_region = ?"
        params.append(to_region)

    if to_district:
        query += " AND to_district = ?"
        params.append(to_district)

    query += """
        ORDER BY ride_date ASC, ride_time ASC
        LIMIT 100
    """

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            query,
            params
        )

        rows = await cursor.fetchall()

    rides = []

    for row in rows:

        ride = dict(row)

        async with aiosqlite.connect(DB_PATH) as db:

            cursor = await db.execute(
                """
                SELECT COALESCE(
                    SUM(seats), 0
                )
                FROM orders
                WHERE ride_id = ?
                AND status = 'active'
                """,
                (ride["id"],)
            )

            booked = (
                await cursor.fetchone()
            )[0]

        ride["booked_seats"] = booked

        ride["available_seats"] = max(
            0,
            int(ride["seats"]) - int(booked)
        )

        rides.append(ride)

    return ok(
        {
            "rides": rides
        }
    )


# =========================================================
# PASSENGER ORDER
# =========================================================

async def api_passenger_order(request):

    user = await get_user(request)

    if not user:
        return error(
            "Telegram foydalanuvchisi aniqlanmadi",
            401
        )

    try:
        data = await request.json()
    except Exception:
        return error("Ma'lumot noto‘g‘ri")

    try:
        ride_id = int(
            data.get("ride_id")
        )
    except Exception:
        return error(
            "Safar tanlanmagan"
        )

    try:
        seats = int(
            str(
                data.get("seats", "")
            ).strip()
        )
    except (TypeError, ValueError):
        seats = 0

    if seats < 1 or seats > 4:
        return error(
            "Yo‘lovchilar soni 1–4 oralig‘ida bo‘lishi kerak"
        )

    phone = normalize_phone(
        data.get("phone")
    )

    if not phone:
        return error(
            "Telefon raqamingizni kiriting"
        )

    telegram_id = int(
        user["id"]
    )

    passenger_name = (
        user.get("first_name", "")
        + " "
        + user.get("last_name", "")
    ).strip()

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM rides
            WHERE id = ?
            AND status = 'active'
            """,
            (ride_id,)
        )

        ride = await cursor.fetchone()

        if not ride:
            return error(
                "Bu safar mavjud emas"
            )

        if int(ride["driver_telegram_id"]) == telegram_id:
            return error(
                "O‘zingiz joylagan safarga buyurtma bera olmaysiz"
            )

        cursor = await db.execute(
            """
            SELECT COALESCE(
                SUM(seats), 0
            )
            FROM orders
            WHERE ride_id = ?
            AND status = 'active'
            """,
            (ride_id,)
        )

        booked = (
            await cursor.fetchone()
        )[0]

        available = (
            int(ride["seats"])
            - int(booked)
        )

        if seats > available:
            return error(
                f"Faqat {available} ta bo‘sh joy bor"
            )

        cursor = await db.execute(
            """
            SELECT id
            FROM orders
            WHERE ride_id = ?
            AND passenger_telegram_id = ?
            AND status = 'active'
            """,
            (
                ride_id,
                telegram_id
            )
        )

        existing = await cursor.fetchone()

        if existing:
            return error(
                "Siz bu safarga allaqachon buyurtma bergansiz"
            )

        await db.execute(
            """
            INSERT INTO orders (
                ride_id,
                passenger_telegram_id,
                passenger_name,
                passenger_phone,
                seats,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                ride_id,
                telegram_id,
                passenger_name,
                phone,
                seats,
                now(),
                now()
            )
        )

        await db.commit()

        driver_telegram_id = int(
            ride["driver_telegram_id"]
        )

    # Haydovchiga xabar
    try:

        await bot.send_message(
            driver_telegram_id,
            (
                "🚕 Yangi yo‘lovchi!\n\n"
                f"👤 {passenger_name}\n"
                f"📞 {phone}\n"
                f"💺 Joy: {seats}\n\n"
                f"📍 {ride['from_region']}, "
                f"{ride['from_district']}\n"
                f"➡️ {ride['to_region']}, "
                f"{ride['to_district']}\n"
                f"📅 {ride['ride_date']}\n"
                f"🕐 {ride['ride_time']}"
            )
        )

    except Exception as e:

        logging.error(
            "DRIVER NOTIFY ERROR: %s",
            e
        )

    return ok(
        message="Buyurtma yuborildi"
    )


# =========================================================
# ORDERS
# =========================================================

async def api_orders(request):

    user = await get_user(request)

    if not user:
        return error(
            "Telegram foydalanuvchisi aniqlanmadi",
            401
        )

    telegram_id = int(
        user["id"]
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM rides
            WHERE driver_telegram_id = ?
            ORDER BY id DESC
            LIMIT 100
            """,
            (telegram_id,)
        )

        driver_rides = [
            dict(x)
            for x in await cursor.fetchall()
        ]

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
            WHERE o.passenger_telegram_id = ?
            ORDER BY o.id DESC
            LIMIT 100
            """,
            (telegram_id,)
        )

        passenger_orders = [
            dict(x)
            for x in await cursor.fetchall()
        ]

    return ok(
        {
            "driver_rides": driver_rides,
            "passenger_orders": passenger_orders
        }
    )


# =========================================================
# CANCEL
# =========================================================

async def api_cancel(request):

    user = await get_user(request)

    if not user:
        return error(
            "Telegram foydalanuvchisi aniqlanmadi",
            401
        )

    try:
        data = await request.json()
    except Exception:
        return error("Ma'lumot noto‘g‘ri")

    telegram_id = int(
        user["id"]
    )

    order_id = data.get("order_id")
    ride_id = data.get("ride_id")

    async with aiosqlite.connect(DB_PATH) as db:

        if order_id:

            await db.execute(
                """
                UPDATE orders
                SET status = 'cancelled',
                    updated_at = ?
                WHERE id = ?
                AND passenger_telegram_id = ?
                """,
                (
                    now(),
                    int(order_id),
                    telegram_id
                )
            )

        elif ride_id:

            await db.execute(
                """
                UPDATE rides
                SET status = 'cancelled',
                    updated_at = ?
                WHERE id = ?
                AND driver_telegram_id = ?
                """,
                (
                    now(),
                    int(ride_id),
                    telegram_id
                )
            )

        else:
            return error(
                "Bekor qilinadigan buyurtma topilmadi"
            )

        await db.commit()

    return ok(
        message="Muvaffaqiyatli bekor qilindi"
    )


# =========================================================
# HEALTH
# =========================================================

async def health(request):

    return web.json_response(
        {
            "ok": True,
            "service": "OPPER TAXI",
            "status": "running"
        }
    )


# =========================================================
# INDEX
# =========================================================

async def index(request):

    if not INDEX_FILE.exists():

        return web.Response(
            text="OPPER TAXI Mini App index.html topilmadi",
            status=500
        )

    response = web.FileResponse(
        INDEX_FILE
    )

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate"
    )

    return response


# =========================================================
# BOT
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
                    text="🚕 Haydovchi bo‘lish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    )
                ),
                KeyboardButton(
                    text="👤 Yo‘lovchi bo‘lish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
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


@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "🚕 OPPER TAXI\n\n"
        "O‘zbekiston bo‘ylab shaharlararo "
        "safar toping yoki haydovchi sifatida "
        "o‘z safaringizni joylang.\n\n"
        "Ilovani ochish uchun pastdagi "
        "🚕 OPPER TAXI tugmasini bosing.",
        reply_markup=main_keyboard()
    )


@dp.message(F.text == "📞 Yordam")
async def help_message(message: Message):

    await message.answer(
        "📞 OPPER TAXI YORDAM\n\n"
        "🚕 Haydovchi bo‘lish — safaringizni joylang.\n"
        "👤 Yo‘lovchi bo‘lish — safar qidiring.\n\n"
        "Muammo bo‘lsa administratorga murojaat qiling."
    )


# =========================================================
# WEB SERVER
# =========================================================

def create_app():

    app = web.Application()

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

    app.router.add_post(
        "/api/profile",
        api_profile
    )

    app.router.add_post(
        "/api/driver/register",
        api_driver_register
    )

    app.router.add_post(
        "/api/driver/status",
        api_driver_status
    )

    app.router.add_post(
        "/api/driver/ride",
        api_driver_ride
    )

    app.router.add_post(
        "/api/rides",
        api_rides
    )

    app.router.add_post(
        "/api/passenger/order",
        api_passenger_order
    )

    app.router.add_post(
        "/api/orders",
        api_orders
    )

    app.router.add_post(
        "/api/order/cancel",
        api_cancel
    )

    return app


# =========================================================
# START
# =========================================================

async def start_web_server():

    app = create_app()

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    logging.info(
        "WEB SERVER STARTED: %s",
        PORT
    )

    return runner


async def setup_bot():

    await bot.set_my_commands(
        [
            BotCommand(
                command="start",
                description="OPPER TAXI"
            )
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

        logging.error(
            "MENU BUTTON ERROR: %s",
            e
        )


async def main():

    await init_db()

    await setup_bot()

    await start_web_server()

    logging.info(
        "OPPER TAXI BOT IS STARTING"
    )

    logging.info(
        "MINI APP URL: %s",
        MINI_APP_URL
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    try:
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        pass
