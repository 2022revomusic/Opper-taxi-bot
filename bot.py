import os
import asyncio
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2

import aiohttp
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

DEFAULT_ADMIN_ID = 653914246

env_admin_ids = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

ADMIN_IDS = env_admin_ids or {DEFAULT_ADMIN_ID}

DB = "oper_taxi.db"

bot = Bot(token=TOKEN)
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

DRIVER_PENDING = "pending"
DRIVER_VERIFIED = "verified"
DRIVER_REJECTED = "rejected"
DRIVER_BLOCKED = "blocked"

RIDE_ACTIVE = "active"
RIDE_FULL = "full"
RIDE_CANCELLED = "cancelled"
RIDE_COMPLETED = "completed"
RIDE_BLOCKED = "blocked"

BOOKING_PENDING_DRIVER = "pending_driver"
BOOKING_ACCEPTED = "accepted"
BOOKING_REJECTED = "rejected"
BOOKING_ARRIVING = "arriving"
BOOKING_ARRIVED = "arrived"
BOOKING_ONBOARD = "onboard"
BOOKING_IN_PROGRESS = "in_progress"
BOOKING_COMPLETED = "completed"
BOOKING_CANCELLED = "cancelled"

MAX_SEATS = 4


# =========================================================
# DATABASE
# =========================================================

async def init_db():

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT,
                gender TEXT,
                age_category TEXT,
                latitude REAL,
                longitude REAL,
                location_updated TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS driver_profiles (
                telegram_id INTEGER PRIMARY KEY,
                car TEXT,
                car_number TEXT,
                license_file_id TEXT,
                vehicle_doc_file_id TEXT,
                vehicle_photo_file_id TEXT,
                status TEXT DEFAULT 'pending',
                rating REAL DEFAULT 5.0,
                rating_count INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                name TEXT,
                phone TEXT,
                role TEXT,
                from_city TEXT,
                to_city TEXT,
                date TEXT,
                time TEXT,
                car TEXT,
                car_number TEXT,
                seats TEXT,
                price TEXT,
                original_seats INTEGER DEFAULT 4,
                available_seats INTEGER DEFAULT 4,
                status TEXT DEFAULT 'active',

                pickup_latitude REAL,
                pickup_longitude REAL,

                driver_latitude REAL,
                driver_longitude REAL,
                driver_location_updated TEXT,

                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ride_id INTEGER,
                passenger_id INTEGER,
                passenger_count INTEGER,

                status TEXT DEFAULT 'pending_driver',

                passenger_latitude REAL,
                passenger_longitude REAL,

                created_at TEXT,
                accepted_at TEXT,
                completed_at TEXT,
                cancelled_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER,
                driver_id INTEGER,
                passenger_id INTEGER,
                rating INTEGER,
                comment TEXT,
                created_at TEXT
            )
        """)

        await db.commit()

        # =================================================
        # MIGRATION
        # =================================================

        async def add_column_if_missing(
            table,
            column,
            definition
        ):

            cursor = await db.execute(
                f"PRAGMA table_info({table})"
            )

            columns = await cursor.fetchall()

            existing = [row[1] for row in columns]

            if column not in existing:

                await db.execute(
                    f"ALTER TABLE {table} "
                    f"ADD COLUMN {column} {definition}"
                )

        # USERS

        await add_column_if_missing(
            "users",
            "gender",
            "TEXT"
        )

        await add_column_if_missing(
            "users",
            "age_category",
            "TEXT"
        )

        await add_column_if_missing(
            "users",
            "latitude",
            "REAL"
        )

        await add_column_if_missing(
            "users",
            "longitude",
            "REAL"
        )

        await add_column_if_missing(
            "users",
            "location_updated",
            "TEXT"
        )

        # RIDES

        await add_column_if_missing(
            "rides",
            "car_number",
            "TEXT"
        )

        await add_column_if_missing(
            "rides",
            "original_seats",
            "INTEGER DEFAULT 4"
        )

        await add_column_if_missing(
            "rides",
            "available_seats",
            "INTEGER DEFAULT 4"
        )

        await add_column_if_missing(
            "rides",
            "status",
            "TEXT DEFAULT 'active'"
        )

        await add_column_if_missing(
            "rides",
            "pickup_latitude",
            "REAL"
        )

        await add_column_if_missing(
            "rides",
            "pickup_longitude",
            "REAL"
        )

        await add_column_if_missing(
            "rides",
            "driver_latitude",
            "REAL"
        )

        await add_column_if_missing(
            "rides",
            "driver_longitude",
            "REAL"
        )

        await add_column_if_missing(
            "rides",
            "driver_location_updated",
            "TEXT"
        )

        await add_column_if_missing(
            "rides",
            "created_at",
            "TEXT"
        )

        # BOOKINGS

        await add_column_if_missing(
            "bookings",
            "status",
            "TEXT DEFAULT 'pending_driver'"
        )

        await add_column_if_missing(
            "bookings",
            "passenger_latitude",
            "REAL"
        )

        await add_column_if_missing(
            "bookings",
            "passenger_longitude",
            "REAL"
        )

        await add_column_if_missing(
            "bookings",
            "accepted_at",
            "TEXT"
        )

        await add_column_if_missing(
            "bookings",
            "completed_at",
            "TEXT"
        )

        await add_column_if_missing(
            "bookings",
            "cancelled_at",
            "TEXT"
        )

        await db.execute("""
            UPDATE rides
            SET created_at = COALESCE(
                created_at,
                ?
            )
            WHERE created_at IS NULL
        """, (
            datetime.now().isoformat(),
        ))

        await db.commit()


# =========================================================
# KEYBOARDS
# =========================================================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🚕 Haydovchi bo‘lish"),
            KeyboardButton(text="👤 Yo‘lovchi bo‘lish"),
        ],
        [
            KeyboardButton(text="🔎 Safar qidirish"),
            KeyboardButton(text="📋 Mening safarlarim"),
        ],
        [
            KeyboardButton(text="✏️ Safarni tahrirlash"),
            KeyboardButton(text="❌ Safarni bekor qilish"),
        ],
        [
            KeyboardButton(text="📍 Lokatsiyam"),
            KeyboardButton(text="👤 Profilim"),
        ],
        [
            KeyboardButton(text="⭐ Haydovchini baholash"),
        ],
        [
            KeyboardButton(text="📞 Yordam"),
        ],
    ],
    resize_keyboard=True,
)


cities = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Toshkent"),
            KeyboardButton(text="Namangan"),
        ],
        [
            KeyboardButton(text="Andijon"),
            KeyboardButton(text="Farg‘ona"),
        ],
        [
            KeyboardButton(text="Qo‘qon"),
            KeyboardButton(text="Marg‘ilon"),
        ],
        [
            KeyboardButton(text="⬅️ Bekor qilish"),
        ],
    ],
    resize_keyboard=True,
)


gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👩 Ayol"),
            KeyboardButton(text="👨 Erkak"),
        ],
        [
            KeyboardButton(text="⬅️ Bekor qilish"),
        ],
    ],
    resize_keyboard=True,
)


age_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👶 Bola"),
            KeyboardButton(text="🧑 Katta odam"),
        ],
        [
            KeyboardButton(text="⬅️ Bekor qilish"),
        ],
    ],
    resize_keyboard=True,
)


def date_keyboard():

    buttons = []

    for i in range(7):

        date = datetime.now() + timedelta(days=i)

        buttons.append([
            KeyboardButton(
                text=date.strftime("%d.%m.%Y")
            )
        ])

    buttons.append([
        KeyboardButton(text="⬅️ Bekor qilish")
    ])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def time_keyboard():

    buttons = []

    for hour in range(8, 23, 2):

        row = [
            KeyboardButton(
                text=f"{hour:02d}:00"
            )
        ]

        if hour + 1 <= 22:

            row.append(
                KeyboardButton(
                    text=f"{hour + 1:02d}:00"
                )
            )

        buttons.append(row)

    buttons.append([
        KeyboardButton(text="⬅️ Bekor qilish")
    ])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def contact_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Telefon raqamimni yuborish",
                    request_contact=True,
                )
            ],
            [
                KeyboardButton(
                    text="⬅️ Bekor qilish"
                )
            ],
        ],
        resize_keyboard=True
    )


def location_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📍 Lokatsiyamni yuborish",
                    request_location=True,
                )
            ],
            [
                KeyboardButton(
                    text="⏭ Lokatsiyasiz davom etish"
                )
            ],
            [
                KeyboardButton(
                    text="⬅️ Bekor qilish"
                )
            ],
        ],
        resize_keyboard=True
    )


def admin_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="👨‍💼 Haydovchilar"
                ),
                KeyboardButton(
                    text="📊 Statistika"
                ),
            ],
            [
                KeyboardButton(
                    text="🟡 Kutilayotgan haydovchilar"
                ),
            ],
            [
                KeyboardButton(
                    text="⬅️ Asosiy menyu"
                ),
            ],
        ],
        resize_keyboard=True
    )


def rating_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="⭐ 1"),
                KeyboardButton(text="⭐ 2"),
                KeyboardButton(text="⭐ 3"),
            ],
            [
                KeyboardButton(text="⭐ 4"),
                KeyboardButton(text="⭐ 5"),
            ],
        ],
        resize_keyboard=True
    )


# =========================================================
# INLINE BUTTONS
# =========================================================

def passenger_driver_keyboard(ride_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ TAKSINI TANLASH",
                    callback_data=f"select_driver:{ride_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ RAD ETISH",
                    callback_data=f"reject_driver:{ride_id}"
                )
            ],
        ]
    )


def driver_booking_keyboard(booking_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ BUYURTMANI QABUL QILISH",
                    callback_data=f"accept_booking:{booking_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ RAD ETISH",
                    callback_data=f"reject_booking:{booking_id}"
                )
            ],
        ]
    )


def driver_active_booking_keyboard(booking_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 LOKATSIYANI YANGILASH",
                    callback_data=f"driver_location:{booking_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📍 YO‘LOVCHINI OLDIM",
                    callback_data=f"picked_up:{booking_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ BUYURTMANI BEKOR QILISH",
                    callback_data=f"cancel_booking:{booking_id}"
                )
            ],
        ]
    )


def passenger_active_booking_keyboard(booking_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 TAKSI LOKATSIYASINI YANGILASH",
                    callback_data=f"refresh_location:{booking_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ BUYURTMANI BEKOR QILISH",
                    callback_data=f"passenger_cancel:{booking_id}"
                )
            ],
        ]
    )


def passenger_arrived_keyboard(booking_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚕 HAYDOVCHI YETIB KELDI",
                    callback_data=f"driver_arrived:{booking_id}"
                )
            ],
        ]
    )


def admin_driver_keyboard(user_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ TASDIQLASH",
                    callback_data=f"verify_driver:{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ RAD ETISH",
                    callback_data=f"reject_driver_admin:{user_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⛔ BLOKLASH",
                    callback_data=f"block_driver:{user_id}"
                ),
            ],
        ]
    )


# =========================================================
# STATES
# =========================================================

class DriverState(StatesGroup):

    name = State()
    phone = State()
    car = State()
    car_number = State()
    license = State()
    vehicle_doc = State()
    vehicle_photo = State()

    from_city = State()
    to_city = State()
    date = State()
    time = State()
    seats = State()
    price = State()
    location = State()


class PassengerState(StatesGroup):

    name = State()
    phone = State()
    gender = State()
    age_category = State()

    from_city = State()
    to_city = State()
    date = State()
    time = State()
    passengers = State()
    location = State()


class SearchState(StatesGroup):

    from_city = State()
    to_city = State()
    date = State()
    time = State()


class CancelRideState(StatesGroup):

    choose = State()


class EditRideState(StatesGroup):

    choose = State()
    field = State()
    value = State()


class RatingState(StatesGroup):

    rating = State()
    comment = State()


# =========================================================
# HELPERS
# =========================================================

def is_admin(user_id):

    return user_id in ADMIN_IDS


async def ensure_user(user_id):

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            INSERT OR IGNORE INTO users
            (telegram_id)
            VALUES (?)
        """, (
            user_id,
        ))

        await db.commit()


async def save_phone(user_id, phone):

    await ensure_user(user_id)

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE users
            SET phone = ?
            WHERE telegram_id = ?
        """, (
            phone,
            user_id,
        ))

        await db.commit()


async def update_user_location(
    user_id,
    latitude,
    longitude
):

    await ensure_user(user_id)

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE users
            SET latitude = ?,
                longitude = ?,
                location_updated = ?
            WHERE telegram_id = ?
        """, (
            latitude,
            longitude,
            datetime.now().isoformat(),
            user_id,
        ))

        await db.commit()


async def get_user_location(user_id):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT latitude, longitude
            FROM users
            WHERE telegram_id = ?
        """, (
            user_id,
        ))

        row = await cursor.fetchone()

    if not row:
        return None

    if row[0] is None or row[1] is None:
        return None

    return float(row[0]), float(row[1])


def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):

    R = 6371

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        +
        cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


async def get_route_info(
    lat1,
    lon1,
    lat2,
    lon2
):

    try:

        url = (
            "https://router.project-osrm.org/"
            "route/v1/driving/"
            f"{lon1},{lat1};{lon2},{lat2}"
            "?overview=false"
        )

        timeout = aiohttp.ClientTimeout(
            total=10
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(url) as response:

                if response.status != 200:
                    return None

                data = await response.json()

                routes = data.get(
                    "routes",
                    []
                )

                if not routes:
                    return None

                route = routes[0]

                return (
                    route["distance"] / 1000,
                    route["duration"] / 60
                )

    except Exception:

        return None


async def calculate_eta(
    lat1,
    lon1,
    lat2,
    lon2
):

    route = await get_route_info(
        lat1,
        lon1,
        lat2,
        lon2
    )

    if route:

        distance, duration = route

        return (
            distance,
            max(1, round(duration))
        )

    distance = calculate_distance(
        lat1,
        lon1,
        lat2,
        lon2
    )

    # Oddiy taxmin: 40 km/h
    duration = max(
        1,
        round((distance / 40) * 60)
    )

    return distance, duration


async def driver_status(user_id):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT status
            FROM driver_profiles
            WHERE telegram_id = ?
        """, (
            user_id,
        ))

        row = await cursor.fetchone()

    return row[0] if row else None


async def get_driver_profile(user_id):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                car,
                car_number,
                status,
                rating,
                rating_count
            FROM driver_profiles
            WHERE telegram_id = ?
        """, (
            user_id,
        ))

        return await cursor.fetchone()


async def get_driver_ride(ride_id):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                id,
                telegram_id,
                name,
                phone,
                car,
                car_number,
                from_city,
                to_city,
                date,
                time,
                available_seats,
                price,
                status,
                driver_latitude,
                driver_longitude
            FROM rides
            WHERE id = ?
            AND role = 'driver'
        """, (
            ride_id,
        ))

        return await cursor.fetchone()


async def get_booking(booking_id):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                b.id,
                b.ride_id,
                b.passenger_id,
                b.passenger_count,
                b.status,

                r.telegram_id,
                r.name,
                r.phone,
                r.car,
                r.car_number,
                r.from_city,
                r.to_city,
                r.date,
                r.time,
                r.price,
                r.driver_latitude,
                r.driver_longitude,

                b.passenger_latitude,
                b.passenger_longitude

            FROM bookings b

            JOIN rides r
                ON r.id = b.ride_id

            WHERE b.id = ?
        """, (
            booking_id,
        ))

        return await cursor.fetchone()


async def notify_user(
    user_id,
    text,
    reply_markup=None
):

    try:

        await bot.send_message(
            user_id,
            text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

        return True

    except Exception:

        return False


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await ensure_user(
        message.from_user.id
    )

    await message.answer(
        "🚕 <b>OPER TAXI</b>\n\n"
        "Vodiy ↔ Toshkent yo‘nalishida "
        "haydovchi va yo‘lovchilarni "
        "bog‘lovchi taxi xizmati.\n\n"
        "Kerakli bo‘limni tanlang 👇",
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================================================
# GLOBAL CANCEL
# =========================================================

@dp.message(F.text == "⬅️ Bekor qilish")
async def global_cancel(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await message.answer(
        "✅ Amal bekor qilindi.",
        reply_markup=main_menu
    )


# =========================================================
# LOCATION
# =========================================================

@dp.message(F.text == "📍 Lokatsiyam")
async def my_location(message: Message):

    await message.answer(
        "📍 Lokatsiyangizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📍 Lokatsiyamni yuborish",
                        request_location=True
                    )
                ],
                [
                    KeyboardButton(
                        text="⬅️ Bekor qilish"
                    )
                ],
            ],
            resize_keyboard=True
        )
    )


@dp.message(F.location)
async def receive_location(
    message: Message,
    state: FSMContext
):

    location = message.location

    await update_user_location(
        message.from_user.id,
        location.latitude,
        location.longitude
    )

    current_state = await state.get_state()

    # Yo‘lovchi buyurtma yaratish jarayonida
    if current_state == PassengerState.location.state:

        await state.update_data(
            pickup_latitude=location.latitude,
            pickup_longitude=location.longitude
        )

        await passenger_finish(
            message,
            state
        )

        return

    # Haydovchi yangi safar joylashtirishda
    if current_state == DriverState.location.state:

        await state.update_data(
            driver_latitude=location.latitude,
            driver_longitude=location.longitude
        )

        await create_driver_ride(
            message,
            state
        )

        return

    await message.answer(
        "✅ Lokatsiyangiz saqlandi.",
        reply_markup=main_menu
    )


# =========================================================
# DRIVER REGISTRATION START
# =========================================================

@dp.message(F.text == "🚕 Haydovchi bo‘lish")
async def driver_start(
    message: Message,
    state: FSMContext
):

    await state.clear()

    status = await driver_status(
        message.from_user.id
    )

    if status == DRIVER_PENDING:

        await message.answer(
            "🟡 <b>Hujjatlaringiz tekshirilmoqda.</b>\n\n"
            "Admin tasdiqlagandan keyin "
            "safar joylashtira olasiz.",
            reply_markup=main_menu,
            parse_mode="HTML"
        )

        return

    if status == DRIVER_BLOCKED:

        await message.answer(
            "⛔ Haydovchi profilingiz bloklangan.",
            reply_markup=main_menu
        )

        return

    if status == DRIVER_VERIFIED:

        await start_driver_ride(
            message,
            state
        )

        return

    await state.set_state(
        DriverState.name
    )

    await message.answer(
        "🚕 <b>Haydovchi ro‘yxatdan o‘tishi</b>\n\n"
        "Ism-familiyangizni yozing:",
        parse_mode="HTML"
    )


# =========================================================
# DRIVER REGISTRATION
# =========================================================

@dp.message(DriverState.name)
async def driver_name(
    message: Message,
    state: FSMContext
):

    await ensure_user(
        message.from_user.id
    )

    await state.update_data(
        name=message.text
    )

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE users
            SET name = ?
            WHERE telegram_id = ?
        """, (
            message.text,
            message.from_user.id
        ))

        await db.commit()

    await state.set_state(
        DriverState.phone
    )

    await message.answer(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=contact_keyboard()
    )


@dp.message(
    DriverState.phone,
    F.contact
)
async def driver_phone_contact(
    message: Message,
    state: FSMContext
):

    phone = message.contact.phone_number

    await save_phone(
        message.from_user.id,
        phone
    )

    await state.update_data(
        phone=phone
    )

    await state.set_state(
        DriverState.car
    )

    await message.answer(
        "🚗 Avtomobilingiz markasi va modelini yozing.\n\n"
        "Masalan: Chevrolet Cobalt"
    )


@dp.message(DriverState.phone)
async def driver_phone_text(
    message: Message,
    state: FSMContext
):

    phone = message.text

    await save_phone(
        message.from_user.id,
        phone
    )

    await state.update_data(
        phone=phone
    )

    await state.set_state(
        DriverState.car
    )

    await message.answer(
        "🚗 Avtomobilingiz markasi va modelini yozing."
    )


@dp.message(DriverState.car)
async def driver_car(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        car=message.text
    )

    await state.set_state(
        DriverState.car_number
    )

    await message.answer(
        "🔢 Avtomobil davlat raqamingizni yozing.\n\n"
        "Masalan: 01 A 123 BC"
    )


@dp.message(DriverState.car_number)
async def driver_car_number(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        car_number=message.text.upper()
    )

    await state.set_state(
        DriverState.license
    )

    await message.answer(
        "🪪 Haydovchilik guvohnomangiz "
        "rasmini yuboring."
    )


@dp.message(
    DriverState.license,
    F.photo
)
async def driver_license(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        license_file_id=message.photo[-1].file_id
    )

    await state.set_state(
        DriverState.vehicle_doc
    )

    await message.answer(
        "📄 Avtomobil texpasporti yoki "
        "tegishli hujjat rasmini yuboring."
    )


@dp.message(DriverState.license)
async def driver_license_invalid(message: Message):

    await message.answer(
        "❗ Iltimos, haydovchilik "
        "guvohnomasining rasmini yuboring."
    )


@dp.message(
    DriverState.vehicle_doc,
    F.photo
)
async def driver_vehicle_doc(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        vehicle_doc_file_id=message.photo[-1].file_id
    )

    await state.set_state(
        DriverState.vehicle_photo
    )

    await message.answer(
        "📸 Avtomobilingizning rasmini yuboring."
    )


@dp.message(DriverState.vehicle_doc)
async def driver_vehicle_doc_invalid(
    message: Message
):

    await message.answer(
        "❗ Iltimos, avtomobil hujjatining "
        "rasmini yuboring."
    )


@dp.message(
    DriverState.vehicle_photo,
    F.photo
)
async def driver_vehicle_photo(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        vehicle_photo_file_id=message.photo[-1].file_id
    )

    data = await state.get_data()

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            INSERT INTO driver_profiles
            (
                telegram_id,
                car,
                car_number,
                license_file_id,
                vehicle_doc_file_id,
                vehicle_photo_file_id,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                car = excluded.car,
                car_number = excluded.car_number,
                license_file_id =
                    excluded.license_file_id,
                vehicle_doc_file_id =
                    excluded.vehicle_doc_file_id,
                vehicle_photo_file_id =
                    excluded.vehicle_photo_file_id,
                status = excluded.status,
                created_at = excluded.created_at
        """, (
            message.from_user.id,
            data["car"],
            data["car_number"],
            data["license_file_id"],
            data["vehicle_doc_file_id"],
            data["vehicle_photo_file_id"],
            DRIVER_PENDING,
            datetime.now().isoformat()
        ))

        await db.commit()

    for admin_id in ADMIN_IDS:

        try:

            await bot.send_message(
                admin_id,
                "🆕 <b>YANGI HAYDOVCHI TEKSHIRUVI</b>\n\n"
                f"👤 Ism: {data['name']}\n"
                f"📱 Telefon: {data['phone']}\n"
                f"🚗 Avtomobil: {data['car']}\n"
                f"🔢 Raqam: {data['car_number']}\n"
                f"🆔 Telegram ID: "
                f"<code>{message.from_user.id}</code>",
                parse_mode="HTML",
                reply_markup=admin_driver_keyboard(
                    message.from_user.id
                )
            )

            await bot.send_photo(
                admin_id,
                data["license_file_id"],
                caption="🪪 Haydovchilik guvohnomasi"
            )

            await bot.send_photo(
                admin_id,
                data["vehicle_doc_file_id"],
                caption="📄 Avtomobil hujjati"
            )

            await bot.send_photo(
                admin_id,
                data["vehicle_photo_file_id"],
                caption="🚗 Avtomobil rasmi"
            )

        except Exception:
            pass

    await state.clear()

    await message.answer(
        "🟡 <b>Hujjatlaringiz yuborildi.</b>\n\n"
        "Admin hujjatlarni tekshiradi.\n"
        "Tasdiqlangandan keyin sizga "
        "xabar keladi.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )


@dp.message(DriverState.vehicle_photo)
async def driver_vehicle_photo_invalid(
    message: Message
):

    await message.answer(
        "❗ Iltimos, avtomobil rasmini yuboring."
    )


# =========================================================
# DRIVER NEW RIDE
# =========================================================

async def start_driver_ride(
    message: Message,
    state: FSMContext
):

    profile = await get_driver_profile(
        message.from_user.id
    )

    if not profile:
        return

    if profile[2] != DRIVER_VERIFIED:

        await message.answer(
            "⛔ Siz tasdiqlangan haydovchi emassiz.",
            reply_markup=main_menu
        )

        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT name, phone
            FROM users
            WHERE telegram_id = ?
        """, (
            message.from_user.id,
        ))

        user = await cursor.fetchone()

    await state.update_data(
        car=profile[0],
        car_number=profile[1],
        name=user[0] if user else "",
        phone=user[1] if user else "",
    )

    await state.set_state(
        DriverState.from_city
    )

    await message.answer(
        "🟢 <b>Haydovchi tasdiqlangan.</b>\n\n"
        "📍 Qayerdan ketasiz?",
        reply_markup=cities,
        parse_mode="HTML"
    )


@dp.message(DriverState.from_city)
async def driver_from(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:

        await message.answer(
            "❗ Shaharni tugmalardan tanlang.",
            reply_markup=cities
        )

        return

    await state.update_data(
        from_city=message.text
    )

    await state.set_state(
        DriverState.to_city
    )

    await message.answer(
        "📍 Qayerga borasiz?",
        reply_markup=cities
    )


@dp.message(DriverState.to_city)
async def driver_to(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:

        await message.answer(
            "❗ Shaharni tugmalardan tanlang.",
            reply_markup=cities
        )

        return

    data = await state.get_data()

    if message.text == data["from_city"]:

        await message.answer(
            "❗ Qayerdan va qayerga "
            "bir xil bo‘lishi mumkin emas."
        )

        return

    await state.update_data(
        to_city=message.text
    )

    await state.set_state(
        DriverState.date
    )

    await message.answer(
        "📅 Safar sanasini tanlang:",
        reply_markup=date_keyboard()
    )


@dp.message(DriverState.date)
async def driver_date(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        date=message.text
    )

    await state.set_state(
        DriverState.time
    )

    await message.answer(
        "⏰ Jo‘nash vaqtini tanlang:",
        reply_markup=time_keyboard()
    )


@dp.message(DriverState.time)
async def driver_time(
    message: Message,
    state: FSMContext
):

    if not message.text.endswith(":00"):

        await message.answer(
            "❗ Vaqtni tugmalardan tanlang.",
            reply_markup=time_keyboard()
        )

        return

    await state.update_data(
        time=message.text
    )

    await state.set_state(
        DriverState.seats
    )

    await message.answer(
        "💺 Nechta yo‘lovchi joyi bor?\n\n"
        "1 dan 4 gacha yozing."
    )


@dp.message(DriverState.seats)
async def driver_seats(
    message: Message,
    state: FSMContext
):

    try:

        seats = int(message.text)

    except ValueError:

        await message.answer(
            "❗ 1 dan 4 gacha raqam yozing."
        )

        return

    if not 1 <= seats <= 4:

        await message.answer(
            "❗ Joylar soni 1 dan 4 gacha."
        )

        return

    await state.update_data(
        seats=seats
    )

    await state.set_state(
        DriverState.price
    )

    await message.answer(
        "💰 Bir yo‘lovchi uchun narxni yozing.\n\n"
        "Masalan: 150000 so‘m"
    )


@dp.message(DriverState.price)
async def driver_price(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        price=message.text
    )

    await state.set_state(
        DriverState.location
    )

    await message.answer(
        "📍 Hozirgi lokatsiyangizni yuboring.\n\n"
        "Bu yo‘lovchiga taksining joylashuvini "
        "ko‘rsatish uchun kerak.\n\n"
        "Majburiy emas.",
        reply_markup=location_keyboard()
    )


@dp.message(
    DriverState.location,
    F.text == "⏭ Lokatsiyasiz davom etish"
)
async def driver_without_location(
    message: Message,
    state: FSMContext
):

    await create_driver_ride(
        message,
        state
    )


async def create_driver_ride(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    status = await driver_status(
        message.from_user.id
    )

    if status != DRIVER_VERIFIED:

        await state.clear()

        await message.answer(
            "⛔ Haydovchi profilingiz "
            "tasdiqlanmagan.",
            reply_markup=main_menu
        )

        return

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            INSERT INTO rides
            (
                telegram_id,
                name,
                phone,
                role,
                from_city,
                to_city,
                date,
                time,
                car,
                car_number,
                seats,
                price,
                original_seats,
                available_seats,
                status,
                driver_latitude,
                driver_longitude,
                driver_location_updated,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.from_user.id,
            data["name"],
            data["phone"],
            "driver",
            data["from_city"],
            data["to_city"],
            data["date"],
            data["time"],
            data["car"],
            data["car_number"],
            str(data["seats"]),
            data["price"],
            data["seats"],
            data["seats"],
            RIDE_ACTIVE,
            data.get("driver_latitude"),
            data.get("driver_longitude"),
            datetime.now().isoformat()
            if data.get("driver_latitude")
            else None,
            datetime.now().isoformat()
        ))

        await db.commit()

    await state.clear()

    await message.answer(
        "✅ <b>Safaringiz joylandi!</b>\n\n"
        f"📍 {data['from_city']} → "
        f"{data['to_city']}\n"
        f"📅 {data['date']}\n"
        f"⏰ {data['time']}\n"
        f"🚗 {data['car']}\n"
        f"🔢 {data['car_number']}\n"
        f"💺 Bo‘sh joy: {data['seats']}\n"
        f"💰 Narx: {data['price']}\n\n"
        "🤖 Yo‘lovchilar sizning safaringizni "
        "ko‘rib, taksini tanlashi mumkin.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================================================
# PASSENGER REGISTRATION
# =========================================================

@dp.message(F.text == "👤 Yo‘lovchi bo‘lish")
async def passenger_start(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await state.set_state(
        PassengerState.name
    )

    await message.answer(
        "👤 <b>Yo‘lovchi</b>\n\n"
        "Ismingizni yozing:",
        parse_mode="HTML"
    )


@dp.message(PassengerState.name)
async def passenger_name(
    message: Message,
    state: FSMContext
):

    await ensure_user(
        message.from_user.id
    )

    await state.update_data(
        name=message.text
    )

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE users
            SET name = ?
            WHERE telegram_id = ?
        """, (
            message.text,
            message.from_user.id
        ))

        await db.commit()

    await state.set_state(
        PassengerState.phone
    )

    await message.answer(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=contact_keyboard()
    )


@dp.message(
    PassengerState.phone,
    F.contact
)
async def passenger_phone_contact(
    message: Message,
    state: FSMContext
):

    phone = message.contact.phone_number

    await save_phone(
        message.from_user.id,
        phone
    )

    await state.update_data(
        phone=phone
    )

    await state.set_state(
        PassengerState.gender
    )

    await message.answer(
        "👤 Jinsingizni tanlang:",
        reply_markup=gender_keyboard
    )


@dp.message(PassengerState.phone)
async def passenger_phone_text(
    message: Message,
    state: FSMContext
):

    await save_phone(
        message.from_user.id,
        message.text
    )

    await state.update_data(
        phone=message.text
    )

    await state.set_state(
        PassengerState.gender
    )

    await message.answer(
        "👤 Jinsingizni tanlang:",
        reply_markup=gender_keyboard
    )


@dp.message(PassengerState.gender)
async def passenger_gender(
    message: Message,
    state: FSMContext
):

    if message.text not in [
        "👩 Ayol",
        "👨 Erkak"
    ]:

        await message.answer(
            "❗ Tugmalardan tanlang.",
            reply_markup=gender_keyboard
        )

        return

    await state.update_data(
        gender=message.text
    )

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE users
            SET gender = ?
            WHERE telegram_id = ?
        """, (
            message.text,
            message.from_user.id
        ))

        await db.commit()

    await state.set_state(
        PassengerState.age_category
    )

    await message.answer(
        "🎂 Yosh toifasini tanlang:",
        reply_markup=age_keyboard
    )


@dp.message(PassengerState.age_category)
async def passenger_age(
    message: Message,
    state: FSMContext
):

    if message.text not in [
        "👶 Bola",
        "🧑 Katta odam"
    ]:

        await message.answer(
            "❗ Tugmalardan tanlang.",
            reply_markup=age_keyboard
        )

        return

    await state.update_data(
        age_category=message.text
    )

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE users
            SET age_category = ?
            WHERE telegram_id = ?
        """, (
            message.text,
            message.from_user.id
        ))

        await db.commit()

    await state.set_state(
        PassengerState.from_city
    )

    await message.answer(
        "📍 Qayerdan ketasiz?",
        reply_markup=cities
    )


@dp.message(PassengerState.from_city)
async def passenger_from(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:

        await message.answer(
            "❗ Shaharni tugmalardan tanlang.",
            reply_markup=cities
        )

        return

    await state.update_data(
        from_city=message.text
    )

    await state.set_state(
        PassengerState.to_city
    )

    await message.answer(
        "📍 Qayerga borasiz?",
        reply_markup=cities
    )


@dp.message(PassengerState.to_city)
async def passenger_to(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:

        await message.answer(
            "❗ Shaharni tugmalardan tanlang.",
            reply_markup=cities
        )

        return

    data = await state.get_data()

    if message.text == data["from_city"]:

        await message.answer(
            "❗ Qayerdan va qayerga "
            "bir xil bo‘lishi mumkin emas."
        )

        return

    await state.update_data(
        to_city=message.text
    )

    await state.set_state(
        PassengerState.date
    )

    await message.answer(
        "📅 Safar sanasini tanlang:",
        reply_markup=date_keyboard()
    )


@dp.message(PassengerState.date)
async def passenger_date(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        date=message.text
    )

    await state.set_state(
        PassengerState.time
    )

    await message.answer(
        "⏰ Qaysi vaqtda ketmoqchisiz?",
        reply_markup=time_keyboard()
    )


@dp.message(PassengerState.time)
async def passenger_time(
    message: Message,
    state: FSMContext
):

    if not message.text.endswith(":00"):

        await message.answer(
            "❗ Vaqtni tugmalardan tanlang.",
            reply_markup=time_keyboard()
        )

        return

    await state.update_data(
        time=message.text
    )

    await state.set_state(
        PassengerState.passengers
    )

    await message.answer(
        "👥 Nechta yo‘lovchi bor?\n\n"
        "1 dan 4 gacha raqam yozing."
    )


@dp.message(PassengerState.passengers)
async def passenger_passengers(
    message: Message,
    state: FSMContext
):

    try:

        count = int(message.text)

    except ValueError:

        await message.answer(
            "❗ 1 dan 4 gacha raqam yozing."
        )

        return

    if not 1 <= count <= 4:

        await message.answer(
            "❗ 1 dan 4 gacha raqam yozing."
        )

        return

    await state.update_data(
        passengers=count
    )

    await state.set_state(
        PassengerState.location
    )

    await message.answer(
        "📍 Olish joyingiz lokatsiyasini yuboring.\n\n"
        "Bu haydovchiga sizni topishga yordam beradi.\n\n"
        "Lokatsiya majburiy emas.",
        reply_markup=location_keyboard()
    )


@dp.message(
    PassengerState.location,
    F.text == "⏭ Lokatsiyasiz davom etish"
)
async def passenger_without_location(
    message: Message,
    state: FSMContext
):

    await passenger_finish(
        message,
        state
    )


# =========================================================
# PASSENGER FINISH
# =========================================================

async def passenger_finish(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    passenger_id = message.from_user.id
    passenger_count = int(
        data["passengers"]
    )

    pickup_lat = data.get(
        "pickup_latitude"
    )

    pickup_lon = data.get(
        "pickup_longitude"
    )

    await state.clear()

    # Haydovchilarni qidiramiz.
    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                id,
                telegram_id,
                name,
                phone,
                car,
                car_number,
                from_city,
                to_city,
                date,
                time,
                available_seats,
                price,
                driver_latitude,
                driver_longitude
            FROM rides
            WHERE role = 'driver'
            AND from_city = ?
            AND to_city = ?
            AND date = ?
            AND time = ?
            AND status = 'active'
            AND available_seats >= ?
            AND telegram_id != ?
            ORDER BY id DESC
        """, (
            data["from_city"],
            data["to_city"],
            data["date"],
            data["time"],
            passenger_count,
            passenger_id
        ))

        drivers = await cursor.fetchall()

    if not drivers:

        await message.answer(
            "😔 <b>Mos taksi topilmadi.</b>\n\n"
            f"📍 {data['from_city']} → "
            f"{data['to_city']}\n"
            f"📅 {data['date']}\n"
            f"⏰ {data['time']}\n"
            f"👥 {passenger_count} kishi\n\n"
            "Keyinroq yana qidirib ko‘rishingiz mumkin.",
            reply_markup=main_menu,
            parse_mode="HTML"
        )

        return

    await message.answer(
        f"🚕 <b>{len(drivers)} ta mos taksi topildi!</b>\n\n"
        "Sizga mos taksilar quyida ko‘rsatiladi.\n"
        "O‘zingiz xohlagan taksini tanlang.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )

    for driver in drivers:

        (
            ride_id,
            driver_id,
            driver_name,
            driver_phone,
            car,
            car_number,
            from_city,
            to_city,
            date,
            time,
            available,
            price,
            driver_lat,
            driver_lon
        ) = driver

        profile = await get_driver_profile(
            driver_id
        )

        rating = 5.0
        rating_count = 0

        if profile:

            rating = float(
                profile[3] or 5.0
            )

            rating_count = int(
                profile[4] or 0
            )

        location_info = ""

        if (
            pickup_lat is not None
            and pickup_lon is not None
            and driver_lat is not None
            and driver_lon is not None
        ):

            distance, eta = await calculate_eta(
                pickup_lat,
                pickup_lon,
                driver_lat,
                driver_lon
            )

            location_info = (
                f"📏 Masofa: {distance:.1f} km\n"
                f"⏱ ETA: {eta} daqiqa\n"
            )

        else:

            location_info = (
                "📍 Lokatsiya ma'lumoti mavjud emas.\n"
            )

        text = (
            "🚕 <b>MOS TAKSI</b>\n\n"
            f"👤 Haydovchi: {driver_name}\n"
            f"⭐ Reyting: {rating:.1f}"
            f" ({rating_count} ta baho)\n"
            f"🚗 Mashina: {car}\n"
            f"🔢 Raqam: {car_number}\n"
            f"💺 Bo‘sh joy: {available}\n"
            f"💰 Narx: {price}\n"
            f"📍 {from_city} → {to_city}\n"
            f"📅 {date}\n"
            f"⏰ {time}\n\n"
            f"{location_info}\n"
            "👇 Shu taksini xohlasangiz tanlang."
        )

        await message.answer(
            text,
            reply_markup=passenger_driver_keyboard(
                ride_id
            ),
            parse_mode="HTML"
        )

    # Vaqtinchalik yo‘lovchi ma’lumotini saqlash
    # alohida jadval kerak emas — callback kelganda
    # foydalanuvchining eng oxirgi faol so‘rovi sifatida
    # passenger request ride yaratamiz.

    async with aiosqlite.connect(DB) as db:

        # eski pending passenger rides
        await db.execute("""
            UPDATE rides
            SET status = 'cancelled'
            WHERE telegram_id = ?
            AND role = 'passenger'
            AND status = 'active'
        """, (
            passenger_id,
        ))

        await db.execute("""
            INSERT INTO rides
            (
                telegram_id,
                name,
                phone,
                role,
                from_city,
                to_city,
                date,
                time,
                seats,
                original_seats,
                available_seats,
                status,
                pickup_latitude,
                pickup_longitude,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            passenger_id,
            data["name"],
            data["phone"],
            "passenger",
            data["from_city"],
            data["to_city"],
            data["date"],
            data["time"],
            str(passenger_count),
            passenger_count,
            passenger_count,
            RIDE_ACTIVE,
            pickup_lat,
            pickup_lon,
            datetime.now().isoformat()
        ))

        await db.commit()


# =========================================================
# PASSENGER SELECT DRIVER
# =========================================================

@dp.callback_query(
    F.data.startswith("select_driver:")
)
async def select_driver(
    callback: CallbackQuery
):

    ride_id = int(
        callback.data.split(":")[1]
    )

    passenger_id = callback.from_user.id

    async with aiosqlite.connect(DB) as db:

        # Yo‘lovchining oxirgi faol so‘rovi
        cursor = await db.execute("""
            SELECT
                id,
                name,
                phone,
                from_city,
                to_city,
                date,
                time,
                seats,
                pickup_latitude,
                pickup_longitude
            FROM rides
            WHERE telegram_id = ?
            AND role = 'passenger'
            AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
        """, (
            passenger_id,
        ))

        passenger = await cursor.fetchone()

        if not passenger:

            await callback.answer(
                "❗ Faol buyurtma topilmadi.",
                show_alert=True
            )

            return

        # Taksi
        cursor = await db.execute("""
            SELECT
                id,
                telegram_id,
                name,
                phone,
                car,
                car_number,
                available_seats,
                price,
                from_city,
                to_city,
                date,
                time,
                status
            FROM rides
            WHERE id = ?
            AND role = 'driver'
        """, (
            ride_id,
        ))

        driver = await cursor.fetchone()

        if not driver:

            await callback.answer(
                "❗ Taksi topilmadi.",
                show_alert=True
            )

            return

        (
            passenger_ride_id,
            passenger_name,
            passenger_phone,
            from_city,
            to_city,
            date,
            time,
            passenger_count,
            pickup_lat,
            pickup_lon
        ) = passenger

        (
            driver_ride_id,
            driver_id,
            driver_name,
            driver_phone,
            car,
            car_number,
            available,
            price,
            driver_from,
            driver_to,
            driver_date,
            driver_time,
            driver_status
        ) = driver

        if driver_status != RIDE_ACTIVE:

            await callback.answer(
                "❗ Bu taksi endi mavjud emas.",
                show_alert=True
            )

            return

        if int(available) < int(passenger_count):

            await callback.answer(
                "❗ Bu taksida yetarli joy qolmagan.",
                show_alert=True
            )

            return

        # Bir xil buyurtmani qayta yuborishni bloklaymiz
        cursor = await db.execute("""
            SELECT id
            FROM bookings
            WHERE ride_id = ?
            AND passenger_id = ?
            AND status IN (
                'pending_driver',
                'accepted',
                'arriving',
                'arrived',
                'onboard',
                'in_progress'
            )
        """, (
            driver_ride_id,
            passenger_id
        ))

        existing = await cursor.fetchone()

        if existing:

            await callback.answer(
                "ℹ️ Bu taksiga buyurtma allaqachon yuborilgan.",
                show_alert=True
            )

            return

        cursor = await db.execute("""
            INSERT INTO bookings
            (
                ride_id,
                passenger_id,
                passenger_count,
                status,
                passenger_latitude,
                passenger_longitude,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            driver_ride_id,
            passenger_id,
            passenger_count,
            BOOKING_PENDING_DRIVER,
            pickup_lat,
            pickup_lon,
            datetime.now().isoformat()
        ))

        booking_id = cursor.lastrowid

        await db.commit()

    await callback.answer(
        "✅ Buyurtma haydovchiga yuborildi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    # Haydovchiga lokatsiya va buyurtma yuboriladi
    location_info = ""

    if (
        pickup_lat is not None
        and pickup_lon is not None
    ):

        try:

            await bot.send_location(
                driver_id,
                latitude=pickup_lat,
                longitude=pickup_lon
            )

            location_info = (
                "📍 Yo‘lovchining olish lokatsiyasi "
                "yuqoridagi xaritada."
            )

        except Exception:
            location_info = (
                "📍 Yo‘lovchi lokatsiya yuborgan."
            )

    else:

        location_info = (
            "📍 Yo‘lovchi lokatsiya yubormagan."
        )

    text = (
        "🔔 <b>YANGI BUYURTMA!</b>\n\n"
        f"👤 Yo‘lovchi: {passenger_name}\n"
        f"📱 Telefon: {passenger_phone}\n"
        f"👥 Yo‘lovchilar: {passenger_count}\n\n"
        f"📍 {from_city} → {to_city}\n"
        f"📅 {date}\n"
        f"⏰ {time}\n"
        f"💰 Jami: {price} × {passenger_count}\n\n"
        f"{location_info}\n\n"
        "❓ Buyurtmani qabul qilasizmi?"
    )

    await notify_user(
        driver_id,
        text,
        driver_booking_keyboard(
            booking_id
        )
    )


# =========================================================
# PASSENGER REJECT DRIVER
# =========================================================

@dp.callback_query(
    F.data.startswith("reject_driver:")
)
async def reject_driver_selection(
    callback: CallbackQuery
):

    await callback.answer(
        "Taksi rad etildi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )


# =========================================================
# DRIVER ACCEPT BOOKING
# =========================================================

@dp.callback_query(
    F.data.startswith("accept_booking:")
)
async def accept_booking(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    driver_id = callback.from_user.id

    async with aiosqlite.connect(DB) as db:

        # Transaction
        await db.execute(
            "BEGIN IMMEDIATE"
        )

        cursor = await db.execute("""
            SELECT
                b.id,
                b.ride_id,
                b.passenger_id,
                b.passenger_count,
                b.status,

                r.telegram_id,
                r.name,
                r.phone,
                r.car,
                r.car_number,
                r.available_seats,
                r.price,
                r.status,
                r.from_city,
                r.to_city,
                r.date,
                r.time,

                b.passenger_latitude,
                b.passenger_longitude

            FROM bookings b

            JOIN rides r
                ON r.id = b.ride_id

            WHERE b.id = ?
            AND r.telegram_id = ?
        """, (
            booking_id,
            driver_id
        ))

        booking = await cursor.fetchone()

        if not booking:

            await db.rollback()

            await callback.answer(
                "❗ Buyurtma topilmadi.",
                show_alert=True
            )

            return

        (
            b_id,
            ride_id,
            passenger_id,
            passenger_count,
            booking_status,
            ride_driver_id,
            driver_name,
            driver_phone,
            car,
            car_number,
            available,
            price,
            ride_status,
            from_city,
            to_city,
            date,
            time,
            passenger_lat,
            passenger_lon
        ) = booking

        if booking_status != BOOKING_PENDING_DRIVER:

            await db.rollback()

            await callback.answer(
                "ℹ️ Bu buyurtma allaqachon ko‘rib chiqilgan.",
                show_alert=True
            )

            return

        if ride_status != RIDE_ACTIVE:

            await db.rollback()

            await callback.answer(
                "❗ Safar endi faol emas.",
                show_alert=True
            )

            return

        available = int(
            available or 0
        )

        passenger_count = int(
            passenger_count
        )

        if available < passenger_count:

            await db.rollback()

            await callback.answer(
                "❗ Yetarli bo‘sh joy qolmagan.",
                show_alert=True
            )

            return

        new_available = (
            available - passenger_count
        )

        new_ride_status = (
            RIDE_FULL
            if new_available == 0
            else RIDE_ACTIVE
        )

        await db.execute("""
            UPDATE rides
            SET available_seats = ?,
                seats = ?,
                status = ?
            WHERE id = ?
        """, (
            new_available,
            str(new_available),
            new_ride_status,
            ride_id
        ))

        await db.execute("""
            UPDATE bookings
            SET status = ?,
                accepted_at = ?
            WHERE id = ?
        """, (
            BOOKING_ACCEPTED,
            datetime.now().isoformat(),
            booking_id
        ))

        await db.commit()

    await callback.answer(
        "✅ Buyurtma qabul qilindi!"
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    # Yo‘lovchiga xabar
    location_text_value = ""

    if (
        passenger_lat is not None
        and passenger_lon is not None
    ):

        try:

            await bot.send_location(
                passenger_id,
                latitude=passenger_lat,
                longitude=passenger_lon
            )

            location_text_value = (
                "📍 Sizning olish lokatsiyangiz "
                "haydovchiga yuborildi."
            )

        except Exception:
            pass

    text = (
        "🟢 <b>TAKSI BUYURTMANI QABUL QILDI!</b>\n\n"
        f"🚗 Mashina: {car}\n"
        f"🔢 Raqam: {car_number}\n"
        f"👤 Haydovchi: {driver_name}\n\n"
        f"📍 {from_city} → {to_city}\n"
        f"📅 {date}\n"
        f"⏰ {time}\n"
        f"👥 Siz: {passenger_count} kishi\n"
        f"💰 Narx: {price}\n\n"
        "🚕 <b>TAKSI SIZ TOMONGA KELMOQDA.</b>\n\n"
        f"{location_text_value}"
    )

    await notify_user(
        passenger_id,
        text,
        passenger_active_booking_keyboard(
            booking_id
        )
    )

    await notify_user(
        driver_id,
        "🟢 <b>BUYURTMA QABUL QILINDI!</b>\n\n"
        f"👤 Yo‘lovchi: {booking[6]}\n"
        f"👥 {passenger_count} kishi\n"
        f"📍 {from_city} → {to_city}\n\n"
        "🚕 Endi yo‘lovchi tomon yo‘l olishingiz mumkin.",
        driver_active_booking_keyboard(
            booking_id
        )
    )


# =========================================================
# DRIVER REJECT BOOKING
# =========================================================

@dp.callback_query(
    F.data.startswith("reject_booking:")
)
async def reject_booking(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    driver_id = callback.from_user.id

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                b.passenger_id,
                b.status,
                r.telegram_id
            FROM bookings b
            JOIN rides r
                ON r.id = b.ride_id
            WHERE b.id = ?
            AND r.telegram_id = ?
        """, (
            booking_id,
            driver_id
        ))

        row = await cursor.fetchone()

        if not row:

            await callback.answer(
                "❗ Buyurtma topilmadi.",
                show_alert=True
            )

            return

        passenger_id, status, _ = row

        if status != BOOKING_PENDING_DRIVER:

            await callback.answer(
                "ℹ️ Bu buyurtma allaqachon ko‘rilgan.",
                show_alert=True
            )

            return

        await db.execute("""
            UPDATE bookings
            SET status = ?
            WHERE id = ?
        """, (
            BOOKING_REJECTED,
            booking_id
        ))

        await db.commit()

    await callback.answer(
        "Buyurtma rad etildi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await notify_user(
        passenger_id,
        "🔴 <b>Haydovchi buyurtmangizni rad etdi.</b>\n\n"
        "Boshqa taksini tanlashingiz mumkin.",
        main_menu
    )


# =========================================================
# DRIVER LOCATION UPDATE
# =========================================================

@dp.callback_query(
    F.data.startswith("driver_location:")
)
async def driver_location_button(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    await callback.answer(
        "📍 Lokatsiya yuborish tugmasini bosing."
    )

    await callback.message.answer(
        "📍 <b>Hozirgi lokatsiyangizni yuboring.</b>\n\n"
        "Telegramdagi lokatsiya tugmasidan foydalaning.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📍 Lokatsiyani yuborish",
                        request_location=True
                    )
                ]
            ],
            resize_keyboard=True
        )
    )

    # Keyingi location handler uchun vaqtinchalik FSM
    # callback orqali state qo‘yish mumkin emas,
    # shuning uchun booking ID ni userga bog‘laymiz.
    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                ride_id
            FROM bookings
            WHERE id = ?
            AND status IN (
                'accepted',
                'arriving',
                'arrived'
            )
        """, (
            booking_id,
        ))

        row = await cursor.fetchone()

    if row:

        # Bu ma'lumotni bot ichidagi DB emas,
        # FSM orqali saqlash uchun dispatcher state
        # olish kerak.
        # Amaliyotda foydalanuvchi location yuborganda
        # oxirgi faol booking topiladi.
        pass


# =========================================================
# RAW DRIVER LOCATION FOR ACTIVE BOOKING
# =========================================================

@dp.message(F.location)
async def active_location_handler(
    message: Message,
    state: FSMContext
):

    # Bu handler yuqoridagi umumiy location handlerdan
    # keyin ham ishlashi mumkin emasligi uchun asl
    # location oqimini shu yerda boshqaramiz.
    #
    # Avval foydalanuvchi holatini tekshiramiz.

    current_state = await state.get_state()

    # FSM orqali yangi safar uchun location
    if current_state == PassengerState.location.state:

        location = message.location

        await update_user_location(
            message.from_user.id,
            location.latitude,
            location.longitude
        )

        await state.update_data(
            pickup_latitude=location.latitude,
            pickup_longitude=location.longitude
        )

        await passenger_finish(
            message,
            state
        )

        return

    if current_state == DriverState.location.state:

        location = message.location

        await update_user_location(
            message.from_user.id,
            location.latitude,
            location.longitude
        )

        await state.update_data(
            driver_latitude=location.latitude,
            driver_longitude=location.longitude
        )

        await create_driver_ride(
            message,
            state
        )

        return

    # Oddiy profil lokatsiyasi
    await update_user_location(
        message.from_user.id,
        message.location.latitude,
        message.location.longitude
    )

    # Faol haydovchi buyurtmasini topamiz
    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                b.id,
                b.passenger_id,
                b.status,
                b.ride_id
            FROM bookings b
            JOIN rides r
                ON r.id = b.ride_id
            WHERE r.telegram_id = ?
            AND b.status IN (
                'accepted',
                'arriving',
                'arrived'
            )
            ORDER BY b.id DESC
            LIMIT 1
        """, (
            message.from_user.id,
        ))

        booking = await cursor.fetchone()

    if not booking:

        await message.answer(
            "✅ Lokatsiyangiz saqlandi.",
            reply_markup=main_menu
        )

        return

    booking_id, passenger_id, booking_status, ride_id = booking

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE rides
            SET driver_latitude = ?,
                driver_longitude = ?,
                driver_location_updated = ?
            WHERE id = ?
        """, (
            message.location.latitude,
            message.location.longitude,
            datetime.now().isoformat(),
            ride_id
        ))

        if booking_status == BOOKING_ACCEPTED:

            await db.execute("""
                UPDATE bookings
                SET status = ?
                WHERE id = ?
            """, (
                BOOKING_ARRIVING,
                booking_id
            ))

        await db.commit()

    # Yo‘lovchining olish lokatsiyasi
    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                passenger_latitude,
                passenger_longitude
            FROM bookings
            WHERE id = ?
        """, (
            booking_id,
        ))

        passenger_location = await cursor.fetchone()

    eta_text = "📍 Yo‘lovchi lokatsiyasi mavjud emas."

    if (
        passenger_location
        and passenger_location[0] is not None
        and passenger_location[1] is not None
    ):

        distance, eta = await calculate_eta(
            message.location.latitude,
            message.location.longitude,
            passenger_location[0],
            passenger_location[1]
        )

        eta_text = (
            f"📏 Masofa: {distance:.1f} km\n"
            f"⏱ Yetib borish: {eta} daqiqa"
        )

    await message.answer(
        "🚕 <b>Lokatsiya yangilandi!</b>\n\n"
        f"{eta_text}",
        reply_markup=main_menu,
        parse_mode="HTML"
    )

    await notify_user(
        passenger_id,
        "🚕 <b>TAKSI SIZ TOMONGA KELMOQDA</b>\n\n"
        f"{eta_text}\n\n"
        "🔄 Haydovchi lokatsiyasini yangiladi.",
        passenger_active_booking_keyboard(
            booking_id
        )
    )


# =========================================================
# PICK UP PASSENGER
# =========================================================

@dp.callback_query(
    F.data.startswith("picked_up:")
)
async def picked_up(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    driver_id = callback.from_user.id

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                b.passenger_id,
                b.status,
                r.telegram_id
            FROM bookings b
            JOIN rides r
                ON r.id = b.ride_id
            WHERE b.id = ?
            AND r.telegram_id = ?
        """, (
            booking_id,
            driver_id
        ))

        row = await cursor.fetchone()

        if not row:

            await callback.answer(
                "❗ Buyurtma topilmadi.",
                show_alert=True
            )

            return

        passenger_id, status, _ = row

        if status not in (
            BOOKING_ACCEPTED,
            BOOKING_ARRIVING,
            BOOKING_ARRIVED
        ):

            await callback.answer(
                "❗ Bu amal hozir mumkin emas.",
                show_alert=True
            )

            return

        await db.execute("""
            UPDATE bookings
            SET status = ?
            WHERE id = ?
        """, (
            BOOKING_IN_PROGRESS,
            booking_id
        ))

        await db.commit()

    await callback.answer(
        "🛣 Safar boshlandi!"
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await notify_user(
        passenger_id,
        "🛣 <b>SAFAR BOSHLANDI!</b>\n\n"
        "🚕 Haydovchi sizni olib, "
        "belgilangan manzil tomon yo‘l oldi.\n\n"
        "🏁 Safar tugagach haydovchini baholashingiz mumkin.",
        None
    )

    await notify_user(
        driver_id,
        "🛣 <b>SAFAR BOSHLANDI!</b>\n\n"
        "Safar tugagach quyidagi tugma orqali "
        "yakunlang.",
        InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏁 SAFARNI YAKUNLASH",
                        callback_data=f"complete_booking:{booking_id}"
                    )
                ]
            ]
        )
    )


# =========================================================
# COMPLETE BOOKING
# =========================================================

@dp.callback_query(
    F.data.startswith("complete_booking:")
)
async def complete_booking(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    driver_id = callback.from_user.id

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                b.passenger_id,
                b.status,
                b.ride_id,
                r.telegram_id
            FROM bookings b
            JOIN rides r
                ON r.id = b.ride_id
            WHERE b.id = ?
            AND r.telegram_id = ?
        """, (
            booking_id,
            driver_id
        ))

        row = await cursor.fetchone()

        if not row:

            await callback.answer(
                "❗ Buyurtma topilmadi.",
                show_alert=True
            )

            return

        passenger_id, status, ride_id, _ = row

        if status != BOOKING_IN_PROGRESS:

            await callback.answer(
                "❗ Safar holati noto‘g‘ri.",
                show_alert=True
            )

            return

        await db.execute("""
            UPDATE bookings
            SET status = ?,
                completed_at = ?
            WHERE id = ?
        """, (
            BOOKING_COMPLETED,
            datetime.now().isoformat(),
            booking_id
        ))

        await db.commit()

    await callback.answer(
        "🏁 Safar yakunlandi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await notify_user(
        passenger_id,
        "🏁 <b>SAFAR YAKUNLANDI!</b>\n\n"
        "Rahmat! Endi haydovchini baholashingiz mumkin. ⭐",
        main_menu
    )

    await notify_user(
        driver_id,
        "🏁 <b>Safar yakunlandi.</b>\n\n"
        "Yo‘lovchiga baholash imkoniyati berildi.",
        main_menu
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

    passenger_id = callback.from_user.id

    async with aiosqlite.connect(DB) as db:

        await db.execute(
            "BEGIN IMMEDIATE"
        )

        cursor = await db.execute("""
            SELECT
                b.ride_id,
                b.passenger_count,
                b.status,
                r.telegram_id,
                r.available_seats,
                r.original_seats
            FROM bookings b
            JOIN rides r
                ON r.id = b.ride_id
            WHERE b.id = ?
            AND b.passenger_id = ?
        """, (
            booking_id,
            passenger_id
        ))

        row = await cursor.fetchone()

        if not row:

            await db.rollback()

            await callback.answer(
                "❗ Buyurtma topilmadi.",
                show_alert=True
            )

            return

        (
            ride_id,
            passenger_count,
            status,
            driver_id,
            available,
            original
        ) = row

        if status not in (
            BOOKING_PENDING_DRIVER,
            BOOKING_ACCEPTED,
            BOOKING_ARRIVING
        ):

            await db.rollback()

            await callback.answer(
                "❗ Bu buyurtmani endi bekor qilib bo‘lmaydi.",
                show_alert=True
            )

            return

        # Agar qabul qilingan bo‘lsa joy qaytariladi
        if status in (
            BOOKING_ACCEPTED,
            BOOKING_ARRIVING
        ):

            new_available = min(
                int(original),
                int(available) + int(passenger_count)
            )

            new_status = (
                RIDE_ACTIVE
                if new_available > 0
                else RIDE_FULL
            )

            await db.execute("""
                UPDATE rides
                SET available_seats = ?,
                    seats = ?,
                    status = ?
                WHERE id = ?
            """, (
                new_available,
                str(new_available),
                new_status,
                ride_id
            ))

        await db.execute("""
            UPDATE bookings
            SET status = ?,
                cancelled_at = ?
            WHERE id = ?
        """, (
            BOOKING_CANCELLED,
            datetime.now().isoformat(),
            booking_id
        ))

        await db.commit()

    await callback.answer(
        "Buyurtma bekor qilindi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await notify_user(
        driver_id,
        "🔴 <b>Yo‘lovchi buyurtmani bekor qildi.</b>\n\n"
        "Bo‘sh joy qayta hisoblandi.",
        None
    )


# =========================================================
# DRIVER CANCEL BOOKING
# =========================================================

@dp.callback_query(
    F.data.startswith("cancel_booking:")
)
async def driver_cancel_booking(
    callback: CallbackQuery
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    driver_id = callback.from_user.id

    async with aiosqlite.connect(DB) as db:

        await db.execute(
            "BEGIN IMMEDIATE"
        )

        cursor = await db.execute("""
            SELECT
                b.passenger_id,
                b.passenger_count,
                b.status,
                b.ride_id,
                r.available_seats,
                r.original_seats,
                r.telegram_id
            FROM bookings b
            JOIN rides r
                ON r.id = b.ride_id
            WHERE b.id = ?
            AND r.telegram_id = ?
        """, (
            booking_id,
            driver_id
        ))

        row = await cursor.fetchone()

        if not row:

            await db.rollback()

            await callback.answer(
                "❗ Buyurtma topilmadi.",
                show_alert=True
            )

            return

        (
            passenger_id,
            passenger_count,
            status,
            ride_id,
            available,
            original,
            _
        ) = row

        if status not in (
            BOOKING_ACCEPTED,
            BOOKING_ARRIVING
        ):

            await db.rollback()

            await callback.answer(
                "❗ Bu buyurtmani bekor qilib bo‘lmaydi.",
                show_alert=True
            )

            return

        new_available = min(
            int(original),
            int(available) + int(passenger_count)
        )

        new_status = (
            RIDE_ACTIVE
            if new_available > 0
            else RIDE_FULL
        )

        await db.execute("""
            UPDATE rides
            SET available_seats = ?,
                seats = ?,
                status = ?
            WHERE id = ?
        """, (
            new_available,
            str(new_available),
            new_status,
            ride_id
        ))

        await db.execute("""
            UPDATE bookings
            SET status = ?,
                cancelled_at = ?
            WHERE id = ?
        """, (
            BOOKING_CANCELLED,
            datetime.now().isoformat(),
            booking_id
        ))

        await db.commit()

    await callback.answer(
        "Buyurtma bekor qilindi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await notify_user(
        passenger_id,
        "🔴 <b>Haydovchi buyurtmani bekor qildi.</b>\n\n"
        "Boshqa taksini tanlashingiz mumkin.",
        main_menu
    )


# =========================================================
# REFRESH PASSENGER LOCATION
# =========================================================

@dp.callback_query(
    F.data.startswith("refresh_location:")
)
async def refresh_location(
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
            "❗ Buyurtma topilmadi.",
            show_alert=True
        )

        return

    (
        b_id,
        ride_id,
        passenger_id,
        passenger_count,
        status,
        driver_id,
        driver_name,
        driver_phone,
        car,
        car_number,
        from_city,
        to_city,
        date,
        time,
        price,
        driver_lat,
        driver_lon,
        passenger_lat,
        passenger_lon
    ) = booking

    if callback.from_user.id != passenger_id:

        await callback.answer(
            "⛔ Sizga tegishli emas.",
            show_alert=True
        )

        return

    if (
        driver_lat is None
        or driver_lon is None
        or passenger_lat is None
        or passenger_lon is None
    ):

        await callback.answer(
            "📍 Hali lokatsiya yetarli emas.",
            show_alert=True
        )

        return

    distance, eta = await calculate_eta(
        driver_lat,
        driver_lon,
        passenger_lat,
        passenger_lon
    )

    await callback.answer(
        f"{distance:.1f} km / {eta} daqiqa"
    )

    await callback.message.answer(
        "🚕 <b>TAKSI JOYLASHUVI</b>\n\n"
        f"🚗 {car}\n"
        f"🔢 {car_number}\n"
        f"👤 {driver_name}\n\n"
        f"📏 Masofa: {distance:.1f} km\n"
        f"⏱ Yetib kelish: {eta} daqiqa\n\n"
        "🔄 Haydovchi oxirgi lokatsiyasini yuborgan.",
        parse_mode="HTML"
    )


# =========================================================
# SEARCH
# =========================================================

@dp.message(F.text == "🔎 Safar qidirish")
async def search_start(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await state.set_state(
        SearchState.from_city
    )

    await message.answer(
        "🔎 <b>Safar qidirish</b>\n\n"
        "📍 Qayerdan?",
        reply_markup=cities,
        parse_mode="HTML"
    )


@dp.message(SearchState.from_city)
async def search_from(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:

        await message.answer(
            "❗ Shaharni tugmalardan tanlang.",
            reply_markup=cities
        )

        return

    await state.update_data(
        from_city=message.text
    )

    await state.set_state(
        SearchState.to_city
    )

    await message.answer(
        "📍 Qayerga?",
        reply_markup=cities
    )


@dp.message(SearchState.to_city)
async def search_to(
    message: Message,
    state: FSMContext
):

    if message.text not in CITIES:

        await message.answer(
            "❗ Shaharni tugmalardan tanlang.",
            reply_markup=cities
        )

        return

    data = await state.get_data()

    if data["from_city"] == message.text:

        await message.answer(
            "❗ Yo‘nalishlar bir xil bo‘lishi mumkin emas."
        )

        return

    await state.update_data(
        to_city=message.text
    )

    await state.set_state(
        SearchState.date
    )

    await message.answer(
        "📅 Safar sanasini tanlang:",
        reply_markup=date_keyboard()
    )


@dp.message(SearchState.date)
async def search_date(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        date=message.text
    )

    await state.set_state(
        SearchState.time
    )

    await message.answer(
        "⏰ Vaqtni tanlang:",
        reply_markup=time_keyboard()
    )


@dp.message(SearchState.time)
async def search_time(
    message: Message,
    state: FSMContext
):

    if not message.text.endswith(":00"):

        await message.answer(
            "❗ Vaqtni tugmalardan tanlang.",
            reply_markup=time_keyboard()
        )

        return

    data = await state.get_data()

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                id,
                telegram_id,
                name,
                phone,
                car,
                car_number,
                from_city,
                to_city,
                date,
                time,
                available_seats,
                price,
                driver_latitude,
                driver_longitude
            FROM rides
            WHERE role = 'driver'
            AND from_city = ?
            AND to_city = ?
            AND date = ?
            AND time = ?
            AND available_seats > 0
            AND status = 'active'
            ORDER BY id DESC
        """, (
            data["from_city"],
            data["to_city"],
            data["date"],
            message.text
        ))

        rides = await cursor.fetchall()

    await state.clear()

    if not rides:

        await message.answer(
            "😔 Mos taksi topilmadi.",
            reply_markup=main_menu
        )

        return

    await message.answer(
        f"🚕 <b>{len(rides)} ta taksi topildi.</b>",
        reply_markup=main_menu,
        parse_mode="HTML"
    )

    for ride in rides:

        (
            ride_id,
            driver_id,
            name,
            phone,
            car,
            car_number,
            from_city,
            to_city,
            date,
            time,
            available,
            price,
            driver_lat,
            driver_lon
        ) = ride

        profile = await get_driver_profile(
            driver_id
        )

        rating = 5.0
        count = 0

        if profile:

            rating = float(
                profile[3] or 5.0
            )

            count = int(
                profile[4] or 0
            )

        text = (
            "🚕 <b>TAKSI</b>\n\n"
            f"👤 Haydovchi: {name}\n"
            f"⭐ Reyting: {rating:.1f}"
            f" ({count})\n"
            f"🚗 {car}\n"
            f"🔢 {car_number}\n"
            f"💺 Bo‘sh joy: {available}\n"
            f"💰 {price}\n"
            f"📍 {from_city} → {to_city}\n"
            f"📅 {date}\n"
            f"⏰ {time}"
        )

        if (
            driver_lat is not None
            and driver_lon is not None
        ):

            text += (
                "\n\n📍 Haydovchining "
                "lokatsiyasi mavjud."
            )

        await message.answer(
            text,
            reply_markup=passenger_driver_keyboard(
                ride_id
            ),
            parse_mode="HTML"
        )


# =========================================================
# MY RIDES
# =========================================================

@dp.message(F.text == "📋 Mening safarlarim")
async def my_rides(message: Message):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                id,
                role,
                from_city,
                to_city,
                date,
                time,
                car,
                car_number,
                seats,
                available_seats,
                price,
                status
            FROM rides
            WHERE telegram_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (
            message.from_user.id,
        ))

        rides = await cursor.fetchall()

    if not rides:

        await message.answer(
            "📋 Sizda hozircha safar yo‘q.",
            reply_markup=main_menu
        )

        return

    text = "📋 <b>MENING SAFARLARIM</b>\n\n"

    for ride in rides:

        (
            ride_id,
            role,
            from_city,
            to_city,
            date,
            time,
            car,
            car_number,
            seats,
            available,
            price,
            status
        ) = ride

        icon = (
            "🚕"
            if role == "driver"
            else "👤"
        )

        text += (
            f"🆔 {ride_id} {icon}\n"
            f"📍 {from_city} → {to_city}\n"
            f"📅 {date} | ⏰ {time}\n"
        )

        if role == "driver":

            text += (
                f"🚗 {car}\n"
                f"🔢 {car_number}\n"
                f"💺 Bo‘sh joy: {available}\n"
                f"💰 {price}\n"
            )

        else:

            text += (
                f"👥 Yo‘lovchilar: {seats}\n"
            )

        text += (
            f"📌 Holat: {status}\n\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================================================
# CANCEL RIDE
# =========================================================

@dp.message(F.text == "❌ Safarni bekor qilish")
async def cancel_ride_menu(
    message: Message,
    state: FSMContext
):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                id,
                role,
                from_city,
                to_city,
                date,
                time
            FROM rides
            WHERE telegram_id = ?
            AND status IN ('active', 'full')
            ORDER BY id DESC
            LIMIT 10
        """, (
            message.from_user.id,
        ))

        rides = await cursor.fetchall()

    if not rides:

        await message.answer(
            "❌ Bekor qilish uchun faol safar yo‘q.",
            reply_markup=main_menu
        )

        return

    text = (
        "❌ <b>Safarni bekor qilish</b>\n\n"
        "Safar ID raqamini yozing:\n\n"
    )

    for ride in rides:

        text += (
            f"🆔 {ride[0]} | "
            f"{ride[2]} → {ride[3]} | "
            f"{ride[4]} | {ride[5]}\n"
        )

    await state.set_state(
        CancelRideState.choose
    )

    await message.answer(
        text,
        reply_markup=main_menu,
        parse_mode="HTML"
    )


@dp.message(CancelRideState.choose)
async def cancel_ride_confirm(
    message: Message,
    state: FSMContext
):

    try:

        ride_id = int(message.text)

    except ValueError:

        await message.answer(
            "❗ Faqat ID raqamini yozing."
        )

        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                id,
                role
            FROM rides
            WHERE id = ?
            AND telegram_id = ?
            AND status IN ('active', 'full')
        """, (
            ride_id,
            message.from_user.id
        ))

        ride = await cursor.fetchone()

        if not ride:

            await state.clear()

            await message.answer(
                "❗ Bunday faol safar topilmadi.",
                reply_markup=main_menu
            )

            return

        if ride[1] == "driver":

            cursor = await db.execute("""
                SELECT passenger_id
                FROM bookings
                WHERE ride_id = ?
                AND status IN (
                    'pending_driver',
                    'accepted',
                    'arriving',
                    'arrived',
                    'onboard',
                    'in_progress'
                )
            """, (
                ride_id,
            ))

            passengers = await cursor.fetchall()

            await db.execute("""
                UPDATE bookings
                SET status = 'cancelled',
                    cancelled_at = ?
                WHERE ride_id = ?
                AND status IN (
                    'pending_driver',
                    'accepted',
                    'arriving',
                    'arrived',
                    'onboard',
                    'in_progress'
                )
            """, (
                datetime.now().isoformat(),
                ride_id
            ))

            for passenger in passengers:

                await notify_user(
                    passenger[0],
                    "🔴 <b>Haydovchi safarni bekor qildi.</b>\n\n"
                    "Boshqa taksini qidirishingiz mumkin.",
                    main_menu
                )

        await db.execute("""
            UPDATE rides
            SET status = ?
            WHERE id = ?
        """, (
            RIDE_CANCELLED,
            ride_id
        ))

        await db.commit()

    await state.clear()

    await message.answer(
        "✅ Safar bekor qilindi.",
        reply_markup=main_menu
    )


# =========================================================
# EDIT RIDE
# =========================================================

@dp.message(F.text == "✏️ Safarni tahrirlash")
async def edit_ride_menu(
    message: Message,
    state: FSMContext
):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                id,
                from_city,
                to_city,
                date,
                time
            FROM rides
            WHERE telegram_id = ?
            AND role = 'driver'
            AND status IN ('active', 'full')
            ORDER BY id DESC
            LIMIT 10
        """, (
            message.from_user.id,
        ))

        rides = await cursor.fetchall()

    if not rides:

        await message.answer(
            "✏️ Tahrirlash uchun faol safar yo‘q.",
            reply_markup=main_menu
        )

        return

    text = (
        "✏️ <b>Safarni tahrirlash</b>\n\n"
        "Safar ID sini yozing:\n\n"
    )

    for ride in rides:

        text += (
            f"🆔 {ride[0]} | "
            f"{ride[1]} → {ride[2]} | "
            f"{ride[3]} | {ride[4]}\n"
        )

    await state.set_state(
        EditRideState.choose
    )

    await message.answer(
        text,
        reply_markup=main_menu,
        parse_mode="HTML"
    )


@dp.message(EditRideState.choose)
async def edit_ride_choose(
    message: Message,
    state: FSMContext
):

    try:

        ride_id = int(message.text)

    except ValueError:

        await message.answer(
            "❗ ID raqamini yozing."
        )

        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT id
            FROM rides
            WHERE id = ?
            AND telegram_id = ?
            AND role = 'driver'
            AND status IN ('active', 'full')
        """, (
            ride_id,
            message.from_user.id
        ))

        ride = await cursor.fetchone()

    if not ride:

        await message.answer(
            "❗ Faol safar topilmadi."
        )

        return

    await state.update_data(
        ride_id=ride_id
    )

    await state.set_state(
        EditRideState.field
    )

    await message.answer(
        "✏️ Nimani o‘zgartirmoqchisiz?\n\n"
        "1 — Qayerdan\n"
        "2 — Qayerga\n"
        "3 — Sana\n"
        "4 — Vaqt\n"
        "5 — Narx\n"
        "6 — Jami joy"
    )


@dp.message(EditRideState.field)
async def edit_ride_field(
    message: Message,
    state: FSMContext
):

    mapping = {
        "1": "from_city",
        "2": "to_city",
        "3": "date",
        "4": "time",
        "5": "price",
        "6": "seats",
    }

    field = mapping.get(
        message.text.strip()
    )

    if not field:

        await message.answer(
            "❗ 1 dan 6 gacha tanlang."
        )

        return

    await state.update_data(
        field=field
    )

    await state.set_state(
        EditRideState.value
    )

    if field in (
        "from_city",
        "to_city"
    ):

        await message.answer(
            "📍 Shaharni tanlang:",
            reply_markup=cities
        )

    elif field == "date":

        await message.answer(
            "📅 Yangi sanani tanlang:",
            reply_markup=date_keyboard()
        )

    elif field == "time":

        await message.answer(
            "⏰ Yangi vaqtni tanlang:",
            reply_markup=time_keyboard()
        )

    elif field == "seats":

        await message.answer(
            "💺 Yangi jami joy sonini yozing: 1–4"
        )

    else:

        await message.answer(
            "💰 Yangi narxni yozing."
        )


@dp.message(EditRideState.value)
async def edit_ride_value(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    ride_id = data["ride_id"]
    field = data["field"]
    value = message.text

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                from_city,
                to_city,
                original_seats,
                available_seats
            FROM rides
            WHERE id = ?
            AND telegram_id = ?
        """, (
            ride_id,
            message.from_user.id
        ))

        current = await cursor.fetchone()

        if not current:

            await state.clear()

            await message.answer(
                "❗ Safar topilmadi.",
                reply_markup=main_menu
            )

            return

        current_from = current[0]
        current_to = current[1]

        if field == "from_city":

            if value not in CITIES:

                await message.answer(
                    "❗ Shaharni tugmalardan tanlang.",
                    reply_markup=cities
                )

                return

            if value == current_to:

                await message.answer(
                    "❗ Qayerdan va qayerga "
                    "bir xil bo‘lishi mumkin emas."
                )

                return

        if field == "to_city":

            if value not in CITIES:

                await message.answer(
                    "❗ Shaharni tugmalardan tanlang.",
                    reply_markup=cities
                )

                return

            if value == current_from:

                await message.answer(
                    "❗ Qayerdan va qayerga "
                    "bir xil bo‘lishi mumkin emas."
                )

                return

        if field == "time":

            if not value.endswith(":00"):

                await message.answer(
                    "❗ Vaqtni tugmalardan tanlang.",
                    reply_markup=time_keyboard()
                )

                return

        if field == "seats":

            try:

                new_total = int(value)

            except ValueError:

                await message.answer(
                    "❗ 1–4 oralig‘ida raqam."
                )

                return

            if not 1 <= new_total <= 4:

                await message.answer(
                    "❗ 1–4 oralig‘ida raqam."
                )

                return

            original = int(
                current[2] or 4
            )

            available = int(
                current[3] or 0
            )

            used = (
                original - available
            )

            if new_total < used:

                await message.answer(
                    "❗ Bu safarda allaqachon "
                    f"{used} ta joy band.\n\n"
                    "Jami joyni bundan kam "
                    "qilib bo‘lmaydi."
                )

                return

            new_available = (
                new_total - used
            )

            new_status = (
                RIDE_FULL
                if new_available == 0
                else RIDE_ACTIVE
            )

            await db.execute("""
                UPDATE rides
                SET original_seats = ?,
                    available_seats = ?,
                    seats = ?,
                    status = ?
                WHERE id = ?
                AND telegram_id = ?
            """, (
                new_total,
                new_available,
                str(new_available),
                new_status,
                ride_id,
                message.from_user.id
            ))

        else:

            await db.execute(
                f"""
                UPDATE rides
                SET {field} = ?
                WHERE id = ?
                AND telegram_id = ?
                """,
                (
                    value,
                    ride_id,
                    message.from_user.id
                )
            )

        await db.commit()

    await state.clear()

    await message.answer(
        "✅ Safar muvaffaqiyatli tahrirlandi.",
        reply_markup=main_menu
    )


# =========================================================
# RATING
# =========================================================

@dp.message(F.text == "⭐ Haydovchini baholash")
async def rating_start(
    message: Message,
    state: FSMContext
):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                b.id,
                b.ride_id,
                r.telegram_id
            FROM bookings b
            JOIN rides r
                ON r.id = b.ride_id
            WHERE b.passenger_id = ?
            AND b.status = 'completed'
            ORDER BY b.id DESC
            LIMIT 10
        """, (
            message.from_user.id,
        ))

        bookings = await cursor.fetchall()

    if not bookings:

        await message.answer(
            "⭐ Hozircha baholash uchun "
            "yakunlangan safar yo‘q.",
            reply_markup=main_menu
        )

        return

    selected = None

    async with aiosqlite.connect(DB) as db:

        for booking in bookings:

            cursor = await db.execute("""
                SELECT id
                FROM ratings
                WHERE ride_id = ?
                AND passenger_id = ?
            """, (
                booking[1],
                message.from_user.id
            ))

            exists = await cursor.fetchone()

            if not exists:

                selected = booking
                break

    if not selected:

        await message.answer(
            "ℹ️ Barcha yakunlangan safarlaringiz "
            "allaqachon baholangan.",
            reply_markup=main_menu
        )

        return

    await state.update_data(
        ride_id=selected[1],
        driver_id=selected[2]
    )

    await state.set_state(
        RatingState.rating
    )

    await message.answer(
        "⭐ <b>Haydovchini baholang</b>\n\n"
        "1 dan 5 gacha tanlang:",
        reply_markup=rating_keyboard(),
        parse_mode="HTML"
    )


@dp.message(RatingState.rating)
async def rating_value(
    message: Message,
    state: FSMContext
):

    try:

        rating = int(
            message.text
            .replace("⭐", "")
            .strip()
        )

    except ValueError:

        await message.answer(
            "❗ 1–5 oralig‘ida tanlang.",
            reply_markup=rating_keyboard()
        )

        return

    if not 1 <= rating <= 5:

        await message.answer(
            "❗ 1–5 oralig‘ida tanlang.",
            reply_markup=rating_keyboard()
        )

        return

    await state.update_data(
        rating=rating
    )

    await state.set_state(
        RatingState.comment
    )

    await message.answer(
        "💬 Izoh yozing.\n\n"
        "Izoh yozishni xohlamasangiz "
        "<code>skip</code> deb yozing.",
        parse_mode="HTML"
    )


@dp.message(RatingState.comment)
async def rating_comment(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    comment = message.text

    if comment.lower() == "skip":

        comment = ""

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT id
            FROM ratings
            WHERE ride_id = ?
            AND passenger_id = ?
        """, (
            data["ride_id"],
            message.from_user.id
        ))

        exists = await cursor.fetchone()

        if exists:

            await state.clear()

            await message.answer(
                "ℹ️ Bu safarga allaqachon "
                "baho bergansiz.",
                reply_markup=main_menu
            )

            return

        await db.execute("""
            INSERT INTO ratings
            (
                ride_id,
                driver_id,
                passenger_id,
                rating,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["ride_id"],
            data["driver_id"],
            message.from_user.id,
            data["rating"],
            comment,
            datetime.now().isoformat()
        ))

        cursor = await db.execute("""
            SELECT
                rating,
                rating_count
            FROM driver_profiles
            WHERE telegram_id = ?
        """, (
            data["driver_id"],
        ))

        driver = await cursor.fetchone()

        if driver:

            old_rating = float(
                driver[0] or 5.0
            )

            old_count = int(
                driver[1] or 0
            )

            new_count = old_count + 1

            new_rating = (
                (
                    old_rating * old_count
                )
                + data["rating"]
            ) / new_count

            await db.execute("""
                UPDATE driver_profiles
                SET rating = ?,
                    rating_count = ?
                WHERE telegram_id = ?
            """, (
                new_rating,
                new_count,
                data["driver_id"]
            ))

        await db.commit()

    await state.clear()

    await message.answer(
        "✅ Rahmat! Bahoyingiz saqlandi. ⭐",
        reply_markup=main_menu
    )


# =========================================================
# PROFILE
# =========================================================

@dp.message(F.text == "👤 Profilim")
async def profile(message: Message):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                name,
                phone,
                gender,
                age_category
            FROM users
            WHERE telegram_id = ?
        """, (
            message.from_user.id,
        ))

        user = await cursor.fetchone()

        cursor = await db.execute("""
            SELECT
                status,
                rating,
                rating_count,
                car,
                car_number
            FROM driver_profiles
            WHERE telegram_id = ?
        """, (
            message.from_user.id,
        ))

        driver = await cursor.fetchone()

    if not user:

        await message.answer(
            "Profil topilmadi.",
            reply_markup=main_menu
        )

        return

    name, phone, gender, age = user

    text = (
        "👤 <b>PROFILIM</b>\n\n"
        f"👤 Ism: {name or 'Kiritilmagan'}\n"
        f"📱 Telefon: {phone or 'Kiritilmagan'}\n"
        f"👤 Jins: {gender or 'Kiritilmagan'}\n"
        f"🎂 Yosh: {age or 'Kiritilmagan'}\n"
    )

    if driver:

        status, rating, count, car, car_number = driver

        text += (
            "\n🚕 <b>HAYDOVCHI PROFILI</b>\n"
            f"📌 Holat: {status}\n"
            f"🚗 Avtomobil: {car}\n"
            f"🔢 Raqam: {car_number}\n"
            f"⭐ Reyting: {float(rating):.1f}\n"
            f"👥 Baholar: {count}\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================================================
# ADMIN
# =========================================================

@dp.message(F.text == "/admin")
async def admin_panel(message: Message):

    if not is_admin(
        message.from_user.id
    ):

        return

    await message.answer(
        "👨‍💼 <b>OPER TAXI ADMIN PANEL</b>\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "👨‍💼 Haydovchilar")
async def admin_drivers(message: Message):

    if not is_admin(
        message.from_user.id
    ):

        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                telegram_id,
                status,
                car,
                car_number,
                rating,
                rating_count
            FROM driver_profiles
            ORDER BY created_at DESC
            LIMIT 30
        """)

        drivers = await cursor.fetchall()

    if not drivers:

        await message.answer(
            "Haydovchilar topilmadi.",
            reply_markup=admin_keyboard()
        )

        return

    text = "👨‍💼 <b>HAYDOVCHILAR</b>\n\n"

    for driver in drivers:

        (
            user_id,
            status,
            car,
            car_number,
            rating,
            rating_count
        ) = driver

        text += (
            f"🆔 <code>{user_id}</code>\n"
            f"📌 {status}\n"
            f"🚗 {car}\n"
            f"🔢 {car_number}\n"
            f"⭐ {float(rating):.1f}"
            f" ({rating_count})\n\n"
        )

    await message.answer(
        text,
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "🟡 Kutilayotgan haydovchilar")
async def admin_pending_drivers(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                telegram_id,
                car,
                car_number,
                created_at
            FROM driver_profiles
            WHERE status = 'pending'
            ORDER BY created_at ASC
        """)

        drivers = await cursor.fetchall()

    if not drivers:

        await message.answer(
            "🟢 Kutilayotgan haydovchilar yo‘q.",
            reply_markup=admin_keyboard()
        )

        return

    for driver in drivers:

        text = (
            "🟡 <b>HAYDOVCHI TEKSHIRUVI</b>\n\n"
            f"🆔 <code>{driver[0]}</code>\n"
            f"🚗 {driver[1]}\n"
            f"🔢 {driver[2]}\n"
        )

        await message.answer(
            text,
            reply_markup=admin_driver_keyboard(
                driver[0]
            ),
            parse_mode="HTML"
        )


# =========================================================
# ADMIN VERIFY CALLBACK
# =========================================================

@dp.callback_query(
    F.data.startswith("verify_driver:")
)
async def verify_driver_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo‘q.",
            show_alert=True
        )

        return

    user_id = int(
        callback.data.split(":")[1]
    )

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE driver_profiles
            SET status = ?
            WHERE telegram_id = ?
        """, (
            DRIVER_VERIFIED,
            user_id
        ))

        await db.commit()

    await callback.answer(
        "Haydovchi tasdiqlandi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await notify_user(
        user_id,
        "🟢 <b>HAYDOVCHI PROFILINGIZ TASDIQLANDI!</b>\n\n"
        "Endi OPER TAXI orqali safar joylashtirishingiz mumkin.",
        main_menu
    )


# =========================================================
# ADMIN REJECT CALLBACK
# =========================================================

@dp.callback_query(
    F.data.startswith("reject_driver_admin:")
)
async def reject_driver_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo‘q.",
            show_alert=True
        )

        return

    user_id = int(
        callback.data.split(":")[1]
    )

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE driver_profiles
            SET status = ?
            WHERE telegram_id = ?
        """, (
            DRIVER_REJECTED,
            user_id
        ))

        await db.commit()

    await callback.answer(
        "Haydovchi rad etildi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await notify_user(
        user_id,
        "🔴 <b>Haydovchilik profilingiz tasdiqlanmadi.</b>\n\n"
        "Hujjatlarni qayta topshirishingiz mumkin.",
        main_menu
    )


# =========================================================
# ADMIN BLOCK CALLBACK
# =========================================================

@dp.callback_query(
    F.data.startswith("block_driver:")
)
async def block_driver_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Ruxsat yo‘q.",
            show_alert=True
        )

        return

    user_id = int(
        callback.data.split(":")[1]
    )

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE driver_profiles
            SET status = ?
            WHERE telegram_id = ?
        """, (
            DRIVER_BLOCKED,
            user_id
        ))

        await db.execute("""
            UPDATE rides
            SET status = ?
            WHERE telegram_id = ?
            AND role = 'driver'
            AND status IN ('active', 'full')
        """, (
            RIDE_BLOCKED,
            user_id
        ))

        await db.commit()

    await callback.answer(
        "Haydovchi bloklandi."
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await notify_user(
        user_id,
        "⛔ <b>Haydovchi profilingiz bloklandi.</b>",
        main_menu
    )


# =========================================================
# ADMIN COMMANDS
# =========================================================

@dp.message(F.text.startswith("/verify "))
async def admin_verify_command(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    try:

        user_id = int(
            message.text.split()[1]
        )

    except Exception:

        await message.answer(
            "❗ /verify TELEGRAM_ID"
        )

        return

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE driver_profiles
            SET status = ?
            WHERE telegram_id = ?
        """, (
            DRIVER_VERIFIED,
            user_id
        ))

        await db.commit()

    await notify_user(
        user_id,
        "🟢 <b>Haydovchi profilingiz tasdiqlandi!</b>\n\n"
        "Endi safar joylashtirishingiz mumkin.",
        main_menu
    )

    await message.answer(
        "✅ Haydovchi tasdiqlandi."
    )


@dp.message(F.text.startswith("/reject "))
async def admin_reject_command(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    try:

        user_id = int(
            message.text.split()[1]
        )

    except Exception:

        await message.answer(
            "❗ /reject TELEGRAM_ID"
        )

        return

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE driver_profiles
            SET status = ?
            WHERE telegram_id = ?
        """, (
            DRIVER_REJECTED,
            user_id
        ))

        await db.commit()

    await notify_user(
        user_id,
        "🔴 Haydovchilik profilingiz "
        "tasdiqlanmadi.",
        main_menu
    )

    await message.answer(
        "🔴 Haydovchi rad etildi."
    )


@dp.message(F.text.startswith("/block "))
async def admin_block_command(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    try:

        user_id = int(
            message.text.split()[1]
        )

    except Exception:

        await message.answer(
            "❗ /block TELEGRAM_ID"
        )

        return

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE driver_profiles
            SET status = ?
            WHERE telegram_id = ?
        """, (
            DRIVER_BLOCKED,
            user_id
        ))

        await db.execute("""
            UPDATE rides
            SET status = ?
            WHERE telegram_id = ?
            AND role = 'driver'
            AND status IN ('active', 'full')
        """, (
            RIDE_BLOCKED,
            user_id
        ))

        await db.commit()

    await notify_user(
        user_id,
        "⛔ Haydovchi profilingiz bloklandi.",
        main_menu
    )

    await message.answer(
        "⛔ Haydovchi bloklandi."
    )


@dp.message(F.text.startswith("/unblock "))
async def admin_unblock(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    try:

        user_id = int(
            message.text.split()[1]
        )

    except Exception:

        await message.answer(
            "❗ /unblock TELEGRAM_ID"
        )

        return

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE driver_profiles
            SET status = ?
            WHERE telegram_id = ?
        """, (
            DRIVER_VERIFIED,
            user_id
        ))

        await db.commit()

    await notify_user(
        user_id,
        "🟢 Haydovchi profilingiz "
        "qayta faollashtirildi.",
        main_menu
    )

    await message.answer(
        "🟢 Haydovchi blokdan chiqarildi."
    )


# =========================================================
# ADMIN STATISTICS
# =========================================================

@dp.message(F.text == "📊 Statistika")
async def admin_statistics(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute(
            "SELECT COUNT(*) FROM users"
        )
        users = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM driver_profiles"
        )
        drivers = (await cursor.fetchone())[0]

        cursor = await db.execute("""
            SELECT COUNT(*)
            FROM driver_profiles
            WHERE status = 'verified'
        """)
        verified = (await cursor.fetchone())[0]

        cursor = await db.execute("""
            SELECT COUNT(*)
            FROM driver_profiles
            WHERE status = 'pending'
        """)
        pending = (await cursor.fetchone())[0]

        cursor = await db.execute("""
            SELECT COUNT(*)
            FROM rides
            WHERE role = 'driver'
            AND status IN ('active', 'full')
        """)
        active_rides = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM bookings"
        )
        bookings = (await cursor.fetchone())[0]

        cursor = await db.execute("""
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'completed'
        """)
        completed = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM ratings"
        )
        ratings = (await cursor.fetchone())[0]

    await message.answer(
        "📊 <b>OPER TAXI STATISTIKASI</b>\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🚕 Haydovchilar: {drivers}\n"
        f"🟢 Tasdiqlangan: {verified}\n"
        f"🟡 Kutilayotgan: {pending}\n"
        f"🚗 Faol safarlar: {active_rides}\n"
        f"🤝 Buyurtmalar: {bookings}\n"
        f"🏁 Tugagan safarlar: {completed}\n"
        f"⭐ Baholar: {ratings}",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN BACK
# =========================================================

@dp.message(F.text == "⬅️ Asosiy menyu")
async def admin_back(message: Message):

    if is_admin(
        message.from_user.id
    ):

        await message.answer(
            "Asosiy menyu.",
            reply_markup=main_menu
        )


# =========================================================
# HELP
# =========================================================

@dp.message(F.text == "📞 Yordam")
async def help_message(message: Message):

    await message.answer(
        "📞 <b>OPER TAXI</b>\n\n"

        "🚕 <b>Haydovchi</b>\n"
        "Hujjatlaringizni yuborasiz. "
        "Admin tekshiradi va tasdiqlaydi.\n\n"

        "👤 <b>Yo‘lovchi</b>\n"
        "Yo‘nalish, sana, vaqt va yo‘lovchilar "
        "sonini kiritadi.\n\n"

        "🤝 <b>Buyurtma</b>\n"
        "Yo‘lovchi taksini tanlaydi. "
        "Buyurtma haydovchiga yuboriladi. "
        "Haydovchi qabul qilgandan keyin "
        "buyurtma tasdiqlanadi.\n\n"

        "💺 <b>Joylar</b>\n"
        "Haydovchi buyurtmani qabul qilganda "
        "bo‘sh joy avtomatik kamayadi.\n\n"

        "📍 <b>Lokatsiya</b>\n"
        "Haydovchi lokatsiyasini yangilaganida "
        "yo‘lovchiga masofa va ETA ko‘rsatiladi.\n\n"

        "🏁 <b>Safar</b>\n"
        "Haydovchi yo‘lovchini oladi, safarni "
        "boshlaydi va yakunlaydi.\n\n"

        "⭐ <b>Reyting</b>\n"
        "Safardan keyin haydovchini baholash mumkin.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================================================
# FALLBACK
# =========================================================

@dp.message()
async def fallback(message: Message):

    if message.text and message.text.startswith("/"):
        return

    await message.answer(
        "❗ Men bu buyruqni tushunmadim.\n\n"
        "Quyidagi menyudan foydalaning 👇",
        reply_markup=main_menu
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    await init_db()

    print(
        "OPER TAXI 2.0 ishga tushdi..."
    )

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
