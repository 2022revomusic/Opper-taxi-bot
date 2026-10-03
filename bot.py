import os
import re
import json
import hmac
import hashlib
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import parse_qsl

import aiohttp
from aiohttp import web
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    MenuButtonWebApp,
    WebAppInfo,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID = int(os.getenv("ADMIN_ID", "653914246"))

PORT = int(os.getenv("PORT", "8080"))

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "oper_taxi.db"

UPLOAD_DIR = BASE_DIR / "uploads" / "drivers"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MINI_APP_URL = (
    os.getenv("MINI_APP_URL", "").strip()
    or "https://opper-taxi-bot-production.up.railway.app"
)

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
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("opper_taxi")


# =========================================================
# BOT
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable topilmadi."
    )


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ),
)

dp = Dispatcher()


# =========================================================
# REGIONS
# =========================================================

REGIONS = {
    "Toshkent shahri": [
        "Chilonzor",
        "Yunusobod",
        "Mirzo Ulug‘bek",
        "Sergeli",
        "Yakkasaroy",
        "Mirobod",
        "Shayxontohur",
        "Olmazor",
        "Uchtepa",
        "Bektemir",
        "Yashnobod",
        "Yangihayot",
    ],
    "Toshkent viloyati": [
        "Angren",
        "Bekobod",
        "Bo‘ka",
        "Chirchiq",
        "Ohangaron",
        "Olmaliq",
        "Parkent",
        "Piskent",
        "Qibray",
        "Yangiyo‘l",
        "Zangiota",
    ],
    "Farg‘ona viloyati": [
        "Farg‘ona",
        "Qo‘qon",
        "Marg‘ilon",
        "Quva",
        "Rishton",
        "Oltiariq",
        "Beshariq",
        "Dang‘ara",
        "Toshloq",
        "Uchko‘prik",
    ],
    "Andijon viloyati": [
        "Andijon",
        "Asaka",
        "Marhamat",
        "Shahrixon",
        "Xo‘jaobod",
        "Paxtaobod",
        "Baliqchi",
        "Bo‘z",
    ],
    "Namangan viloyati": [
        "Namangan",
        "Chortoq",
        "Chust",
        "Kosonsoy",
        "Pop",
        "To‘raqo‘rg‘on",
        "Uychi",
        "Uchqo‘rg‘on",
    ],
    "Samarqand viloyati": [
        "Samarqand",
        "Kattaqo‘rg‘on",
        "Urgut",
        "Bulung‘ur",
        "Jomboy",
        "Ishtixon",
        "Narpay",
        "Pastdarg‘om",
    ],
    "Buxoro viloyati": [
        "Buxoro",
        "G‘ijduvon",
        "Kogon",
        "Vobkent",
        "Romitan",
        "Shofirkon",
    ],
    "Qashqadaryo viloyati": [
        "Qarshi",
        "Shahrisabz",
        "Kitob",
        "Koson",
        "Kasbi",
        "Chiroqchi",
        "Yakkabog‘",
    ],
    "Surxondaryo viloyati": [
        "Termiz",
        "Denov",
        "Sherobod",
        "Boysun",
        "Jarqo‘rg‘on",
        "Qumqo‘rg‘on",
    ],
    "Jizzax viloyati": [
        "Jizzax",
        "G‘allaorol",
        "Do‘stlik",
        "Zomin",
        "Paxtakor",
        "Forish",
    ],
    "Sirdaryo viloyati": [
        "Guliston",
        "Yangiyer",
        "Shirin",
        "Boyovut",
        "Sayxunobod",
    ],
    "Navoiy viloyati": [
        "Navoiy",
        "Zarafshon",
        "Karmana",
        "Konimex",
        "Qiziltepa",
        "Xatirchi",
    ],
    "Xorazm viloyati": [
        "Urganch",
        "Xiva",
        "Hazorasp",
        "Shovot",
        "Bog‘ot",
        "Gurlan",
    ],
    "Qoraqalpog‘iston Respublikasi": [
        "Nukus",
        "Beruniy",
        "Chimboy",
        "Qo‘ng‘irot",
        "Mo‘ynoq",
        "Xo‘jayli",
    ],
}


# =========================================================
# HELPERS
# =========================================================

def now_str():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def clean_text(value, max_len=500):
    if value is None:
        return ""

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)

    return value[:max_len]


def safe_int(value, default=None):
    try:
        return int(value)
    except Exception:
        return default


def valid_seats(value):
    value = safe_int(value)

    if value is None:
        return False

    return MIN_SEATS <= value <= MAX_SEATS


def normalize_phone(phone):
    if not phone:
        return ""

    phone = re.sub(
        r"[^\d+]",
        "",
        str(phone),
    )

    if phone.startswith("998"):
        phone = "+" + phone

    if phone.startswith("8") and len(phone) == 10:
        phone = "+998" + phone[1:]

    return phone


def json_ok(data=None):
    return web.json_response({
        "ok": True,
        "data": data or {}
    })


def json_error(message, status=400):
    return web.json_response(
        {
            "ok": False,
            "error": message
        },
        status=status,
    )


async def request_json(request):
    try:
        return await request.json()
    except Exception:
        return {}


# =========================================================
# TELEGRAM WEB APP VALIDATION
# =========================================================

def validate_telegram_webapp(init_data: str) -> bool:

    if not init_data:
        logger.warning(
            "Telegram initData bo‘sh."
        )
        return False

    try:

        parsed_items = parse_qsl(
            init_data,
            keep_blank_values=True,
        )

        parsed = dict(parsed_items)

        received_hash = parsed.pop(
            "hash",
            None,
        )

        if not received_hash:
            logger.warning(
                "Telegram initData ichida hash topilmadi."
            )
            return False

        data_check_string = "\n".join(
            f"{key}={parsed[key]}"
            for key in sorted(parsed.keys())
        )

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=BOT_TOKEN.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            calculated_hash,
            received_hash,
        )

    except Exception:
        logger.exception(
            "Telegram WebApp validation error"
        )
        return False


def get_web_user(request):

    init_data = request.headers.get(
        "X-Telegram-Init-Data",
        "",
    ).strip()

    if not init_data:
        return None

    if not validate_telegram_webapp(
        init_data
    ):
        return None

    try:

        parsed = dict(
            parse_qsl(
                init_data,
                keep_blank_values=True,
            )
        )

        user_raw = parsed.get("user")

        if not user_raw:
            return None

        user = json.loads(user_raw)

        if not isinstance(user, dict):
            return None

        if not user.get("id"):
            return None

        return user

    except Exception:
        logger.exception(
            "Web user parse error"
        )
        return None


async def require_web_user(request):

    return get_web_user(request)


async def require_admin_web_user(request):

    user = await require_web_user(request)

    if not user:
        return None, json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    if int(user["id"]) != ADMIN_ID:
        return None, json_error(
            "Admin huquqi kerak.",
            403,
        )

    return user, None


# =========================================================
# DATABASE
# =========================================================

async def db_execute(
    query,
    params=(),
    fetchone=False,
    fetchall=False,
):

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            query,
            params,
        )

        if fetchone:

            row = await cursor.fetchone()

            await cursor.close()

            return (
                dict(row)
                if row
                else None
            )

        if fetchall:

            rows = await cursor.fetchall()

            await cursor.close()

            return [
                dict(row)
                for row in rows
            ]

        await db.commit()

        last_id = cursor.lastrowid

        await cursor.close()

        return last_id


async def db_fetchone(
    query,
    params=(),
):
    return await db_execute(
        query,
        params,
        fetchone=True,
    )


async def db_fetchall(
    query,
    params=(),
):
    return await db_execute(
        query,
        params,
        fetchall=True,
    )


# =========================================================
# INIT DATABASE
# =========================================================

async def init_db():

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                region TEXT DEFAULT '',
                district TEXT DEFAULT '',
                passport_file TEXT DEFAULT '',
                driver_license_file TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_telegram_id INTEGER NOT NULL,
                brand TEXT DEFAULT '',
                model TEXT DEFAULT '',
                color TEXT DEFAULT '',
                plate TEXT DEFAULT '',
                seats INTEGER DEFAULT 4,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_telegram_id INTEGER NOT NULL,
                from_region TEXT NOT NULL,
                from_district TEXT DEFAULT '',
                to_region TEXT NOT NULL,
                to_district TEXT DEFAULT '',
                travel_date TEXT NOT NULL,
                travel_time TEXT NOT NULL,
                price INTEGER NOT NULL,
                seats INTEGER NOT NULL,
                available_seats INTEGER NOT NULL,
                car_id INTEGER,
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER NOT NULL,
                passenger_telegram_id INTEGER NOT NULL,
                driver_telegram_id INTEGER NOT NULL,
                seats INTEGER NOT NULL,
                phone TEXT DEFAULT '',
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER,
                from_telegram_id INTEGER NOT NULL,
                to_telegram_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(
                    ride_id,
                    from_telegram_id,
                    to_telegram_id
                )
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                title TEXT DEFAULT '',
                message TEXT DEFAULT '',
                type TEXT DEFAULT 'info',
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS passenger_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                passenger_telegram_id INTEGER NOT NULL,
                from_region TEXT NOT NULL,
                from_district TEXT DEFAULT '',
                to_region TEXT NOT NULL,
                to_district TEXT DEFAULT '',
                travel_date TEXT NOT NULL,
                travel_time TEXT DEFAULT '',
                seats INTEGER NOT NULL,
                price INTEGER DEFAULT 0,
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_telegram_id INTEGER NOT NULL,
                target_telegram_id INTEGER,
                ride_id INTEGER,
                order_id INTEGER,
                reason TEXT DEFAULT '',
                status TEXT DEFAULT 'new',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_telegram_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_telegram_id INTEGER,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_users_telegram
            ON users(telegram_id);

            CREATE INDEX IF NOT EXISTS idx_drivers_telegram
            ON drivers(telegram_id);

            CREATE INDEX IF NOT EXISTS idx_rides_driver
            ON rides(driver_telegram_id);

            CREATE INDEX IF NOT EXISTS idx_rides_status
            ON rides(status);

            CREATE INDEX IF NOT EXISTS idx_orders_driver
            ON orders(driver_telegram_id);

            CREATE INDEX IF NOT EXISTS idx_orders_passenger
            ON orders(passenger_telegram_id);

            CREATE INDEX IF NOT EXISTS idx_notifications_user
            ON notifications(telegram_id);
            """
        )

        await db.commit()

    logger.info("Database initialized")


# =========================================================
# USER
# =========================================================

async def ensure_user(
    telegram_id,
    username="",
    first_name="",
    last_name="",
    phone=None,
):

    existing = await db_fetchone(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    now = now_str()

    if existing:

        if phone is None:
            phone = existing["phone"] or ""

        await db_execute(
            """
            UPDATE users
            SET username = ?,
                first_name = ?,
                last_name = ?,
                phone = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                username,
                first_name,
                last_name,
                phone,
                now,
                telegram_id,
            ),
        )

    else:

        await db_execute(
            """
            INSERT INTO users (
                telegram_id,
                username,
                first_name,
                last_name,
                phone,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                username,
                first_name,
                last_name,
                phone or "",
                now,
                now,
            ),
        )


# =========================================================
# NOTIFICATIONS
# =========================================================

async def create_notification(
    telegram_id,
    title,
    message,
    notification_type="info",
):

    await db_execute(
        """
        INSERT INTO notifications (
            telegram_id,
            title,
            message,
            type,
            is_read,
            created_at
        )
        VALUES (?, ?, ?, ?, 0, ?)
        """,
        (
            telegram_id,
            title,
            message,
            notification_type,
            now_str(),
        ),
    )


async def send_notification(
    telegram_id,
    text,
    reply_markup=None,
):

    try:

        await bot.send_message(
            telegram_id,
            text,
            reply_markup=reply_markup,
        )

        return True

    except Exception as e:

        logger.warning(
            "Telegram notification failed %s: %s",
            telegram_id,
            e,
        )

        return False


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🚕 Haydovchi bo‘lish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL + "?mode=driver"
                    ),
                ),
                KeyboardButton(
                    text="👤 Yo‘lovchi bo‘lish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    ),
                ),
            ],
            [
                KeyboardButton(
                    text="🔎 Safar qidirish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL + "?mode=search"
                    ),
                ),
                KeyboardButton(
                    text="📋 Mening safarlarim",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL + "?mode=orders"
                    ),
                ),
            ],
            [
                KeyboardButton(
                    text="👤 Profilim",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL + "?mode=profile"
                    ),
                ),
                KeyboardButton(
                    text="📞 Yordam"
                ),
            ],
        ],
        resize_keyboard=True,
    )


# =========================================================
# START
# =========================================================

@dp.message(Command("start"))
async def start_handler(message: Message):

    user = message.from_user

    if user:

        await ensure_user(
            telegram_id=user.id,
            username=user.username or "",
            first_name=user.first_name or "",
            last_name=user.last_name or "",
        )

    await message.answer(
        "🚕 <b>OPPER TAXI</b>\n\n"
        "O‘zbekiston bo‘ylab shaharlararo safar toping "
        "yoki o‘zingizga yo‘lovchi toping.\n\n"
        "📱 Mini App orqali barcha xizmatlardan foydalaning.",
        reply_markup=main_keyboard(),
    )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_handler(message: Message):

    await message.answer(
        "📞 <b>OPPER TAXI yordam</b>\n\n"
        "🚕 Haydovchi — safar joylash\n"
        "👤 Yo‘lovchi — safar qidirish\n"
        "📋 Buyurtmalar — buyurtmalarni ko‘rish\n"
        "👤 Profil — ma’lumotlarni boshqarish\n\n"
        "Muammo bo‘lsa administratorga murojaat qiling.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "📞 Yordam")
async def help_button_handler(message: Message):

    await message.answer(
        "📞 <b>OPPER TAXI yordam</b>\n\n"
        "Bot orqali safar topishingiz yoki "
        "safar joylashingiz mumkin.\n\n"
        "Administrator: @Oppertaxibot",
        reply_markup=main_keyboard(),
    )


# =========================================================
# PROFILE API
# =========================================================

async def api_profile(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    telegram_id = int(user["id"])

    await ensure_user(
        telegram_id=telegram_id,
        username=user.get("username", ""),
        first_name=user.get("first_name", ""),
        last_name=user.get("last_name", ""),
        phone=None,
    )

    profile = await db_fetchone(
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

    return json_ok({
        "user": profile,
        "driver": driver,
    })


# =========================================================
# PROFILE UPDATE
# =========================================================

async def api_profile_update(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    data = await request_json(request)

    telegram_id = int(user["id"])

    current = await db_fetchone(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    raw_phone = data.get("phone")

    if raw_phone is None:
        phone = (
            current["phone"]
            if current
            else ""
        )
    else:
        phone = normalize_phone(raw_phone)

    first_name = clean_text(
        data.get("first_name", ""),
        100,
    )

    last_name = clean_text(
        data.get("last_name", ""),
        100,
    )

    await ensure_user(
        telegram_id=telegram_id,
        username=user.get("username", ""),
        first_name=(
            first_name
            or user.get("first_name", "")
        ),
        last_name=(
            last_name
            or user.get("last_name", "")
        ),
        phone=phone,
    )

    return json_ok({
        "message": "Profil yangilandi."
    })


# =========================================================
# DRIVER STATUS
# =========================================================

async def api_driver_status(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    telegram_id = int(user["id"])

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    if not driver:
        return json_ok({
            "registered": False
        })

    return json_ok({
        "registered": True,
        "driver": driver,
    })


# =========================================================
# DRIVER REGISTER
# =========================================================

async def api_driver_register(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    data = await request_json(request)

    telegram_id = int(user["id"])

    full_name = clean_text(
        data.get("full_name")
        or (
            f"{user.get('first_name', '')} "
            f"{user.get('last_name', '')}"
        ),
        150,
    )

    phone = normalize_phone(
        data.get("phone", "")
    )

    region = clean_text(
        data.get("region", ""),
        150,
    )

    district = clean_text(
        data.get("district", ""),
        150,
    )

    if not full_name:
        return json_error(
            "F.I.Sh. kiriting."
        )

    if not phone:
        return json_error(
            "Telefon raqamingizni kiriting."
        )

    if not region:
        return json_error(
            "Viloyatni tanlang."
        )

    existing = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    now = now_str()

    # -----------------------------------------------------
    # PENDING yoki APPROVED bo‘lsa qayta ariza yo‘q
    # -----------------------------------------------------

    if existing:

        if existing["status"] in (
            DRIVER_PENDING,
            DRIVER_APPROVED,
        ):

            return json_ok({
                "success": False,
                "already_exists": True,
                "status": existing["status"],
                "driver": existing,
                "message": (
                    "Sizning haydovchilik arizangiz "
                    "allaqachon mavjud."
                ),
            })

        # -------------------------------------------------
        # REJECTED bo‘lsa qayta ariza
        # -------------------------------------------------

        await db_execute(
            """
            UPDATE drivers
            SET full_name = ?,
                phone = ?,
                region = ?,
                district = ?,
                status = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                full_name,
                phone,
                region,
                district,
                DRIVER_PENDING,
                now,
                telegram_id,
            ),
        )

    else:

        await db_execute(
            """
            INSERT INTO drivers (
                telegram_id,
                full_name,
                phone,
                region,
                district,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                full_name,
                phone,
                region,
                district,
                DRIVER_PENDING,
                now,
                now,
            ),
        )

    await ensure_user(
        telegram_id=telegram_id,
        username=user.get("username", ""),
        first_name=user.get("first_name", ""),
        last_name=user.get("last_name", ""),
        phone=phone,
    )

    try:

        await bot.send_message(
            ADMIN_ID,
            "🚕 <b>YANGI HAYDOVCHI ARIZASI</b>\n\n"
            f"👤 {full_name}\n"
            f"📱 {phone}\n"
            f"📍 {region}\n"
            f"🏘 {district or '-'}\n"
            f"🆔 <code>{telegram_id}</code>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Tasdiqlash",
                            callback_data=(
                                f"driver_approve:{telegram_id}"
                            ),
                        ),
                        InlineKeyboardButton(
                            text="❌ Rad etish",
                            callback_data=(
                                f"driver_reject:{telegram_id}"
                            ),
                        ),
                    ]
                ]
            ),
        )

    except Exception:
        logger.exception(
            "Admin notification error"
        )

    return json_ok({
        "success": True,
        "message": (
            "Haydovchilik arizasi yuborildi."
        )
    })


# =========================================================
# DRIVER RIDE
# =========================================================

async def api_driver_ride(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    telegram_id = int(user["id"])

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    if not driver:
        return json_error(
            "Avval haydovchi sifatida ro‘yxatdan o‘ting."
        )

    if driver["status"] != DRIVER_APPROVED:
        return json_error(
            "Haydovchilik profilingiz hali tasdiqlanmagan."
        )

    data = await request_json(request)

    from_region = clean_text(
        data.get("from_region", ""),
        150,
    )

    from_district = clean_text(
        data.get("from_district", ""),
        150,
    )

    to_region = clean_text(
        data.get("to_region", ""),
        150,
    )

    to_district = clean_text(
        data.get("to_district", ""),
        150,
    )

    travel_date = clean_text(
        data.get("travel_date")
        or data.get("date")
        or data.get("ride_date")
        or "",
        30,
    )

    travel_time = clean_text(
        data.get("travel_time")
        or data.get("time")
        or data.get("ride_time")
        or "",
        20,
    )

    price = safe_int(
        data.get("price")
    )

    seats = safe_int(
        data.get("seats")
    )

    note = clean_text(
        data.get("note", ""),
        500,
    )

    if not from_region or not to_region:
        return json_error(
            "Yo‘nalishni to‘liq tanlang."
        )

    if (
        from_region == to_region
        and (
            not from_district
            or not to_district
            or from_district == to_district
        )
    ):
        return json_error(
            "Jo‘nash va borish joylari "
            "bir xil bo‘lmasin."
        )

    if not travel_date:
        return json_error(
            "Safar sanasini kiriting."
        )

    if not travel_time:
        return json_error(
            "Safar vaqtini kiriting."
        )

    if price is None or price < 0:
        return json_error(
            "Narxni to‘g‘ri kiriting."
        )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni 1–4 "
            "oralig‘ida bo‘lishi kerak."
        )

    car_brand = clean_text(
        data.get("car_brand", ""),
        50,
    )

    car_model = clean_text(
        data.get("car_model", ""),
        50,
    )

    car_color = clean_text(
        data.get("car_color", ""),
        50,
    )

    car_plate = clean_text(
        data.get("car_plate", ""),
        30,
    )

    car_id = None

    if (
        car_brand
        or car_model
        or car_color
        or car_plate
    ):

        car_id = await db_execute(
            """
            INSERT INTO cars (
                driver_telegram_id,
                brand,
                model,
                color,
                plate,
                seats,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                car_brand,
                car_model,
                car_color,
                car_plate,
                seats,
                now_str(),
            ),
        )

    ride_id = await db_execute(
        """
        INSERT INTO rides (
            driver_telegram_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            price,
            seats,
            available_seats,
            car_id,
            note,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            price,
            seats,
            seats,
            car_id,
            note,
            RIDE_ACTIVE,
            now_str(),
            now_str(),
        ),
    )

    return json_ok({
        "ride_id": ride_id,
        "message": "Safar muvaffaqiyatli joylandi."
    })


# =========================================================
# RIDES SEARCH
# =========================================================

async def api_rides(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    params = request.rel_url.query

    from_region = clean_text(
        params.get("from_region", ""),
        150,
    )

    from_district = clean_text(
        params.get("from_district", ""),
        150,
    )

    to_region = clean_text(
        params.get("to_region", ""),
        150,
    )

    to_district = clean_text(
        params.get("to_district", ""),
        150,
    )

    travel_date = clean_text(
        params.get("travel_date", ""),
        30,
    )

    query = """
        SELECT
            r.*,
            u.first_name,
            u.last_name,
            u.username,
            d.full_name AS driver_name,
            d.phone AS driver_phone,
            d.status AS driver_status,
            c.brand,
            c.model,
            c.color,
            c.plate
        FROM rides r
        LEFT JOIN users u
            ON u.telegram_id = r.driver_telegram_id
        LEFT JOIN drivers d
            ON d.telegram_id = r.driver_telegram_id
        LEFT JOIN cars c
            ON c.id = r.car_id
        WHERE r.status = ?
        AND r.available_seats > 0
        AND d.status = ?
    """

    values = [
        RIDE_ACTIVE,
        DRIVER_APPROVED,
    ]

    if from_region:

        query += " AND r.from_region = ?"
        values.append(from_region)

    if from_district:

        query += " AND r.from_district = ?"
        values.append(from_district)

    if to_region:

        query += " AND r.to_region = ?"
        values.append(to_region)

    if to_district:

        query += " AND r.to_district = ?"
        values.append(to_district)

    if travel_date:

        query += " AND r.travel_date = ?"
        values.append(travel_date)

    query += """
        ORDER BY
            r.travel_date ASC,
            r.travel_time ASC,
            r.id DESC
        LIMIT 100
    """

    rides = await db_fetchall(
        query,
        values,
    )

    return json_ok({
        "rides": rides
    })


# =========================================================
# PASSENGER ORDER
# =========================================================

async def api_passenger_order(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    data = await request_json(request)

    passenger_id = int(user["id"])

    ride_id = safe_int(
        data.get("ride_id")
    )

    seats = safe_int(
        data.get("seats")
    )

    phone = normalize_phone(
        data.get("phone", "")
    )

    note = clean_text(
        data.get("note", ""),
        500,
    )

    if not ride_id:
        return json_error(
            "Safar tanlanmagan."
        )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni 1–4 "
            "oralig‘ida bo‘lishi kerak."
        )

    if not phone:
        return json_error(
            "Telefon raqamingizni kiriting."
        )

    ride = await db_fetchone(
        """
        SELECT
            r.*,
            d.full_name AS driver_name,
            d.phone AS driver_phone,
            d.status AS driver_status,
            u.first_name AS driver_first_name
        FROM rides r
        LEFT JOIN drivers d
            ON d.telegram_id = r.driver_telegram_id
        LEFT JOIN users u
            ON u.telegram_id = r.driver_telegram_id
        WHERE r.id = ?
        """,
        (ride_id,),
    )

    if not ride:
        return json_error(
            "Safar topilmadi."
        )

    if ride["driver_telegram_id"] == passenger_id:
        return json_error(
            "O‘zingizning safaringizga "
            "buyurtma bera olmaysiz."
        )

    if ride["driver_status"] != DRIVER_APPROVED:
        return json_error(
            "Bu haydovchi hali tasdiqlanmagan."
        )

    if ride["status"] != RIDE_ACTIVE:
        return json_error(
            "Bu safar hozir faol emas."
        )

    if ride["available_seats"] < seats:
        return json_error(
            "Yetarli joy yo‘q. "
            f"Qolgan joy: {ride['available_seats']}."
        )

    existing = await db_fetchone(
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
            ORDER_ACCEPTED,
        ),
    )

    if existing:
        return json_error(
            "Bu safarga allaqachon "
            "buyurtma bergansiz."
        )

    await ensure_user(
        telegram_id=passenger_id,
        username=user.get("username", ""),
        first_name=user.get("first_name", ""),
        last_name=user.get("last_name", ""),
        phone=phone,
    )

    order_id = await db_execute(
        """
        INSERT INTO orders (
            ride_id,
            passenger_telegram_id,
            driver_telegram_id,
            seats,
            phone,
            note,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ride_id,
            passenger_id,
            ride["driver_telegram_id"],
            seats,
            phone,
            note,
            ORDER_PENDING,
            now_str(),
            now_str(),
        ),
    )

    await create_notification(
        ride["driver_telegram_id"],
        "🚕 Yangi buyurtma",
        (
            f"Yo‘lovchi {seats} ta joy so‘radi.\n"
            f"Yo‘nalish: "
            f"{ride['from_region']} → "
            f"{ride['to_region']}"
        ),
        "order",
    )

    driver_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Qabul qilish",
                    callback_data=f"order_accept:{order_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"order_reject:{order_id}",
                ),
            ]
        ]
    )

    passenger_name = (
        f"{user.get('first_name', '')} "
        f"{user.get('last_name', '')}"
    ).strip()

    driver_text = (
        "🚕 <b>YANGI O‘RINDIQ BUYURTMASI</b>\n\n"
        f"📍 <b>{ride['from_region']}</b>"
        f"{' — ' + ride['from_district'] if ride['from_district'] else ''}\n"
        f"➡️ <b>{ride['to_region']}</b>"
        f"{' — ' + ride['to_district'] if ride['to_district'] else ''}\n\n"
        f"📅 Sana: <b>{ride['travel_date']}</b>\n"
        f"🕐 Vaqt: <b>{ride['travel_time']}</b>\n"
        f"💰 Narx: <b>{ride['price']:,} so‘m</b>\n"
        f"💺 So‘ralgan joy: <b>{seats}</b>\n\n"
        f"👤 Yo‘lovchi: <b>{passenger_name}</b>\n"
        f"📱 Telefon: <code>{phone}</code>\n"
        f"🆔 Buyurtma: <code>#{order_id}</code>"
    )

    if note:
        driver_text += f"\n\n📝 Izoh:\n{note}"

    await send_notification(
        ride["driver_telegram_id"],
        driver_text,
        reply_markup=driver_keyboard,
    )

    return json_ok({
        "order_id": order_id,
        "message": "Buyurtma haydovchiga yuborildi."
    })


# =========================================================
# ACCEPT ORDER CORE
# =========================================================

async def process_accept_order(
    order_id,
    driver_telegram_id,
):

    order = await db_fetchone(
        """
        SELECT
            o.*,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price,
            r.available_seats,
            r.seats AS ride_seats,
            r.status AS ride_status
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        WHERE o.id = ?
        """,
        (order_id,),
    )

    if not order:
        return False, "Buyurtma topilmadi.", None

    if order["driver_telegram_id"] != driver_telegram_id:
        return False, "Bu buyurtma sizga tegishli emas.", order

    if order["status"] != ORDER_PENDING:
        return False, "Bu buyurtma allaqachon ko‘rib chiqilgan.", order

    if order["ride_status"] != RIDE_ACTIVE:
        return False, "Bu safar faol emas.", order

    if order["available_seats"] < order["seats"]:
        return False, "Yetarli bo‘sh joy qolmagan.", order

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        await db.execute("BEGIN IMMEDIATE")

        cursor = await db.execute(
            """
            SELECT
                o.*,
                r.available_seats,
                r.seats AS ride_seats,
                r.status AS ride_status
            FROM orders o
            JOIN rides r
                ON r.id = o.ride_id
            WHERE o.id = ?
            """,
            (order_id,),
        )

        current = await cursor.fetchone()

        if not current:
            await db.rollback()
            return False, "Buyurtma topilmadi.", order

        if current["status"] != ORDER_PENDING:
            await db.rollback()
            return False, "Bu buyurtma allaqachon ko‘rib chiqilgan.", dict(current)

        if current["ride_status"] != RIDE_ACTIVE:
            await db.rollback()
            return False, "Safar faol emas.", dict(current)

        if current["available_seats"] < current["seats"]:
            await db.rollback()
            return False, "Yetarli bo‘sh joy qolmagan.", dict(current)

        new_available = (
            current["available_seats"]
            - current["seats"]
        )

        new_ride_status = (
            RIDE_FULL
            if new_available <= 0
            else RIDE_ACTIVE
        )

        await db.execute(
            """
            UPDATE orders
            SET status = ?,
                updated_at = ?
            WHERE id = ?
            AND status = ?
            """,
            (
                ORDER_ACCEPTED,
                now_str(),
                order_id,
                ORDER_PENDING,
            ),
        )

        await db.execute(
            """
            UPDATE rides
            SET available_seats = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                new_available,
                new_ride_status,
                now_str(),
                current["ride_id"],
            ),
        )

        await db.commit()

    await create_notification(
        order["passenger_telegram_id"],
        "✅ Buyurtma qabul qilindi",
        (
            "Haydovchi buyurtmangizni qabul qildi.\n"
            f"📍 {order['from_region']} → {order['to_region']}\n"
            f"📅 {order['travel_date']}\n"
            f"🕐 {order['travel_time']}"
        ),
        "order_accepted",
    )

    await send_notification(
        order["passenger_telegram_id"],
        "✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
        f"📍 {order['from_region']} → {order['to_region']}\n"
        f"📅 {order['travel_date']}\n"
        f"🕐 {order['travel_time']}\n\n"
        "Haydovchi siz bilan bog‘lanadi.",
    )

    return True, "Buyurtma qabul qilindi.", order


# =========================================================
# REJECT ORDER CORE
# =========================================================

async def process_reject_order(
    order_id,
    driver_telegram_id,
):

    order = await db_fetchone(
        """
        SELECT
            o.*,
            r.from_region,
            r.to_region,
            r.travel_date,
            r.travel_time
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        WHERE o.id = ?
        """,
        (order_id,),
    )

    if not order:
        return False, "Buyurtma topilmadi.", None

    if order["driver_telegram_id"] != driver_telegram_id:
        return False, "Bu buyurtma sizga tegishli emas.", order

    if order["status"] != ORDER_PENDING:
        return False, "Bu buyurtma allaqachon ko‘rib chiqilgan.", order

    await db_execute(
        """
        UPDATE orders
        SET status = ?,
            updated_at = ?
        WHERE id = ?
        AND status = ?
        """,
        (
            ORDER_REJECTED,
            now_str(),
            order_id,
            ORDER_PENDING,
        ),
    )

    await create_notification(
        order["passenger_telegram_id"],
        "❌ Buyurtma rad etildi",
        (
            f"Haydovchi #{order['ride_id']} "
            "safaridagi buyurtmangizni rad etdi."
        ),
        "order_rejected",
    )

    await send_notification(
        order["passenger_telegram_id"],
        "❌ <b>Buyurtmangiz rad etildi.</b>\n\n"
        "Boshqa safarni qidirib ko‘rishingiz mumkin.",
    )

    return True, "Buyurtma rad etildi.", order


# =========================================================
# ORDER CALLBACKS
# =========================================================

@dp.callback_query(F.data.startswith("order_accept:"))
async def order_accept_callback(callback: CallbackQuery):

    try:
        order_id = int(
            callback.data.split(":", 1)[1]
        )
    except Exception:
        await callback.answer(
            "Buyurtma ID noto‘g‘ri.",
            show_alert=True,
        )
        return

    success, message, _ = await process_accept_order(
        order_id,
        callback.from_user.id,
    )

    await callback.answer(
        message,
        show_alert=not success,
    )

    if success and callback.message:
        try:
            await callback.message.edit_text(
                callback.message.text
                + "\n\n"
                "✅ <b>BUYURTMA QABUL QILINDI</b>"
            )
        except Exception:
            pass


@dp.callback_query(F.data.startswith("order_reject:"))
async def order_reject_callback(callback: CallbackQuery):

    try:
        order_id = int(
            callback.data.split(":", 1)[1]
        )
    except Exception:
        await callback.answer(
            "Buyurtma ID noto‘g‘ri.",
            show_alert=True,
        )
        return

    success, message, _ = await process_reject_order(
        order_id,
        callback.from_user.id,
    )

    await callback.answer(
        message,
        show_alert=not success,
    )

    if success and callback.message:
        try:
            await callback.message.edit_text(
                callback.message.text
                + "\n\n"
                "❌ <b>BUYURTMA RAD ETILDI</b>"
            )
        except Exception:
            pass


# =========================================================
# DRIVER ORDERS
# =========================================================

async def api_driver_orders(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    telegram_id = int(user["id"])

    orders = await db_fetchall(
        """
        SELECT
            o.*,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price,
            u.first_name AS passenger_first_name,
            u.last_name AS passenger_last_name,
            u.username AS passenger_username
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        LEFT JOIN users u
            ON u.telegram_id = o.passenger_telegram_id
        WHERE o.driver_telegram_id = ?
        ORDER BY o.id DESC
        LIMIT 100
        """,
        (telegram_id,),
    )

    return json_ok({
        "orders": orders
    })


# =========================================================
# ORDER ACCEPT API
# =========================================================

async def api_order_accept(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    data = await request_json(request)

    order_id = safe_int(
        data.get("order_id")
    )

    if not order_id:
        return json_error(
            "Buyurtma ID topilmadi."
        )

    success, message, _ = await process_accept_order(
        order_id,
        int(user["id"]),
    )

    if not success:
        return json_error(message)

    return json_ok({
        "message": message
    })


# =========================================================
# ORDER REJECT API
# =========================================================

async def api_order_reject(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    data = await request_json(request)

    order_id = safe_int(
        data.get("order_id")
    )

    if not order_id:
        return json_error(
            "Buyurtma ID topilmadi."
        )

    success, message, _ = await process_reject_order(
        order_id,
        int(user["id"]),
    )

    if not success:
        return json_error(message)

    return json_ok({
        "message": message
    })


# =========================================================
# ALL ORDERS
# =========================================================

async def api_orders(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    telegram_id = int(user["id"])

    orders = await db_fetchall(
        """
        SELECT
            o.*,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price,
            r.available_seats,
            d.full_name AS driver_name,
            d.phone AS driver_phone,
            u.first_name AS passenger_first_name,
            u.last_name AS passenger_last_name
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        LEFT JOIN drivers d
            ON d.telegram_id = o.driver_telegram_id
        LEFT JOIN users u
            ON u.telegram_id = o.passenger_telegram_id
        WHERE
            o.passenger_telegram_id = ?
            OR o.driver_telegram_id = ?
        ORDER BY o.id DESC
        LIMIT 100
        """,
        (
            telegram_id,
            telegram_id,
        ),
    )

    return json_ok({
        "orders": orders
    })


# =========================================================
# CANCEL ORDER
# =========================================================

async def api_order_cancel(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    data = await request_json(request)

    order_id = safe_int(
        data.get("order_id")
    )

    if not order_id:
        return json_error(
            "Buyurtma ID topilmadi."
        )

    telegram_id = int(user["id"])

    order = await db_fetchone(
        """
        SELECT *
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    )

    if not order:
        return json_error(
            "Buyurtma topilmadi."
        )

    if telegram_id not in (
        order["passenger_telegram_id"],
        order["driver_telegram_id"],
    ):
        return json_error(
            "Bu buyurtmani bekor qilish "
            "huquqingiz yo‘q.",
            403,
        )

    if order["status"] not in (
        ORDER_PENDING,
        ORDER_ACCEPTED,
    ):
        return json_error(
            "Bu buyurtmani bekor qilib bo‘lmaydi."
        )

    await db_execute(
        """
        UPDATE orders
        SET status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            ORDER_CANCELLED,
            now_str(),
            order_id,
        ),
    )

    if order["status"] == ORDER_ACCEPTED:

        ride = await db_fetchone(
            """
            SELECT *
            FROM rides
            WHERE id = ?
            """,
            (order["ride_id"],),
        )

        if ride:

            available = (
                ride["available_seats"]
                + order["seats"]
            )

            status = (
                RIDE_ACTIVE
                if available > 0
                else RIDE_FULL
            )

            await db_execute(
                """
                UPDATE rides
                SET available_seats = ?,
                    status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    available,
                    status,
                    now_str(),
                    order["ride_id"],
                ),
            )

    other_user = (
        order["driver_telegram_id"]
        if telegram_id == order["passenger_telegram_id"]
        else order["passenger_telegram_id"]
    )

    await create_notification(
        other_user,
        "🚫 Buyurtma bekor qilindi",
        f"#{order_id} buyurtma bekor qilindi.",
        "order_cancelled",
    )

    await send_notification(
        other_user,
        f"🚫 <b>Buyurtma #{order_id} bekor qilindi.</b>",
    )

    return json_ok({
        "message": "Buyurtma bekor qilindi."
    })


# =========================================================
# NOTIFICATIONS
# =========================================================

async def api_notifications(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    telegram_id = int(user["id"])

    notifications = await db_fetchall(
        """
        SELECT *
        FROM notifications
        WHERE telegram_id = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        (telegram_id,),
    )

    unread = await db_fetchone(
        """
        SELECT COUNT(*) AS count
        FROM notifications
        WHERE telegram_id = ?
        AND is_read = 0
        """,
        (telegram_id,),
    )

    return json_ok({
        "notifications": notifications,
        "unread": unread["count"] if unread else 0,
        "unread_count": unread["count"] if unread else 0,
    })


# =========================================================
# MARK NOTIFICATION READ
# =========================================================

async def api_notifications_read(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    data = await request_json(request)

    telegram_id = int(user["id"])

    notification_id = safe_int(
        data.get("notification_id")
    )

    if notification_id:

        await db_execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
            AND telegram_id = ?
            """,
            (
                notification_id,
                telegram_id,
            ),
        )

    else:

        await db_execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

    return json_ok({
        "message": "Bildirishnoma o‘qildi."
    })


# =========================================================
# RATING
# =========================================================

async def api_rating(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    data = await request_json(request)

    ride_id = safe_int(
        data.get("ride_id")
    )

    to_telegram_id = safe_int(
        data.get("to_telegram_id")
    )

    rating = safe_int(
        data.get("rating")
    )

    comment = clean_text(
        data.get("comment", ""),
        500,
    )

    if not ride_id or not to_telegram_id:
        return json_error(
            "Ma’lumotlar to‘liq emas."
        )

    if rating is None or not 1 <= rating <= 5:
        return json_error(
            "Reyting 1 dan 5 gacha bo‘lishi kerak."
        )

    from_id = int(user["id"])

    existing = await db_fetchone(
        """
        SELECT *
        FROM ratings
        WHERE ride_id = ?
        AND from_telegram_id = ?
        AND to_telegram_id = ?
        """,
        (
            ride_id,
            from_id,
            to_telegram_id,
        ),
    )

    if existing:
        return json_error(
            "Siz allaqachon reyting bergansiz."
        )

    await db_execute(
        """
        INSERT INTO ratings (
            ride_id,
            from_telegram_id,
            to_telegram_id,
            rating,
            comment,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ride_id,
            from_id,
            to_telegram_id,
            rating,
            comment,
            now_str(),
        ),
    )

    return json_ok({
        "message": "Reyting saqlandi."
    })


# =========================================================
# PASSENGER REQUEST
# =========================================================

async def api_passenger_request(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    data = await request_json(request)

    telegram_id = int(user["id"])

    from_region = clean_text(
        data.get("from_region", ""),
        150,
    )

    from_district = clean_text(
        data.get("from_district", ""),
        150,
    )

    to_region = clean_text(
        data.get("to_region", ""),
        150,
    )

    to_district = clean_text(
        data.get("to_district", ""),
        150,
    )

    travel_date = clean_text(
        data.get("travel_date", ""),
        30,
    )

    travel_time = clean_text(
        data.get("travel_time", ""),
        20,
    )

    seats = safe_int(
        data.get("seats")
    )

    price = safe_int(
        data.get("price"),
        0,
    )

    note = clean_text(
        data.get("note", ""),
        500,
    )

    if not from_region or not to_region:
        return json_error(
            "Yo‘nalishni tanlang."
        )

    if not travel_date:
        return json_error(
            "Safar sanasini kiriting."
        )

    if not valid_seats(seats):
        return json_error(
            "O‘rindiqlar soni noto‘g‘ri."
        )

    request_id = await db_execute(
        """
        INSERT INTO passenger_requests (
            passenger_telegram_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            seats,
            price,
            note,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            seats,
            price,
            note,
            "active",
            now_str(),
            now_str(),
        ),
    )

    return json_ok({
        "request_id": request_id,
        "message": "Yo‘lovchi so‘rovi joylandi."
    })


# =========================================================
# DRIVER REQUESTS
# =========================================================

async def api_driver_requests(request):

    user = await require_web_user(request)

    if not user:
        return json_error(
            "Telegram foydalanuvchisi aniqlanmadi.",
            401,
        )

    requests = await db_fetchall(
        """
        SELECT *
        FROM passenger_requests
        WHERE status = 'active'
        ORDER BY id DESC
        LIMIT 100
        """
    )

    return json_ok({
        "requests": requests
    })


# =========================================================
# ADMIN STATS
# =========================================================

async def get_admin_dashboard_data():

    users = await db_fetchone(
        "SELECT COUNT(*) AS count FROM users"
    )

    drivers = await db_fetchone(
        "SELECT COUNT(*) AS count FROM drivers"
    )

    pending_drivers = await db_fetchone(
        """
        SELECT COUNT(*) AS count
        FROM drivers
        WHERE status = ?
        """,
        (DRIVER_PENDING,),
    )

    approved_drivers = await db_fetchone(
        """
        SELECT COUNT(*) AS count
        FROM drivers
        WHERE status = ?
        """,
        (DRIVER_APPROVED,),
    )

    rejected_drivers = await db_fetchone(
        """
        SELECT COUNT(*) AS count
        FROM drivers
        WHERE status = ?
        """,
        (DRIVER_REJECTED,),
    )

    rides = await db_fetchone(
        "SELECT COUNT(*) AS count FROM rides"
    )

    active_rides = await db_fetchone(
        """
        SELECT COUNT(*) AS count
        FROM rides
        WHERE status = ?
        """,
        (RIDE_ACTIVE,),
    )

    orders = await db_fetchone(
        "SELECT COUNT(*) AS count FROM orders"
    )

    pending_orders = await db_fetchone(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE status = ?
        """,
        (ORDER_PENDING,),
    )

    ratings = await db_fetchone(
        "SELECT COUNT(*) AS count FROM ratings"
    )

    pending_list = await db_fetchall(
        """
        SELECT *
        FROM drivers
        WHERE status = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        (DRIVER_PENDING,),
    )

    stats = {
        "users": users["count"],
        "drivers": drivers["count"],
        "pending_drivers": pending_drivers["count"],
        "approved_drivers": approved_drivers["count"],
        "rejected_drivers": rejected_drivers["count"],
        "rides": rides["count"],
        "active_rides": active_rides["count"],
        "orders": orders["count"],
        "pending_orders": pending_orders["count"],
        "ratings": ratings["count"],
    }

    return stats, pending_list


async def api_admin_stats(request):

    user, error_response = await require_admin_web_user(
        request
    )

    if error_response:
        return error_response

    stats, _ = await get_admin_dashboard_data()

    return json_ok(stats)


# =========================================================
# ADMIN DASHBOARD
# =========================================================

async def api_admin_dashboard(request):

    user, error_response = await require_admin_web_user(
        request
    )

    if error_response:
        return error_response

    stats, pending_drivers = (
        await get_admin_dashboard_data()
    )

    return json_ok({
        "stats": stats,
        "pending_drivers": pending_drivers,
        "users": stats["users"],
        "drivers": stats["drivers"],
        "rides": stats["rides"],
        "orders": stats["orders"],
    })


# =========================================================
# ADMIN APPROVE HELPER
# =========================================================

async def approve_driver_by_admin(
    telegram_id,
    admin_id,
):

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    if not driver:
        return False, "Haydovchi topilmadi.", None

    await db_execute(
        """
        UPDATE drivers
        SET status = ?,
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            DRIVER_APPROVED,
            now_str(),
            telegram_id,
        ),
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
            admin_id,
            "driver_approve",
            telegram_id,
            "Driver approved",
            now_str(),
        ),
    )

    await create_notification(
        telegram_id,
        "✅ Haydovchilik tasdiqlandi",
        (
            "Siz OPPER TAXI haydovchisi "
            "sifatida tasdiqlandingiz."
        ),
        "driver",
    )

    await send_notification(
        telegram_id,
        "🎉 <b>Tabriklaymiz!</b>\n\n"
        "Sizning OPPER TAXI haydovchilik "
        "arizangiz tasdiqlandi.\n\n"
        "Endi Mini App orqali safar "
        "joylashingiz mumkin.",
    )

    return True, "Haydovchi tasdiqlandi.", driver


# =========================================================
# ADMIN REJECT HELPER
# =========================================================

async def reject_driver_by_admin(
    telegram_id,
    admin_id,
):

    driver = await db_fetchone(
        """
        SELECT *
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    if not driver:
        return False, "Haydovchi topilmadi.", None

    await db_execute(
        """
        UPDATE drivers
        SET status = ?,
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            DRIVER_REJECTED,
            now_str(),
            telegram_id,
        ),
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
            admin_id,
            "driver_reject",
            telegram_id,
            "Driver rejected",
            now_str(),
        ),
    )

    await create_notification(
        telegram_id,
        "❌ Haydovchilik arizasi rad etildi",
        "Haydovchilik arizangiz rad etildi.",
        "driver",
    )

    await send_notification(
        telegram_id,
        "❌ <b>Haydovchilik arizangiz rad etildi.</b>\n\n"
        "Ma’lumotlarni tekshirib, "
        "qayta ariza topshirishingiz mumkin.",
    )

    return True, "Haydovchi rad etildi.", driver


# =========================================================
# ADMIN APPROVE API
# =========================================================

async def api_admin_driver_approve(request):

    user, error_response = await require_admin_web_user(
        request
    )

    if error_response:
        return error_response

    data = await request_json(request)

    telegram_id = safe_int(
        data.get("telegram_id")
        or data.get("driver_telegram_id")
    )

    if not telegram_id:

        driver_id = safe_int(
            data.get("driver_id")
        )

        if driver_id:
            driver = await db_fetchone(
                """
                SELECT *
                FROM drivers
                WHERE id = ?
                """,
                (driver_id,),
            )

            if driver:
                telegram_id = driver["telegram_id"]

    if not telegram_id:
        return json_error(
            "Haydovchi ID topilmadi."
        )

    success, message, driver = (
        await approve_driver_by_admin(
            telegram_id,
            int(user["id"]),
        )
    )

    if not success:
        return json_error(message, 404)

    return json_ok({
        "success": True,
        "message": message,
        "driver": driver,
    })


# =========================================================
# ADMIN REJECT API
# =========================================================

async def api_admin_driver_reject(request):

    user, error_response = await require_admin_web_user(
        request
    )

    if error_response:
        return error_response

    data = await request_json(request)

    telegram_id = safe_int(
        data.get("telegram_id")
        or data.get("driver_telegram_id")
    )

    if not telegram_id:

        driver_id = safe_int(
            data.get("driver_id")
        )

        if driver_id:
            driver = await db_fetchone(
                """
                SELECT *
                FROM drivers
                WHERE id = ?
                """,
                (driver_id,),
            )

            if driver:
                telegram_id = driver["telegram_id"]

    if not telegram_id:
        return json_error(
            "Haydovchi ID topilmadi."
        )

    success, message, driver = (
        await reject_driver_by_admin(
            telegram_id,
            int(user["id"]),
        )
    )

    if not success:
        return json_error(message, 404)

    return json_ok({
        "success": True,
        "message": message,
        "driver": driver,
    })


# =========================================================
# ADMIN TELEGRAM APPROVE BUTTON
# =========================================================

@dp.callback_query(F.data.startswith("driver_approve:"))
async def admin_driver_approve(
    callback: CallbackQuery,
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Sizda admin huquqi yo‘q.",
            show_alert=True,
        )

        return

    try:
        telegram_id = int(
            callback.data.split(":", 1)[1]
        )
    except Exception:
        await callback.answer(
            "ID noto‘g‘ri.",
            show_alert=True,
        )
        return

    success, message, _ = (
        await approve_driver_by_admin(
            telegram_id,
            ADMIN_ID,
        )
    )

    await callback.answer(
        message,
        show_alert=not success,
    )

    if success and callback.message:
        try:
            await callback.message.edit_text(
                callback.message.text
                + "\n\n"
                "✅ <b>TASDIQLANDI</b>"
            )
        except Exception:
            pass


# =========================================================
# ADMIN TELEGRAM REJECT BUTTON
# =========================================================

@dp.callback_query(F.data.startswith("driver_reject:"))
async def admin_driver_reject(
    callback: CallbackQuery,
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Sizda admin huquqi yo‘q.",
            show_alert=True,
        )

        return

    try:
        telegram_id = int(
            callback.data.split(":", 1)[1]
        )
    except Exception:
        await callback.answer(
            "ID noto‘g‘ri.",
            show_alert=True,
        )
        return

    success, message, _ = (
        await reject_driver_by_admin(
            telegram_id,
            ADMIN_ID,
        )
    )

    await callback.answer(
        message,
        show_alert=not success,
    )

    if success and callback.message:
        try:
            await callback.message.edit_text(
                callback.message.text
                + "\n\n"
                "❌ <b>RAD ETILDI</b>"
            )
        except Exception:
            pass


# =========================================================
# HEALTH
# =========================================================

async def health_handler(request):

    return json_ok({
        "service": "OPPER TAXI",
        "status": "online",
        "time": now_str(),
    })


# =========================================================
# INDEX
# =========================================================

async def index_handler(request):

    index_file = (
        BASE_DIR
        / "web"
        / "index.html"
    )

    if not index_file.exists():

        return web.Response(
            text=(
                "OPPER TAXI Mini App "
                "web/index.html topilmadi."
            ),
            content_type="text/plain",
            status=404,
        )

    return web.FileResponse(
        path=index_file
    )


# =========================================================
# SETUP ROUTES
# =========================================================

def setup_routes(app):

    # -----------------------------------------------------
    # MAIN MINI APP
    # -----------------------------------------------------

    app.router.add_get(
        "/",
        index_handler,
    )

    app.router.add_static(
        "/web/",
        BASE_DIR / "web",
        show_index=False,
    )

    # -----------------------------------------------------
    # ADMIN PANEL
    # -----------------------------------------------------

    app.router.add_static(
        "/admin/",
        BASE_DIR / "admin",
        show_index=False,
    )

    # -----------------------------------------------------
    # UPLOADS
    # -----------------------------------------------------

    app.router.add_static(
        "/uploads/",
        BASE_DIR / "uploads",
        show_index=False,
    )

    # -----------------------------------------------------
    # HEALTH
    # -----------------------------------------------------

    app.router.add_get(
        "/health",
        health_handler,
    )

    # -----------------------------------------------------
    # PROFILE
    # -----------------------------------------------------

    app.router.add_get(
        "/api/profile",
        api_profile,
    )

    app.router.add_post(
        "/api/profile/update",
        api_profile_update,
    )

    # -----------------------------------------------------
    # DRIVER
    # -----------------------------------------------------

    app.router.add_get(
        "/api/driver/status",
        api_driver_status,
    )

    app.router.add_post(
        "/api/driver/register",
        api_driver_register,
    )

    app.router.add_post(
        "/api/driver/ride",
        api_driver_ride,
    )

    app.router.add_get(
        "/api/driver/orders",
        api_driver_orders,
    )

    app.router.add_get(
        "/api/driver/requests",
        api_driver_requests,
    )

    # -----------------------------------------------------
    # RIDES
    # -----------------------------------------------------

    app.router.add_get(
        "/api/rides",
        api_rides,
    )

    # -----------------------------------------------------
    # PASSENGER
    # -----------------------------------------------------

    app.router.add_post(
        "/api/passenger/order",
        api_passenger_order,
    )

    app.router.add_post(
        "/api/passenger/request",
        api_passenger_request,
    )

    # -----------------------------------------------------
    # ORDERS
    # -----------------------------------------------------

    app.router.add_get(
        "/api/orders",
        api_orders,
    )

    app.router.add_post(
        "/api/order/accept",
        api_order_accept,
    )

    app.router.add_post(
        "/api/order/reject",
        api_order_reject,
    )

    app.router.add_post(
        "/api/order/cancel",
        api_order_cancel,
    )

    # -----------------------------------------------------
    # NOTIFICATIONS
    # -----------------------------------------------------

    app.router.add_get(
        "/api/notifications",
        api_notifications,
    )

    app.router.add_post(
        "/api/notifications/read",
        api_notifications_read,
    )

    # -----------------------------------------------------
    # RATING
    # -----------------------------------------------------

    app.router.add_post(
        "/api/rating",
        api_rating,
    )

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    app.router.add_get(
        "/api/admin/stats",
        api_admin_stats,
    )

    app.router.add_get(
        "/api/admin/dashboard",
        api_admin_dashboard,
    )

    app.router.add_post(
        "/api/admin/driver/approve",
        api_admin_driver_approve,
    )

    app.router.add_post(
        "/api/admin/driver/reject",
        api_admin_driver_reject,
    )


# =========================================================
# WEB SERVER
# =========================================================

async def start_web_server():

    app = web.Application()

    setup_routes(app)

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    logger.info(
        "Web server started on port %s",
        PORT,
    )

    return runner


# =========================================================
# BOT SETUP
# =========================================================

async def setup_bot():

    try:

        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🚕 OPPER TAXI",
                web_app=WebAppInfo(
                    url=MINI_APP_URL
                ),
            )
        )

        logger.info(
            "Telegram Mini App menu button configured."
        )

    except Exception:

        logger.exception(
            "Menu button setup error"
        )


# =========================================================
# MAIN
# =========================================================

async def main():

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

        await dp.start_polling(bot)

    finally:

        await runner.cleanup()

        await bot.session.close()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    asyncio.run(main())
