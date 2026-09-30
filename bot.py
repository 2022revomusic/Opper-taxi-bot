import os
import re
import html
import asyncio
from datetime import datetime

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
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv(
        "ADMIN_IDS",
        "653914246"
    ).split(",")
    if x.strip().isdigit()
}

DB_PATH = "oper_taxi.db"

BOT_USERNAME = "@Oppertaxibot"

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
# BOT
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# HELPERS
# =========================================================

def now():
    return datetime.now().isoformat(timespec="seconds")


def esc(value):
    return html.escape(str(value or "-"))


def normalize_phone(value):
    if not value:
        return None

    digits = re.sub(r"\D", "", str(value))

    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits

    if len(digits) == 9:
        return "+998" + digits

    if digits.startswith("8") and len(digits) == 10:
        return "+998" + digits[1:]

    return None


def normalize_text(text):
    if not text:
        return ""

    text = text.lower()

    text = (
        text
        .replace("’", "'")
        .replace("‘", "'")
        .replace("ʻ", "'")
        .replace("`", "'")
        .replace("ʼ", "'")
    )

    # Apostroflarni olib tashlaymiz:
    text = re.sub(r"[']", "", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


async def db_execute(
    query,
    params=(),
    fetchone=False,
    fetchall=False,
):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(query, params)

        if fetchone:
            result = await cursor.fetchone()
        elif fetchall:
            result = await cursor.fetchall()
        else:
            result = cursor.lastrowid

        await db.commit()
        return result


async def db_transaction(callback):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        await db.execute("BEGIN IMMEDIATE")

        try:
            result = await callback(db)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise


async def ensure_column(table, column, definition):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()

        columns = {row[1] for row in rows}

        if column not in columns:
            await db.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

        await db.commit()


async def safe_send(user_id, text, reply_markup=None):
    try:
        await bot.send_message(
            user_id,
            text,
            reply_markup=reply_markup,
        )
        return True
    except Exception:
        return False


async def save_user(message: Message):
    if not message.from_user:
        return

    await db_execute(
        """
        INSERT INTO users (
            user_id,
            full_name,
            username,
            created_at
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            full_name=excluded.full_name,
            username=excluded.username
        """,
        (
            message.from_user.id,
            message.from_user.full_name,
            message.from_user.username,
            now(),
        ),
    )


async def get_driver(user_id):
    return await db_execute(
        """
        SELECT *
        FROM driver_profiles
        WHERE user_id=?
        """,
        (user_id,),
        fetchone=True,
    )


async def get_request(request_id):
    return await db_execute(
        """
        SELECT *
        FROM passenger_requests
        WHERE id=?
        """,
        (request_id,),
        fetchone=True,
    )


async def get_ride(ride_id):
    return await db_execute(
        """
        SELECT *
        FROM rides
        WHERE id=?
        """,
        (ride_id,),
        fetchone=True,
    )


async def get_booking(booking_id):
    return await db_execute(
        """
        SELECT *
        FROM bookings
        WHERE id=?
        """,
        (booking_id,),
        fetchone=True,
    )


# =========================================================
# DATABASE
# =========================================================

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
                source_chat_id INTEGER,
                source_message_id INTEGER,
                source_text TEXT,
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
                source_chat_id INTEGER,
                source_message_id INTEGER,
                source_text TEXT,
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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_messages (
                chat_id INTEGER,
                message_id INTEGER,
                message_text TEXT,
                processed_type TEXT,
                created_at TEXT,
                PRIMARY KEY(chat_id, message_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)

        await db.commit()

    # Eski DB uchun migration
    await ensure_column(
        "rides",
        "source_chat_id",
        "INTEGER"
    )

    await ensure_column(
        "rides",
        "source_message_id",
        "INTEGER"
    )

    await ensure_column(
        "rides",
        "source_text",
        "TEXT"
    )

    await ensure_column(
        "passenger_requests",
        "source_chat_id",
        "INTEGER"
    )

    await ensure_column(
        "passenger_requests",
        "source_message_id",
        "INTEGER"
    )

    await ensure_column(
        "passenger_requests",
        "source_text",
        "TEXT"
    )


# =========================================================
# KEYBOARDS
# =========================================================

def main_menu():

    return ReplyKeyboardMarkup(
        keyboard=[
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
        ],
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


def phone_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Telefon raqamimni yuborish",
                    request_contact=True,
                )
            ],
            [
                KeyboardButton(text="❌ Bekor qilish")
            ],
        ],
        resize_keyboard=True,
    )


def city_keyboard():

    buttons = []

    row = []

    for city in CITIES:
        row.append(
            KeyboardButton(text=city)
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        KeyboardButton(text="❌ Bekor qilish")
    ])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )


def time_keyboard():

    buttons = []

    row = []

    for time in TIMES:
        row.append(
            KeyboardButton(text=time)
        )

        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        KeyboardButton(text="❌ Bekor qilish")
    ])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )


def passenger_count_keyboard():

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


def driver_count_keyboard():

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
                    text="📍 Joylashuvimni yuborish",
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


def driver_request_keyboard(request_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ QABUL QILISH",
                    callback_data=f"accept_request:{request_id}",
                ),
                InlineKeyboardButton(
                    text="❌ RAD ETISH",
                    callback_data=f"reject_request:{request_id}",
                ),
            ]
        ]
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


def group_request_keyboard(request_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Buyurtmani bekor qilish",
                    callback_data=f"group_cancel:{request_id}",
                )
            ]
        ]
    )


def passenger_book_ride_keyboard(request_id, ride_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚕 SHU TAKSINI TANLASH",
                    callback_data=f"book_ride:{request_id}:{ride_id}",
                )
            ]
        ]
    )


def booking_driver_keyboard(booking_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 Men yetib keldim",
                    callback_data=f"driver_arrived:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Yo‘lovchi oldim",
                    callback_data=f"driver_onboard:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏁 Safarni tugatdim",
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
                    text="❌ Buyurtmani bekor qilish",
                    callback_data=f"passenger_cancel_booking:{booking_id}",
                )
            ]
        ]
    )


def rating_keyboard(booking_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ 1",
                    callback_data=f"rate:{booking_id}:1",
                ),
                InlineKeyboardButton(
                    text="⭐ 2",
                    callback_data=f"rate:{booking_id}:2",
                ),
                InlineKeyboardButton(
                    text="⭐ 3",
                    callback_data=f"rate:{booking_id}:3",
                ),
                InlineKeyboardButton(
                    text="⭐ 4",
                    callback_data=f"rate:{booking_id}:4",
                ),
                InlineKeyboardButton(
                    text="⭐ 5",
                    callback_data=f"rate:{booking_id}:5",
                ),
            ]
        ]
    )


def admin_driver_keyboard(user_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ TASDIQLASH",
                    callback_data=f"admin_approve:{user_id}",
                ),
                InlineKeyboardButton(
                    text="❌ RAD ETISH",
                    callback_data=f"admin_reject:{user_id}",
                ),
            ]
        ]
    )


# =========================================================
# FSM
# =========================================================

class PassengerState(StatesGroup):
    from_city = State()
    to_city = State()
    time = State()
    seats = State()
    name = State()
    phone = State()
    location = State()


class DriverRegisterState(StatesGroup):
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
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    await state.clear()
    await save_user(message)

    await message.answer(
        "🚕 <b>OPPERTAXI</b>\n\n"
        "Assalomu alaykum!\n"
        "Toshkent, Namangan, Andijon, Farg‘ona, "
        "Qo‘qon va Marg‘ilon yo‘nalishlarida "
        "yo‘lovchi va haydovchilarni bog‘laymiz.\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=main_menu(),
    )


# =========================================================
# CANCEL ALL
# =========================================================

@dp.message(F.text == "❌ Bekor qilish")
async def global_cancel(message: Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "❌ Amal bekor qilindi.",
        reply_markup=main_menu(),
    )


# =========================================================
# PASSENGER - START
# =========================================================

@dp.message(F.text == "🚕 Taksi chaqirish")
async def passenger_start(message: Message, state: FSMContext):

    await state.clear()
    await save_user(message)

    await state.set_state(
        PassengerState.from_city
    )

    await message.answer(
        "📍 <b>Qayerdan yo‘lga chiqasiz?</b>",
        reply_markup=city_keyboard(),
    )


@dp.message(PassengerState.from_city)
async def passenger_from_city(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:
        await message.answer(
            "Iltimos, ro‘yxatdan shahar tanlang.",
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
async def passenger_to_city(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:
        await message.answer(
            "Iltimos, ro‘yxatdan shahar tanlang.",
            reply_markup=city_keyboard(),
        )
        return

    data = await state.get_data()

    if message.text == data.get("from_city"):
        await message.answer(
            "❗ Ketish va borish shahri bir xil bo‘lishi mumkin emas."
        )
        return

    await state.update_data(
        to_city=message.text
    )

    await state.set_state(
        PassengerState.time
    )

    await message.answer(
        "⏰ <b>Qaysi vaqtda ketasiz?</b>",
        reply_markup=time_keyboard(),
    )


@dp.message(PassengerState.time)
async def passenger_time(
    message: Message,
    state: FSMContext
):

    if message.text not in TIMES:
        await message.answer(
            "Iltimos, vaqtni ro‘yxatdan tanlang.",
            reply_markup=time_keyboard(),
        )
        return

    await state.update_data(
        ride_time=message.text
    )

    await state.set_state(
        PassengerState.seats
    )

    await message.answer(
        "👥 <b>Necha kishi bor?</b>",
        reply_markup=passenger_count_keyboard(),
    )


@dp.message(PassengerState.seats)
async def passenger_seats(
    message: Message,
    state: FSMContext
):

    if not message.text or not message.text.isdigit():
        await message.answer(
            "1 dan 4 gacha son tanlang.",
            reply_markup=passenger_count_keyboard(),
        )
        return

    seats = int(message.text)

    if seats < 1 or seats > PASSENGER_LIMIT:
        await message.answer(
            "Yo‘lovchilar soni 1–4 oralig‘ida bo‘lishi kerak.",
            reply_markup=passenger_count_keyboard(),
        )
        return

    await state.update_data(
        seats=seats
    )

    await state.set_state(
        PassengerState.name
    )

    await message.answer(
        "👤 <b>Ismingiz va familiyangizni yozing:</b>",
        reply_markup=cancel_keyboard(),
    )


@dp.message(PassengerState.name)
async def passenger_name(
    message: Message,
    state: FSMContext
):

    name = (message.text or "").strip()

    if len(name) < 2:
        await message.answer(
            "Iltimos, ism va familiyangizni kiriting."
        )
        return

    await state.update_data(
        name=name
    )

    await state.set_state(
        PassengerState.phone
    )

    await message.answer(
        "📞 <b>Telefon raqamingizni yuboring:</b>",
        reply_markup=phone_keyboard(),
    )


@dp.message(PassengerState.phone, F.contact)
async def passenger_phone_contact(
    message: Message,
    state: FSMContext
):

    if (
        message.contact
        and message.contact.user_id
        and message.contact.user_id != message.from_user.id
    ):
        await message.answer(
            "❗ Iltimos, o‘zingizning telefon raqamingizni yuboring."
        )
        return

    phone = normalize_phone(
        message.contact.phone_number
    )

    if not phone:
        await message.answer(
            "Telefon raqamini aniqlab bo‘lmadi."
        )
        return

    await state.update_data(
        phone=phone
    )

    await state.set_state(
        PassengerState.location
    )

    await message.answer(
        "📍 <b>Joylashuvingizni yuborasizmi?</b>\n\n"
        "Bu haydovchiga sizni topishda yordam beradi.",
        reply_markup=location_keyboard(),
    )


@dp.message(PassengerState.phone)
async def passenger_phone_text(
    message: Message,
    state: FSMContext
):

    phone = normalize_phone(message.text)

    if not phone:
        await message.answer(
            "❗ Telefon raqamini to‘g‘ri kiriting.\n"
            "Masalan: +998901234567",
            reply_markup=phone_keyboard(),
        )
        return

    await state.update_data(
        phone=phone
    )

    await state.set_state(
        PassengerState.location
    )

    await message.answer(
        "📍 <b>Joylashuvingizni yuborasizmi?</b>",
        reply_markup=location_keyboard(),
    )


async def create_passenger_request(
    user_id,
    data,
    latitude=None,
    longitude=None,
    source_chat_id=None,
    source_message_id=None,
    source_text=None,
):

    request_id = await db_execute(
        """
        INSERT INTO passenger_requests (
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
            source_chat_id,
            source_message_id,
            source_text,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'searching', ?, ?, ?, ?)
        """,
        (
            user_id,
            data["from_city"],
            data["to_city"],
            data["ride_time"],
            data["seats"],
            data["name"],
            data["phone"],
            latitude,
            longitude,
            source_chat_id,
            source_message_id,
            source_text,
            now(),
        ),
    )

    return request_id


@dp.message(PassengerState.location, F.location)
async def passenger_location(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    request_id = await create_passenger_request(
        message.from_user.id,
        data,
        latitude=message.location.latitude,
        longitude=message.location.longitude,
    )

    await state.clear()

    await db_execute(
        """
        UPDATE users
        SET phone=?
        WHERE user_id=?
        """,
        (
            data["phone"],
            message.from_user.id,
        ),
    )

    await message.answer(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"📍 {esc(data['from_city'])} → {esc(data['to_city'])}\n"
        f"⏰ {esc(data['ride_time'])}\n"
        f"👥 {data['seats']} kishi\n"
        f"👤 {esc(data['name'])}\n\n"
        f"🚕 Mos haydovchilar qidirilmoqda...",
        reply_markup=passenger_cancel_keyboard(request_id),
    )

    count = await notify_matching_drivers(request_id)

    if count:
        await message.answer(
            f"🚕 {count} ta mos haydovchiga buyurtma yuborildi.",
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            "⏳ Hozircha mos tasdiqlangan haydovchi topilmadi.\n"
            "Buyurtmangiz qidiruvda qoladi.",
            reply_markup=main_menu(),
        )


@dp.message(PassengerState.location)
async def passenger_location_skip(
    message: Message,
    state: FSMContext
):

    if message.text != "⏭ O‘tkazib yuborish":
        await message.answer(
            "📍 Joylashuvni yuboring yoki "
            "⏭ O‘tkazib yuborish tugmasini bosing.",
            reply_markup=location_keyboard(),
        )
        return

    data = await state.get_data()

    request_id = await create_passenger_request(
        message.from_user.id,
        data,
    )

    await state.clear()

    await db_execute(
        """
        UPDATE users
        SET phone=?
        WHERE user_id=?
        """,
        (
            data["phone"],
            message.from_user.id,
        ),
    )

    await message.answer(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"📍 {esc(data['from_city'])} → {esc(data['to_city'])}\n"
        f"⏰ {esc(data['ride_time'])}\n"
        f"👥 {data['seats']} kishi\n"
        f"👤 {esc(data['name'])}\n\n"
        f"🚕 Haydovchilar qidirilmoqda...",
        reply_markup=passenger_cancel_keyboard(request_id),
    )

    count = await notify_matching_drivers(request_id)

    if count:
        await message.answer(
            f"🚕 Buyurtma {count} ta haydovchiga yuborildi.",
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            "⏳ Hozircha mos haydovchi topilmadi.",
            reply_markup=main_menu(),
        )


# =========================================================
# DRIVER REGISTRATION
# =========================================================

@dp.message(F.text == "🚗 Haydovchi bo‘lish")
async def driver_start(
    message: Message,
    state: FSMContext
):

    await state.clear()
    await save_user(message)

    driver = await get_driver(
        message.from_user.id
    )

    if driver:

        if driver["status"] == "approved":

            await state.set_state(
                DriverRideState.from_city
            )

            await message.answer(
                "🚗 <b>Haydovchi paneli</b>\n\n"
                "Yo‘nalishni tanlang.\n"
                "Bu safar guruhga yoki bot orqali kelgan "
                "yo‘lovchilarga ham ko‘rinadi.",
                reply_markup=city_keyboard(),
            )

            return

        if driver["status"] == "pending":

            await message.answer(
                "⏳ <b>Profilingiz admin tasdig‘ini kutmoqda.</b>\n\n"
                "Tasdiqlangandan keyin taksi e'lon qilishingiz mumkin.",
                reply_markup=main_menu(),
            )

            return

        if driver["status"] == "rejected":

            await state.set_state(
                DriverRegisterState.full_name
            )

            await message.answer(
                "❌ Oldingi haydovchi profilingiz rad etilgan.\n\n"
                "Qaytadan ro‘yxatdan o‘tamiz.\n\n"
                "👤 To‘liq ism-familiyangizni yozing:",
                reply_markup=cancel_keyboard(),
            )

            return

    await state.set_state(
        DriverRegisterState.full_name
    )

    await message.answer(
        "🚗 <b>Haydovchi sifatida ro‘yxatdan o‘tish</b>\n\n"
        "👤 To‘liq ism-familiyangizni yozing:",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DriverRegisterState.full_name)
async def driver_register_name(
    message: Message,
    state: FSMContext
):

    name = (message.text or "").strip()

    if len(name) < 2:
        await message.answer(
            "Iltimos, to‘liq ism-familiyangizni yozing."
        )
        return

    await state.update_data(
        full_name=name
    )

    await state.set_state(
        DriverRegisterState.phone
    )

    await message.answer(
        "📞 Telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard(),
    )


@dp.message(DriverRegisterState.phone, F.contact)
async def driver_register_phone_contact(
    message: Message,
    state: FSMContext
):

    if (
        message.contact
        and message.contact.user_id
        and message.contact.user_id != message.from_user.id
    ):
        await message.answer(
            "❗ O‘zingizning telefon raqamingizni yuboring."
        )
        return

    phone = normalize_phone(
        message.contact.phone_number
    )

    if not phone:
        await message.answer(
            "Telefon raqamini aniqlab bo‘lmadi."
        )
        return

    await state.update_data(
        phone=phone
    )

    await state.set_state(
        DriverRegisterState.car_model
    )

    await message.answer(
        "🚘 Mashina markasi/modelini yozing.\n\n"
        "Masalan: Chevrolet Cobalt",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DriverRegisterState.phone)
async def driver_register_phone_text(
    message: Message,
    state: FSMContext
):

    phone = normalize_phone(message.text)

    if not phone:
        await message.answer(
            "Telefon raqamini to‘g‘ri kiriting.",
            reply_markup=phone_keyboard(),
        )
        return

    await state.update_data(
        phone=phone
    )

    await state.set_state(
        DriverRegisterState.car_model
    )

    await message.answer(
        "🚘 Mashina markasi/modelini yozing.",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DriverRegisterState.car_model)
async def driver_register_car_model(
    message: Message,
    state: FSMContext
):

    model = (message.text or "").strip()

    if len(model) < 2:
        await message.answer(
            "Mashina modelini yozing."
        )
        return

    await state.update_data(
        car_model=model
    )

    await state.set_state(
        DriverRegisterState.car_number
    )

    await message.answer(
        "🔢 Mashina davlat raqamini yozing.\n\n"
        "Masalan: 01 A 123 BC",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DriverRegisterState.car_number)
async def driver_register_car_number(
    message: Message,
    state: FSMContext
):

    car_number = (message.text or "").strip()

    if len(car_number) < 3:
        await message.answer(
            "Mashina raqamini to‘g‘ri kiriting."
        )
        return

    await state.update_data(
        car_number=car_number
    )

    await state.set_state(
        DriverRegisterState.seats
    )

    await message.answer(
        "💺 Mashinangizda nechta yo‘lovchi joyi bor?",
        reply_markup=driver_count_keyboard(),
    )


@dp.message(DriverRegisterState.seats)
async def driver_register_seats(
    message: Message,
    state: FSMContext
):

    if not message.text or not message.text.isdigit():
        await message.answer(
            "1 dan 4 gacha son tanlang.",
            reply_markup=driver_count_keyboard(),
        )
        return

    seats = int(message.text)

    if seats < 1 or seats > 4:
        await message.answer(
            "Joylar soni 1–4 oralig‘ida bo‘lishi kerak."
        )
        return

    data = await state.get_data()

    await db_execute(
        """
        INSERT INTO driver_profiles (
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
        ON CONFLICT(user_id)
        DO UPDATE SET
            full_name=excluded.full_name,
            phone=excluded.phone,
            car_model=excluded.car_model,
            car_number=excluded.car_number,
            seats=excluded.seats,
            status='pending'
        """,
        (
            message.from_user.id,
            data["full_name"],
            data["phone"],
            data["car_model"],
            data["car_number"],
            seats,
            now(),
        ),
    )

    await db_execute(
        """
        UPDATE users
        SET phone=?
        WHERE user_id=?
        """,
        (
            data["phone"],
            message.from_user.id,
        ),
    )

    await state.clear()

    await message.answer(
        "✅ <b>Haydovchi profilingiz yuborildi.</b>\n\n"
        f"👤 {esc(data['full_name'])}\n"
        f"📞 {esc(data['phone'])}\n"
        f"🚘 {esc(data['car_model'])}\n"
        f"🔢 {esc(data['car_number'])}\n"
        f"💺 {seats} ta joy\n\n"
        "⏳ Admin tasdig‘idan keyin taksi e'lon qilishingiz mumkin.",
        reply_markup=main_menu(),
    )

    for admin_id in ADMIN_IDS:

        await safe_send(
            admin_id,
            "🚗 <b>YANGI HAYDOVCHI RO‘YXATDAN O‘TDI</b>\n\n"
            f"👤 {esc(data['full_name'])}\n"
            f"📞 {esc(data['phone'])}\n"
            f"🚘 {esc(data['car_model'])}\n"
            f"🔢 {esc(data['car_number'])}\n"
            f"💺 {seats} ta joy\n"
            f"🆔 <code>{message.from_user.id}</code>",
            reply_markup=admin_driver_keyboard(
                message.from_user.id
            ),
        )


# =========================================================
# DRIVER RIDE CREATION
# =========================================================

@dp.message(DriverRideState.from_city)
async def driver_from_city(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:
        await message.answer(
            "Shaharni ro‘yxatdan tanlang.",
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
async def driver_to_city(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:
        await message.answer(
            "Shaharni ro‘yxatdan tanlang.",
            reply_markup=city_keyboard(),
        )
        return

    data = await state.get_data()

    if message.text == data.get("from_city"):
        await message.answer(
            "Ketish va borish shahri bir xil bo‘lishi mumkin emas."
        )
        return

    await state.update_data(
        to_city=message.text
    )

    await state.set_state(
        DriverRideState.time
    )

    await message.answer(
        "⏰ Qaysi vaqtda ketasiz?",
        reply_markup=time_keyboard(),
    )


@dp.message(DriverRideState.time)
async def driver_time(
    message: Message,
    state: FSMContext
):

    if message.text not in TIMES:
        await message.answer(
            "Vaqtni ro‘yxatdan tanlang.",
            reply_markup=time_keyboard(),
        )
        return

    await state.update_data(
        ride_time=message.text
    )

    await state.set_state(
        DriverRideState.seats
    )

    await message.answer(
        "💺 Nechta bo‘sh joy bor?",
        reply_markup=driver_count_keyboard(),
    )


@dp.message(DriverRideState.seats)
async def driver_seats(
    message: Message,
    state: FSMContext
):

    if not message.text or not message.text.isdigit():
        await message.answer(
            "1 dan 4 gacha son tanlang.",
            reply_markup=driver_count_keyboard(),
        )
        return

    seats = int(message.text)

    if seats < 1 or seats > 4:
        await message.answer(
            "Bo‘sh joy 1–4 oralig‘ida bo‘lishi kerak."
        )
        return

    driver = await get_driver(
        message.from_user.id
    )

    if not driver or driver["status"] != "approved":
        await state.clear()

        await message.answer(
            "❌ Siz hali tasdiqlangan haydovchi emassiz.",
            reply_markup=main_menu(),
        )
        return

    data = await state.get_data()

    ride_id = await db_execute(
        """
        INSERT INTO rides (
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
            message.from_user.id,
            data["from_city"],
            data["to_city"],
            data["ride_time"],
            seats,
            seats,
            now(),
        ),
    )

    await state.clear()

    await message.answer(
        "✅ <b>Safaringiz e'lon qilindi!</b>\n\n"
        f"📍 {esc(data['from_city'])} → {esc(data['to_city'])}\n"
        f"⏰ {esc(data['ride_time'])}\n"
        f"💺 {seats} ta bo‘sh joy\n\n"
        "🚕 Mos yo‘lovchilarga xabar beramiz.",
        reply_markup=main_menu(),
    )

    await notify_matching_passengers(
        ride_id
    )


# =========================================================
# MATCH PASSENGERS -> DRIVERS
# =========================================================

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
            MAX(r.available_seats) AS available_seats
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
        GROUP BY d.user_id
        """,
        (
            request["from_city"],
            request["to_city"],
            request["ride_time"],
            request["seats"],
        ),
        fetchall=True,
    )

    sent = 0

    for driver in drivers:

        text = (
            "🚕 <b>YANGI YO‘LOVCHI BUYURTMASI</b>\n\n"
            f"📍 {esc(request['from_city'])} → "
            f"{esc(request['to_city'])}\n"
            f"⏰ {esc(request['ride_time'])}\n"
            f"👥 {request['seats']} kishi\n"
            f"👤 {esc(request['name'])}\n\n"
            "Buyurtmani qabul qilasizmi?"
        )

        ok = await safe_send(
            driver["user_id"],
            text,
            reply_markup=driver_request_keyboard(
                request_id
            ),
        )

        if ok:
            sent += 1

    return sent


# =========================================================
# DRIVER ACCEPT REQUEST
# =========================================================

@dp.callback_query(F.data.startswith("accept_request:"))
async def accept_request(callback: CallbackQuery):

    request_id = int(
        callback.data.split(":")[1]
    )

    driver_id = callback.from_user.id

    driver = await get_driver(driver_id)

    if not driver or driver["status"] != "approved":
        await callback.answer(
            "Siz tasdiqlangan haydovchi emassiz.",
            show_alert=True,
        )
        return

    async def transaction(db):

        request_cursor = await db.execute(
            """
            SELECT *
            FROM passenger_requests
            WHERE id=?
            """,
            (request_id,),
        )

        request = await request_cursor.fetchone()

        if not request:
            return "not_found", None

        if request["status"] != "searching":
            return "closed", None

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
            ORDER BY id DESC
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
            return "no_ride", None

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
            SET available_seats=available_seats-?
            WHERE id=?
            """,
            (
                request["seats"],
                ride["id"],
            ),
        )

        cursor = await db.execute(
            """
            INSERT INTO bookings (
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

        booking_id = cursor.lastrowid

        return "success", (
            dict(request),
            dict(ride),
            booking_id,
        )

    result, payload = await db_transaction(
        transaction
    )

    if result == "not_found":
        await callback.answer(
            "Buyurtma topilmadi.",
            show_alert=True,
        )
        return

    if result == "closed":
        await callback.answer(
            "Bu buyurtmani boshqa haydovchi qabul qilgan.",
            show_alert=True,
        )
        return

    if result == "no_ride":
        await callback.answer(
            "Sizda mos faol safar yoki yetarli joy yo‘q.",
            show_alert=True,
        )
        return

    request, ride, booking_id = payload

    await callback.answer(
        "✅ Buyurtma qabul qilindi!"
    )

    try:
        await callback.message.edit_text(
            "✅ <b>BUYURTMA QABUL QILINDI</b>\n\n"
            "Yo‘lovchi bilan bog‘lanishingiz mumkin."
        )
    except Exception:
        pass

    driver_text = (
        "🚕 <b>BUYURTMA TASDIQLANDI</b>\n\n"
        f"📍 {esc(request['from_city'])} → "
        f"{esc(request['to_city'])}\n"
        f"⏰ {esc(request['ride_time'])}\n"
        f"👥 {request['seats']} kishi\n\n"
        f"👤 Yo‘lovchi: {esc(request['name'])}\n"
        f"📞 Telefon: <code>{esc(request['phone'])}</code>\n\n"
        "Quyidagi tugmalar orqali safar holatini boshqaring."
    )

    await bot.send_message(
        driver_id,
        driver_text,
        reply_markup=booking_driver_keyboard(
            booking_id
        ),
    )

    passenger_text = (
        "🎉 <b>SIZGA HAYDOVCHI TOPILDI!</b>\n\n"
        f"📍 {esc(request['from_city'])} → "
        f"{esc(request['to_city'])}\n"
        f"⏰ {esc(request['ride_time'])}\n\n"
        f"🚗 Haydovchi: {esc(driver['full_name'])}\n"
        f"🚘 Mashina: {esc(driver['car_model'])}\n"
        f"🔢 Raqam: {esc(driver['car_number'])}\n"
        f"⭐ Reyting: {driver['rating']:.1f}\n"
        f"📞 Telefon: <code>{esc(driver['phone'])}</code>"
    )

    if request["latitude"] and request["longitude"]:
        await safe_send(
            request["passenger_id"],
            passenger_text,
            reply_markup=passenger_booking_keyboard(
                booking_id
            ),
        )

        try:
            await bot.send_location(
                request["passenger_id"],
                request["latitude"],
                request["longitude"],
            )
        except Exception:
            pass
    else:
        await safe_send(
            request["passenger_id"],
            passenger_text,
            reply_markup=passenger_booking_keyboard(
                booking_id
            ),
        )

    # Guruhdan kelgan buyurtma bo‘lsa
    if request["source_chat_id"]:

        await safe_send(
            request["source_chat_id"],
            "🚕 <b>Buyurtma qabul qilindi.</b>\n\n"
            "Haydovchi va yo‘lovchiga tafsilotlar "
            "shaxsiy xabarda yuborildi.",
        )


# =========================================================
# DRIVER REJECT
# =========================================================

@dp.callback_query(F.data.startswith("reject_request:"))
async def reject_request(callback: CallbackQuery):

    await callback.answer(
        "❌ Buyurtma rad etildi."
    )

    try:
        await callback.message.edit_text(
            "❌ Siz bu buyurtmani rad etdingiz."
        )
    except Exception:
        pass


# =========================================================
# PASSENGER CANCEL REQUEST
# =========================================================

@dp.callback_query(F.data.startswith("cancel_request:"))
async def cancel_request(callback: CallbackQuery):

    request_id = int(
        callback.data.split(":")[1]
    )

    request = await get_request(request_id)

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

    if request["status"] not in (
        "searching",
        "accepted",
    ):
        await callback.answer(
            "Bu buyurtmani bekor qilib bo‘lmaydi.",
            show_alert=True,
        )
        return

    async def transaction(db):

        cursor = await db.execute(
            """
            SELECT *
            FROM bookings
            WHERE request_id=?
              AND status NOT IN ('cancelled','completed')
            LIMIT 1
            """,
            (request_id,),
        )

        booking = await cursor.fetchone()

        await db.execute(
            """
            UPDATE passenger_requests
            SET status='cancelled'
            WHERE id=?
            """,
            (request_id,),
        )

        if booking:

            await db.execute(
                """
                UPDATE bookings
                SET status='cancelled'
                WHERE id=?
                """,
                (booking["id"],),
            )

            await db.execute(
                """
                UPDATE rides
                SET available_seats=available_seats+?
                WHERE id=?
                """,
                (
                    booking["seats"],
                    booking["ride_id"],
                ),
            )

            return dict(booking)

        return None

    booking = await db_transaction(
        transaction
    )

    await callback.answer(
        "Buyurtma bekor qilindi."
    )

    try:
        await callback.message.edit_text(
            "❌ <b>Buyurtma bekor qilindi.</b>"
        )
    except Exception:
        pass

    if booking:
        await safe_send(
            booking["driver_id"],
            "⚠️ Yo‘lovchi buyurtmani bekor qildi."
        )


# =========================================================
# GROUP CANCEL
# =========================================================

@dp.callback_query(F.data.startswith("group_cancel:"))
async def group_cancel(callback: CallbackQuery):

    request_id = int(
        callback.data.split(":")[1]
    )

    request = await get_request(request_id)

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

    if request["status"] != "searching":
        await callback.answer(
            "Buyurtma allaqachon yopilgan.",
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

    await callback.answer(
        "Buyurtma bekor qilindi."
    )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    try:
        await callback.message.reply(
            "❌ Buyurtma bekor qilindi."
        )
    except Exception:
        pass


# =========================================================
# PASSENGER BOOK A DRIVER RIDE
# =========================================================

@dp.callback_query(F.data.startswith("book_ride:"))
async def book_ride(callback: CallbackQuery):

    parts = callback.data.split(":")

    request_id = int(parts[1])
    ride_id = int(parts[2])

    passenger_id = callback.from_user.id

    async def transaction(db):

        req_cursor = await db.execute(
            """
            SELECT *
            FROM passenger_requests
            WHERE id=?
            """,
            (request_id,),
        )

        request = await req_cursor.fetchone()

        if not request:
            return "not_found", None

        if request["passenger_id"] != passenger_id:
            return "not_owner", None

        if request["status"] != "searching":
            return "closed", None

        ride_cursor = await db.execute(
            """
            SELECT *
            FROM rides
            WHERE id=?
            """,
            (ride_id,),
        )

        ride = await ride_cursor.fetchone()

        if not ride:
            return "ride_not_found", None

        if ride["status"] != "active":
            return "ride_closed", None

        if ride["available_seats"] < request["seats"]:
            return "no_seats", None

        driver_cursor = await db.execute(
            """
            SELECT *
            FROM driver_profiles
            WHERE user_id=?
              AND status='approved'
            """,
            (ride["driver_id"],),
        )

        driver = await driver_cursor.fetchone()

        if not driver:
            return "driver_not_found", None

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
            SET available_seats=available_seats-?
            WHERE id=?
            """,
            (
                request["seats"],
                ride_id,
            ),
        )

        cursor = await db.execute(
            """
            INSERT INTO bookings (
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
                ride_id,
                passenger_id,
                ride["driver_id"],
                request["seats"],
                now(),
            ),
        )

        return "success", (
            dict(request),
            dict(ride),
            dict(driver),
            cursor.lastrowid,
        )

    result, payload = await db_transaction(
        transaction
    )

    if result != "success":

        messages = {
            "not_found": "Buyurtma topilmadi.",
            "not_owner": "Bu buyurtma sizniki emas.",
            "closed": "Buyurtma allaqachon yopilgan.",
            "ride_not_found": "Taksi topilmadi.",
            "ride_closed": "Bu taksi safarni yopgan.",
            "no_seats": "Bo‘sh joy qolmagan.",
            "driver_not_found": "Haydovchi topilmadi.",
        }

        await callback.answer(
            messages.get(result, "Xatolik."),
            show_alert=True,
        )
        return

    request, ride, driver, booking_id = payload

    await callback.answer(
        "🚕 Taksi tanlandi!"
    )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    passenger_text = (
        "🎉 <b>TAKSI TASDIQLANDI!</b>\n\n"
        f"📍 {esc(request['from_city'])} → "
        f"{esc(request['to_city'])}\n"
        f"⏰ {esc(request['ride_time'])}\n\n"
        f"🚗 Haydovchi: {esc(driver['full_name'])}\n"
        f"🚘 Mashina: {esc(driver['car_model'])}\n"
        f"🔢 Raqam: {esc(driver['car_number'])}\n"
        f"⭐ Reyting: {driver['rating']:.1f}\n"
        f"📞 Telefon: <code>{esc(driver['phone'])}</code>"
    )

    await bot.send_message(
        passenger_id,
        passenger_text,
        reply_markup=passenger_booking_keyboard(
            booking_id
        ),
    )

    driver_text = (
        "🚕 <b>YO‘LOVCHI SAFARINGIZNI TANLADI!</b>\n\n"
        f"📍 {esc(request['from_city'])} → "
        f"{esc(request['to_city'])}\n"
        f"⏰ {esc(request['ride_time'])}\n"
        f"👥 {request['seats']} kishi\n\n"
        f"👤 {esc(request['name'])}\n"
        f"📞 <code>{esc(request['phone'])}</code>"
    )

    await bot.send_message(
        ride["driver_id"],
        driver_text,
        reply_markup=booking_driver_keyboard(
            booking_id
        ),
    )


# =========================================================
# DRIVER LOCATION
# =========================================================

@dp.message(F.location)
async def driver_location(message: Message):

    driver = await get_driver(
        message.from_user.id
    )

    if not driver:
        return

    await db_execute(
        """
        UPDATE driver_profiles
        SET latitude=?,
            longitude=?
        WHERE user_id=?
        """,
        (
            message.location.latitude,
            message.location.longitude,
            message.from_user.id,
        ),
    )

    booking = await db_execute(
        """
        SELECT *
        FROM bookings
        WHERE driver_id=?
          AND status IN (
              'accepted',
              'arrived',
              'onboard'
          )
        ORDER BY id DESC
        LIMIT 1
        """,
        (message.from_user.id,),
        fetchone=True,
    )

    if not booking:
        return

    await db_execute(
        """
        UPDATE bookings
        SET driver_latitude=?,
            driver_longitude=?
        WHERE id=?
        """,
        (
            message.location.latitude,
            message.location.longitude,
            booking["id"],
        ),
    )

    await safe_send(
        booking["passenger_id"],
        "📍 <b>Haydovchi joylashuvini yangiladi.</b>\n"
        "Quyidagi xaritada ko‘rishingiz mumkin.",
    )

    try:
        await bot.send_location(
            booking["passenger_id"],
            message.location.latitude,
            message.location.longitude,
        )
    except Exception:
        pass


# =========================================================
# DRIVER STATUS
# =========================================================

@dp.callback_query(F.data.startswith("driver_arrived:"))
async def driver_arrived(callback: CallbackQuery):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Booking topilmadi.",
            show_alert=True,
        )
        return

    if booking["driver_id"] != callback.from_user.id:
        await callback.answer(
            "Bu booking sizniki emas.",
            show_alert=True,
        )
        return

    await db_execute(
        """
        UPDATE bookings
        SET status='arrived'
        WHERE id=?
          AND status='accepted'
        """,
        (booking_id,),
    )

    await callback.answer(
        "📍 Yo‘lovchiga xabar yuborildi."
    )

    await safe_send(
        booking["passenger_id"],
        "📍 <b>Haydovchi yetib keldi!</b>\n\n"
        "Haydovchini kutib oling.",
        reply_markup=passenger_booking_keyboard(
            booking_id
        ),
    )


@dp.callback_query(F.data.startswith("driver_onboard:"))
async def driver_onboard(callback: CallbackQuery):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Booking topilmadi.",
            show_alert=True,
        )
        return

    if booking["driver_id"] != callback.from_user.id:
        await callback.answer(
            "Bu booking sizniki emas.",
            show_alert=True,
        )
        return

    await db_execute(
        """
        UPDATE bookings
        SET status='onboard'
        WHERE id=?
          AND status IN ('accepted','arrived')
        """,
        (booking_id,),
    )

    await callback.answer(
        "👤 Safar boshlandi."
    )

    await safe_send(
        booking["passenger_id"],
        "🚕 <b>Sizni haydovchi olib ketdi.</b>\n\n"
        "Xavfsiz safar tilaymiz!",
        reply_markup=passenger_booking_keyboard(
            booking_id
        ),
    )


@dp.callback_query(F.data.startswith("driver_complete:"))
async def driver_complete(callback: CallbackQuery):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Booking topilmadi.",
            show_alert=True,
        )
        return

    if booking["driver_id"] != callback.from_user.id:
        await callback.answer(
            "Bu booking sizniki emas.",
            show_alert=True,
        )
        return

    if booking["status"] == "completed":
        await callback.answer(
            "Safar allaqachon tugagan."
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
        (callback.from_user.id,),
    )

    await callback.answer(
        "🏁 Safar tugadi."
    )

    await safe_send(
        booking["passenger_id"],
        "🏁 <b>Safar yakunlandi.</b>\n\n"
        "Iltimos, haydovchini baholang:",
        reply_markup=rating_keyboard(
            booking_id
        ),
    )

    try:
        await callback.message.edit_text(
            "🏁 <b>Safar yakunlandi.</b>\n\n"
            "Yo‘lovchi sizga baho berishi mumkin."
        )
    except Exception:
        pass


@dp.callback_query(F.data.startswith("driver_cancel:"))
async def driver_cancel(callback: CallbackQuery):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Booking topilmadi.",
            show_alert=True,
        )
        return

    if booking["driver_id"] != callback.from_user.id:
        await callback.answer(
            "Bu booking sizniki emas.",
            show_alert=True,
        )
        return

    async def transaction(db):

        cursor = await db.execute(
            """
            SELECT *
            FROM bookings
            WHERE id=?
            """,
            (booking_id,),
        )

        row = await cursor.fetchone()

        if not row:
            return False

        if row["status"] in (
            "cancelled",
            "completed",
        ):
            return False

        await db.execute(
            """
            UPDATE bookings
            SET status='cancelled'
            WHERE id=?
            """,
            (booking_id,),
        )

        await db.execute(
            """
            UPDATE passenger_requests
            SET status='searching'
            WHERE id=?
            """,
            (row["request_id"],),
        )

        await db.execute(
            """
            UPDATE rides
            SET available_seats=available_seats+?
            WHERE id=?
            """,
            (
                row["seats"],
                row["ride_id"],
            ),
        )

        return True

    ok = await db_transaction(
        transaction
    )

    if not ok:
        await callback.answer(
            "Safarni bekor qilib bo‘lmaydi.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Safar bekor qilindi."
    )

    await safe_send(
        booking["passenger_id"],
        "⚠️ <b>Haydovchi safarni bekor qildi.</b>\n\n"
        "Siz uchun boshqa haydovchi qidirilmoqda.",
    )

    await notify_matching_drivers(
        booking["request_id"]
    )

    try:
        await callback.message.edit_text(
            "❌ <b>Safar bekor qilindi.</b>"
        )
    except Exception:
        pass


# =========================================================
# PASSENGER CANCEL BOOKING
# =========================================================

@dp.callback_query(F.data.startswith("passenger_cancel_booking:"))
async def passenger_cancel_booking(callback: CallbackQuery):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Booking topilmadi.",
            show_alert=True,
        )
        return

    if booking["passenger_id"] != callback.from_user.id:
        await callback.answer(
            "Bu booking sizniki emas.",
            show_alert=True,
        )
        return

    if booking["status"] in (
        "cancelled",
        "completed",
    ):
        await callback.answer(
            "Booking allaqachon yopilgan.",
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
        SET available_seats=available_seats+?
        WHERE id=?
        """,
        (
            booking["seats"],
            booking["ride_id"],
        ),
    )

    await callback.answer(
        "Buyurtma bekor qilindi."
    )

    await safe_send(
        booking["driver_id"],
        "⚠️ Yo‘lovchi safarni bekor qildi."
    )

    try:
        await callback.message.edit_text(
            "❌ <b>Buyurtma bekor qilindi.</b>"
        )
    except Exception:
        pass


# =========================================================
# TRACK DRIVER
# =========================================================

@dp.callback_query(F.data.startswith("track_driver:"))
async def track_driver(callback: CallbackQuery):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Booking topilmadi.",
            show_alert=True,
        )
        return

    if booking["passenger_id"] != callback.from_user.id:
        await callback.answer(
            "Bu booking sizniki emas.",
            show_alert=True,
        )
        return

    if (
        booking["driver_latitude"] is None
        or booking["driver_longitude"] is None
    ):
        driver = await get_driver(
            booking["driver_id"]
        )

        if (
            not driver
            or driver["latitude"] is None
        ):
            await callback.answer(
                "Haydovchi hali joylashuv yubormagan.",
                show_alert=True,
            )
            return

        latitude = driver["latitude"]
        longitude = driver["longitude"]

    else:
        latitude = booking["driver_latitude"]
        longitude = booking["driver_longitude"]

    await callback.answer(
        "📍 Joylashuv yuborildi."
    )

    try:
        await bot.send_location(
            callback.from_user.id,
            latitude,
            longitude,
        )
    except Exception:
        pass


# =========================================================
# RATINGS
# =========================================================

@dp.callback_query(F.data.startswith("rate:"))
async def rate_driver(callback: CallbackQuery):

    parts = callback.data.split(":")

    booking_id = int(parts[1])
    rating = int(parts[2])

    booking = await get_booking(
        booking_id
    )

    if not booking:
        await callback.answer(
            "Booking topilmadi.",
            show_alert=True,
        )
        return

    if booking["passenger_id"] != callback.from_user.id:
        await callback.answer(
            "Bu booking sizniki emas.",
            show_alert=True,
        )
        return

    if booking["status"] != "completed":
        await callback.answer(
            "Safar hali tugamagan.",
            show_alert=True,
        )
        return

    existing = await db_execute(
        """
        SELECT id
        FROM ratings
        WHERE booking_id=?
        """,
        (booking_id,),
        fetchone=True,
    )

    if existing:
        await callback.answer(
            "Siz allaqachon baho bergansiz.",
            show_alert=True,
        )
        return

    await db_execute(
        """
        INSERT INTO ratings (
            booking_id,
            passenger_id,
            driver_id,
            rating,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            booking_id,
            callback.from_user.id,
            booking["driver_id"],
            rating,
            now(),
        ),
    )

    avg_row = await db_execute(
        """
        SELECT AVG(rating) AS avg_rating
        FROM ratings
        WHERE driver_id=?
        """,
        (booking["driver_id"],),
        fetchone=True,
    )

    avg_rating = avg_row["avg_rating"] or 5.0

    await db_execute(
        """
        UPDATE driver_profiles
        SET rating=?
        WHERE user_id=?
        """,
        (
            avg_rating,
            booking["driver_id"],
        ),
    )

    await callback.answer(
        "⭐ Baho qabul qilindi!"
    )

    try:
        await callback.message.edit_text(
            f"⭐ <b>Siz haydovchiga {rating}/5 baho berdingiz.</b>\n\n"
            "Rahmat!"
        )
    except Exception:
        pass

    await safe_send(
        booking["driver_id"],
        f"⭐ Yo‘lovchi sizga <b>{rating}/5</b> baho berdi.\n\n"
        f"Umumiy reytingingiz: <b>{avg_rating:.1f}</b>"
    )


# =========================================================
# SEARCH TAXIS
# =========================================================

@dp.message(F.text == "🔎 Taksilarni qidirish")
async def search_taxis(message: Message):

    await save_user(message)

    rows = await db_execute(
        """
        SELECT
            r.*,
            d.full_name,
            d.car_model,
            d.car_number,
            d.phone,
            d.rating
        FROM rides r
        JOIN driver_profiles d
            ON d.user_id=r.driver_id
        WHERE
            r.status='active'
            AND r.available_seats>0
            AND d.status='approved'
        ORDER BY r.id DESC
        LIMIT 20
        """,
        fetchall=True,
    )

    if not rows:
        await message.answer(
            "🔎 Hozircha faol taksi topilmadi.",
            reply_markup=main_menu(),
        )
        return

    text = "🚕 <b>FAOL TAKSILAR</b>\n\n"

    for row in rows:

        text += (
            f"📍 <b>{esc(row['from_city'])} → "
            f"{esc(row['to_city'])}</b>\n"
            f"⏰ {esc(row['ride_time'])}\n"
            f"💺 Bo‘sh joy: {row['available_seats']}\n"
            f"🚗 {esc(row['car_model'])}\n"
            f"👤 {esc(row['full_name'])}\n"
            f"⭐ {row['rating']:.1f}\n"
            f"📞 {esc(row['phone'])}\n\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# =========================================================
# MY BOOKINGS
# =========================================================

@dp.message(F.text == "📋 Buyurtmalarim")
async def my_bookings(message: Message):

    await save_user(message)

    passenger_rows = await db_execute(
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
        JOIN rides r
            ON r.id=b.ride_id
        JOIN driver_profiles d
            ON d.user_id=b.driver_id
        WHERE b.passenger_id=?
        ORDER BY b.id DESC
        LIMIT 10
        """,
        (message.from_user.id,),
        fetchall=True,
    )

    driver_rows = await db_execute(
        """
        SELECT
            b.*,
            r.from_city,
            r.to_city,
            r.ride_time,
            p.name AS passenger_name,
            p.phone AS passenger_phone
        FROM bookings b
        JOIN rides r
            ON r.id=b.ride_id
        JOIN passenger_requests p
            ON p.id=b.request_id
        WHERE b.driver_id=?
        ORDER BY b.id DESC
        LIMIT 10
        """,
        (message.from_user.id,),
        fetchall=True,
    )

    rides = await db_execute(
        """
        SELECT *
        FROM rides
        WHERE driver_id=?
        ORDER BY id DESC
        LIMIT 10
        """,
        (message.from_user.id,),
        fetchall=True,
    )

    text = "📋 <b>BUYURTMALARIM</b>\n\n"

    if passenger_rows:

        text += "👤 <b>YO‘LOVCHI SIFATIDA:</b>\n\n"

        for row in passenger_rows:

            text += (
                f"🚕 {esc(row['from_city'])} → "
                f"{esc(row['to_city'])}\n"
                f"⏰ {esc(row['ride_time'])}\n"
                f"🚗 {esc(row['driver_name'])}\n"
                f"📞 {esc(row['driver_phone'])}\n"
                f"📌 Holat: {esc(row['status'])}\n\n"
            )

    if driver_rows:

        text += "🚗 <b>HAYDOVCHI SIFATIDA:</b>\n\n"

        for row in driver_rows:

            text += (
                f"🚕 {esc(row['from_city'])} → "
                f"{esc(row['to_city'])}\n"
                f"⏰ {esc(row['ride_time'])}\n"
                f"👤 {esc(row['passenger_name'])}\n"
                f"📞 {esc(row['passenger_phone'])}\n"
                f"📌 Holat: {esc(row['status'])}\n\n"
            )

    if rides:

        text += "🛣 <b>MENING SAFARLARIM:</b>\n\n"

        for row in rides:

            text += (
                f"📍 {esc(row['from_city'])} → "
                f"{esc(row['to_city'])}\n"
                f"⏰ {esc(row['ride_time'])}\n"
                f"💺 {row['available_seats']} ta bo‘sh joy\n"
                f"📌 {esc(row['status'])}\n\n"
            )

    if (
        not passenger_rows
        and not driver_rows
        and not rides
    ):
        text += "Hozircha buyurtma yoki safarlar yo‘q."

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# =========================================================
# PROFILE
# =========================================================

@dp.message(F.text == "👤 Profil")
async def profile(message: Message):

    await save_user(message)

    user = await db_execute(
        """
        SELECT *
        FROM users
        WHERE user_id=?
        """,
        (message.from_user.id,),
        fetchone=True,
    )

    driver = await get_driver(
        message.from_user.id
    )

    text = (
        "👤 <b>PROFIL</b>\n\n"
        f"👤 Ism: {esc(user['full_name'] if user else message.from_user.full_name)}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
    )

    if user and user["phone"]:
        text += (
            f"📞 Telefon: <code>{esc(user['phone'])}</code>\n"
        )

    if driver:

        text += (
            "\n🚗 <b>HAYDOVCHI PROFILI</b>\n\n"
            f"🚘 Mashina: {esc(driver['car_model'])}\n"
            f"🔢 Raqam: {esc(driver['car_number'])}\n"
            f"💺 Joy: {driver['seats']}\n"
            f"⭐ Reyting: {driver['rating']:.1f}\n"
            f"🛣 Safarlar: {driver['trips']}\n"
            f"📌 Holat: {esc(driver['status'])}\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# =========================================================
# HELP
# =========================================================

@dp.message(F.text == "ℹ️ Yordam")
async def help_message(message: Message):

    await message.answer(
        "ℹ️ <b>OPPERTAXI YORDAM</b>\n\n"
        "🚕 <b>Taksi chaqirish</b> — yo‘nalish, vaqt va "
        "yo‘lovchilar sonini kiriting.\n\n"
        "🚗 <b>Haydovchi bo‘lish</b> — haydovchi profilini "
        "yarating va admin tasdig‘ini oling.\n\n"
        "🔎 <b>Taksilarni qidirish</b> — faol safarlarni ko‘ring.\n\n"
        "📋 <b>Buyurtmalarim</b> — yo‘lovchi/haydovchi "
        "buyurtmalarini ko‘ring.\n\n"
        "📍 Haydovchi joylashuvini yuborsa, yo‘lovchi "
        "uni xaritada kuzatishi mumkin.\n\n"
        "💬 Bot qo‘shilgan guruhlarda taksi e’lonlarini "
        "avtomatik aniqlash ham ishlaydi.",
        reply_markup=main_menu(),
    )


# =========================================================
# ADMIN
# =========================================================

@dp.message(Command("admin"))
async def admin_command(message: Message):

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

    groups = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM group_settings
        WHERE enabled=1
        """,
        fetchone=True,
    )

    await message.answer(
        "👑 <b>ADMIN PANEL</b>\n\n"
        f"👥 Foydalanuvchilar: {users['c']}\n"
        f"🚗 Tasdiqlangan haydovchilar: {drivers['c']}\n"
        f"⏳ Kutilayotgan haydovchilar: {pending['c']}\n"
        f"🚕 Faol safarlar: {rides['c']}\n"
        f"🔎 Qidirilayotgan buyurtmalar: {requests['c']}\n"
        f"👥 Faol guruhlar: {groups['c']}"
    )


@dp.message(Command("drivers"))
async def drivers_command(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    rows = await db_execute(
        """
        SELECT *
        FROM driver_profiles
        ORDER BY created_at DESC
        LIMIT 50
        """,
        fetchall=True,
    )

    if not rows:
        await message.answer(
            "Haydovchilar yo‘q."
        )
        return

    for driver in rows:

        await message.answer(
            "🚗 <b>HAYDOVCHI</b>\n\n"
            f"👤 {esc(driver['full_name'])}\n"
            f"📞 {esc(driver['phone'])}\n"
            f"🚘 {esc(driver['car_model'])}\n"
            f"🔢 {esc(driver['car_number'])}\n"
            f"💺 {driver['seats']}\n"
            f"⭐ {driver['rating']:.1f}\n"
            f"🛣 {driver['trips']} safar\n"
            f"📌 {esc(driver['status'])}\n"
            f"🆔 <code>{driver['user_id']}</code>",
            reply_markup=(
                admin_driver_keyboard(driver["user_id"])
                if driver["status"] == "pending"
                else None
            ),
        )


@dp.callback_query(F.data.startswith("admin_approve:"))
async def admin_approve(callback: CallbackQuery):

    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Siz admin emassiz.",
            show_alert=True,
        )
        return

    user_id = int(
        callback.data.split(":")[1]
    )

    await db_execute(
        """
        UPDATE driver_profiles
        SET status='approved'
        WHERE user_id=?
        """,
        (user_id,),
    )

    await callback.answer(
        "Haydovchi tasdiqlandi."
    )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await safe_send(
        user_id,
        "🎉 <b>TABRIKLAYMIZ!</b>\n\n"
        "🚗 Haydovchi profilingiz admin tomonidan "
        "tasdiqlandi.\n\n"
        "Endi «🚗 Haydovchi bo‘lish» tugmasi orqali "
        "safaringizni e’lon qilishingiz mumkin.",
    )


@dp.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject(callback: CallbackQuery):

    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "Siz admin emassiz.",
            show_alert=True,
        )
        return

    user_id = int(
        callback.data.split(":")[1]
    )

    await db_execute(
        """
        UPDATE driver_profiles
        SET status='rejected'
        WHERE user_id=?
        """,
        (user_id,),
    )

    await callback.answer(
        "Haydovchi rad etildi."
    )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await safe_send(
        user_id,
        "❌ Haydovchi profilingiz rad etildi.\n\n"
        "Ma'lumotlarni tekshirib, qaytadan ro‘yxatdan "
        "o‘tishingiz mumkin.",
    )


# =========================================================
# GROUP SYSTEM
# =========================================================

CITY_ALIASES = {
    "toshkent": "Toshkent",
    "tashkent": "Toshkent",
    "namangan": "Namangan",
    "andijon": "Andijon",
    "fargona": "Farg‘ona",
    "fergana": "Farg‘ona",
    "qoqon": "Qo‘qon",
    "kokand": "Qo‘qon",
    "margilon": "Marg‘ilon",
    "margilan": "Marg‘ilon",
}


PASSENGER_WORDS = [
    "taksi kerak",
    "taxi kerak",
    "mashina kerak",
    "joy kerak",
    "taksi qidir",
    "taxi qidir",
    "mashina qidir",
    "olib ket",
    "olib keting",
    "chiqaman",
    "ketaman",
    "yo lovchi",
    "yolovchi",
]


DRIVER_WORDS = [
    "joy bor",
    "bosh joy",
    "taksi bor",
    "taxi bor",
    "mashina bor",
    "olaman",
    "yolovchi olaman",
    "joy mavjud",
    "bolsh joy",
]


def extract_cities(text):

    t = normalize_text(text)

    found = []

    for alias, city in CITY_ALIASES.items():

        start = 0

        while True:

            pos = t.find(alias, start)

            if pos == -1:
                break

            found.append(
                (
                    pos,
                    city,
                )
            )

            start = pos + len(alias)

    found.sort(key=lambda x: x[0])

    result = []

    for _, city in found:

        if city not in result:
            result.append(city)

    return result[:2]


def extract_time(text):

    t = normalize_text(text)

    # 18:00 / 18.00 / 18 00
    match = re.search(
        r"\b([01]?\d|2[0-3])\s*[:.]\s*([0-5]\d)\b",
        t,
    )

    if match:

        hour = int(match.group(1))
        minute = int(match.group(2))

        return f"{hour:02d}:{minute:02d}"

    # 18 ga / 18 da
    match = re.search(
        r"\b([01]?\d|2[0-3])\s*(?:ga|da)\b",
        t,
    )

    if match:

        hour = int(match.group(1))

        return f"{hour:02d}:00"

    return None


def extract_seats(text):

    t = normalize_text(text)

    numbers = {
        "bir": 1,
        "ikki": 2,
        "uch": 3,
        "tort": 4,
    }

    match = re.search(
        r"\b([1-9]|10)\s*"
        r"(?:kishi|odam|yolovchi|joy|ta|mesta|mesto)\b",
        t,
    )

    if match:

        value = int(match.group(1))

        if 1 <= value <= 10:
            return value

    for word, value in numbers.items():

        if re.search(
            rf"\b{word}\s*(?:kishi|odam|yolovchi|joy)\b",
            t,
        ):
            return value

    return None


def extract_phone(text):

    match = re.search(
        r"(?<!\d)"
        r"(?:\+?998[\s\-]?)?"
        r"(?:\d[\s\-]?){9}"
        r"(?!\d)",
        text,
    )

    if not match:
        return None

    return normalize_phone(
        match.group(0)
    )


def classify_group_message(text):

    t = normalize_text(text)

    passenger_score = 0
    driver_score = 0

    for word in PASSENGER_WORDS:
        if word in t:
            passenger_score += 1

    for word in DRIVER_WORDS:
        if word in t:
            driver_score += 1

    # Kuchli belgilar
    if "kerak" in t:
        passenger_score += 2

    if "joy bor" in t or "taksi bor" in t:
        driver_score += 2

    if passenger_score == 0 and driver_score == 0:
        return None

    if passenger_score > driver_score:
        return "passenger"

    if driver_score > passenger_score:
        return "driver"

    return "ambiguous"


def parse_group_taxi_message(text):

    kind = classify_group_message(text)

    if not kind:
        return None

    cities = extract_cities(text)
    ride_time = extract_time(text)
    seats = extract_seats(text)
    phone = extract_phone(text)

    missing = []

    if len(cities) < 2:
        missing.append(
            "📍 Qayerdan → qayerga"
        )

    if not ride_time:
        missing.append(
            "⏰ Ketish vaqti"
        )

    if not seats:
        missing.append(
            "👥 Yo‘lovchi/bo‘sh joy soni"
        )

    return {
        "kind": kind,
        "from_city": cities[0] if len(cities) >= 1 else None,
        "to_city": cities[1] if len(cities) >= 2 else None,
        "ride_time": ride_time,
        "seats": seats,
        "phone": phone,
        "missing": missing,
    }


async def claim_group_message(
    chat_id,
    message_id,
    text,
    processed_type,
):

    existing = await db_execute(
        """
        SELECT 1
        FROM group_messages
        WHERE chat_id=?
          AND message_id=?
        """,
        (
            chat_id,
            message_id,
        ),
        fetchone=True,
    )

    if existing:
        return False

    await db_execute(
        """
        INSERT INTO group_messages (
            chat_id,
            message_id,
            message_text,
            processed_type,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            message_id,
            text,
            processed_type,
            now(),
        ),
    )

    return True


async def group_is_enabled(
    chat_id,
    title,
):

    row = await db_execute(
        """
        SELECT *
        FROM group_settings
        WHERE chat_id=?
        """,
        (chat_id,),
        fetchone=True,
    )

    if not row:

        await db_execute(
            """
            INSERT INTO group_settings (
                chat_id,
                title,
                enabled,
                created_at
            )
            VALUES (?, ?, 1, ?)
            """,
            (
                chat_id,
                title,
                now(),
            ),
        )

        return True

    return bool(row["enabled"])


# =========================================================
# GROUP ADMIN COMMANDS
# =========================================================

@dp.message(Command("groupon"))
async def group_on(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    if message.chat.type not in (
        "group",
        "supergroup",
    ):
        return

    await db_execute(
        """
        INSERT INTO group_settings (
            chat_id,
            title,
            enabled,
            created_at
        )
        VALUES (?, ?, 1, ?)
        ON CONFLICT(chat_id)
        DO UPDATE SET
            title=excluded.title,
            enabled=1
        """,
        (
            message.chat.id,
            message.chat.title or "",
            now(),
        ),
    )

    await message.reply(
        "✅ <b>OPPERTAXI guruh tizimi yoqildi.</b>"
    )


@dp.message(Command("groupoff"))
async def group_off(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    if message.chat.type not in (
        "group",
        "supergroup",
    ):
        return

    await db_execute(
        """
        INSERT INTO group_settings (
            chat_id,
            title,
            enabled,
            created_at
        )
        VALUES (?, ?, 0, ?)
        ON CONFLICT(chat_id)
        DO UPDATE SET
            title=excluded.title,
            enabled=0
        """,
        (
            message.chat.id,
            message.chat.title or "",
            now(),
        ),
    )

    await message.reply(
        "⛔ <b>OPPERTAXI guruh tizimi o‘chirildi.</b>"
    )


@dp.message(Command("groupstatus"))
async def group_status(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    if message.chat.type not in (
        "group",
        "supergroup",
    ):
        return

    enabled = await group_is_enabled(
        message.chat.id,
        message.chat.title or "",
    )

    await message.reply(
        "📊 Guruh holati: "
        + ("🟢 YOQILGAN" if enabled else "🔴 O‘CHIRILGAN")
    )


@dp.message(Command("groups"))
async def groups_command(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    rows = await db_execute(
        """
        SELECT *
        FROM group_settings
        ORDER BY created_at DESC
        """,
        fetchall=True,
    )

    if not rows:
        await message.answer(
            "Hali hech qanday guruh qayd etilmagan."
        )
        return

    text = "👥 <b>OPPERTAXI GURUHLARI</b>\n\n"

    for row in rows:

        text += (
            f"📌 {esc(row['title'])}\n"
            f"🆔 <code>{row['chat_id']}</code>\n"
            f"Holat: "
            f"{'🟢' if row['enabled'] else '🔴'}\n\n"
        )

    await message.answer(text)


# =========================================================
# GROUP PASSENGER
# =========================================================

async def process_group_passenger(
    message: Message,
    parsed,
    text,
):

    passenger_id = message.from_user.id

    phone = parsed["phone"]

    if not phone:

        user = await db_execute(
            """
            SELECT phone
            FROM users
            WHERE user_id=?
            """,
            (passenger_id,),
            fetchone=True,
        )

        if user:
            phone = user["phone"]

    if not phone:
        phone = "Telefon bot orqali olinadi"

    name = message.from_user.full_name

    data = {
        "from_city": parsed["from_city"],
        "to_city": parsed["to_city"],
        "ride_time": parsed["ride_time"],
        "seats": parsed["seats"],
        "name": name,
        "phone": phone,
    }

    request_id = await create_passenger_request(
        passenger_id,
        data,
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
        source_text=text,
    )

    await message.reply(
        "🤖 <b>OPPERTAXI buyurtmani aniqladi.</b>\n\n"
        f"📍 {esc(parsed['from_city'])} → "
        f"{esc(parsed['to_city'])}\n"
        f"⏰ {esc(parsed['ride_time'])}\n"
        f"👥 {parsed['seats']} kishi\n"
        f"👤 {esc(name)}\n\n"
        "🚕 Mos haydovchilar qidirilmoqda.\n"
        "Shaxsiy ma'lumotlar guruhga chiqarilmaydi.",
        reply_markup=group_request_keyboard(
            request_id
        ),
    )

    count = await notify_matching_drivers(
        request_id
    )

    if count:

        await message.reply(
            f"🚕 <b>{count} ta mos haydovchiga "
            "buyurtma yuborildi.</b>"
        )

    else:

        await message.reply(
            "⏳ Hozircha mos haydovchi topilmadi.\n"
            "Buyurtma qidiruvda saqlanadi."
        )

    # Telegram bot foydalanuvchiga o‘zi birinchi bo‘lib DM
    # yubora olmaydi. Shuning uchun /start tavsiya qilamiz.
    if not phone or phone == "Telefon bot orqali olinadi":

        await message.reply(
            f"ℹ️ Haydovchi topilganda shaxsiy xabar olish uchun "
            f"{BOT_USERNAME} botiga <code>/start</code> yuboring."
        )


# =========================================================
# GROUP DRIVER
# =========================================================

async def process_group_driver(
    message: Message,
    parsed,
    text,
):

    driver_id = message.from_user.id

    driver = await get_driver(driver_id)

    if not driver or driver["status"] != "approved":

        await message.reply(
            "⚠️ <b>Taksi e'loni aniqlandi.</b>\n\n"
            "Lekin sizning haydovchi profilingiz "
            "hali tasdiqlanmagan.\n\n"
            f"🚗 Haydovchi sifatida ro‘yxatdan o‘tish uchun "
            f"{BOT_USERNAME} botiga /start yuboring."
        )

        return

    # Bir xil safarni qayta-qayta e'lon qilishni kamaytirish
    existing = await db_execute(
        """
        SELECT *
        FROM rides
        WHERE
            driver_id=?
            AND from_city=?
            AND to_city=?
            AND ride_time=?
            AND status='active'
        LIMIT 1
        """,
        (
            driver_id,
            parsed["from_city"],
            parsed["to_city"],
            parsed["ride_time"],
        ),
        fetchone=True,
    )

    if existing:

        await message.reply(
            "ℹ️ Sizning shu yo‘nalish va vaqtdagi "
            "faol safaringiz allaqachon mavjud."
        )

        await notify_matching_passengers(
            existing["id"]
        )

        return

    ride_id = await db_execute(
        """
        INSERT INTO rides (
            driver_id,
            from_city,
            to_city,
            ride_time,
            seats,
            available_seats,
            reserved_seats,
            status,
            source_chat_id,
            source_message_id,
            source_text,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, 'active', ?, ?, ?, ?)
        """,
        (
            driver_id,
            parsed["from_city"],
            parsed["to_city"],
            parsed["ride_time"],
            parsed["seats"],
            parsed["seats"],
            message.chat.id,
            message.message_id,
            text,
            now(),
        ),
    )

    await message.reply(
        "🚕 <b>HAYDOVCHI E'LONI QABUL QILINDI</b>\n\n"
        f"📍 {esc(parsed['from_city'])} → "
        f"{esc(parsed['to_city'])}\n"
        f"⏰ {esc(parsed['ride_time'])}\n"
        f"💺 {parsed['seats']} ta bo‘sh joy\n\n"
        "🤖 Mos yo‘lovchilarga avtomatik xabar yuboriladi."
    )

    count = await notify_matching_passengers(
        ride_id
    )

    if count:

        await message.reply(
            f"👥 {count} ta mos yo‘lovchiga "
            "taksi haqida xabar yuborildi."
        )


# =========================================================
# GROUP MESSAGE MAIN HANDLER
# =========================================================

@dp.message(
    F.chat.type.in_(
        {"group", "supergroup"}
    )
)
async def group_message_handler(message: Message):

    if not message.from_user:
        return

    if message.from_user.is_bot:
        return

    text = message.text or message.caption

    if not text:
        return

    text = text.strip()

    # Commandlarni parserga bermaymiz
    if text.startswith("/"):
        return

    enabled = await group_is_enabled(
        message.chat.id,
        message.chat.title or "",
    )

    if not enabled:
        return

    parsed = parse_group_taxi_message(text)

    if not parsed:
        return

    # Ambiguous bo‘lsa taxmin qilmaymiz
    if parsed["kind"] == "ambiguous":

        await message.reply(
            "🤖 <b>OPPERTAXI xabarni taksi e'loni "
            "sifatida aniqladi, lekin kim uchun ekanini "
            "aniq ajrata olmadi.</b>\n\n"
            "Iltimos, quyidagicha yozing:\n\n"
            "👤 Yo‘lovchi:\n"
            "<code>Toshkentdan Farg‘onaga 2 kishi, "
            "18:00 da taksi kerak</code>\n\n"
            "🚗 Haydovchi:\n"
            "<code>Toshkentdan Farg‘onaga 2 ta joy bor, "
            "18:00 da</code>"
        )

        await claim_group_message(
            message.chat.id,
            message.message_id,
            text,
            "ambiguous",
        )

        return

    # Yetishmayotgan ma'lumotlar
    if parsed["missing"]:

        missing_text = "\n".join(
            parsed["missing"]
        )

        await message.reply(
            "🤖 <b>OPPERTAXI xabarni aniqladi, "
            "lekin ma'lumot yetarli emas.</b>\n\n"
            f"{missing_text}\n\n"
            "Masalan:\n"
            "<code>Toshkentdan Farg‘onaga "
            "2 kishi 18:00 da taksi kerak</code>"
        )

        await claim_group_message(
            message.chat.id,
            message.message_id,
            text,
            "needs_info",
        )

        return

    claimed = await claim_group_message(
        message.chat.id,
        message.message_id,
        text,
        parsed["kind"],
    )

    if not claimed:
        return

    await save_user(message)

    if parsed["kind"] == "passenger":

        await process_group_passenger(
            message,
            parsed,
            text,
        )

    elif parsed["kind"] == "driver":

        await process_group_driver(
            message,
            parsed,
            text,
        )


# =========================================================
# MATCH DRIVER RIDE -> PASSENGERS
# =========================================================

async def notify_matching_passengers(ride_id):

    ride = await get_ride(ride_id)

    if not ride:
        return 0

    passengers = await db_execute(
        """
        SELECT
            p.*,
            d.full_name AS driver_name,
            d.phone AS driver_phone,
            d.car_model,
            d.car_number,
            d.rating
        FROM passenger_requests p
        JOIN driver_profiles d
            ON d.user_id=?
        WHERE
            p.status='searching'
            AND p.from_city=?
            AND p.to_city=?
            AND p.ride_time=?
            AND p.seats<=?
        ORDER BY p.id ASC
        """,
        (
            ride["driver_id"],
            ride["from_city"],
            ride["to_city"],
            ride["ride_time"],
            ride["available_seats"],
        ),
        fetchall=True,
    )

    sent = 0

    for passenger in passengers:

        text = (
            "🚕 <b>YANGI TAKSI TOPILDI!</b>\n\n"
            f"📍 {esc(ride['from_city'])} → "
            f"{esc(ride['to_city'])}\n"
            f"⏰ {esc(ride['ride_time'])}\n\n"
            f"🚗 Haydovchi: {esc(passenger['driver_name'])}\n"
            f"🚘 Mashina: {esc(passenger['car_model'])}\n"
            f"🔢 Raqam: {esc(passenger['car_number'])}\n"
            f"⭐ Reyting: {passenger['rating']:.1f}\n"
            f"📞 Telefon: <code>{esc(passenger['driver_phone'])}</code>\n\n"
            "Ushbu taksini tanlaysizmi?"
        )

        ok = await safe_send(
            passenger["passenger_id"],
            text,
            reply_markup=passenger_book_ride_keyboard(
                passenger["id"],
                ride_id,
            ),
        )

        if ok:
            sent += 1

    return sent


# =========================================================
# ADMIN / GROUP MESSAGE STATS
# =========================================================

@dp.message(Command("groupstats"))
async def group_stats(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    total = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM group_messages
        """,
        fetchone=True,
    )

    passengers = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM group_messages
        WHERE processed_type='passenger'
        """,
        fetchone=True,
    )

    drivers = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM group_messages
        WHERE processed_type='driver'
        """,
        fetchone=True,
    )

    await message.answer(
        "📊 <b>GURUH TIZIMI STATISTIKASI</b>\n\n"
        f"💬 Qayta ishlangan xabarlar: {total['c']}\n"
        f"👤 Yo‘lovchi e'lonlari: {passengers['c']}\n"
        f"🚗 Haydovchi e'lonlari: {drivers['c']}"
    )


# =========================================================
# PRIVATE FALLBACK
# =========================================================

@dp.message(F.chat.type == "private")
async def private_fallback(message: Message):

    await message.answer(
        "🤖 Buyruqni tushunmadim.\n\n"
        "Pastdagi menyudan kerakli bo‘limni tanlang.",
        reply_markup=main_menu(),
    )


# =========================================================
# HEALTH SERVER FOR RAILWAY
# =========================================================

async def health(request):
    return web.Response(
        text="OPPERTAXI BOT IS RUNNING"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health,
    )

    app.router.add_get(
        "/health",
        health,
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(
        os.getenv("PORT", "8080")
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port,
    )

    await site.start()

    print(
        f"Health server started on port {port}"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    print("OPPERTAXI BOT STARTING...")

    await init_db()

    await start_web_server()

    print("Database OK")
    print("Bot polling started")

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "OPPERTAXI BOT STOPPED"
        )
