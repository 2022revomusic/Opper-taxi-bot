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
    KeyboardButton
)


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

# Siz bergan Telegram ID
DEFAULT_ADMIN_ID = 653914246

env_admin_ids = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

ADMIN_IDS = env_admin_ids or {DEFAULT_ADMIN_ID}

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB = "oper_taxi.db"


# =========================================================
# CONSTANTS
# =========================================================

CITIES = [
    "Toshkent",
    "Namangan",
    "Andijon",
    "Farg‘ona",
    "Qo‘qon",
    "Marg‘ilon"
]

DRIVER_STATUS_PENDING = "pending"
DRIVER_STATUS_VERIFIED = "verified"
DRIVER_STATUS_REJECTED = "rejected"
DRIVER_STATUS_BLOCKED = "blocked"

RIDE_ACTIVE = "active"
RIDE_CANCELLED = "cancelled"
RIDE_COMPLETED = "completed"
RIDE_BLOCKED = "blocked"


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
                latitude REAL,
                longitude REAL,
                created_at TEXT
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
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER,
                passenger_id INTEGER,
                passenger_count INTEGER,
                status TEXT DEFAULT 'active',
                created_at TEXT
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
            "latitude",
            "REAL"
        )

        await add_column_if_missing(
            "rides",
            "longitude",
            "REAL"
        )

        await add_column_if_missing(
            "rides",
            "created_at",
            "TEXT"
        )

        # Eski safarlarga created_at
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

        # Eski haydovchi safarlarida available_seats
        await db.execute("""
            UPDATE rides
            SET original_seats =
                CASE
                    WHEN original_seats IS NULL
                    THEN
                        CASE
                            WHEN CAST(seats AS INTEGER)
                            BETWEEN 1 AND 4
                            THEN CAST(seats AS INTEGER)
                            ELSE 4
                        END
                    ELSE original_seats
                END
            WHERE role = 'driver'
        """)

        await db.execute("""
            UPDATE rides
            SET available_seats =
                CASE
                    WHEN available_seats IS NULL
                    THEN original_seats
                    ELSE available_seats
                END
            WHERE role = 'driver'
        """)

        await db.commit()


# =========================================================
# KEYBOARDS
# =========================================================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
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
                text="🔎 Safar qidirish"
            ),
            KeyboardButton(
                text="📋 Mening safarlarim"
            )
        ],
        [
            KeyboardButton(
                text="✏️ Safarni tahrirlash"
            ),
            KeyboardButton(
                text="❌ Safarni bekor qilish"
            )
        ],
        [
            KeyboardButton(
                text="📍 Lokatsiyam"
            ),
            KeyboardButton(
                text="👤 Profilim"
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


cities = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Toshkent"),
            KeyboardButton(text="Namangan")
        ],
        [
            KeyboardButton(text="Andijon"),
            KeyboardButton(text="Farg‘ona")
        ],
        [
            KeyboardButton(text="Qo‘qon"),
            KeyboardButton(text="Marg‘ilon")
        ],
        [
            KeyboardButton(text="⬅️ Bekor qilish")
        ]
    ],
    resize_keyboard=True
)


gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👩 Ayol"),
            KeyboardButton(text="👨 Erkak")
        ],
        [
            KeyboardButton(text="⬅️ Bekor qilish")
        ]
    ],
    resize_keyboard=True
)


age_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👶 Bola"),
            KeyboardButton(text="🧑 Katta odam")
        ],
        [
            KeyboardButton(text="⬅️ Bekor qilish")
        ]
    ],
    resize_keyboard=True
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
                    request_contact=True
                )
            ],
            [
                KeyboardButton(
                    text="⬅️ Bekor qilish"
                )
            ]
        ],
        resize_keyboard=True
    )


def location_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📍 Lokatsiyamni yuborish",
                    request_location=True
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
            ]
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
                )
            ],
            [
                KeyboardButton(
                    text="🟡 Kutilayotgan haydovchilar"
                )
            ],
            [
                KeyboardButton(
                    text="⬅️ Asosiy menyu"
                )
            ]
        ],
        resize_keyboard=True
    )


def rating_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="⭐ 1"),
                KeyboardButton(text="⭐ 2"),
                KeyboardButton(text="⭐ 3")
            ],
            [
                KeyboardButton(text="⭐ 4"),
                KeyboardButton(text="⭐ 5")
            ]
        ],
        resize_keyboard=True
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


class EditRideState(StatesGroup):

    choose = State()
    field = State()
    value = State()


class CancelRideState(StatesGroup):

    choose = State()


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


async def update_location(
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
            user_id
        ))

        await db.commit()


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

    return row[0], row[1]


async def location_text(
    user1_id,
    user2_id
):

    loc1 = await get_user_location(
        user1_id
    )

    loc2 = await get_user_location(
        user2_id
    )

    if not loc1:
        return (
            "📍 Sizning lokatsiyangiz mavjud emas."
        )

    if not loc2:
        return (
            "📍 Ikkinchi tomon lokatsiyasini "
            "hali yubormagan."
        )

    route = await get_route_info(
        loc1[0],
        loc1[1],
        loc2[0],
        loc2[1]
    )

    if route:

        distance,
        duration = route

        return (
            f"📏 Masofa: {distance:.1f} km\n"
            f"⏱ Taxminiy yetib borish: "
            f"{max(1, round(duration))} daqiqa"
        )

    distance = calculate_distance(
        loc1[0],
        loc1[1],
        loc2[0],
        loc2[1]
    )

    return (
        f"📏 Taxminiy masofa: "
        f"{distance:.1f} km"
    )


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


async def notify_admins(text):

    for admin_id in ADMIN_IDS:

        try:

            await bot.send_message(
                admin_id,
                text,
                parse_mode="HTML"
            )

        except Exception:
            pass


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
        "bog‘lovchi xizmat.\n\n"
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
                ]
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

    await update_location(
        message.from_user.id,
        location.latitude,
        location.longitude
    )

    current_state = await state.get_state()

    if current_state == PassengerState.location.state:

        await state.update_data(
            latitude=location.latitude,
            longitude=location.longitude
        )

        await passenger_finish(
            message,
            state
        )

        return

    await message.answer(
        "✅ Lokatsiyangiz saqlandi.",
        reply_markup=main_menu
    )


# =========================================================
# DRIVER START
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

    if status == DRIVER_STATUS_PENDING:

        await message.answer(
            "🟡 Hujjatlaringiz hali tekshirilmoqda.\n\n"
            "Admin tasdiqlaganidan keyin "
            "safar joylashtira olasiz.",
            reply_markup=main_menu
        )

        return

    if status == DRIVER_STATUS_BLOCKED:

        await message.answer(
            "⛔ Haydovchi profilingiz bloklangan.",
            reply_markup=main_menu
        )

        return

    if status == DRIVER_STATUS_VERIFIED:

        await start_driver_ride(
            message,
            state
        )

        return

    # Yangi haydovchi
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

    await state.update_data(
        name=message.text
    )

    await ensure_user(
        message.from_user.id
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

    await save_phone(
        message.from_user.id,
        message.text
    )

    await state.update_data(
        phone=message.text
    )

    await state.set_state(
        DriverState.car
    )

    await message.answer(
        "🚗 Avtomobilingiz markasi va modelini yozing."
    )


async def save_phone(
    user_id,
    phone
):

    await ensure_user(user_id)

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            UPDATE users
            SET phone = ?
            WHERE telegram_id = ?
        """, (
            phone,
            user_id
        ))

        await db.commit()


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
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)

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
                status = 'pending',
                created_at = excluded.created_at
        """, (
            message.from_user.id,
            data["car"],
            data["car_number"],
            data["license_file_id"],
            data["vehicle_doc_file_id"],
            data["vehicle_photo_file_id"],
            datetime.now().isoformat()
        ))

        await db.commit()

    # Adminlarga xabar
    for admin_id in ADMIN_IDS:

        try:

            await bot.send_message(
                admin_id,
                "🆕 <b>Yangi haydovchi!</b>\n\n"
                f"👤 Ism: {data['name']}\n"
                f"📱 Telefon: {data['phone']}\n"
                f"🚗 Avtomobil: {data['car']}\n"
                f"🔢 Raqam: {data['car_number']}\n"
                f"🆔 Telegram ID: "
                f"{message.from_user.id}\n\n"
                "Tasdiqlash:\n"
                f"<code>/verify {message.from_user.id}</code>\n\n"
                "Rad etish:\n"
                f"<code>/reject {message.from_user.id}</code>\n\n"
                "Bloklash:\n"
                f"<code>/block {message.from_user.id}</code>",
                parse_mode="HTML"
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
        "Tasdiqlangandan keyin sizga xabar keladi "
        "va safar joylashtira olasiz.",
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

    car = profile[0]
    car_number = profile[1]

    await state.update_data(
        car=car,
        car_number=car_number
    )

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT name, phone
            FROM users
            WHERE telegram_id = ?
        """, (
            message.from_user.id,
        ))

        user = await cursor.fetchone()

    if user:

        await state.update_data(
            name=user[0],
            phone=user[1]
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

    if message.text == data.get("from_city"):

        await message.answer(
            "❗ Qayerdan va qayerga shaharlari "
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
        "💺 Mashinada nechta bo‘sh yo‘lovchi "
        "o‘rni bor?\n\n"
        "1 dan 4 gacha tanlang."
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

    data = await state.get_data()

    status = await driver_status(
        message.from_user.id
    )

    if status != DRIVER_STATUS_VERIFIED:

        await state.clear()

        await message.answer(
            "⛔ Haydovchi profilingiz tasdiqlanmagan.",
            reply_markup=main_menu
        )

        return

    await state.update_data(
        price=message.text
    )

    data = await state.get_data()

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
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.from_user.id,
            data.get("name", ""),
            data.get("phone", ""),
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
        "🤖 Bot mos yo‘lovchilarni qidiradi.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================================================
# PASSENGER
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

    await state.update_data(
        name=message.text
    )

    await ensure_user(
        message.from_user.id
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

    await ensure_user(
        message.from_user.id
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

    if data["from_city"] == message.text:

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
            "❗ Vaqtni tugmadan tanlang.",
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
            "❗ Yo‘lovchilar soni 1 dan 4 gacha."
        )

        return

    await state.update_data(
        passengers=count
    )

    await state.set_state(
        PassengerState.location
    )

    await message.answer(
        "📍 Haydovchi sizni osonroq topishi uchun "
        "lokatsiyangizni yuborishingiz mumkin.\n\n"
        "Lokatsiya yuborish majburiy emas.",
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
# PASSENGER FINISH + MATCH
# =========================================================

async def passenger_finish(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    passenger_count = int(
        data["passengers"]
    )

    passenger_id = message.from_user.id

    async with aiosqlite.connect(DB) as db:

        # Yo‘lovchi so‘rovi
        cursor = await db.execute("""
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
                latitude,
                longitude,
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
            data.get("latitude"),
            data.get("longitude"),
            datetime.now().isoformat()
        ))

        passenger_ride_id = cursor.lastrowid

        # Mos haydovchi
        cursor = await db.execute("""
            SELECT
                id,
                telegram_id,
                name,
                phone,
                car,
                car_number,
                available_seats,
                price
            FROM rides
            WHERE role = 'driver'
            AND from_city = ?
            AND to_city = ?
            AND date = ?
            AND time = ?
            AND status = 'active'
            AND available_seats >= ?
            AND telegram_id != ?
            ORDER BY available_seats ASC, id ASC
            LIMIT 1
        """, (
            data["from_city"],
            data["to_city"],
            data["date"],
            data["time"],
            passenger_count,
            passenger_id
        ))

        driver = await cursor.fetchone()

        if not driver:

            await db.commit()

        else:

            (
                driver_ride_id,
                driver_id,
                driver_name,
                driver_phone,
                driver_car,
                driver_car_number,
                available,
                driver_price
            ) = driver

            new_available = (
                int(available) - passenger_count
            )

            await db.execute("""
                UPDATE rides
                SET available_seats = ?,
                    seats = ?
                WHERE id = ?
            """, (
                new_available,
                str(new_available),
                driver_ride_id
            ))

            cursor = await db.execute("""
                INSERT INTO bookings
                (
                    ride_id,
                    passenger_id,
                    passenger_count,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, 'active', ?)
            """, (
                driver_ride_id,
                passenger_id,
                passenger_count,
                datetime.now().isoformat()
            ))

            booking_id = cursor.lastrowid

            await db.commit()

    await state.clear()

    if not driver:

        await message.answer(
            "✅ <b>Safar so‘rovingiz saqlandi!</b>\n\n"
            f"📍 {data['from_city']} → "
            f"{data['to_city']}\n"
            f"📅 {data['date']}\n"
            f"⏰ {data['time']}\n"
            f"👥 Yo‘lovchilar: {passenger_count}\n\n"
            "😔 Hozircha mos haydovchi topilmadi.\n\n"
            "Keyinroq «Safar qidirish» orqali "
            "yana tekshirishingiz mumkin.",
            reply_markup=main_menu,
            parse_mode="HTML"
        )

        return

    location_info = await location_text(
        passenger_id,
        driver_id
    )

    await message.answer(
        "🚕 <b>Sizga haydovchi topildi!</b>\n\n"
        f"👤 Haydovchi: {driver_name}\n"
        f"📱 Telefon: {driver_phone}\n"
        f"🚗 Mashina: {driver_car}\n"
        f"🔢 Raqam: {driver_car_number}\n"
        f"📍 {data['from_city']} → "
        f"{data['to_city']}\n"
        f"📅 {data['date']}\n"
        f"⏰ {data['time']}\n"
        f"💺 Sizning joyingiz: "
        f"{passenger_count}\n"
        f"💺 Qolgan joy: "
        f"{new_available}\n"
        f"💰 Narx: {driver_price}\n\n"
        f"{location_info}\n\n"
        "⭐ Safardan keyin haydovchini baholashingiz mumkin.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )

    try:

        await bot.send_message(
            driver_id,
            "👤 <b>Sizga yo‘lovchi topildi!</b>\n\n"
            f"👤 Yo‘lovchi: {data['name']}\n"
            f"📱 Telefon: {data['phone']}\n"
            f"👤 Jinsi: {data['gender']}\n"
            f"🎂 Yosh: {data['age_category']}\n"
            f"👥 Yo‘lovchilar: {passenger_count}\n"
            f"📍 {data['from_city']} → "
            f"{data['to_city']}\n"
            f"📅 {data['date']}\n"
            f"⏰ {data['time']}\n"
            f"💺 Qolgan joy: "
            f"{new_available}\n"
            f"💰 Narx: {driver_price}\n\n"
            f"{location_info}",
            parse_mode="HTML"
        )

    except Exception:
        pass


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
            "❗ Shaharni tugmadan tanlang.",
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
            "❗ Shaharni tugmadan tanlang.",
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
            "❗ Vaqtni tugmadan tanlang.",
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
                from_city,
                to_city,
                date,
                time,
                car,
                car_number,
                available_seats,
                price
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
            "😔 Aynan shu sana va vaqtda "
            "mos haydovchi topilmadi.",
            reply_markup=main_menu
        )

        return

    text = (
        "🚕 <b>Topilgan haydovchilar:</b>\n\n"
    )

    for i, ride in enumerate(rides, 1):

        (
            ride_id,
            driver_id,
            name,
            phone,
            from_city,
            to_city,
            date,
            time,
            car,
            car_number,
            seats,
            price
        ) = ride

        profile = await get_driver_profile(
            driver_id
        )

        rating_text = "⭐ 5.0"

        if profile:

            rating_text = (
                f"⭐ {float(profile[3]):.1f}"
            )

        text += (
            f"<b>{i}. {name}</b> "
            f"{rating_text}\n"
            f"📍 {from_city} → {to_city}\n"
            f"📅 {date} | ⏰ {time}\n"
            f"🚗 {car}\n"
            f"🔢 {car_number}\n"
            f"💺 Bo‘sh joy: {seats}\n"
            f"💰 {price}\n"
            f"📱 {phone}\n\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu,
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

    text = "📋 <b>Mening safarlarim</b>\n\n"

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
            f"🆔 <b>{ride_id}</b> {icon}\n"
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
            AND status = 'active'
            ORDER BY id DESC
            LIMIT 10
        """, (
            message.from_user.id,
        ))

        rides = await cursor.fetchall()

    if not rides:

        await message.answer(
            "❌ Faol safaringiz yo‘q.",
            reply_markup=main_menu
        )

        return

    text = (
        "❌ Bekor qilish uchun "
        "safar ID raqamini yozing:\n\n"
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
        reply_markup=main_menu
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
            "❗ Faqat safar ID raqamini yozing."
        )

        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT
                id,
                telegram_id,
                role,
                from_city,
                to_city,
                date,
                time
            FROM rides
            WHERE id = ?
            AND telegram_id = ?
            AND status = 'active'
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

        await db.execute("""
            UPDATE rides
            SET status = ?
            WHERE id = ?
        """, (
            RIDE_CANCELLED,
            ride_id
        ))

        # Agar haydovchi safarini bekor qilsa,
        # faol bookinglar ham bekor qilinadi.
        if ride[2] == "driver":

            await db.execute("""
                UPDATE bookings
                SET status = 'cancelled'
                WHERE ride_id = ?
                AND status = 'active'
            """, (
                ride_id,
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
                role,
                from_city,
                to_city,
                date,
                time
            FROM rides
            WHERE telegram_id = ?
            AND status = 'active'
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
        "✏️ Tahrir qilmoqchi bo‘lgan "
        "safar ID sini yozing:\n\n"
    )

    for ride in rides:

        text += (
            f"🆔 {ride[0]} | "
            f"{ride[2]} → {ride[3]} | "
            f"{ride[4]} | {ride[5]}\n"
        )

    await state.set_state(
        EditRideState.choose
    )

    await message.answer(
        text,
        reply_markup=main_menu
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
            "❗ Safar ID raqamini yozing."
        )

        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute("""
            SELECT id
            FROM rides
            WHERE id = ?
            AND telegram_id = ?
            AND status = 'active'
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
        "from_city\n"
        "to_city\n"
        "date\n"
        "time\n"
        "price\n"
        "seats\n\n"
        "Shulardan birini yozing."
    )


@dp.message(EditRideState.field)
async def edit_ride_field(
    message: Message,
    state: FSMContext
):

    field = message.text.strip().lower()

    allowed = {
        "from_city",
        "to_city",
        "date",
        "time",
        "price",
        "seats"
    }

    if field not in allowed:

        await message.answer(
            "❗ Quyidagilardan birini yozing:\n\n"
            "from_city\n"
            "to_city\n"
            "date\n"
            "time\n"
            "price\n"
            "seats"
        )

        return

    await state.update_data(
        field=field
    )

    await state.set_state(
        EditRideState.value
    )

    await message.answer(
        f"✏️ Yangi {field} qiymatini yozing:"
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

    if field == "from_city" and value not in CITIES:

        await message.answer(
            "❗ Shahar noto‘g‘ri."
        )

        return

    if field == "to_city" and value not in CITIES:

        await message.answer(
            "❗ Shahar noto‘g‘ri."
        )

        return

    if field == "time" and not value.endswith(":00"):

        await message.answer(
            "❗ Masalan: 14:00"
        )

        return

    if field == "seats":

        try:

            seats = int(value)

        except ValueError:

            await message.answer(
                "❗ 1 dan 4 gacha raqam."
            )

            return

        if not 1 <= seats <= 4:

            await message.answer(
                "❗ 1 dan 4 gacha."
            )

            return

        value = str(seats)

    # SQL field nomi whitelist orqali kelmoqda
    async with aiosqlite.connect(DB) as db:

        if field == "seats":

            # Faqat bo‘sh joy kamaymagan bo‘lsa
            cursor = await db.execute("""
                SELECT original_seats,
                       available_seats
                FROM rides
                WHERE id = ?
                AND telegram_id = ?
                AND role = 'driver'
            """, (
                ride_id,
                message.from_user.id
            ))

            current = await cursor.fetchone()

            if current:

                original = int(
                    current[0] or 4
                )

                available = int(
                    current[1] or 0
                )

                old_original = original

                new_total = int(value)

                used = (
                    old_original - available
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

                await db.execute("""
                    UPDATE rides
                    SET original_seats = ?,
                        available_seats = ?,
                        seats = ?
                    WHERE id = ?
                    AND telegram_id = ?
                """, (
                    new_total,
                    new_available,
                    str(new_available),
                    ride_id,
                    message.from_user.id
                ))

            else:

                await db.execute("""
                    UPDATE rides
                    SET seats = ?
                    WHERE id = ?
                    AND telegram_id = ?
                """, (
                    value,
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
                b.ride_id,
                r.telegram_id,
                r.from_city,
                r.to_city
            FROM bookings b
            JOIN rides r
                ON r.id = b.ride_id
            WHERE b.passenger_id = ?
            AND b.status = 'active'
            ORDER BY b.id DESC
            LIMIT 1
        """, (
            message.from_user.id,
        ))

        booking = await cursor.fetchone()

    if not booking:

        await message.answer(
            "⭐ Hozircha baholash uchun "
            "safar topilmadi.",
            reply_markup=main_menu
        )

        return

    await state.update_data(
        ride_id=booking[0],
        driver_id=booking[1]
    )

    await state.set_state(
        RatingState.rating
    )

    await message.answer(
        "⭐ Haydovchini 1 dan 5 gacha baholang:",
        reply_markup=rating_keyboard()
    )


@dp.message(RatingState.rating)
async def rating_value(
    message: Message,
    state: FSMContext
):

    try:

        rating = int(
            message.text.replace("⭐", "").strip()
        )

    except ValueError:

        await message.answer(
            "❗ 1–5 oralig‘ida baholang.",
            reply_markup=rating_keyboard()
        )

        return

    if not 1 <= rating <= 5:

        await message.answer(
            "❗ 1–5 oralig‘ida baholang.",
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
        "💬 Haydovchi haqida qisqa izoh yozing.\n\n"
        "Agar izoh yozishni xohlamasangiz "
        "«skip» deb yozing."
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
                "ℹ️ Siz bu safarga allaqachon "
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
                driver[0] or 5
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
        "👤 <b>Profilim</b>\n\n"
        f"👤 Ism: {name or 'Kiritilmagan'}\n"
        f"📱 Telefon: {phone or 'Kiritilmagan'}\n"
        f"👤 Jins: {gender or 'Kiritilmagan'}\n"
        f"🎂 Yosh: {age or 'Kiritilmagan'}\n"
    )

    if driver:

        status, rating, rating_count, car, car_number = driver

        text += (
            "\n🚕 <b>Haydovchi profili</b>\n"
            f"📌 Holat: {status}\n"
            f"🚗 Avtomobil: {car}\n"
            f"🔢 Raqam: {car_number}\n"
            f"⭐ Reyting: {float(rating):.1f}\n"
            f"👥 Baholar: {rating_count}\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================================================
# ADMIN PANEL
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

    text = "👨‍💼 <b>Haydovchilar</b>\n\n"

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
            f"⭐ {float(rating):.1f} "
            f"({rating_count})\n\n"
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

    text = "🟡 <b>Kutilayotgan haydovchilar</b>\n\n"

    for driver in drivers:

        text += (
            f"🆔 <code>{driver[0]}</code>\n"
            f"🚗 {driver[1]}\n"
            f"🔢 {driver[2]}\n\n"
            f"✅ /verify {driver[0]}\n"
            f"❌ /reject {driver[0]}\n"
            f"⛔ /block {driver[0]}\n\n"
        )

    await message.answer(
        text,
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN VERIFY
# =========================================================

@dp.message(F.text.startswith("/verify "))
async def admin_verify(message: Message):

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
            SET status = 'verified'
            WHERE telegram_id = ?
        """, (
            user_id,
        ))

        await db.commit()

    try:

        await bot.send_message(
            user_id,
            "🟢 <b>Haydovchi profilingiz tasdiqlandi!</b>\n\n"
            "Endi OPER TAXI orqali "
            "safar joylashtirishingiz mumkin.",
            parse_mode="HTML"
        )

    except Exception:
        pass

    await message.answer(
        "✅ Haydovchi tasdiqlandi."
    )


# =========================================================
# ADMIN REJECT
# =========================================================

@dp.message(F.text.startswith("/reject "))
async def admin_reject(message: Message):

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
            SET status = 'rejected'
            WHERE telegram_id = ?
        """, (
            user_id,
        ))

        await db.commit()

    try:

        await bot.send_message(
            user_id,
            "🔴 Haydovchilik hujjatlaringiz "
            "tasdiqlanmadi.\n\n"
            "Qayta ro‘yxatdan o‘tishingiz mumkin."
        )

    except Exception:
        pass

    await message.answer(
        "🔴 Haydovchi rad etildi."
    )


# =========================================================
# ADMIN BLOCK
# =========================================================

@dp.message(F.text.startswith("/block "))
async def admin_block(message: Message):

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
            SET status = 'blocked'
            WHERE telegram_id = ?
        """, (
            user_id,
        ))

        await db.execute("""
            UPDATE rides
            SET status = 'blocked'
            WHERE telegram_id = ?
            AND role = 'driver'
            AND status = 'active'
        """, (
            user_id,
        ))

        await db.commit()

    try:

        await bot.send_message(
            user_id,
            "⛔ Haydovchi profilingiz bloklandi."
        )

    except Exception:
        pass

    await message.answer(
        "⛔ Haydovchi bloklandi."
    )


# =========================================================
# ADMIN UNBLOCK
# =========================================================

@dp.message(F.text.startswith("/unblock "))
async def admin_unblock(message: Message):

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
            SET status = 'verified'
            WHERE telegram_id = ?
        """, (
            user_id,
        ))

        await db.commit()

    try:

        await bot.send_message(
            user_id,
            "🟢 Haydovchi profilingiz qayta ochildi."
        )

    except Exception:
        pass

    await message.answer(
        "🟢 Haydovchi blokdan chiqarildi."
    )


# =========================================================
# ADMIN STATISTICS
# =========================================================

@dp.message(F.text == "📊 Statistika")
async def admin_statistics(message: Message):

    if not is_admin(
        message.from_user.id
    ):
        return

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute(
            "SELECT COUNT(*) FROM users"
        )

        users = (
            await cursor.fetchone()
        )[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM driver_profiles"
        )

        drivers = (
            await cursor.fetchone()
        )[0]

        cursor = await db.execute("""
            SELECT COUNT(*)
            FROM driver_profiles
            WHERE status = 'verified'
        """)

        verified = (
            await cursor.fetchone()
        )[0]

        cursor = await db.execute("""
            SELECT COUNT(*)
            FROM driver_profiles
            WHERE status = 'pending'
        """)

        pending = (
            await cursor.fetchone()
        )[0]

        cursor = await db.execute("""
            SELECT COUNT(*)
            FROM rides
            WHERE status = 'active'
        """)

        active_rides = (
            await cursor.fetchone()
        )[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM bookings"
        )

        bookings = (
            await cursor.fetchone()
        )[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM ratings"
        )

        ratings = (
            await cursor.fetchone()
        )[0]

    await message.answer(
        "📊 <b>OPER TAXI statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🚕 Haydovchilar: {drivers}\n"
        f"🟢 Tasdiqlangan: {verified}\n"
        f"🟡 Kutilayotgan: {pending}\n"
        f"🚗 Faol safarlar: {active_rides}\n"
        f"🤝 Moslashtirilgan safarlar: {bookings}\n"
        f"⭐ Berilgan baholar: {ratings}",
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
        "📞 <b>OPER TAXI yordam</b>\n\n"
        "🚕 <b>Haydovchi</b>\n"
        "Hujjatlaringizni yuborasiz. "
        "Admin tekshiradi va tasdiqlaydi.\n\n"
        "👤 <b>Yo‘lovchi</b>\n"
        "Yo‘nalish, sana, vaqt va yo‘lovchilar "
        "sonini kiritasiz.\n\n"
        "💺 <b>O‘rinlar</b>\n"
        "4 o‘rinli mashinada har bir band qilingan "
        "joy avtomatik hisobdan chiqadi.\n\n"
        "📍 <b>Lokatsiya</b>\n"
        "Lokatsiya yuborilsa, tomonlar orasidagi "
        "taxminiy masofa va yetib borish vaqti "
        "ko‘rsatiladi.\n\n"
        "✏️ <b>Tahrirlash</b>\n"
        "Faol safaringiz ma’lumotlarini o‘zgartirish "
        "mumkin.\n\n"
        "⭐ <b>Reyting</b>\n"
        "Safardan keyin haydovchiga baho va izoh "
        "qoldirish mumkin.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================================================
# RATING MENU HANDLER
# =========================================================

@dp.message(F.text == "⭐ Haydovchini baholash")
async def rating_button(
    message: Message,
    state: FSMContext
):

    await rating_start(
        message,
        state
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
# BOT
# =========================================================

async def main():

    await init_db()

    print(
        "OPER TAXI bot ishga tushdi..."
    )

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
