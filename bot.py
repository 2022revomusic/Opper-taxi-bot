import os
import asyncio
import json
import hmac
import hashlib
import time
import html
from pathlib import Path
from datetime import datetime
from urllib.parse import parse_qsl

import aiosqlite
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "653914246").split(",")
    if x.strip().isdigit()
}

DB_PATH = os.getenv("DB_PATH", "oper_taxi.db")

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
INDEX_FILE = WEB_DIR / "index.html"

PORT = int(os.getenv("PORT", "8080"))

# Railway'da MINII_APP_URL berish mumkin:
# https://your-app.up.railway.app
#
# Agar berilmasa RAILWAY_PUBLIC_DOMAIN'dan foydalanadi.
MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()

if not MINI_APP_URL:
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

    if railway_domain:
        MINI_APP_URL = (
            railway_domain
            if railway_domain.startswith("http")
            else f"https://{railway_domain}"
        )


# =========================================================
# BOT
# =========================================================

bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


# =========================================================
# CONSTANTS
# =========================================================

CITIES = [
    "Toshkent",
    "Namangan",
    "Andijon",
    "Farg‘ona",
    "Qo‘qon",
    "Marg‘ilon",
]

TIMES = [
    "06:00",
    "07:00",
    "08:00",
    "09:00",
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
    "18:00",
    "19:00",
    "20:00",
    "21:00",
    "22:00",
    "23:00",
]

PASSENGER_LIMIT = 4


# =========================================================
# FSM STATES
# =========================================================

class PassengerState(StatesGroup):
    from_city = State()
    to_city = State()
    time = State()
    seats = State()
    name = State()
    phone = State()
    location = State()


class DriverState(StatesGroup):
    full_name = State()
    phone = State()
    car_model = State()
    car_number = State()
    seats = State()


class DriverRideState(StatesGroup):
    from_city = State()
    to_city = State()
    time = State()
    seats = State()


# =========================================================
# GENERAL HELPERS
# =========================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def esc(value):
    if value is None:
        return ""
    return html.escape(str(value))


async def safe_send(user_id, text, **kwargs):
    try:
        return await bot.send_message(user_id, text, **kwargs)
    except Exception as e:
        print(f"safe_send error {user_id}: {e}")
        return None


async def notify_admins(text, **kwargs):
    for admin_id in ADMIN_IDS:
        await safe_send(admin_id, text, **kwargs)


# =========================================================
# DATABASE
# =========================================================

async def db_execute(
    query,
    params=(),
    fetch=False,
    fetchone=False,
):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(query, params)

        if fetchone:
            return await cursor.fetchone()

        if fetch:
            return await cursor.fetchall()

        await db.commit()

        return cursor.lastrowid


async def init_db():

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            phone TEXT,
            created_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS driver_profiles (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            car_model TEXT,
            car_number TEXT,
            seats INTEGER DEFAULT 4,
            status TEXT DEFAULT 'pending',
            rating REAL DEFAULT 5.0,
            trips INTEGER DEFAULT 0,
            latitude REAL,
            longitude REAL,
            created_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            from_city TEXT,
            to_city TEXT,
            ride_time TEXT,
            seats INTEGER,
            available_seats INTEGER,
            reserved_seats INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS passenger_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_id INTEGER,
            from_city TEXT,
            to_city TEXT,
            ride_time TEXT,
            seats INTEGER,
            name TEXT,
            phone TEXT,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'searching',
            created_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            ride_id INTEGER,
            passenger_id INTEGER,
            driver_id INTEGER,
            seats INTEGER,
            status TEXT DEFAULT 'pending_driver',
            driver_latitude REAL,
            driver_longitude REAL,
            created_at TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER UNIQUE,
            passenger_id INTEGER,
            driver_id INTEGER,
            rating INTEGER,
            comment TEXT,
            created_at TEXT
        )
        """)

        await db.commit()


# =========================================================
# USER FUNCTIONS
# =========================================================

async def save_user_from_message(message: Message):

    user = message.from_user

    if not user:
        return

    existing = await db_execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user.id,),
        fetchone=True,
    )

    if existing:

        await db_execute(
            """
            UPDATE users
            SET full_name=?,
                username=?
            WHERE user_id=?
            """,
            (
                user.full_name,
                user.username or "",
                user.id,
            ),
        )

    else:

        await db_execute(
            """
            INSERT INTO users(
                user_id,
                full_name,
                username,
                phone,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.full_name,
                user.username or "",
                "",
                now(),
            ),
        )


async def save_user(
    user_id,
    full_name="",
    username="",
    phone="",
):

    existing = await db_execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,),
        fetchone=True,
    )

    if existing:

        await db_execute(
            """
            UPDATE users
            SET full_name=COALESCE(NULLIF(?, ''), full_name),
                username=COALESCE(NULLIF(?, ''), username),
                phone=COALESCE(NULLIF(?, ''), phone)
            WHERE user_id=?
            """,
            (
                full_name,
                username,
                phone,
                user_id,
            ),
        )

    else:

        await db_execute(
            """
            INSERT INTO users(
                user_id,
                full_name,
                username,
                phone,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                full_name,
                username,
                phone,
                now(),
            ),
        )


async def get_user(user_id):

    return await db_execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,),
        fetchone=True,
    )


async def get_driver(user_id):

    return await db_execute(
        "SELECT * FROM driver_profiles WHERE user_id=?",
        (user_id,),
        fetchone=True,
    )


async def get_request(request_id):

    return await db_execute(
        "SELECT * FROM passenger_requests WHERE id=?",
        (request_id,),
        fetchone=True,
    )


async def get_booking(booking_id):

    return await db_execute(
        "SELECT * FROM bookings WHERE id=?",
        (booking_id,),
        fetchone=True,
    )


# =========================================================
# KEYBOARDS
# =========================================================

def main_menu():

    rows = []

    if MINI_APP_URL:

        rows.append([
            KeyboardButton(
                text="🚕 OPPER TAXI",
                web_app=WebAppInfo(url=MINI_APP_URL),
            )
        ])

    rows.extend([
        [
            KeyboardButton(text="🚕 Taksi chaqirish"),
            KeyboardButton(text="🚗 Haydovchi bo‘lish"),
        ],
        [
            KeyboardButton(text="🔎 Taksilarni qidirish"),
            KeyboardButton(text="📋 Buyurtmalarim"),
        ],
        [
            KeyboardButton(text="👤 Profil"),
            KeyboardButton(text="ℹ️ Yordam"),
        ],
    ])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )


def cancel_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="❌ Bekor qilish")
            ]
        ],
        resize_keyboard=True,
    )


def city_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=CITIES[0]),
                KeyboardButton(text=CITIES[1]),
            ],
            [
                KeyboardButton(text=CITIES[2]),
                KeyboardButton(text=CITIES[3]),
            ],
            [
                KeyboardButton(text=CITIES[4]),
                KeyboardButton(text=CITIES[5]),
            ],
            [
                KeyboardButton(text="❌ Bekor qilish")
            ],
        ],
        resize_keyboard=True,
    )


def time_keyboard():

    rows = []

    for i in range(0, len(TIMES), 3):
        rows.append([
            KeyboardButton(text=x)
            for x in TIMES[i:i + 3]
        ])

    rows.append([
        KeyboardButton(text="❌ Bekor qilish")
    ])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )


def seats_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="1"),
                KeyboardButton(text="2"),
            ],
            [
                KeyboardButton(text="3"),
                KeyboardButton(text="4"),
            ],
            [
                KeyboardButton(text="❌ Bekor qilish")
            ],
        ],
        resize_keyboard=True,
    )


def location_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📍 Lokatsiyani yuborish",
                    request_location=True,
                )
            ],
            [
                KeyboardButton(text="⏭ O‘tkazib yuborish")
            ],
            [
                KeyboardButton(text="❌ Bekor qilish")
            ],
        ],
        resize_keyboard=True,
    )


def passenger_cancel_keyboard(request_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Buyurtmani bekor qilish",
                    callback_data=f"cancel_request:{request_id}",
                )
            ]
        ]
    )


def driver_request_keyboard(request_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Qabul qilish",
                    callback_data=f"accept_request:{request_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"reject_request:{request_id}",
                ),
            ]
        ]
    )


def booking_driver_keyboard(booking_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 Lokatsiyamni yuborish",
                    callback_data=f"driver_location:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚕 Yetib bordim",
                    callback_data=f"driver_arrived:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Yo‘lovchini oldim",
                    callback_data=f"driver_onboard:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏁 Safarni tugatish",
                    callback_data=f"driver_complete:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Safarni bekor qilish",
                    callback_data=f"driver_cancel:{booking_id}",
                )
            ],
        ]
    )


def passenger_booking_keyboard(booking_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 Haydovchini kuzatish",
                    callback_data=f"track_driver:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Safarni bekor qilish",
                    callback_data=f"passenger_cancel:{booking_id}",
                )
            ],
        ]
    )


def admin_driver_keyboard(user_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"admin_approve:{user_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"admin_reject:{user_id}",
                ),
            ]
        ]
    )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await save_user_from_message(message)

    text = (
        "🚕 <b>OPPER TAXI</b>\n\n"
        "Assalomu alaykum!\n"
        "OPPER TAXI xizmatiga xush kelibsiz.\n\n"
        "📍 Shaharlararo taksi\n"
        "🚗 Haydovchilar\n"
        "👤 Yo‘lovchilar\n"
        "📍 Lokatsiya\n"
        "📱 Mini App"
    )

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# =========================================================
# CANCEL
# =========================================================

@dp.message(F.text == "❌ Bekor qilish")
async def cancel_handler(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await message.answer(
        "❌ Amal bekor qilindi.",
        reply_markup=main_menu(),
    )


# =========================================================
# PASSENGER - BOT
# =========================================================

@dp.message(F.text == "🚕 Taksi chaqirish")
async def taxi_start(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await state.set_state(
        PassengerState.from_city
    )

    await message.answer(
        "🚕 <b>Qayerdan yo‘lga chiqasiz?</b>",
        reply_markup=city_keyboard(),
    )


@dp.message(PassengerState.from_city)
async def passenger_from(
    message: Message,
    state: FSMContext,
):

    if message.text not in CITIES:

        await message.answer(
            "Iltimos, shaharni tugmadan tanlang.",
            reply_markup=city_keyboard(),
        )
        return

    await state.update_data(
        from_city=message.text
    )

    await state.set_state(
        PassengerState.to_city
    )

    await message.answer(
        "📍 <b>Qayerga borasiz?</b>",
        reply_markup=city_keyboard(),
    )


@dp.message(PassengerState.to_city)
async def passenger_to(
    message: Message,
    state: FSMContext,
):

    if message.text not in CITIES:

        await message.answer(
            "Iltimos, shaharni tugmadan tanlang.",
            reply_markup=city_keyboard(),
        )
        return

    data = await state.get_data()

    if message.text == data["from_city"]:

        await message.answer(
            "❗ Qayerdan va qayerga shaharlari bir xil bo‘lishi mumkin emas.",
            reply_markup=city_keyboard(),
        )
        return

    await state.update_data(
        to_city=message.text
    )

    await state.set_state(
        PassengerState.time
    )

    await message.answer(
        "🕐 <b>Qaysi vaqtda yo‘lga chiqasiz?</b>",
        reply_markup=time_keyboard(),
    )


@dp.message(PassengerState.time)
async def passenger_time(
    message: Message,
    state: FSMContext,
):

    if message.text not in TIMES:

        await message.answer(
            "Vaqtni tugmadan tanlang.",
            reply_markup=time_keyboard(),
        )
        return

    await state.update_data(
        time=message.text
    )

    await state.set_state(
        PassengerState.seats
    )

    await message.answer(
        "👥 <b>Necha kishi?</b>",
        reply_markup=seats_keyboard(),
    )


@dp.message(PassengerState.seats)
async def passenger_seats(
    message: Message,
    state: FSMContext,
):

    if message.text not in {"1", "2", "3", "4"}:

        await message.answer(
            "1 dan 4 gacha tanlang.",
            reply_markup=seats_keyboard(),
        )
        return

    await state.update_data(
        seats=int(message.text)
    )

    await state.set_state(
        PassengerState.name
    )

    await message.answer(
        "👤 <b>Ismingizni yozing:</b>",
        reply_markup=cancel_keyboard(),
    )


@dp.message(PassengerState.name)
async def passenger_name(
    message: Message,
    state: FSMContext,
):

    if not message.text:
        return

    await state.update_data(
        name=message.text.strip()
    )

    await state.set_state(
        PassengerState.phone
    )

    await message.answer(
        "📞 <b>Telefon raqamingizni yuboring:</b>\n\n"
        "Masalan: +998901234567",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📞 Raqamimni yuborish",
                        request_contact=True,
                    )
                ],
                [
                    KeyboardButton(text="❌ Bekor qilish")
                ],
            ],
            resize_keyboard=True,
        ),
    )


@dp.message(PassengerState.phone)
async def passenger_phone(
    message: Message,
    state: FSMContext,
):

    phone = ""

    if message.contact:
        phone = message.contact.phone_number

    elif message.text:
        phone = message.text.strip()

    if not phone:

        await message.answer(
            "Telefon raqamingizni yuboring."
        )
        return

    await state.update_data(
        phone=phone
    )

    await state.set_state(
        PassengerState.location
    )

    await message.answer(
        "📍 Lokatsiyangizni yuboring.\n"
        "Bu haydovchiga sizni topishda yordam beradi.",
        reply_markup=location_keyboard(),
    )


async def create_passenger_request(
    user_id,
    from_city,
    to_city,
    ride_time,
    seats,
    name,
    phone,
    latitude=None,
    longitude=None,
):

    request_id = await db_execute(
        """
        INSERT INTO passenger_requests(
            passenger_id,
            from_city,
            to_city,
            ride_time,
            seats,
            name,
            phone,
            latitude,
            longitude,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'searching', ?)
        """,
        (
            user_id,
            from_city,
            to_city,
            ride_time,
            seats,
            name,
            phone,
            latitude,
            longitude,
            now(),
        ),
    )

    await save_user(
        user_id=user_id,
        phone=phone,
        full_name=name,
    )

    return request_id


async def notify_matching_drivers(request_id):

    request = await get_request(request_id)

    if not request:
        return 0

    drivers = await db_execute(
        """
        SELECT
            d.user_id,
            d.full_name,
            d.phone,
            d.car_model,
            d.car_number,
            d.seats,
            r.id AS ride_id,
            r.available_seats
        FROM driver_profiles d
        JOIN rides r
            ON r.driver_id=d.user_id
        WHERE
            d.status='approved'
            AND r.status='active'
            AND r.from_city=?
            AND r.to_city=?
            AND r.ride_time=?
            AND r.available_seats>=?
        """,
        (
            request["from_city"],
            request["to_city"],
            request["ride_time"],
            request["seats"],
        ),
        fetch=True,
    )

    sent = 0

    for driver in drivers:

        text = (
            "🚕 <b>YANGI BUYURTMA!</b>\n\n"
            f"📍 {esc(request['from_city'])} → "
            f"{esc(request['to_city'])}\n"
            f"🕐 Vaqt: <b>{esc(request['ride_time'])}</b>\n"
            f"👥 Yo‘lovchilar: <b>{request['seats']}</b>\n"
            f"👤 Ism: {esc(request['name'])}\n"
            f"📞 Telefon: {esc(request['phone'])}\n\n"
            "Buyurtmani qabul qilasizmi?"
        )

        result = await safe_send(
            driver["user_id"],
            text,
            reply_markup=driver_request_keyboard(
                request_id
            ),
        )

        if result:
            sent += 1

    return sent


async def finish_passenger_request(
    message,
    state,
    latitude=None,
    longitude=None,
):

    data = await state.get_data()

    request_id = await create_passenger_request(
        user_id=message.from_user.id,
        from_city=data["from_city"],
        to_city=data["to_city"],
        ride_time=data["time"],
        seats=data["seats"],
        name=data["name"],
        phone=data["phone"],
        latitude=latitude,
        longitude=longitude,
    )

    count = await notify_matching_drivers(
        request_id
    )

    await state.clear()

    if count:

        await message.answer(
            "✅ <b>Buyurtmangiz qabul qilindi.</b>\n\n"
            f"📍 {esc(data['from_city'])} → "
            f"{esc(data['to_city'])}\n"
            f"🕐 {esc(data['time'])}\n"
            f"👥 {data['seats']} kishi\n\n"
            "🚗 Hozir haydovchilar qidirilmoqda.\n"
            "Haydovchi buyurtmani qabul qilganda sizga xabar keladi.",
            reply_markup=main_menu(),
        )

    else:

        await message.answer(
            "🔎 <b>Hozircha mos haydovchi topilmadi.</b>\n\n"
            "Buyurtmangiz qidiruvda qoladi. "
            "Mos haydovchi paydo bo‘lsa, buyurtma yuboriladi.",
            reply_markup=main_menu(),
        )

        await message.answer(
            "Buyurtmani bekor qilish:",
            reply_markup=passenger_cancel_keyboard(
                request_id
            ),
        )


@dp.message(PassengerState.location, F.location)
async def passenger_location(
    message: Message,
    state: FSMContext,
):

    await finish_passenger_request(
        message,
        state,
        latitude=message.location.latitude,
        longitude=message.location.longitude,
    )


@dp.message(PassengerState.location)
async def passenger_location_skip(
    message: Message,
    state: FSMContext,
):

    if message.text == "⏭ O‘tkazib yuborish":

        await finish_passenger_request(
            message,
            state,
        )
        return

    await message.answer(
        "📍 Lokatsiyani yuboring yoki "
        "⏭ O‘tkazib yuborish tugmasini bosing.",
        reply_markup=location_keyboard(),
    )


# =========================================================
# DRIVER REGISTRATION
# =========================================================

@dp.message(F.text == "🚗 Haydovchi bo‘lish")
async def driver_start(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    driver = await get_driver(
        message.from_user.id
    )

    if driver:

        if driver["status"] == "approved":

            await message.answer(
                "✅ Siz allaqachon tasdiqlangan haydovchisiz.\n\n"
                "Safar e’lon qilish uchun "
                "🚗 Haydovchi bo‘lish tugmasidan foydalanishingiz mumkin.",
                reply_markup=main_menu(),
            )

            await state.set_state(
                DriverRideState.from_city
            )

            await message.answer(
                "📍 Qayerdan ketasiz?",
                reply_markup=city_keyboard(),
            )

            return

        if driver["status"] == "pending":

            await message.answer(
                "⏳ Haydovchi arizangiz admin tomonidan ko‘rib chiqilmoqda.",
                reply_markup=main_menu(),
            )
            return

        if driver["status"] == "rejected":

            await message.answer(
                "❌ Oldingi haydovchi arizangiz rad etilgan.\n"
                "Qaytadan ro‘yxatdan o‘tishingiz mumkin."
            )

    await state.set_state(
        DriverState.full_name
    )

    await message.answer(
        "🚗 <b>Haydovchi ro‘yxatdan o‘tishi</b>\n\n"
        "Ism va familiyangizni yozing:",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DriverState.full_name)
async def driver_full_name(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        full_name=message.text.strip()
    )

    await state.set_state(
        DriverState.phone
    )

    await message.answer(
        "📞 Telefon raqamingiz:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📞 Raqamimni yuborish",
                        request_contact=True,
                    )
                ],
                [
                    KeyboardButton(
                        text="❌ Bekor qilish"
                    )
                ],
            ],
            resize_keyboard=True,
        ),
    )


@dp.message(DriverState.phone)
async def driver_phone(
    message: Message,
    state: FSMContext,
):

    phone = (
        message.contact.phone_number
        if message.contact
        else message.text.strip()
        if message.text
        else ""
    )

    if not phone:
        await message.answer(
            "Telefon raqamingizni yuboring."
        )
        return

    await state.update_data(
        phone=phone
    )

    await state.set_state(
        DriverState.car_model
    )

    await message.answer(
        "🚘 Mashina markasi/modelini yozing.\n\n"
        "Masalan: Chevrolet Cobalt"
    )


@dp.message(DriverState.car_model)
async def driver_car_model(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        car_model=message.text.strip()
    )

    await state.set_state(
        DriverState.car_number
    )

    await message.answer(
        "🔢 Mashina raqamini yozing.\n\n"
        "Masalan: 01 A 777 AA"
    )


@dp.message(DriverState.car_number)
async def driver_car_number(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        car_number=message.text.strip()
    )

    await state.set_state(
        DriverState.seats
    )

    await message.answer(
        "👥 Mashinada nechta yo‘lovchi o‘rni bor?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="1"),
                    KeyboardButton(text="2"),
                    KeyboardButton(text="3"),
                    KeyboardButton(text="4"),
                ],
                [
                    KeyboardButton(text="5"),
                    KeyboardButton(text="6"),
                    KeyboardButton(text="7"),
                    KeyboardButton(text="8"),
                ],
                [
                    KeyboardButton(text="❌ Bekor qilish")
                ],
            ],
            resize_keyboard=True,
        ),
    )


async def ensure_driver_profile(
    user_id,
    full_name,
    phone,
    car_model,
    car_number,
    seats,
):

    existing = await get_driver(user_id)

    if existing:

        await db_execute(
            """
            UPDATE driver_profiles
            SET full_name=?,
                phone=?,
                car_model=?,
                car_number=?,
                seats=?,
                status='pending'
            WHERE user_id=?
            """,
            (
                full_name,
                phone,
                car_model,
                car_number,
                seats,
                user_id,
            ),
        )

    else:

        await db_execute(
            """
            INSERT INTO driver_profiles(
                user_id,
                full_name,
                phone,
                car_model,
                car_number,
                seats,
                status,
                rating,
                trips,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending', 5.0, 0, ?)
            """,
            (
                user_id,
                full_name,
                phone,
                car_model,
                car_number,
                seats,
                now(),
            ),
        )


@dp.message(DriverState.seats)
async def driver_seats(
    message: Message,
    state: FSMContext,
):

    try:
        seats = int(message.text)
    except:
        seats = 0

    if seats < 1 or seats > 8:

        await message.answer(
            "1 dan 8 gacha tanlang."
        )
        return

    data = await state.get_data()

    await ensure_driver_profile(
        user_id=message.from_user.id,
        full_name=data["full_name"],
        phone=data["phone"],
        car_model=data["car_model"],
        car_number=data["car_number"],
        seats=seats,
    )

    await state.clear()

    await message.answer(
        "✅ <b>Haydovchi arizangiz yuborildi.</b>\n\n"
        "Admin tekshiruvdan o‘tkazadi.\n"
        "Tasdiqlangandan keyin safar e’lon qilishingiz mumkin.",
        reply_markup=main_menu(),
    )

    text = (
        "🚗 <b>YANGI HAYDOVCHI ARIZASI</b>\n\n"
        f"👤 {esc(data['full_name'])}\n"
        f"📞 {esc(data['phone'])}\n"
        f"🚘 {esc(data['car_model'])}\n"
        f"🔢 {esc(data['car_number'])}\n"
        f"👥 O‘rinlar: {seats}\n"
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>"
    )

    await notify_admins(
        text,
        reply_markup=admin_driver_keyboard(
            message.from_user.id
        ),
    )


# =========================================================
# DRIVER RIDE
# =========================================================

@dp.message(F.text == "🚗 Safar e’lon qilish")
async def driver_ride_start(
    message: Message,
    state: FSMContext,
):

    driver = await get_driver(
        message.from_user.id
    )

    if not driver or driver["status"] != "approved":

        await message.answer(
            "❗ Avval haydovchi sifatida admin tomonidan tasdiqlanishingiz kerak."
        )
        return

    await state.set_state(
        DriverRideState.from_city
    )

    await message.answer(
        "📍 Qayerdan ketasiz?",
        reply_markup=city_keyboard(),
    )


@dp.message(DriverRideState.from_city)
async def ride_from(
    message: Message,
    state: FSMContext,
):

    if message.text not in CITIES:
        await message.answer(
            "Shaharni tanlang.",
            reply_markup=city_keyboard(),
        )
        return

    await state.update_data(
        from_city=message.text
    )

    await state.set_state(
        DriverRideState.to_city
    )

    await message.answer(
        "📍 Qayerga borasiz?",
        reply_markup=city_keyboard(),
    )


@dp.message(DriverRideState.to_city)
async def ride_to(
    message: Message,
    state: FSMContext,
):

    if message.text not in CITIES:
        await message.answer(
            "Shaharni tanlang.",
            reply_markup=city_keyboard(),
        )
        return

    data = await state.get_data()

    if message.text == data["from_city"]:

        await message.answer(
            "Qayerdan va qayerga bir xil bo‘lishi mumkin emas."
        )
        return

    await state.update_data(
        to_city=message.text
    )

    await state.set_state(
        DriverRideState.time
    )

    await message.answer(
        "🕐 Safar vaqti:",
        reply_markup=time_keyboard(),
    )


@dp.message(DriverRideState.time)
async def ride_time(
    message: Message,
    state: FSMContext,
):

    if message.text not in TIMES:

        await message.answer(
            "Vaqtni tanlang.",
            reply_markup=time_keyboard(),
        )
        return

    await state.update_data(
        time=message.text
    )

    await state.set_state(
        DriverRideState.seats
    )

    await message.answer(
        "👥 Nechta yo‘lovchi olasiz?",
        reply_markup=seats_keyboard(),
    )


@dp.message(DriverRideState.seats)
async def ride_seats(
    message: Message,
    state: FSMContext,
):

    if message.text not in {"1", "2", "3", "4"}:

        await message.answer(
            "1 dan 4 gacha tanlang.",
            reply_markup=seats_keyboard(),
        )
        return

    seats = int(message.text)

    driver = await get_driver(
        message.from_user.id
    )

    if not driver:
        await state.clear()
        await message.answer(
            "Haydovchi profili topilmadi."
        )
        return

    if seats > driver["seats"]:

        await message.answer(
            f"❗ Sizning mashinangizda maksimum "
            f"{driver['seats']} ta yo‘lovchi o‘rni bor."
        )
        return

    data = await state.get_data()

    ride_id = await create_driver_ride(
        driver_id=message.from_user.id,
        from_city=data["from_city"],
        to_city=data["to_city"],
        ride_time=data["time"],
        seats=seats,
    )

    await state.clear()

    await message.answer(
        "✅ <b>Safaringiz e’lon qilindi!</b>\n\n"
        f"📍 {esc(data['from_city'])} → "
        f"{esc(data['to_city'])}\n"
        f"🕐 {esc(data['time'])}\n"
        f"👥 O‘rinlar: {seats}",
        reply_markup=main_menu(),
    )

    await notify_searching_passengers_for_ride(
        ride_id
    )


async def create_driver_ride(
    driver_id,
    from_city,
    to_city,
    ride_time,
    seats,
):

    return await db_execute(
        """
        INSERT INTO rides(
            driver_id,
            from_city,
            to_city,
            ride_time,
            seats,
            available_seats,
            reserved_seats,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, 'active', ?)
        """,
        (
            driver_id,
            from_city,
            to_city,
            ride_time,
            seats,
            seats,
            now(),
        ),
    )


async def notify_searching_passengers_for_ride(
    ride_id
):

    ride = await db_execute(
        "SELECT * FROM rides WHERE id=?",
        (ride_id,),
        fetchone=True,
    )

    if not ride:
        return

    requests = await db_execute(
        """
        SELECT *
        FROM passenger_requests
        WHERE
            status='searching'
            AND from_city=?
            AND to_city=?
            AND ride_time=?
            AND seats<=?
        """,
        (
            ride["from_city"],
            ride["to_city"],
            ride["ride_time"],
            ride["available_seats"],
        ),
        fetch=True,
    )

    for request in requests:

        await safe_send(
            request["passenger_id"],
            "🚕 <b>MOS HAYDOVCHI TOPILDI!</b>\n\n"
            f"📍 {esc(ride['from_city'])} → "
            f"{esc(ride['to_city'])}\n"
            f"🕐 {esc(ride['ride_time'])}\n\n"
            "Haydovchi buyurtmangizni qabul qilishi kutilmoqda.",
        )


# =========================================================
# DRIVER ACCEPT
# =========================================================

@dp.callback_query(
    F.data.startswith("accept_request:")
)
async def accept_request(
    callback: CallbackQuery
):

    request_id = int(
        callback.data.split(":")[1]
    )

    driver_id = callback.from_user.id

    driver = await get_driver(driver_id)

    if not driver or driver["status"] != "approved":

        await callback.answer(
            "Haydovchi tasdiqlanmagan.",
            show_alert=True,
        )
        return

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        await db.execute("BEGIN IMMEDIATE")

        request = await db.execute(
            "SELECT * FROM passenger_requests WHERE id=?",
            (request_id,),
        )

        request = await request.fetchone()

        if not request:

            await db.rollback()

            await callback.answer(
                "Buyurtma topilmadi.",
                show_alert=True,
            )
            return

        if request["status"] != "searching":

            await db.rollback()

            await callback.answer(
                "Bu buyurtma allaqachon yopilgan.",
                show_alert=True,
            )
            return

        ride_cursor = await db.execute(
            """
            SELECT *
            FROM rides
            WHERE
                driver_id=?
                AND from_city=?
                AND to_city=?
                AND ride_time=?
                AND status='active'
                AND available_seats>=?
            LIMIT 1
            """,
            (
                driver_id,
                request["from_city"],
                request["to_city"],
                request["ride_time"],
                request["seats"],
            ),
        )

        ride = await ride_cursor.fetchone()

        if not ride:

            await db.rollback()

            await callback.answer(
                "Sizda mos safar yoki bo‘sh joy yo‘q.",
                show_alert=True,
            )
            return

        await db.execute(
            """
            UPDATE passenger_requests
            SET status='accepted'
            WHERE id=?
            """,
            (request_id,),
        )

        await db.execute(
            """
            UPDATE rides
            SET
                available_seats=available_seats-?,
                reserved_seats=reserved_seats+?
            WHERE id=?
            """,
            (
                request["seats"],
                request["seats"],
                ride["id"],
            ),
        )

        booking_id = await db.execute(
            """
            INSERT INTO bookings(
                request_id,
                ride_id,
                passenger_id,
                driver_id,
                seats,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, 'accepted', ?)
            """,
            (
                request_id,
                ride["id"],
                request["passenger_id"],
                driver_id,
                request["seats"],
                now(),
            ),
        )

        await db.commit()

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"👤 {esc(request['name'])}\n"
        f"📞 {esc(request['phone'])}\n"
        f"📍 {esc(request['from_city'])} → "
        f"{esc(request['to_city'])}\n"
        f"🕐 {esc(request['ride_time'])}\n\n"
        "Yo‘lovchi bilan bog‘laning.",
        reply_markup=booking_driver_keyboard(
            booking_id
        ),
    )

    await safe_send(
        request["passenger_id"],
        "🎉 <b>Haydovchi topildi!</b>\n\n"
        f"👤 {esc(driver['full_name'])}\n"
        f"🚘 {esc(driver['car_model'])}\n"
        f"🔢 {esc(driver['car_number'])}\n"
        f"📞 {esc(driver['phone'])}\n"
        f"⭐ Reyting: {driver['rating']}\n\n"
        "Haydovchi buyurtmangizni qabul qildi.",
        reply_markup=passenger_booking_keyboard(
            booking_id
        ),
    )

    await callback.answer(
        "Buyurtma qabul qilindi!"
    )


# =========================================================
# DRIVER REJECT
# =========================================================

@dp.callback_query(
    F.data.startswith("reject_request:")
)
async def reject_request(
    callback: CallbackQuery
):

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "❌ Buyurtma rad etildi."
    )

    await callback.answer()


# =========================================================
# PASSENGER CANCEL REQUEST
# =========================================================

@dp.callback_query(
    F.data.startswith("cancel_request:")
)
async def cancel_request(
    callback: CallbackQuery
):

    request_id = int(
        callback.data.split(":")[1]
    )

    request = await get_request(
        request_id
    )

    if not request:
        await callback.answer(
            "Buyurtma topilmadi.",
            show_alert=True,
        )
        return

    if request["passenger_id"] != callback.from_user.id:

        await callback.answer(
            "Bu buyurtma sizniki emas.",
            show_alert=True,
        )
        return

    await db_execute(
        """
        UPDATE passenger_requests
        SET status='cancelled'
        WHERE id=?
        """,
        (request_id,),
    )

    booking = await db_execute(
        """
        SELECT *
        FROM bookings
        WHERE request_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (request_id,),
        fetchone=True,
    )

    if booking:

        await db_execute(
            """
            UPDATE bookings
            SET status='cancelled'
            WHERE id=?
            """,
            (booking["id"],),
        )

        await db_execute(
            """
            UPDATE rides
            SET
                available_seats=available_seats+?,
                reserved_seats=
                    CASE
                        WHEN reserved_seats>=? THEN reserved_seats-?
                        ELSE 0
                    END
            WHERE id=?
            """,
            (
                booking["seats"],
                booking["seats"],
                booking["seats"],
                booking["ride_id"],
            ),
        )

        await safe_send(
            booking["driver_id"],
            "❌ Yo‘lovchi buyurtmani bekor qildi."
        )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "❌ Buyurtma bekor qilindi.",
        reply_markup=main_menu(),
    )

    await callback.answer()


# =========================================================
# DRIVER LOCATION
# =========================================================

@dp.callback_query(
    F.data.startswith("driver_location:")
)
async def driver_location_request(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    await callback.message.answer(
        "📍 Telegram orqali hozirgi lokatsiyangizni yuboring.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📍 Lokatsiyani yuborish",
                        request_location=True,
                    )
                ]
            ],
            resize_keyboard=True,
        ),
    )

    await callback.answer()


@dp.message(F.location)
async def general_location_handler(
    message: Message
):

    driver_id = message.from_user.id

    booking = await db_execute(
        """
        SELECT *
        FROM bookings
        WHERE
            driver_id=?
            AND status IN ('accepted', 'arrived', 'onboard')
        ORDER BY id DESC
        LIMIT 1
        """,
        (driver_id,),
        fetchone=True,
    )

    if not booking:

        await message.answer(
            "📍 Lokatsiya qabul qilindi."
        )
        return

    lat = message.location.latitude
    lon = message.location.longitude

    await db_execute(
        """
        UPDATE bookings
        SET
            driver_latitude=?,
            driver_longitude=?
        WHERE id=?
        """,
        (
            lat,
            lon,
            booking["id"],
        ),
    )

    await safe_send(
        booking["passenger_id"],
        "📍 <b>Haydovchi lokatsiyasini yangiladi.</b>",
    )

    try:

        await bot.send_location(
            booking["passenger_id"],
            latitude=lat,
            longitude=lon,
        )

    except Exception as e:
        print("send location error:", e)

    await message.answer(
        "✅ Lokatsiyangiz yo‘lovchiga yuborildi.",
        reply_markup=main_menu(),
    )


# =========================================================
# DRIVER STATUS
# =========================================================

@dp.callback_query(
    F.data.startswith("driver_arrived:")
)
async def driver_arrived(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Buyurtma topilmadi."
        )
        return

    await db_execute(
        """
        UPDATE bookings
        SET status='arrived'
        WHERE id=?
        """,
        (booking_id,),
    )

    await safe_send(
        booking["passenger_id"],
        "🚕 <b>Haydovchi yetib bordi!</b>"
    )

    await callback.answer(
        "Yo‘lovchiga xabar yuborildi."
    )


@dp.callback_query(
    F.data.startswith("driver_onboard:")
)
async def driver_onboard(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Buyurtma topilmadi."
        )
        return

    await db_execute(
        """
        UPDATE bookings
        SET status='onboard'
        WHERE id=?
        """,
        (booking_id,),
    )

    await safe_send(
        booking["passenger_id"],
        "👤 <b>Haydovchi sizni oldi.</b>\n"
        "🚕 Safar boshlandi."
    )

    await callback.answer(
        "Safar boshlandi."
    )


@dp.callback_query(
    F.data.startswith("driver_complete:")
)
async def driver_complete(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Buyurtma topilmadi."
        )
        return

    await db_execute(
        """
        UPDATE bookings
        SET status='completed'
        WHERE id=?
        """,
        (booking_id,),
    )

    await db_execute(
        """
        UPDATE driver_profiles
        SET trips=trips+1
        WHERE user_id=?
        """,
        (booking["driver_id"],),
    )

    await safe_send(
        booking["passenger_id"],
        "🏁 <b>Safar yakunlandi.</b>\n\n"
        "Rahmat! OPPER TAXI xizmatidan foydalanganingiz uchun."
    )

    await callback.answer(
        "Safar yakunlandi."
    )


@dp.callback_query(
    F.data.startswith("driver_cancel:")
)
async def driver_cancel(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Buyurtma topilmadi."
        )
        return

    await db_execute(
        """
        UPDATE bookings
        SET status='cancelled'
        WHERE id=?
        """,
        (booking_id,),
    )

    await db_execute(
        """
        UPDATE passenger_requests
        SET status='searching'
        WHERE id=?
        """,
        (booking["request_id"],),
    )

    await db_execute(
        """
        UPDATE rides
        SET
            available_seats=available_seats+?,
            reserved_seats=
                CASE
                    WHEN reserved_seats>=? THEN reserved_seats-?
                    ELSE 0
                END
        WHERE id=?
        """,
        (
            booking["seats"],
            booking["seats"],
            booking["seats"],
            booking["ride_id"],
        ),
    )

    await safe_send(
        booking["passenger_id"],
        "⚠️ Haydovchi safarni bekor qildi.\n\n"
        "Boshqa haydovchi qidirilmoqda."
    )

    await notify_matching_drivers(
        booking["request_id"]
    )

    await callback.message.answer(
        "❌ Safar bekor qilindi."
    )

    await callback.answer()


# =========================================================
# PASSENGER TRACK DRIVER
# =========================================================

@dp.callback_query(
    F.data.startswith("track_driver:")
)
async def track_driver(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Buyurtma topilmadi.",
            show_alert=True,
        )
        return

    if not booking["driver_latitude"]:

        await callback.answer(
            "Haydovchi hali lokatsiyasini yubormadi.",
            show_alert=True,
        )
        return

    try:

        await bot.send_location(
            callback.from_user.id,
            latitude=booking["driver_latitude"],
            longitude=booking["driver_longitude"],
        )

        await callback.answer(
            "📍 Haydovchi lokatsiyasi yuborildi."
        )

    except Exception:

        await callback.answer(
            "Lokatsiyani yuborishda xatolik.",
            show_alert=True,
        )


# =========================================================
# PASSENGER CANCEL BOOKING
# =========================================================

@dp.callback_query(
    F.data.startswith("passenger_cancel:")
)
async def passenger_cancel_booking(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:

        await callback.answer(
            "Buyurtma topilmadi.",
            show_alert=True,
        )
        return

    if booking["passenger_id"] != callback.from_user.id:

        await callback.answer(
            "Bu buyurtma sizniki emas.",
            show_alert=True,
        )
        return

    if booking["status"] == "completed":

        await callback.answer(
            "Safar allaqachon tugagan.",
            show_alert=True,
        )
        return

    await db_execute(
        """
        UPDATE bookings
        SET status='cancelled'
        WHERE id=?
        """,
        (booking_id,),
    )

    await db_execute(
        """
        UPDATE passenger_requests
        SET status='cancelled'
        WHERE id=?
        """,
        (booking["request_id"],),
    )

    await db_execute(
        """
        UPDATE rides
        SET
            available_seats=available_seats+?,
            reserved_seats=
                CASE
                    WHEN reserved_seats>=? THEN reserved_seats-?
                    ELSE 0
                END
        WHERE id=?
        """,
        (
            booking["seats"],
            booking["seats"],
            booking["seats"],
            booking["ride_id"],
        ),
    )

    await safe_send(
        booking["driver_id"],
        "❌ Yo‘lovchi safarni bekor qildi."
    )

    await callback.message.answer(
        "❌ Safar bekor qilindi.",
        reply_markup=main_menu(),
    )

    await callback.answer()


# =========================================================
# SEARCH RIDES
# =========================================================

@dp.message(F.text == "🔎 Taksilarni qidirish")
async def search_rides(
    message: Message
):

    rides = await db_execute(
        """
        SELECT
            r.*,
            d.full_name,
            d.phone,
            d.car_model,
            d.car_number,
            d.rating,
            d.trips
        FROM rides r
        JOIN driver_profiles d
            ON d.user_id=r.driver_id
        WHERE
            r.status='active'
            AND r.available_seats>0
            AND d.status='approved'
        ORDER BY r.id DESC
        LIMIT 30
        """,
        fetch=True,
    )

    if not rides:

        await message.answer(
            "🔎 Hozircha faol taksilar mavjud emas.",
            reply_markup=main_menu(),
        )
        return

    text = "🚕 <b>Faol taksilar:</b>\n\n"

    for ride in rides:

        text += (
            f"🚗 <b>{esc(ride['from_city'])} → "
            f"{esc(ride['to_city'])}</b>\n"
            f"🕐 {esc(ride['ride_time'])}\n"
            f"👤 {esc(ride['full_name'])}\n"
            f"🚘 {esc(ride['car_model'])}\n"
            f"🔢 {esc(ride['car_number'])}\n"
            f"⭐ {ride['rating']}\n"
            f"💺 Bo‘sh joy: {ride['available_seats']}\n\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# =========================================================
# MY BOOKINGS
# =========================================================

@dp.message(F.text == "📋 Buyurtmalarim")
async def my_bookings(
    message: Message
):

    user_id = message.from_user.id

    passenger_bookings = await db_execute(
        """
        SELECT
            b.*,
            r.from_city,
            r.to_city,
            r.ride_time,
            d.full_name AS driver_name,
            d.phone AS driver_phone,
            d.car_model,
            d.car_number
        FROM bookings b
        JOIN passenger_requests r
            ON r.id=b.request_id
        LEFT JOIN driver_profiles d
            ON d.user_id=b.driver_id
        WHERE b.passenger_id=?
        ORDER BY b.id DESC
        LIMIT 20
        """,
        (user_id,),
        fetch=True,
    )

    driver_bookings = await db_execute(
        """
        SELECT
            b.*,
            r.from_city,
            r.to_city,
            r.ride_time,
            r.name AS passenger_name,
            r.phone AS passenger_phone
        FROM bookings b
        JOIN passenger_requests r
            ON r.id=b.request_id
        WHERE b.driver_id=?
        ORDER BY b.id DESC
        LIMIT 20
        """,
        (user_id,),
        fetch=True,
    )

    text = "📋 <b>Buyurtmalarim</b>\n\n"

    if passenger_bookings:

        text += "<b>👤 Yo‘lovchi sifatida:</b>\n\n"

        for b in passenger_bookings:

            text += (
                f"#{b['id']} — "
                f"{esc(b['from_city'])} → "
                f"{esc(b['to_city'])}\n"
                f"🕐 {esc(b['ride_time'])}\n"
                f"📌 Holat: {esc(b['status'])}\n"
            )

            if b["driver_name"]:

                text += (
                    f"🚗 Haydovchi: "
                    f"{esc(b['driver_name'])}\n"
                )

            text += "\n"

    if driver_bookings:

        text += "<b>🚗 Haydovchi sifatida:</b>\n\n"

        for b in driver_bookings:

            text += (
                f"#{b['id']} — "
                f"{esc(b['from_city'])} → "
                f"{esc(b['to_city'])}\n"
                f"🕐 {esc(b['ride_time'])}\n"
                f"👤 {esc(b['passenger_name'])}\n"
                f"📞 {esc(b['passenger_phone'])}\n"
                f"📌 Holat: {esc(b['status'])}\n\n"
            )

    if not passenger_bookings and not driver_bookings:

        text += "Hozircha buyurtmalar yo‘q."

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# =========================================================
# PROFILE
# =========================================================

@dp.message(F.text == "👤 Profil")
async def profile(
    message: Message
):

    user_id = message.from_user.id

    user = await get_user(user_id)
    driver = await get_driver(user_id)

    text = "👤 <b>Profil</b>\n\n"

    if user:

        text += (
            f"👤 Ism: {esc(user['full_name'])}\n"
            f"📞 Telefon: {esc(user['phone'])}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
        )

    if driver:

        text += (
            "\n🚗 <b>Haydovchi profili</b>\n"
            f"👤 {esc(driver['full_name'])}\n"
            f"🚘 {esc(driver['car_model'])}\n"
            f"🔢 {esc(driver['car_number'])}\n"
            f"👥 O‘rin: {driver['seats']}\n"
            f"📌 Status: {esc(driver['status'])}\n"
            f"⭐ Reyting: {driver['rating']}\n"
            f"🏁 Safarlar: {driver['trips']}\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# =========================================================
# HELP
# =========================================================

@dp.message(F.text == "ℹ️ Yordam")
async def help_handler(
    message: Message
):

    await message.answer(
        "ℹ️ <b>OPPER TAXI yordam</b>\n\n"
        "🚕 <b>Taksi chaqirish</b> — yo‘lovchi sifatida buyurtma berish.\n\n"
        "🚗 <b>Haydovchi bo‘lish</b> — haydovchi sifatida ro‘yxatdan o‘tish.\n\n"
        "🔎 <b>Taksilarni qidirish</b> — faol safarlarni ko‘rish.\n\n"
        "📋 <b>Buyurtmalarim</b> — buyurtmalar tarixi.\n\n"
        "👤 <b>Profil</b> — shaxsiy ma’lumotlar.\n\n"
        "📱 <b>OPPER TAXI</b> — Mini App orqali tezkor foydalanish.",
        reply_markup=main_menu(),
    )


# =========================================================
# ADMIN
# =========================================================

@dp.message(Command("drivers"))
async def pending_drivers(
    message: Message
):

    if message.from_user.id not in ADMIN_IDS:
        return

    drivers = await db_execute(
        """
        SELECT *
        FROM driver_profiles
        WHERE status='pending'
        ORDER BY created_at DESC
        """,
        fetch=True,
    )

    if not drivers:

        await message.answer(
            "⏳ Kutilayotgan haydovchi arizalari yo‘q."
        )
        return

    for driver in drivers:

        text = (
            "🚗 <b>Haydovchi arizasi</b>\n\n"
            f"👤 {esc(driver['full_name'])}\n"
            f"📞 {esc(driver['phone'])}\n"
            f"🚘 {esc(driver['car_model'])}\n"
            f"🔢 {esc(driver['car_number'])}\n"
            f"👥 O‘rin: {driver['seats']}\n"
            f"🆔 <code>{driver['user_id']}</code>"
        )

        await message.answer(
            text,
            reply_markup=admin_driver_keyboard(
                driver["user_id"]
            ),
        )


@dp.message(Command("admin"))
async def admin_panel(
    message: Message
):

    if message.from_user.id not in ADMIN_IDS:
        return

    users = await db_execute(
        "SELECT COUNT(*) AS c FROM users",
        fetchone=True,
    )

    drivers = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM driver_profiles
        WHERE status='approved'
        """,
        fetchone=True,
    )

    pending = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM driver_profiles
        WHERE status='pending'
        """,
        fetchone=True,
    )

    rides = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM rides
        WHERE status='active'
        """,
        fetchone=True,
    )

    requests = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM passenger_requests
        WHERE status='searching'
        """,
        fetchone=True,
    )

    await message.answer(
        "👑 <b>OPPER TAXI ADMIN</b>\n\n"
        f"👤 Foydalanuvchilar: {users['c']}\n"
        f"🚗 Tasdiqlangan haydovchilar: {drivers['c']}\n"
        f"⏳ Kutilayotgan haydovchilar: {pending['c']}\n"
        f"🚕 Faol safarlar: {rides['c']}\n"
        f"🔎 Qidirilayotgan buyurtmalar: {requests['c']}"
    )


@dp.callback_query(
    F.data.startswith("admin_approve:")
)
async def admin_approve(
    callback: CallbackQuery
):

    if callback.from_user.id not in ADMIN_IDS:

        await callback.answer(
            "Ruxsat yo‘q.",
            show_alert=True,
        )
        return

    user_id = int(
        callback.data.split(":")[1]
    )

    driver = await get_driver(user_id)

    if not driver:

        await callback.answer(
            "Haydovchi topilmadi.",
            show_alert=True,
        )
        return

    await db_execute(
        """
        UPDATE driver_profiles
        SET status='approved'
        WHERE user_id=?
        """,
        (user_id,),
    )

    await safe_send(
        user_id,
        "🎉 <b>Tabriklaymiz!</b>\n\n"
        "Sizning OPPER TAXI haydovchi arizangiz tasdiqlandi.\n\n"
        "Endi safarlaringizni e’lon qilishingiz mumkin."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        f"✅ {esc(driver['full_name'])} tasdiqlandi."
    )

    await callback.answer(
        "Tasdiqlandi."
    )


@dp.callback_query(
    F.data.startswith("admin_reject:")
)
async def admin_reject(
    callback: CallbackQuery
):

    if callback.from_user.id not in ADMIN_IDS:

        await callback.answer(
            "Ruxsat yo‘q.",
            show_alert=True,
        )
        return

    user_id = int(
        callback.data.split(":")[1]
    )

    driver = await get_driver(user_id)

    await db_execute(
        """
        UPDATE driver_profiles
        SET status='rejected'
        WHERE user_id=?
        """,
        (user_id,),
    )

    await safe_send(
        user_id,
        "❌ OPPER TAXI haydovchi arizangiz "
        "hozircha tasdiqlanmadi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    if driver:

        await callback.message.answer(
            f"❌ {esc(driver['full_name'])} rad etildi."
        )

    await callback.answer(
        "Rad etildi."
    )


# =========================================================
# MINI APP SECURITY
# =========================================================

def validate_telegram_webapp(init_data: str):

    if not init_data:
        return None

    try:

        parsed = dict(
            parse_qsl(
                init_data,
                keep_blank_values=True,
            )
        )

        received_hash = parsed.pop(
            "hash",
            None,
        )

        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value
            in sorted(parsed.items())
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

        auth_date = int(
            parsed.get("auth_date", "0")
        )

        # 24 soatlik xavfsizlik
        if abs(time.time() - auth_date) > 86400:
            return None

        user = json.loads(
            parsed.get("user", "{}")
        )

        if not user.get("id"):
            return None

        return user

    except Exception as e:

        print(
            "Mini App validation error:",
            e,
        )

        return None


async def web_user(request):

    try:
        data = await request.json()
    except Exception:

        raise web.HTTPBadRequest(
            text=json.dumps({
                "error": "JSON noto‘g‘ri"
            }),
            content_type="application/json",
        )

    init_data = data.get(
        "init_data",
        "",
    )

    user = validate_telegram_webapp(
        init_data
    )

    if not user:

        raise web.HTTPUnauthorized(
            text=json.dumps({
                "error":
                "Telegram autentifikatsiyasi noto‘g‘ri"
            }),
            content_type="application/json",
        )

    return data, user


def json_response(data, status=200):

    return web.Response(
        status=status,
        text=json.dumps(
            data,
            ensure_ascii=False,
        ),
        content_type="application/json",
    )


# =========================================================
# MINI APP HOME
# =========================================================

async def web_index(request):

    if not INDEX_FILE.exists():

        return web.Response(
            status=500,
            text="web/index.html topilmadi",
        )

    return web.FileResponse(
        INDEX_FILE
    )


# =========================================================
# MINI APP - PASSENGER ORDER
# =========================================================

async def web_passenger_order(request):

    try:

        data, user = await web_user(request)

        from_city = str(
            data.get("from_city", "")
        ).strip()

        to_city = str(
            data.get("to_city", "")
        ).strip()

        ride_time = str(
            data.get("time", "")
        ).strip()

        seats = int(
            data.get("seats", 1)
        )

        name = str(
            data.get("name")
            or user.get("first_name")
            or ""
        ).strip()

        phone = str(
            data.get("phone", "")
        ).strip()

        latitude = data.get(
            "latitude"
        )

        longitude = data.get(
            "longitude"
        )

        if from_city not in CITIES:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Qayerdan shahri noto‘g‘ri"
                },
                400,
            )

        if to_city not in CITIES:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Qayerga shahri noto‘g‘ri"
                },
                400,
            )

        if from_city == to_city:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Shaharlar bir xil bo‘lishi mumkin emas"
                },
                400,
            )

        if ride_time not in TIMES:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Vaqt noto‘g‘ri"
                },
                400,
            )

        if seats < 1 or seats > 4:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Yo‘lovchilar soni 1-4 bo‘lishi kerak"
                },
                400,
            )

        request_id = await create_passenger_request(
            user_id=user["id"],
            from_city=from_city,
            to_city=to_city,
            ride_time=ride_time,
            seats=seats,
            name=name,
            phone=phone,
            latitude=latitude,
            longitude=longitude,
        )

        count = await notify_matching_drivers(
            request_id
        )

        return json_response(
            {
                "ok": True,
                "request_id": request_id,
                "drivers_notified": count,
                "message":
                    "Buyurtma yaratildi",
            }
        )

    except web.HTTPException:
        raise

    except Exception as e:

        print(
            "web_passenger_order:",
            e,
        )

        return json_response(
            {
                "ok": False,
                "error":
                "Server xatosi"
            },
            500,
        )


# =========================================================
# MINI APP - DRIVER REGISTER
# =========================================================

async def web_driver_register(request):

    try:

        data, user = await web_user(request)

        user_id = user["id"]

        full_name = str(
            data.get("full_name")
            or user.get("first_name")
            or ""
        ).strip()

        last_name = str(
            user.get("last_name")
            or ""
        ).strip()

        if last_name and last_name not in full_name:

            full_name = (
                f"{full_name} {last_name}"
            ).strip()

        phone = str(
            data.get("phone", "")
        ).strip()

        car_model = str(
            data.get("car_model", "")
        ).strip()

        car_number = str(
            data.get("car_number", "")
        ).strip()

        seats = int(
            data.get("seats", 4)
        )

        if not full_name:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Ism kerak"
                },
                400,
            )

        if not phone:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Telefon kerak"
                },
                400,
            )

        if not car_model:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Mashina modeli kerak"
                },
                400,
            )

        if not car_number:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Mashina raqami kerak"
                },
                400,
            )

        if seats < 1 or seats > 8:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "O‘rinlar 1-8 oralig‘ida"
                },
                400,
            )

        await save_user(
            user_id=user_id,
            full_name=full_name,
            username=user.get(
                "username",
                "",
            ),
            phone=phone,
        )

        old_driver = await get_driver(
            user_id
        )

        await ensure_driver_profile(
            user_id=user_id,
            full_name=full_name,
            phone=phone,
            car_model=car_model,
            car_number=car_number,
            seats=seats,
        )

        # Adminlarga faqat yangi yoki rejected profil qayta yuboriladi
        if (
            not old_driver
            or old_driver["status"] == "rejected"
        ):

            text = (
                "🚗 <b>MINI APP — YANGI HAYDOVCHI</b>\n\n"
                f"👤 {esc(full_name)}\n"
                f"📞 {esc(phone)}\n"
                f"🚘 {esc(car_model)}\n"
                f"🔢 {esc(car_number)}\n"
                f"👥 O‘rin: {seats}\n"
                f"🆔 <code>{user_id}</code>"
            )

            await notify_admins(
                text,
                reply_markup=admin_driver_keyboard(
                    user_id
                ),
            )

        return json_response(
            {
                "ok": True,
                "status": "pending",
                "message":
                    "Ariza yuborildi",
            }
        )

    except web.HTTPException:
        raise

    except Exception as e:

        print(
            "web_driver_register:",
            e,
        )

        return json_response(
            {
                "ok": False,
                "error":
                "Server xatosi"
            },
            500,
        )


# =========================================================
# MINI APP - DRIVER RIDE
# =========================================================

async def web_driver_ride(request):

    try:

        data, user = await web_user(request)

        user_id = user["id"]

        driver = await get_driver(
            user_id
        )

        if not driver:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Haydovchi profili topilmadi"
                },
                403,
            )

        if driver["status"] != "approved":

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Haydovchi hali admin tomonidan tasdiqlanmagan"
                },
                403,
            )

        from_city = str(
            data.get("from_city", "")
        ).strip()

        to_city = str(
            data.get("to_city", "")
        ).strip()

        ride_time = str(
            data.get("time", "")
        ).strip()

        seats = int(
            data.get("seats", 1)
        )

        if from_city not in CITIES:
            return json_response(
                {
                    "ok": False,
                    "error":
                    "Qayerdan noto‘g‘ri"
                },
                400,
            )

        if to_city not in CITIES:
            return json_response(
                {
                    "ok": False,
                    "error":
                    "Qayerga noto‘g‘ri"
                },
                400,
            )

        if from_city == to_city:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Shaharlar bir xil bo‘lishi mumkin emas"
                },
                400,
            )

        if ride_time not in TIMES:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Vaqt noto‘g‘ri"
                },
                400,
            )

        if seats < 1 or seats > driver["seats"]:

            return json_response(
                {
                    "ok": False,
                    "error":
                    f"Sizning mashinangizda maksimum "
                    f"{driver['seats']} ta o‘rin bor"
                },
                400,
            )

        ride_id = await create_driver_ride(
            driver_id=user_id,
            from_city=from_city,
            to_city=to_city,
            ride_time=ride_time,
            seats=seats,
        )

        await notify_searching_passengers_for_ride(
            ride_id
        )

        return json_response(
            {
                "ok": True,
                "ride_id": ride_id,
                "message":
                    "Safar e’lon qilindi",
            }
        )

    except web.HTTPException:
        raise

    except Exception as e:

        print(
            "web_driver_ride:",
            e,
        )

        return json_response(
            {
                "ok": False,
                "error":
                "Server xatosi"
            },
            500,
        )


# =========================================================
# MINI APP - ORDERS
# =========================================================

async def web_orders(request):

    try:

        data, user = await web_user(request)

        user_id = user["id"]

        passenger = await db_execute(
            """
            SELECT
                b.id,
                b.status,
                b.seats,
                r.from_city,
                r.to_city,
                r.ride_time,
                d.full_name AS driver_name,
                d.phone AS driver_phone,
                d.car_model,
                d.car_number
            FROM bookings b
            JOIN passenger_requests r
                ON r.id=b.request_id
            LEFT JOIN driver_profiles d
                ON d.user_id=b.driver_id
            WHERE b.passenger_id=?
            ORDER BY b.id DESC
            LIMIT 30
            """,
            (user_id,),
            fetch=True,
        )

        driver = await db_execute(
            """
            SELECT
                b.id,
                b.status,
                b.seats,
                r.from_city,
                r.to_city,
                r.ride_time,
                r.name AS passenger_name,
                r.phone AS passenger_phone
            FROM bookings b
            JOIN passenger_requests r
                ON r.id=b.request_id
            WHERE b.driver_id=?
            ORDER BY b.id DESC
            LIMIT 30
            """,
            (user_id,),
            fetch=True,
        )

        return json_response(
            {
                "ok": True,
                "passenger_orders": [
                    dict(x)
                    for x in passenger
                ],
                "driver_orders": [
                    dict(x)
                    for x in driver
                ],
            }
        )

    except web.HTTPException:
        raise

    except Exception as e:

        print(
            "web_orders:",
            e,
        )

        return json_response(
            {
                "ok": False,
                "error":
                "Server xatosi"
            },
            500,
        )


# =========================================================
# MINI APP - PROFILE
# =========================================================

async def web_profile(request):

    try:

        data, user = await web_user(request)

        user_id = user["id"]

        db_user = await get_user(
            user_id
        )

        driver = await get_driver(
            user_id
        )

        return json_response(
            {
                "ok": True,
                "user": dict(db_user)
                if db_user
                else {
                    "user_id": user_id,
                    "full_name":
                        user.get(
                            "first_name",
                            "",
                        ),
                    "username":
                        user.get(
                            "username",
                            "",
                        ),
                    "phone": "",
                },
                "driver":
                    dict(driver)
                    if driver
                    else None,
            }
        )

    except web.HTTPException:
        raise

    except Exception as e:

        print(
            "web_profile:",
            e,
        )

        return json_response(
            {
                "ok": False,
                "error":
                "Server xatosi"
            },
            500,
        )


# =========================================================
# MINI APP - PROFILE UPDATE
# =========================================================

async def web_profile_update(request):

    try:

        data, user = await web_user(request)

        user_id = user["id"]

        full_name = str(
            data.get("full_name", "")
        ).strip()

        phone = str(
            data.get("phone", "")
        ).strip()

        await save_user(
            user_id=user_id,
            full_name=full_name,
            username=user.get(
                "username",
                "",
            ),
            phone=phone,
        )

        return json_response(
            {
                "ok": True,
                "message":
                    "Profil yangilandi",
            }
        )

    except web.HTTPException:
        raise

    except Exception as e:

        print(
            "web_profile_update:",
            e,
        )

        return json_response(
            {
                "ok": False,
                "error":
                "Server xatosi"
            },
            500,
        )


# =========================================================
# MINI APP - ACTIVE RIDES
# =========================================================

async def web_rides(request):

    try:

        await web_user(request)

        rides = await db_execute(
            """
            SELECT
                r.*,
                d.full_name,
                d.phone,
                d.car_model,
                d.car_number,
                d.rating,
                d.trips
            FROM rides r
            JOIN driver_profiles d
                ON d.user_id=r.driver_id
            WHERE
                r.status='active'
                AND r.available_seats>0
                AND d.status='approved'
            ORDER BY r.id DESC
            LIMIT 100
            """,
            fetch=True,
        )

        return json_response(
            {
                "ok": True,
                "rides": [
                    dict(x)
                    for x in rides
                ],
            }
        )

    except web.HTTPException:
        raise

    except Exception as e:

        print(
            "web_rides:",
            e,
        )

        return json_response(
            {
                "ok": False,
                "error":
                "Server xatosi"
            },
            500,
        )


# =========================================================
# MINI APP - CANCEL REQUEST
# =========================================================

async def web_cancel_order(request):

    try:

        data, user = await web_user(request)

        request_id = int(
            data.get("request_id")
        )

        passenger_request = await get_request(
            request_id
        )

        if not passenger_request:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Buyurtma topilmadi"
                },
                404,
            )

        if passenger_request["passenger_id"] != user["id"]:

            return json_response(
                {
                    "ok": False,
                    "error":
                    "Ruxsat yo‘q"
                },
                403,
            )

        booking = await db_execute(
            """
            SELECT *
            FROM bookings
            WHERE request_id=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (request_id,),
            fetchone=True,
        )

        await db_execute(
            """
            UPDATE passenger_requests
            SET status='cancelled'
            WHERE id=?
            """,
            (request_id,),
        )

        if booking:

            await db_execute(
                """
                UPDATE bookings
                SET status='cancelled'
                WHERE id=?
                """,
                (booking["id"],),
            )

            await db_execute(
                """
                UPDATE rides
                SET
                    available_seats=available_seats+?,
                    reserved_seats=
                        CASE
                            WHEN reserved_seats>=? THEN reserved_seats-?
                            ELSE 0
                        END
                WHERE id=?
                """,
                (
                    booking["seats"],
                    booking["seats"],
                    booking["seats"],
                    booking["ride_id"],
                ),
            )

            await safe_send(
                booking["driver_id"],
                "❌ Yo‘lovchi buyurtmani bekor qildi."
            )

        return json_response(
            {
                "ok": True,
                "message":
                    "Buyurtma bekor qilindi",
            }
        )

    except web.HTTPException:
        raise

    except Exception as e:

        print(
            "web_cancel_order:",
            e,
        )

        return json_response(
            {
                "ok": False,
                "error":
                "Server xatosi"
            },
            500,
        )


# =========================================================
# HEALTH
# =========================================================

async def health_handler(
    request
):

    return web.Response(
        text="OPPER TAXI BOT OK"
    )


# =========================================================
# WEB SERVER
# =========================================================

async def start_web_server():

    app = web.Application()

    # Frontend
    app.router.add_get(
        "/",
        web_index,
    )

    app.router.add_get(
        "/app",
        web_index,
    )

    # Health
    app.router.add_get(
        "/health",
        health_handler,
    )

    # Mini App API
    app.router.add_post(
        "/api/passenger/order",
        web_passenger_order,
    )

    app.router.add_post(
        "/api/driver/register",
        web_driver_register,
    )

    app.router.add_post(
        "/api/driver/ride",
        web_driver_ride,
    )

    app.router.add_post(
        "/api/orders",
        web_orders,
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
        "/api/rides",
        web_rides,
    )

    app.router.add_post(
        "/api/order/cancel",
        web_cancel_order,
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    print(
        f"🌐 WEB SERVER RUNNING: {PORT}"
    )

    if MINI_APP_URL:

        print(
            f"📱 MINI APP: {MINI_APP_URL}"
        )

    else:

        print(
            "⚠️ MINI_APP_URL belgilanmagan"
        )


# =========================================================
# BOT MENU BUTTON
# =========================================================

async def setup_bot_menu():

    if not MINI_APP_URL:
        print(
            "⚠️ MINI_APP_URL yo‘q. "
            "Telegram Mini App tugmasi o‘rnatilmadi."
        )
        return

    try:

        from aiogram.types import MenuButtonWebApp

        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="OPPER TAXI",
                web_app=WebAppInfo(
                    url=MINI_APP_URL
                ),
            )
        )

        print(
            "✅ Telegram Mini App menu button o‘rnatildi."
        )

    except Exception as e:

        print(
            "Menu button error:",
            e,
        )


# =========================================================
# FALLBACK
# =========================================================

@dp.message()
async def fallback(
    message: Message
):

    await save_user_from_message(
        message
    )

    await message.answer(
        "🚕 <b>OPPER TAXI</b>\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=main_menu(),
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    print(
        "🚕 OPPER TAXI BOT STARTING..."
    )

    await init_db()

    print(
        "✅ DATABASE READY"
    )

    await start_web_server()

    await setup_bot_menu()

    print(
        "🤖 BOT POLLING STARTED"
    )

    await dp.start_polling(
        bot,
        allowed_updates=
            dp.resolve_used_update_types(),
    )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "BOT STOPPED"
        )
