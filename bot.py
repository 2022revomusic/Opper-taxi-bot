import os
import asyncio
import html
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2

import aiohttp
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN Railway Variables ichida topilmadi.")

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
RIDE_CANCELLED = "cancelled"
RIDE_COMPLETED = "completed"

BOOKING_PENDING = "pending_driver"
BOOKING_ACCEPTED = "accepted"
BOOKING_REJECTED = "rejected"
BOOKING_CANCELLED = "cancelled"
BOOKING_ARRIVING = "arriving"
BOOKING_ARRIVED = "arrived"
BOOKING_ONBOARD = "onboard"
BOOKING_IN_PROGRESS = "in_progress"
BOOKING_COMPLETED = "completed"


# =========================================================
# KEYBOARDS
# =========================================================

def main_menu():
    return ReplyKeyboardMarkup(
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
                KeyboardButton(text="📞 Yordam"),
            ],
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
            [KeyboardButton(text="⬅️ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
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
            [KeyboardButton(text="⏭ Lokatsiyasiz davom etish")],
            [KeyboardButton(text="⬅️ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def city_keyboard(prefix=""):
    rows = []
    row = []

    for city in CITIES:
        row.append(KeyboardButton(text=prefix + city))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([KeyboardButton(text="⬅️ Bekor qilish")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def date_keyboard():
    today = datetime.now().date()
    rows = []

    for i in range(8):
        d = today + timedelta(days=i)

        if i == 0:
            label = f"Bugun ({d.strftime('%d.%m')})"
        elif i == 1:
            label = f"Ertaga ({d.strftime('%d.%m')})"
        else:
            label = d.strftime("%d.%m.%Y")

        rows.append([KeyboardButton(text=label)])

    rows.append([KeyboardButton(text="⬅️ Bekor qilish")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def time_keyboard():
    times = [
        "06:00", "07:00", "08:00", "09:00",
        "10:00", "11:00", "12:00", "13:00",
        "14:00", "15:00", "16:00", "17:00",
        "18:00", "19:00", "20:00", "21:00",
        "22:00",
    ]

    rows = []
    row = []

    for t in times:
        row.append(KeyboardButton(text=t))

        if len(row) == 3:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([KeyboardButton(text="⬅️ Bekor qilish")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=True,
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
            [KeyboardButton(text="⬅️ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
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
            [KeyboardButton(text="⬅️ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def gender_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👨 Erkak"),
                KeyboardButton(text="👩 Ayol"),
            ],
            [KeyboardButton(text="⬅️ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def age_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="18-25"),
                KeyboardButton(text="26-35"),
            ],
            [
                KeyboardButton(text="36-50"),
                KeyboardButton(text="51+"),
            ],
            [KeyboardButton(text="⬅️ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def driver_booking_keyboard(booking_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Buyurtmani qabul qilish",
                    callback_data=f"accept_booking:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"reject_booking:{booking_id}",
                )
            ],
        ]
    )


def passenger_taxi_keyboard(booking_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Buyurtmani bekor qilish",
                    callback_data=f"cancel_booking:{booking_id}",
                )
            ]
        ]
    )


def driver_active_keyboard(booking_id: int):
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
                    text="🚕 Manzilga keldim",
                    callback_data=f"arrived:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Yo‘lovchini oldim",
                    callback_data=f"onboard:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏁 Safarni yakunlash",
                    callback_data=f"complete:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Buyurtmani bekor qilish",
                    callback_data=f"driver_cancel:{booking_id}",
                )
            ],
        ]
    )


def passenger_active_keyboard(booking_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 Haydovchi lokatsiyasi",
                    callback_data=f"track:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Buyurtmani bekor qilish",
                    callback_data=f"cancel_booking:{booking_id}",
                )
            ],
        ]
    )


def admin_driver_keyboard(driver_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"admin_verify:{driver_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"admin_reject:{driver_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Bloklash",
                    callback_data=f"admin_block:{driver_id}",
                )
            ],
        ]
    )


def rating_keyboard(booking_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 1", callback_data=f"rating:{booking_id}:1"),
                InlineKeyboardButton(text="⭐ 2", callback_data=f"rating:{booking_id}:2"),
                InlineKeyboardButton(text="⭐ 3", callback_data=f"rating:{booking_id}:3"),
            ],
            [
                InlineKeyboardButton(text="⭐ 4", callback_data=f"rating:{booking_id}:4"),
                InlineKeyboardButton(text="⭐ 5", callback_data=f"rating:{booking_id}:5"),
            ],
        ]
    )


# =========================================================
# FSM
# =========================================================

class DriverState(StatesGroup):
    name = State()
    phone = State()
    car = State()
    car_number = State()
    license = State()
    vehicle_doc = State()
    vehicle_photo = State()


class DriverRideState(StatesGroup):
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
    passengers = State()


class RatingState(StatesGroup):
    comment = State()


# =========================================================
# DATABASE
# =========================================================

async def db_execute(query, params=(), fetchone=False, fetchall=False, commit=True):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(query, params)

        if commit:
            await db.commit()

        if fetchone:
            return await cursor.fetchone()

        if fetchall:
            return await cursor.fetchall()

        return cursor


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
                rating REAL DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                name TEXT,
                phone TEXT,
                role TEXT DEFAULT 'driver',
                from_city TEXT,
                to_city TEXT,
                date TEXT,
                time TEXT,
                car TEXT,
                car_number TEXT,
                seats INTEGER DEFAULT 1,
                price INTEGER DEFAULT 0,
                original_seats INTEGER DEFAULT 1,
                available_seats INTEGER DEFAULT 1,
                reserved_seats INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                latitude REAL,
                longitude REAL,
                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS passenger_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                name TEXT,
                phone TEXT,
                gender TEXT,
                age_category TEXT,
                from_city TEXT,
                to_city TEXT,
                date TEXT,
                time TEXT,
                passengers INTEGER DEFAULT 1,
                pickup_latitude REAL,
                pickup_longitude REAL,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                ride_id INTEGER NOT NULL,
                passenger_id INTEGER NOT NULL,
                passenger_count INTEGER DEFAULT 1,

                pickup_latitude REAL,
                pickup_longitude REAL,

                driver_latitude REAL,
                driver_longitude REAL,

                status TEXT DEFAULT 'pending_driver',

                created_at TEXT,
                accepted_at TEXT,
                arrived_at TEXT,
                started_at TEXT,
                completed_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER,
                ride_id INTEGER,
                driver_id INTEGER,
                passenger_id INTEGER,
                rating INTEGER,
                comment TEXT,
                created_at TEXT
            )
        """)

        # Migration
        columns = await db.execute_fetchall(
            "PRAGMA table_info(rides)"
        )

        existing_columns = {row[1] for row in columns}

        if "reserved_seats" not in existing_columns:
            await db.execute(
                "ALTER TABLE rides ADD COLUMN reserved_seats INTEGER DEFAULT 0"
            )

        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_booking_active
            ON bookings(ride_id, passenger_id)
            WHERE status NOT IN (
                'rejected',
                'cancelled',
                'completed'
            )
        """)

        await db.commit()


# =========================================================
# HELPERS
# =========================================================

async def ensure_user(message: Message):
    name = message.from_user.full_name or ""

    await db_execute("""
        INSERT INTO users (telegram_id, name)
        VALUES (?, ?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET name=excluded.name
    """, (
        message.from_user.id,
        name,
    ))


async def update_user_location(user_id, latitude, longitude):
    await db_execute("""
        INSERT INTO users (
            telegram_id,
            latitude,
            longitude,
            location_updated
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            latitude=excluded.latitude,
            longitude=excluded.longitude,
            location_updated=excluded.location_updated
    """, (
        user_id,
        latitude,
        longitude,
        datetime.now().isoformat(),
    ))


async def get_user_location(user_id):
    row = await db_execute("""
        SELECT latitude, longitude
        FROM users
        WHERE telegram_id=?
    """, (user_id,), fetchone=True)

    if not row:
        return None

    if row["latitude"] is None or row["longitude"] is None:
        return None

    return row["latitude"], row["longitude"]


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


async def get_route_info(lat1, lon1, lat2, lon2):
    distance = calculate_distance(lat1, lon1, lat2, lon2)

    fallback_minutes = max(1, round((distance / 35) * 60))

    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
        f"?overview=false"
    )

    try:
        timeout = aiohttp.ClientTimeout(total=8)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:

                if response.status != 200:
                    return distance, fallback_minutes

                data = await response.json()

                routes = data.get("routes", [])

                if not routes:
                    return distance, fallback_minutes

                route = routes[0]

                km = route["distance"] / 1000
                minutes = max(1, round(route["duration"] / 60))

                return km, minutes

    except Exception:
        return distance, fallback_minutes


def clean_city(text):
    if not text:
        return None

    for city in CITIES:
        if text == city or text.endswith(city):
            return city

    return text


def parse_date(text):
    today = datetime.now().date()

    if text.startswith("Bugun"):
        return today.strftime("%d.%m.%Y")

    if text.startswith("Ertaga"):
        return (today + timedelta(days=1)).strftime("%d.%m.%Y")

    try:
        return datetime.strptime(text, "%d.%m.%Y").strftime("%d.%m.%Y")
    except Exception:
        return None


def is_admin(user_id):
    return user_id in ADMIN_IDS


async def get_driver_profile(user_id):
    return await db_execute("""
        SELECT *
        FROM driver_profiles
        WHERE telegram_id=?
    """, (user_id,), fetchone=True)


async def driver_status(user_id):
    row = await get_driver_profile(user_id)

    if not row:
        return None

    return row["status"]


async def send_location_to_user(user_id, lat, lon):
    try:
        await bot.send_location(
            chat_id=user_id,
            latitude=lat,
            longitude=lon,
        )
        return True
    except Exception:
        return False


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await ensure_user(message)

    await message.answer(
        "🚕 <b>OPPER TAXI</b>\n\n"
        "Farg‘ona vodiysi ↔ Toshkent yo‘nalishlarida "
        "haydovchi va yo‘lovchilarni bog‘lovchi xizmat.\n\n"
        "Kerakli bo‘limni tanlang:",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================================================
# CANCEL FSM
# =========================================================

@dp.message(F.text == "⬅️ Bekor qilish")
async def cancel_all(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "❌ Amal bekor qilindi.",
        reply_markup=main_menu(),
    )


# =========================================================
# DRIVER REGISTRATION
# =========================================================

@dp.message(F.text == "🚕 Haydovchi bo‘lish")
async def driver_start(message: Message, state: FSMContext):
    await ensure_user(message)

    profile = await get_driver_profile(message.from_user.id)

    if profile:

        if profile["status"] == DRIVER_VERIFIED:
            await start_driver_ride(message, state)
            return

        if profile["status"] == DRIVER_PENDING:
            await message.answer(
                "⏳ Sizning haydovchilik arizangiz hali admin tomonidan "
                "tasdiqlanmagan."
            )
            return

        if profile["status"] == DRIVER_BLOCKED:
            await message.answer(
                "🚫 Sizning haydovchilik profilingiz bloklangan."
            )
            return

    await state.set_state(DriverState.name)

    await message.answer(
        "👤 Ism-familiyangizni kiriting:"
    )


@dp.message(DriverState.name)
async def driver_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(DriverState.phone)

    await message.answer(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard(),
    )


@dp.message(DriverState.phone, F.contact)
async def driver_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number

    await state.update_data(phone=phone)
    await state.set_state(DriverState.car)

    await message.answer(
        "🚗 Mashina markasi va modelini yozing:",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(DriverState.phone)
async def driver_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()

    await state.update_data(phone=phone)
    await state.set_state(DriverState.car)

    await message.answer(
        "🚗 Mashina markasi va modelini yozing:"
    )


@dp.message(DriverState.car)
async def driver_car(message: Message, state: FSMContext):
    await state.update_data(car=message.text.strip())
    await state.set_state(DriverState.car_number)

    await message.answer(
        "🔢 Avtomobil davlat raqamini yozing:"
    )


@dp.message(DriverState.car_number)
async def driver_car_number(message: Message, state: FSMContext):
    await state.update_data(car_number=message.text.strip())
    await state.set_state(DriverState.license)

    await message.answer(
        "🪪 Haydovchilik guvohnomangiz rasmini yuboring:"
    )


@dp.message(DriverState.license, F.photo)
async def driver_license(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id

    await state.update_data(license_file_id=file_id)
    await state.set_state(DriverState.vehicle_doc)

    await message.answer(
        "📄 Texpasport yoki avtomobil hujjatini yuboring:"
    )


@dp.message(DriverState.vehicle_doc, F.photo)
async def driver_vehicle_doc(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id

    await state.update_data(vehicle_doc_file_id=file_id)
    await state.set_state(DriverState.vehicle_photo)

    await message.answer(
        "🚗 Avtomobilingizning tashqi ko‘rinishdagi rasmini yuboring:"
    )


@dp.message(DriverState.vehicle_photo, F.photo)
async def driver_vehicle_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id

    data = await state.get_data()

    await db_execute("""
        INSERT INTO driver_profiles (
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
            car=excluded.car,
            car_number=excluded.car_number,
            license_file_id=excluded.license_file_id,
            vehicle_doc_file_id=excluded.vehicle_doc_file_id,
            vehicle_photo_file_id=excluded.vehicle_photo_file_id,
            status=excluded.status,
            created_at=excluded.created_at
    """, (
        message.from_user.id,
        data["car"],
        data["car_number"],
        data["license_file_id"],
        data["vehicle_doc_file_id"],
        file_id,
        DRIVER_PENDING,
        datetime.now().isoformat(),
    ))

    await state.clear()

    await message.answer(
        "✅ Hujjatlaringiz qabul qilindi.\n\n"
        "⏳ Admin tekshiruvdan o‘tkazadi.\n"
        "Tasdiqlangandan keyin siz safar joylashingiz mumkin.",
        reply_markup=main_menu(),
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                "🚕 <b>Yangi haydovchi arizasi</b>\n\n"
                f"👤 {html.escape(data['name'])}\n"
                f"📱 {html.escape(data['phone'])}\n"
                f"🚗 {html.escape(data['car'])}\n"
                f"🔢 {html.escape(data['car_number'])}\n"
                f"🆔 Telegram ID: <code>{message.from_user.id}</code>",
                parse_mode="HTML",
                reply_markup=admin_driver_keyboard(message.from_user.id),
            )

            await bot.send_photo(
                admin_id,
                data["license_file_id"],
                caption="🪪 Haydovchilik guvohnomasi",
            )

            await bot.send_photo(
                admin_id,
                data["vehicle_doc_file_id"],
                caption="📄 Avtomobil hujjati",
            )

            await bot.send_photo(
                admin_id,
                file_id,
                caption="🚗 Avtomobil rasmi",
            )

        except Exception:
            pass


# =========================================================
# ADMIN DRIVER CALLBACKS
# =========================================================

@dp.callback_query(F.data.startswith("admin_verify:"))
async def admin_verify(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return

    driver_id = int(callback.data.split(":")[1])

    await db_execute("""
        UPDATE driver_profiles
        SET status=?
        WHERE telegram_id=?
    """, (DRIVER_VERIFIED, driver_id))

    try:
        await bot.send_message(
            driver_id,
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Sizning haydovchilik profilingiz tasdiqlandi.\n"
            "Endi safar joylashingiz mumkin.",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
    except Exception:
        pass

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.answer("Haydovchi tasdiqlandi.")


@dp.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return

    driver_id = int(callback.data.split(":")[1])

    await db_execute("""
        UPDATE driver_profiles
        SET status=?
        WHERE telegram_id=?
    """, (DRIVER_REJECTED, driver_id))

    try:
        await bot.send_message(
            driver_id,
            "❌ Haydovchilik arizangiz rad etildi."
        )
    except Exception:
        pass

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Ariza rad etildi.")


@dp.callback_query(F.data.startswith("admin_block:"))
async def admin_block(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return

    driver_id = int(callback.data.split(":")[1])

    await db_execute("""
        UPDATE driver_profiles
        SET status=?
        WHERE telegram_id=?
    """, (DRIVER_BLOCKED, driver_id))

    await db_execute("""
        UPDATE rides
        SET status=?
        WHERE telegram_id=? AND status=?
    """, (RIDE_CANCELLED, driver_id, RIDE_ACTIVE))

    try:
        await bot.send_message(
            driver_id,
            "🚫 Sizning haydovchilik profilingiz bloklandi."
        )
    except Exception:
        pass

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Haydovchi bloklandi.")


# =========================================================
# DRIVER RIDE CREATION
# =========================================================

async def start_driver_ride(message: Message, state: FSMContext):
    profile = await get_driver_profile(message.from_user.id)

    if not profile or profile["status"] != DRIVER_VERIFIED:
        await message.answer(
            "❌ Avval haydovchilik profilingiz tasdiqlanishi kerak."
        )
        return

    await state.set_state(DriverRideState.from_city)

    await message.answer(
        "🚕 Yangi safar joylash\n\n"
        "Qayerdan chiqasiz?",
        reply_markup=city_keyboard(),
    )


@dp.message(DriverRideState.from_city)
async def ride_from_city(message: Message, state: FSMContext):
    city = clean_city(message.text)

    if city not in CITIES:
        await message.answer("Shaharni tugmalardan tanlang.")
        return

    await state.update_data(from_city=city)
    await state.set_state(DriverRideState.to_city)

    await message.answer(
        "📍 Qayerga borasiz?",
        reply_markup=city_keyboard(),
    )


@dp.message(DriverRideState.to_city)
async def ride_to_city(message: Message, state: FSMContext):
    city = clean_city(message.text)

    if city not in CITIES:
        await message.answer("Shaharni tugmalardan tanlang.")
        return

    data = await state.get_data()

    if city == data["from_city"]:
        await message.answer(
            "❌ Ketish va borish shahri bir xil bo‘lishi mumkin emas."
        )
        return

    await state.update_data(to_city=city)
    await state.set_state(DriverRideState.date)

    await message.answer(
        "📅 Safar sanasini tanlang:",
        reply_markup=date_keyboard(),
    )


@dp.message(DriverRideState.date)
async def ride_date(message: Message, state: FSMContext):
    date = parse_date(message.text)

    if not date:
        await message.answer("Sanani tugmalardan tanlang.")
        return

    await state.update_data(date=date)
    await state.set_state(DriverRideState.time)

    await message.answer(
        "⏰ Safar vaqtini tanlang:",
        reply_markup=time_keyboard(),
    )


@dp.message(DriverRideState.time)
async def ride_time(message: Message, state: FSMContext):
    if message.text not in {
        "06:00", "07:00", "08:00", "09:00",
        "10:00", "11:00", "12:00", "13:00",
        "14:00", "15:00", "16:00", "17:00",
        "18:00", "19:00", "20:00", "21:00",
        "22:00",
    }:
        await message.answer("Vaqtni tugmalardan tanlang.")
        return

    await state.update_data(time=message.text)
    await state.set_state(DriverRideState.seats)

    await message.answer(
        "💺 Nechta bo‘sh joy bor?",
        reply_markup=seats_keyboard(),
    )


@dp.message(DriverRideState.seats)
async def ride_seats(message: Message, state: FSMContext):
    if message.text not in {"1", "2", "3", "4"}:
        await message.answer("1 dan 4 gacha tanlang.")
        return

    await state.update_data(seats=int(message.text))
    await state.set_state(DriverRideState.price)

    await message.answer(
        "💰 Bir yo‘lovchi uchun narxni so‘mda kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(DriverRideState.price)
async def ride_price(message: Message, state: FSMContext):
    try:
        price = int(
            message.text
            .replace(" ", "")
            .replace(",", "")
            .replace(".", "")
        )
    except Exception:
        await message.answer("Narxni faqat raqamda kiriting. Masalan: 150000")
        return

    if price <= 0:
        await message.answer("Narx 0 dan katta bo‘lishi kerak.")
        return

    data = await state.get_data()

    profile = await get_driver_profile(message.from_user.id)

    if not profile or profile["status"] != DRIVER_VERIFIED:
        await state.clear()
        await message.answer(
            "❌ Haydovchi profilingiz tasdiqlanmagan.",
            reply_markup=main_menu(),
        )
        return

    user = await db_execute("""
        SELECT name, phone
        FROM users
        WHERE telegram_id=?
    """, (message.from_user.id,), fetchone=True)

    name = user["name"] if user else message.from_user.full_name
    phone = user["phone"] if user else None

    seats = data["seats"]

    await db_execute("""
        INSERT INTO rides (
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
            reserved_seats,
            status,
            created_at
        )
        VALUES (?, ?, ?, 'driver', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
    """, (
        message.from_user.id,
        name,
        phone,
        data["from_city"],
        data["to_city"],
        data["date"],
        data["time"],
        profile["car"],
        profile["car_number"],
        seats,
        price,
        seats,
        seats,
        RIDE_ACTIVE,
        datetime.now().isoformat(),
    ))

    await state.clear()

    await message.answer(
        "🎉 <b>Safar muvaffaqiyatli joylandi!</b>\n\n"
        f"🚕 {data['from_city']} → {data['to_city']}\n"
        f"📅 {data['date']}\n"
        f"⏰ {data['time']}\n"
        f"💺 Bo‘sh joy: {seats}\n"
        f"💰 Narx: {price:,} so‘m\n"
        f"🚗 {html.escape(profile['car'])}\n"
        f"🔢 {html.escape(profile['car_number'])}",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================================================
# PASSENGER FLOW
# =========================================================

@dp.message(F.text == "👤 Yo‘lovchi bo‘lish")
async def passenger_start(message: Message, state: FSMContext):
    await ensure_user(message)

    await state.set_state(PassengerState.name)

    await message.answer(
        "👤 Ism-familiyangizni kiriting:"
    )


@dp.message(PassengerState.name)
async def passenger_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PassengerState.phone)

    await message.answer(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard(),
    )


@dp.message(PassengerState.phone, F.contact)
async def passenger_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(PassengerState.gender)

    await message.answer(
        "👤 Jinsingizni tanlang:",
        reply_markup=gender_keyboard(),
    )


@dp.message(PassengerState.phone)
async def passenger_phone_text(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(PassengerState.gender)

    await message.answer(
        "👤 Jinsingizni tanlang:",
        reply_markup=gender_keyboard(),
    )


@dp.message(PassengerState.gender)
async def passenger_gender(message: Message, state: FSMContext):
    if message.text not in {"👨 Erkak", "👩 Ayol"}:
        await message.answer("Jinsingizni tugmadan tanlang.")
        return

    await state.update_data(gender=message.text)
    await state.set_state(PassengerState.age_category)

    await message.answer(
        "🎂 Yosh toifangizni tanlang:",
        reply_markup=age_keyboard(),
    )


@dp.message(PassengerState.age_category)
async def passenger_age(message: Message, state: FSMContext):
    if message.text not in {"18-25", "26-35", "36-50", "51+"}:
        await message.answer("Yosh toifasini tanlang.")
        return

    await state.update_data(age_category=message.text)
    await state.set_state(PassengerState.from_city)

    await message.answer(
        "📍 Qayerdan ketasiz?",
        reply_markup=city_keyboard(),
    )


@dp.message(PassengerState.from_city)
async def passenger_from(message: Message, state: FSMContext):
    city = clean_city(message.text)

    if city not in CITIES:
        await message.answer("Shaharni tugmadan tanlang.")
        return

    await state.update_data(from_city=city)
    await state.set_state(PassengerState.to_city)

    await message.answer(
        "📍 Qayerga borasiz?",
        reply_markup=city_keyboard(),
    )


@dp.message(PassengerState.to_city)
async def passenger_to(message: Message, state: FSMContext):
    city = clean_city(message.text)

    if city not in CITIES:
        await message.answer("Shaharni tugmadan tanlang.")
        return

    data = await state.get_data()

    if city == data["from_city"]:
        await message.answer(
            "❌ Ketish va borish shahri bir xil bo‘lishi mumkin emas."
        )
        return

    await state.update_data(to_city=city)
    await state.set_state(PassengerState.date)

    await message.answer(
        "📅 Safar sanasi:",
        reply_markup=date_keyboard(),
    )


@dp.message(PassengerState.date)
async def passenger_date(message: Message, state: FSMContext):
    date = parse_date(message.text)

    if not date:
        await message.answer("Sanani tugmadan tanlang.")
        return

    await state.update_data(date=date)
    await state.set_state(PassengerState.time)

    await message.answer(
        "⏰ Safar vaqti:",
        reply_markup=time_keyboard(),
    )


@dp.message(PassengerState.time)
async def passenger_time(message: Message, state: FSMContext):
    if ":" not in message.text:
        await message.answer("Vaqtni tugmadan tanlang.")
        return

    await state.update_data(time=message.text)
    await state.set_state(PassengerState.passengers)

    await message.answer(
        "👥 Nechta yo‘lovchi bo‘lasiz?",
        reply_markup=passenger_count_keyboard(),
    )


@dp.message(PassengerState.passengers)
async def passenger_count(message: Message, state: FSMContext):
    if message.text not in {"1", "2", "3", "4"}:
        await message.answer("1 dan 4 gacha tanlang.")
        return

    await state.update_data(passengers=int(message.text))
    await state.set_state(PassengerState.location)

    await message.answer(
        "📍 <b>Eng muhim qadam</b>\n\n"
        "Haydovchi sizni aniqroq topishi uchun "
        "lokatsiyangizni yuboring.\n\n"
        "Pastdagi <b>📍 Lokatsiyani yuborish</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=location_keyboard(),
    )


# =========================================================
# PASSENGER LOCATION
# =========================================================

@dp.message(PassengerState.location, F.location)
async def passenger_location_received(
    message: Message,
    state: FSMContext
):
    lat = message.location.latitude
    lon = message.location.longitude

    await update_user_location(
        message.from_user.id,
        lat,
        lon,
    )

    await state.update_data(
        pickup_latitude=lat,
        pickup_longitude=lon,
    )

    await passenger_finish(message, state)


@dp.message(PassengerState.location, F.text == "⏭ Lokatsiyasiz davom etish")
async def passenger_without_location(
    message: Message,
    state: FSMContext
):
    await passenger_finish(message, state)


@dp.message(PassengerState.location, F.text == "📍 Lokatsiyani yuborish")
async def passenger_location_button(
    message: Message,
    state: FSMContext
):
    await message.answer(
        "📍 Iltimos, Telegram chiqargan <b>Lokatsiyani yuborish</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=location_keyboard(),
    )


@dp.message(PassengerState.location)
async def passenger_location_invalid(
    message: Message,
    state: FSMContext
):
    await message.answer(
        "📍 Lokatsiyani yuboring yoki "
        "⏭ Lokatsiyasiz davom etish tugmasini bosing.",
        reply_markup=location_keyboard(),
    )


async def passenger_finish(message: Message, state: FSMContext):
    data = await state.get_data()

    await db_execute("""
        INSERT INTO passenger_requests (
            telegram_id,
            name,
            phone,
            gender,
            age_category,
            from_city,
            to_city,
            date,
            time,
            passengers,
            pickup_latitude,
            pickup_longitude,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message.from_user.id,
        data["name"],
        data["phone"],
        data["gender"],
        data["age_category"],
        data["from_city"],
        data["to_city"],
        data["date"],
        data["time"],
        data["passengers"],
        data.get("pickup_latitude"),
        data.get("pickup_longitude"),
        "active",
        datetime.now().isoformat(),
    ))

    request_id = (
        await db_execute(
            "SELECT last_insert_rowid() AS id",
            fetchone=True,
        )
    )["id"]

    await state.clear()

    await message.answer(
        "🔎 <b>Safarlar qidirilmoqda...</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )

    rides = await db_execute("""
        SELECT
            r.*,
            d.rating,
            d.rating_count
        FROM rides r
        LEFT JOIN driver_profiles d
            ON d.telegram_id = r.telegram_id
        WHERE r.role='driver'
          AND r.status=?
          AND r.from_city=?
          AND r.to_city=?
          AND r.date=?
          AND r.available_seats >= ?
          AND r.telegram_id != ?
        ORDER BY r.time ASC
        LIMIT 20
    """, (
        RIDE_ACTIVE,
        data["from_city"],
        data["to_city"],
        data["date"],
        data["passengers"],
        message.from_user.id,
    ), fetchall=True)

    if not rides:
        await message.answer(
            "😔 Hozircha mos taksi topilmadi.\n\n"
            "Keyinroq yana qidirib ko‘ring.",
            reply_markup=main_menu(),
        )
        return

    await message.answer(
        f"🚕 <b>{len(rides)} ta mos taksi topildi.</b>\n\n"
        "Kerakli taksini tanlang:",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )

    for ride in rides:
        rating = ride["rating"] or 0
        rating_count = ride["rating_count"] or 0

        text = (
            f"🚕 <b>{html.escape(ride['car'])}</b>\n"
            f"🔢 {html.escape(ride['car_number'])}\n"
            f"🛣 {ride['from_city']} → {ride['to_city']}\n"
            f"📅 {ride['date']}\n"
            f"⏰ {ride['time']}\n"
            f"💺 Bo‘sh joy: {ride['available_seats']}\n"
            f"💰 {ride['price']:,} so‘m\n"
            f"⭐ {rating:.1f} ({rating_count} ta baho)\n"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚕 Shu taksini tanlash",
                        callback_data=(
                            f"select_taxi:{request_id}:"
                            f"{ride['id']}"
                        ),
                    )
                ]
            ]
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )


# =========================================================
# SELECT TAXI
# =========================================================

@dp.callback_query(F.data.startswith("select_taxi:"))
async def select_taxi(callback: CallbackQuery):
    _, request_id, ride_id = callback.data.split(":")

    request_id = int(request_id)
    ride_id = int(ride_id)

    request = await db_execute("""
        SELECT *
        FROM passenger_requests
        WHERE id=?
          AND telegram_id=?
          AND status='active'
    """, (
        request_id,
        callback.from_user.id,
    ), fetchone=True)

    if not request:
        await callback.answer(
            "Buyurtma topilmadi yoki yopilgan.",
            show_alert=True,
        )
        return

    # Transaction bilan joyni rezerv qilamiz
    async with aiosqlite.connect(DB) as db:

        try:
            await db.execute("BEGIN IMMEDIATE")

            ride = await db.execute_fetchone("""
                SELECT *
                FROM rides
                WHERE id=?
                  AND status=?
            """, (
                ride_id,
                RIDE_ACTIVE,
            ))

            if not ride:
                await db.rollback()
                await callback.answer(
                    "Bu safar endi mavjud emas.",
                    show_alert=True,
                )
                return

            available = ride[14]
            reserved = ride[15]

            # rides column indexes:
            # 0 id
            # 1 telegram_id
            # ...
            # available_seats = 14
            # reserved_seats = 15

            passengers = request["passengers"]

            if available - reserved < passengers:
                await db.rollback()
                await callback.answer(
                    "Bu taksida yetarli joy qolmagan.",
                    show_alert=True,
                )
                return

            duplicate = await db.execute_fetchone("""
                SELECT id
                FROM bookings
                WHERE ride_id=?
                  AND passenger_id=?
                  AND status NOT IN (
                      'rejected',
                      'cancelled',
                      'completed'
                  )
            """, (
                ride_id,
                callback.from_user.id,
            ))

            if duplicate:
                await db.rollback()
                await callback.answer(
                    "Siz bu taksiga allaqachon buyurtma yuborgansiz.",
                    show_alert=True,
                )
                return

            now = datetime.now().isoformat()

            await db.execute("""
                UPDATE rides
                SET reserved_seats=reserved_seats+?
                WHERE id=?
            """, (
                passengers,
                ride_id,
            ))

            await db.execute("""
                INSERT INTO bookings (
                    request_id,
                    ride_id,
                    passenger_id,
                    passenger_count,
                    pickup_latitude,
                    pickup_longitude,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request_id,
                ride_id,
                callback.from_user.id,
                passengers,
                request["pickup_latitude"],
                request["pickup_longitude"],
                BOOKING_PENDING,
                now,
            ))

            booking_id = (
                await db.execute_fetchone(
                    "SELECT last_insert_rowid()"
                )
            )[0]

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    # Yo‘lovchi request holati
    await db_execute("""
        UPDATE passenger_requests
        SET status='waiting'
        WHERE id=?
    """, (request_id,))

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        "📨 <b>Buyurtma haydovchiga yuborildi.</b>\n\n"
        "⏳ Haydovchi tasdiqlashini kuting.",
        parse_mode="HTML",
        reply_markup=passenger_taxi_keyboard(booking_id),
    )

    ride = await db_execute("""
        SELECT *
        FROM rides
        WHERE id=?
    """, (ride_id,), fetchone=True)

    if ride:
        passenger_name = html.escape(request["name"])
        passenger_phone = html.escape(request["phone"])

        driver_text = (
            "🚕 <b>YANGI YO‘LOVCHI BUYURTMASI</b>\n\n"
            f"👤 Ism: {passenger_name}\n"
            f"📱 Telefon: {passenger_phone}\n"
            f"👥 Yo‘lovchilar: {request['passengers']} ta\n"
            f"👫 Jins: {html.escape(request['gender'])}\n"
            f"🎂 Yosh: {html.escape(request['age_category'])}\n\n"
            f"🛣 {request['from_city']} → {request['to_city']}\n"
            f"📅 {request['date']}\n"
            f"⏰ {request['time']}\n\n"
            "⚠️ Buyurtmani qabul qilsangiz, joy avtomatik band qilinadi."
        )

        try:
            await bot.send_message(
                ride["telegram_id"],
                driver_text,
                parse_mode="HTML",
                reply_markup=driver_booking_keyboard(booking_id),
            )

            if (
                request["pickup_latitude"] is not None
                and request["pickup_longitude"] is not None
            ):
                await bot.send_location(
                    ride["telegram_id"],
                    request["pickup_latitude"],
                    request["pickup_longitude"],
                )

        except Exception:
            pass

    await callback.answer("Buyurtma haydovchiga yuborildi.")


# =========================================================
# DRIVER ACCEPT
# =========================================================

@dp.callback_query(F.data.startswith("accept_booking:"))
async def accept_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    async with aiosqlite.connect(DB) as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            booking = await db.execute_fetchone("""
                SELECT
                    b.*,
                    r.telegram_id AS driver_id,
                    r.available_seats,
                    r.reserved_seats,
                    r.car,
                    r.car_number,
                    r.price,
                    pr.name AS passenger_name,
                    pr.phone AS passenger_phone,
                    pr.from_city,
                    pr.to_city,
                    pr.date,
                    pr.time
                FROM bookings b
                JOIN rides r ON r.id=b.ride_id
                JOIN passenger_requests pr
                    ON pr.id=b.request_id
                WHERE b.id=?
            """, (booking_id,))

            if not booking:
                await db.rollback()
                await callback.answer(
                    "Buyurtma topilmadi.",
                    show_alert=True,
                )
                return

            if booking["driver_id"] != callback.from_user.id:
                await db.rollback()
                await callback.answer(
                    "Bu buyurtma sizga tegishli emas.",
                    show_alert=True,
                )
                return

            if booking["status"] != BOOKING_PENDING:
                await db.rollback()
                await callback.answer(
                    "Bu buyurtma allaqachon ko‘rib chiqilgan.",
                    show_alert=True,
                )
                return

            if booking["available_seats"] < booking["passenger_count"]:
                await db.rollback()
                await callback.answer(
                    "Bo‘sh joy yetarli emas.",
                    show_alert=True,
                )
                return

            now = datetime.now().isoformat()

            await db.execute("""
                UPDATE rides
                SET
                    available_seats=available_seats-?,
                    reserved_seats=reserved_seats-?
                WHERE id=?
            """, (
                booking["passenger_count"],
                booking["passenger_count"],
                booking["ride_id"],
            ))

            await db.execute("""
                UPDATE bookings
                SET
                    status=?,
                    accepted_at=?
                WHERE id=?
            """, (
                BOOKING_ACCEPTED,
                now,
                booking_id,
            ))

            await db.execute("""
                UPDATE passenger_requests
                SET status='accepted'
                WHERE id=?
            """, (
                booking["request_id"],
            ))

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        "✅ Buyurtma qabul qilindi.\n\n"
        f"👤 {html.escape(booking['passenger_name'])}\n"
        f"📱 {html.escape(booking['passenger_phone'])}\n"
        f"🛣 {booking['from_city']} → {booking['to_city']}\n\n"
        "📍 Yo‘lovchi lokatsiyasi buyurtma bilan birga yuborilgan.",
        parse_mode="HTML",
        reply_markup=driver_active_keyboard(booking_id),
    )

    try:
        await bot.send_message(
            booking["passenger_id"],
            "🎉 <b>Haydovchi buyurtmangizni qabul qildi!</b>\n\n"
            f"🚕 {html.escape(booking['car'])}\n"
            f"🔢 {html.escape(booking['car_number'])}\n"
            f"💰 {booking['price']:,} so‘m\n\n"
            "🚕 Haydovchi siz tomon yo‘l olmoqda.",
            parse_mode="HTML",
            reply_markup=passenger_active_keyboard(booking_id),
        )
    except Exception:
        pass

    await callback.answer("Buyurtma qabul qilindi.")


# =========================================================
# DRIVER REJECT
# =========================================================

@dp.callback_query(F.data.startswith("reject_booking:"))
async def reject_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    async with aiosqlite.connect(DB) as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            booking = await db.execute_fetchone("""
                SELECT *
                FROM bookings
                WHERE id=?
            """, (booking_id,))

            if not booking:
                await db.rollback()
                await callback.answer(
                    "Buyurtma topilmadi.",
                    show_alert=True,
                )
                return

            ride = await db.execute_fetchone("""
                SELECT telegram_id
                FROM rides
                WHERE id=?
            """, (booking["ride_id"],))

            if not ride or ride["telegram_id"] != callback.from_user.id:
                await db.rollback()
                await callback.answer(
                    "Ruxsat yo‘q.",
                    show_alert=True,
                )
                return

            if booking["status"] != BOOKING_PENDING:
                await db.rollback()
                await callback.answer(
                    "Buyurtma allaqachon ko‘rib chiqilgan.",
                    show_alert=True,
                )
                return

            await db.execute("""
                UPDATE bookings
                SET status=?
                WHERE id=?
            """, (
                BOOKING_REJECTED,
                booking_id,
            ))

            await db.execute("""
                UPDATE rides
                SET reserved_seats=MAX(
                    0,
                    reserved_seats-?
                )
                WHERE id=?
            """, (
                booking["passenger_count"],
                booking["ride_id"],
            ))

            await db.execute("""
                UPDATE passenger_requests
                SET status='rejected'
                WHERE id=?
            """, (
                booking["request_id"],
            ))

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    await callback.message.edit_reply_markup(reply_markup=None)

    try:
        await bot.send_message(
            booking["passenger_id"],
            "❌ Afsuski, haydovchi buyurtmangizni rad etdi.\n\n"
            "🔎 Boshqa taksini qidirishingiz mumkin.",
            reply_markup=main_menu(),
        )
    except Exception:
        pass

    await callback.answer("Buyurtma rad etildi.")


# =========================================================
# DRIVER LOCATION
# =========================================================

@dp.message(F.location)
async def universal_location(message: Message, state: FSMContext):
    """
    Agar PassengerState.location bo‘lsa yuqoridagi handler ishlaydi.
    Bu handler oddiy menyudagi Lokatsiyam yoki faol haydovchi uchun ishlaydi.
    """

    current_state = await state.get_state()

    if current_state == PassengerState.location.state:
        return

    lat = message.location.latitude
    lon = message.location.longitude

    await update_user_location(
        message.from_user.id,
        lat,
        lon,
    )

    active_booking = await db_execute("""
        SELECT
            b.*,
            r.telegram_id AS driver_id
        FROM bookings b
        JOIN rides r ON r.id=b.ride_id
        WHERE r.telegram_id=?
          AND b.status IN (
              'accepted',
              'arriving',
              'arrived',
              'onboard',
              'in_progress'
          )
        ORDER BY b.id DESC
        LIMIT 1
    """, (
        message.from_user.id,
    ), fetchone=True)

    if active_booking:
        await db_execute("""
            UPDATE bookings
            SET
                driver_latitude=?,
                driver_longitude=?
            WHERE id=?
        """, (
            lat,
            lon,
            active_booking["id"],
        ))

        passenger = await db_execute("""
            SELECT *
            FROM bookings
            WHERE id=?
        """, (
            active_booking["id"],
        ), fetchone=True)

        pickup_lat = active_booking["pickup_latitude"]
        pickup_lon = active_booking["pickup_longitude"]

        if pickup_lat is not None and pickup_lon is not None:
            km, minutes = await get_route_info(
                lat,
                lon,
                pickup_lat,
                pickup_lon,
            )

            text = (
                "📍 <b>Haydovchi lokatsiyasi yangilandi</b>\n\n"
                f"📏 Masofa: <b>{km:.1f} km</b>\n"
                f"⏱ Taxminiy yetib kelish: <b>{minutes} daqiqa</b>"
            )
        else:
            text = (
                "📍 <b>Haydovchi lokatsiyasi yangilandi.</b>\n"
                "Xaritadagi lokatsiyani tekshiring."
            )

        try:
            await bot.send_message(
                active_booking["passenger_id"],
                text,
                parse_mode="HTML",
                reply_markup=passenger_active_keyboard(
                    active_booking["id"]
                ),
            )

            await bot.send_location(
                active_booking["passenger_id"],
                latitude=lat,
                longitude=lon,
            )

        except Exception:
            pass

        await message.answer(
            "✅ Lokatsiyangiz yangilandi.\n"
            "Yo‘lovchiga yuborildi.",
            reply_markup=main_menu(),
        )

    else:
        await message.answer(
            "✅ Lokatsiyangiz saqlandi.",
            reply_markup=main_menu(),
        )


# =========================================================
# LOCATION MENU
# =========================================================

@dp.message(F.text == "📍 Lokatsiyam")
async def location_menu(message: Message):
    await message.answer(
        "📍 Lokatsiyangizni yuborish uchun pastdagi tugmani bosing:",
        reply_markup=location_keyboard(),
    )


@dp.message(F.text == "📍 Lokatsiyani yuborish")
async def location_manual_text(message: Message):
    await message.answer(
        "📍 Telegram'dagi <b>Lokatsiyani yuborish</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=location_keyboard(),
    )


# =========================================================
# DRIVER LOCATION CALLBACK
# =========================================================

@dp.callback_query(F.data.startswith("driver_location:"))
async def driver_location_request(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    booking = await db_execute("""
        SELECT
            b.*,
            r.telegram_id AS driver_id
        FROM bookings b
        JOIN rides r ON r.id=b.ride_id
        WHERE b.id=?
    """, (
        booking_id,
    ), fetchone=True)

    if not booking:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return

    if booking["driver_id"] != callback.from_user.id:
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return

    await callback.message.answer(
        "📍 Lokatsiyangizni yuboring:",
        reply_markup=location_keyboard(),
    )

    await callback.answer()


# =========================================================
# TRACK DRIVER
# =========================================================

@dp.callback_query(F.data.startswith("track:"))
async def track_driver(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    booking = await db_execute("""
        SELECT *
        FROM bookings
        WHERE id=?
    """, (
        booking_id,
    ), fetchone=True)

    if not booking:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return

    if booking["passenger_id"] != callback.from_user.id:
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return

    if (
        booking["driver_latitude"] is None
        or booking["driver_longitude"] is None
    ):
        await callback.answer(
            "Haydovchi hali lokatsiyasini yubormagan.",
            show_alert=True,
        )
        return

    lat = booking["driver_latitude"]
    lon = booking["driver_longitude"]

    if (
        booking["pickup_latitude"] is not None
        and booking["pickup_longitude"] is not None
    ):
        km, minutes = await get_route_info(
            lat,
            lon,
            booking["pickup_latitude"],
            booking["pickup_longitude"],
        )

        await callback.message.answer(
            "🚕 <b>Haydovchi lokatsiyasi</b>\n\n"
            f"📏 Masofa: <b>{km:.1f} km</b>\n"
            f"⏱ Yetib kelish: <b>{minutes} daqiqa</b>",
            parse_mode="HTML",
        )

    await bot.send_location(
        callback.from_user.id,
        latitude=lat,
        longitude=lon,
    )

    await callback.answer()


# =========================================================
# ARRIVED
# =========================================================

@dp.callback_query(F.data.startswith("arrived:"))
async def driver_arrived(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    booking = await db_execute("""
        SELECT
            b.*,
            r.telegram_id AS driver_id
        FROM bookings b
        JOIN rides r ON r.id=b.ride_id
        WHERE b.id=?
    """, (
        booking_id,
    ), fetchone=True)

    if not booking or booking["driver_id"] != callback.from_user.id:
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return

    await db_execute("""
        UPDATE bookings
        SET
            status=?,
            arrived_at=?
        WHERE id=?
    """, (
        BOOKING_ARRIVED,
        datetime.now().isoformat(),
        booking_id,
    ))

    try:
        await bot.send_message(
            booking["passenger_id"],
            "📍 <b>Haydovchi manzilga yetib keldi.</b>\n\n"
            "Iltimos, mashinani toping.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.message.answer(
        "📍 Yo‘lovchiga haydovchi kelgani bildirildi.",
        reply_markup=driver_active_keyboard(booking_id),
    )

    await callback.answer("Yo‘lovchiga xabar yuborildi.")


# =========================================================
# ONBOARD
# =========================================================

@dp.callback_query(F.data.startswith("onboard:"))
async def driver_onboard(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    booking = await db_execute("""
        SELECT
            b.*,
            r.telegram_id AS driver_id
        FROM bookings b
        JOIN rides r ON r.id=b.ride_id
        WHERE b.id=?
    """, (
        booking_id,
    ), fetchone=True)

    if not booking or booking["driver_id"] != callback.from_user.id:
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return

    await db_execute("""
        UPDATE bookings
        SET
            status=?,
            started_at=?
        WHERE id=?
    """, (
        BOOKING_ONBOARD,
        datetime.now().isoformat(),
        booking_id,
    ))

    try:
        await bot.send_message(
            booking["passenger_id"],
            "🚕 <b>Sizni haydovchi oldi.</b>\n\n"
            "Safaringiz boshlandi.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("Safar boshlandi.")


# =========================================================
# COMPLETE
# =========================================================

@dp.callback_query(F.data.startswith("complete:"))
async def complete_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    booking = await db_execute("""
        SELECT
            b.*,
            r.telegram_id AS driver_id,
            r.id AS ride_id
        FROM bookings b
        JOIN rides r ON r.id=b.ride_id
        WHERE b.id=?
    """, (
        booking_id,
    ), fetchone=True)

    if not booking:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return

    if booking["driver_id"] != callback.from_user.id:
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return

    if booking["status"] not in {
        BOOKING_ONBOARD,
        BOOKING_IN_PROGRESS,
        BOOKING_ARRIVED,
    }:
        await callback.answer(
            "Bu buyurtmani hozir yakunlab bo‘lmaydi.",
            show_alert=True,
        )
        return

    await db_execute("""
        UPDATE bookings
        SET
            status=?,
            completed_at=?
        WHERE id=?
    """, (
        BOOKING_COMPLETED,
        datetime.now().isoformat(),
        booking_id,
    ))

    try:
        await bot.send_message(
            booking["passenger_id"],
            "🏁 <b>Sizning safaringiz yakunlandi.</b>\n\n"
            "Haydovchini baholashingiz mumkin:",
            parse_mode="HTML",
            reply_markup=rating_keyboard(booking_id),
        )
    except Exception:
        pass

    await callback.message.answer(
        "🏁 Safar yakunlandi.",
        reply_markup=main_menu(),
    )

    await callback.answer("Safar yakunlandi.")


# =========================================================
# CANCEL BOOKING BY PASSENGER
# =========================================================

@dp.callback_query(F.data.startswith("cancel_booking:"))
async def cancel_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    async with aiosqlite.connect(DB) as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            booking = await db.execute_fetchone("""
                SELECT *
                FROM bookings
                WHERE id=?
            """, (
                booking_id,
            ))

            if not booking:
                await db.rollback()
                await callback.answer(
                    "Buyurtma topilmadi.",
                    show_alert=True,
                )
                return

            if booking["passenger_id"] != callback.from_user.id:
                await db.rollback()
                await callback.answer(
                    "Ruxsat yo‘q.",
                    show_alert=True,
                )
                return

            if booking["status"] in {
                BOOKING_CANCELLED,
                BOOKING_REJECTED,
                BOOKING_COMPLETED,
            }:
                await db.rollback()
                await callback.answer(
                    "Buyurtma allaqachon yopilgan.",
                    show_alert=True,
                )
                return

            if booking["status"] == BOOKING_PENDING:
                await db.execute("""
                    UPDATE rides
                    SET reserved_seats=MAX(
                        0,
                        reserved_seats-?
                    )
                    WHERE id=?
                """, (
                    booking["passenger_count"],
                    booking["ride_id"],
                ))

            elif booking["status"] in {
                BOOKING_ACCEPTED,
                BOOKING_ARRIVING,
                BOOKING_ARRIVED,
            }:
                await db.execute("""
                    UPDATE rides
                    SET available_seats=available_seats+?
                    WHERE id=?
                """, (
                    booking["passenger_count"],
                    booking["ride_id"],
                ))

            await db.execute("""
                UPDATE bookings
                SET status=?
                WHERE id=?
            """, (
                BOOKING_CANCELLED,
                booking_id,
            ))

            await db.execute("""
                UPDATE passenger_requests
                SET status='cancelled'
                WHERE id=?
            """, (
                booking["request_id"],
            ))

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    ride = await db_execute("""
        SELECT telegram_id
        FROM rides
        WHERE id=?
    """, (
        booking["ride_id"],
    ), fetchone=True)

    if ride:
        try:
            await bot.send_message(
                ride["telegram_id"],
                "❌ Yo‘lovchi buyurtmani bekor qildi."
            )
        except Exception:
            pass

    await callback.message.answer(
        "❌ Buyurtma bekor qilindi.",
        reply_markup=main_menu(),
    )

    await callback.answer("Buyurtma bekor qilindi.")


# =========================================================
# DRIVER CANCEL
# =========================================================

@dp.callback_query(F.data.startswith("driver_cancel:"))
async def driver_cancel(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    async with aiosqlite.connect(DB) as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            booking = await db.execute_fetchone("""
                SELECT
                    b.*,
                    r.telegram_id AS driver_id
                FROM bookings b
                JOIN rides r ON r.id=b.ride_id
                WHERE b.id=?
            """, (
                booking_id,
            ))

            if not booking:
                await db.rollback()
                await callback.answer(
                    "Buyurtma topilmadi.",
                    show_alert=True,
                )
                return

            if booking["driver_id"] != callback.from_user.id:
                await db.rollback()
                await callback.answer(
                    "Ruxsat yo‘q.",
                    show_alert=True,
                )
                return

            if booking["status"] == BOOKING_PENDING:

                await db.execute("""
                    UPDATE rides
                    SET reserved_seats=MAX(
                        0,
                        reserved_seats-?
                    )
                    WHERE id=?
                """, (
                    booking["passenger_count"],
                    booking["ride_id"],
                ))

            elif booking["status"] in {
                BOOKING_ACCEPTED,
                BOOKING_ARRIVING,
                BOOKING_ARRIVED,
            }:

                await db.execute("""
                    UPDATE rides
                    SET available_seats=available_seats+?
                    WHERE id=?
                """, (
                    booking["passenger_count"],
                    booking["ride_id"],
                ))

            await db.execute("""
                UPDATE bookings
                SET status=?
                WHERE id=?
            """, (
                BOOKING_CANCELLED,
                booking_id,
            ))

            await db.execute("""
                UPDATE passenger_requests
                SET status='cancelled'
                WHERE id=?
            """, (
                booking["request_id"],
            ))

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    try:
        await bot.send_message(
            booking["passenger_id"],
            "❌ Haydovchi buyurtmani bekor qildi.\n\n"
            "Boshqa taksini qidirishingiz mumkin.",
            reply_markup=main_menu(),
        )
    except Exception:
        pass

    await callback.message.answer(
        "❌ Buyurtma bekor qilindi.",
        reply_markup=main_menu(),
    )

    await callback.answer("Buyurtma bekor qilindi.")


# =========================================================
# SEARCH TAXI
# =========================================================

@dp.message(F.text == "🔎 Safar qidirish")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(SearchState.from_city)

    await message.answer(
        "🔎 Qayerdan?",
        reply_markup=city_keyboard(),
    )


@dp.message(SearchState.from_city)
async def search_from(message: Message, state: FSMContext):
    city = clean_city(message.text)

    if city not in CITIES:
        await message.answer("Shaharni tugmadan tanlang.")
        return

    await state.update_data(from_city=city)
    await state.set_state(SearchState.to_city)

    await message.answer(
        "📍 Qayerga?",
        reply_markup=city_keyboard(),
    )


@dp.message(SearchState.to_city)
async def search_to(message: Message, state: FSMContext):
    city = clean_city(message.text)

    if city not in CITIES:
        await message.answer("Shaharni tugmadan tanlang.")
        return

    data = await state.get_data()

    if city == data["from_city"]:
        await message.answer("❌ Shaharlar bir xil bo‘lmasin.")
        return

    await state.update_data(to_city=city)
    await state.set_state(SearchState.date)

    await message.answer(
        "📅 Sana:",
        reply_markup=date_keyboard(),
    )


@dp.message(SearchState.date)
async def search_date(message: Message, state: FSMContext):
    date = parse_date(message.text)

    if not date:
        await message.answer("Sanani tugmadan tanlang.")
        return

    await state.update_data(date=date)
    await state.set_state(SearchState.time)

    await message.answer(
        "⏰ Vaqt:",
        reply_markup=time_keyboard(),
    )


@dp.message(SearchState.time)
async def search_time(message: Message, state: FSMContext):
    await state.update_data(time=message.text)
    await state.set_state(SearchState.passengers)

    await message.answer(
        "👥 Nechta yo‘lovchi?",
        reply_markup=passenger_count_keyboard(),
    )


@dp.message(SearchState.passengers)
async def search_passengers(message: Message, state: FSMContext):
    if message.text not in {"1", "2", "3", "4"}:
        await message.answer("1 dan 4 gacha tanlang.")
        return

    data = await state.get_data()

    passengers = int(message.text)

    rides = await db_execute("""
        SELECT
            r.*,
            d.rating,
            d.rating_count
        FROM rides r
        LEFT JOIN driver_profiles d
            ON d.telegram_id=r.telegram_id
        WHERE r.role='driver'
          AND r.status=?
          AND r.from_city=?
          AND r.to_city=?
          AND r.date=?
          AND r.available_seats>=?
        ORDER BY r.time ASC
        LIMIT 20
    """, (
        RIDE_ACTIVE,
        data["from_city"],
        data["to_city"],
        data["date"],
        passengers,
    ), fetchall=True)

    await state.clear()

    if not rides:
        await message.answer(
            "😔 Mos safar topilmadi.",
            reply_markup=main_menu(),
        )
        return

    await message.answer(
        f"🚕 {len(rides)} ta safar topildi:",
        reply_markup=main_menu(),
    )

    for ride in rides:
        rating = ride["rating"] or 0
        count = ride["rating_count"] or 0

        await message.answer(
            f"🚕 <b>{html.escape(ride['car'])}</b>\n"
            f"🔢 {html.escape(ride['car_number'])}\n"
            f"🛣 {ride['from_city']} → {ride['to_city']}\n"
            f"📅 {ride['date']}\n"
            f"⏰ {ride['time']}\n"
            f"💺 {ride['available_seats']} ta joy\n"
            f"💰 {ride['price']:,} so‘m\n"
            f"⭐ {rating:.1f} ({count})",
            parse_mode="HTML",
        )


# =========================================================
# MY RIDES
# =========================================================

@dp.message(F.text == "📋 Mening safarlarim")
async def my_rides(message: Message):
    driver_rides = await db_execute("""
        SELECT *
        FROM rides
        WHERE telegram_id=?
        ORDER BY id DESC
        LIMIT 20
    """, (
        message.from_user.id,
    ), fetchall=True)

    bookings = await db_execute("""
        SELECT
            b.*,
            r.from_city,
            r.to_city,
            r.date,
            r.time,
            r.car,
            r.car_number,
            r.price
        FROM bookings b
        JOIN rides r ON r.id=b.ride_id
        WHERE b.passenger_id=?
        ORDER BY b.id DESC
        LIMIT 20
    """, (
        message.from_user.id,
    ), fetchall=True)

    text = "📋 <b>Mening safarlarim</b>\n\n"

    if driver_rides:
        text += "<b>🚕 Haydovchi safarlarim:</b>\n"

        for ride in driver_rides:
            text += (
                f"#{ride['id']} "
                f"{ride['from_city']} → {ride['to_city']} | "
                f"{ride['date']} {ride['time']} | "
                f"💺 {ride['available_seats']}/{ride['original_seats']} | "
                f"{ride['status']}\n"
            )

        text += "\n"

    if bookings:
        text += "<b>👤 Yo‘lovchi buyurtmalarim:</b>\n"

        for b in bookings:
            text += (
                f"#{b['id']} "
                f"{b['from_city']} → {b['to_city']} | "
                f"{b['date']} {b['time']} | "
                f"🚕 {html.escape(b['car'])} | "
                f"{b['status']}\n"
            )

    if not driver_rides and not bookings:
        text += "Hozircha safarlar yo‘q."

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================================================
# PROFILE
# =========================================================

@dp.message(F.text == "👤 Profilim")
async def profile(message: Message):
    user = await db_execute("""
        SELECT *
        FROM users
        WHERE telegram_id=?
    """, (
        message.from_user.id,
    ), fetchone=True)

    driver = await get_driver_profile(message.from_user.id)

    text = "👤 <b>Profilim</b>\n\n"

    if user:
        text += f"👤 Ism: {html.escape(user['name'] or '-')}\n"
        text += f"📱 Telefon: {html.escape(user['phone'] or '-')}\n"

    if driver:
        text += "\n<b>🚕 Haydovchi profili:</b>\n"
        text += f"🚗 {html.escape(driver['car'] or '-')}\n"
        text += f"🔢 {html.escape(driver['car_number'] or '-')}\n"
        text += f"📌 Holat: {driver['status']}\n"
        text += f"⭐ Reyting: {driver['rating']:.1f}\n"

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================================================
# RATING
# =========================================================

@dp.message(F.text == "⭐ Haydovchini baholash")
async def rating_start(message: Message):
    booking = await db_execute("""
        SELECT *
        FROM bookings
        WHERE passenger_id=?
          AND status='completed'
        ORDER BY completed_at DESC
        LIMIT 1
    """, (
        message.from_user.id,
    ), fetchone=True)

    if not booking:
        await message.answer(
            "⭐ Baholash uchun yakunlangan safar topilmadi."
        )
        return

    existing = await db_execute("""
        SELECT id
        FROM ratings
        WHERE booking_id=?
    """, (
        booking["id"],
    ), fetchone=True)

    if existing:
        await message.answer(
            "Siz bu safarni allaqachon baholagansiz."
        )
        return

    await message.answer(
        "⭐ Haydovchini baholang:",
        reply_markup=rating_keyboard(booking["id"]),
    )


@dp.callback_query(F.data.startswith("rating:"))
async def rating_select(callback: CallbackQuery, state: FSMContext):
    _, booking_id, rating = callback.data.split(":")

    booking_id = int(booking_id)
    rating = int(rating)

    booking = await db_execute("""
        SELECT *
        FROM bookings
        WHERE id=?
          AND passenger_id=?
          AND status='completed'
    """, (
        booking_id,
        callback.from_user.id,
    ), fetchone=True)

    if not booking:
        await callback.answer(
            "Baholash mumkin emas.",
            show_alert=True,
        )
        return

    existing = await db_execute("""
        SELECT id
        FROM ratings
        WHERE booking_id=?
    """, (
        booking_id,
    ), fetchone=True)

    if existing:
        await callback.answer(
            "Allaqachon baholangan.",
            show_alert=True,
        )
        return

    await db_execute("""
        INSERT INTO ratings (
            booking_id,
            ride_id,
            driver_id,
            passenger_id,
            rating,
            created_at
        )
        SELECT
            ?,
            b.ride_id,
            r.telegram_id,
            ?,
            ?,
            ?
        FROM bookings b
        JOIN rides r ON r.id=b.ride_id
        WHERE b.id=?
    """, (
        booking_id,
        callback.from_user.id,
        rating,
        datetime.now().isoformat(),
        booking_id,
    ))

    await db_execute("""
        UPDATE driver_profiles
        SET
            rating=(
                SELECT AVG(rating)
                FROM ratings
                WHERE driver_id=?
            ),
            rating_count=(
                SELECT COUNT(*)
                FROM ratings
                WHERE driver_id=?
            )
        WHERE telegram_id=(
            SELECT telegram_id
            FROM rides
            WHERE id=?
        )
    """, (
        booking["driver_id"] if "driver_id" in booking.keys() else 0,
        booking["driver_id"] if "driver_id" in booking.keys() else 0,
        booking["ride_id"],
    ))

    await callback.message.answer(
        f"⭐ Rahmat! Siz {rating}/5 baho berdingiz.",
        reply_markup=main_menu(),
    )

    await callback.answer("Baholandi.")


# =========================================================
# CANCEL RIDE
# =========================================================

@dp.message(F.text == "❌ Safarni bekor qilish")
async def cancel_ride_start(message: Message):
    rides = await db_execute("""
        SELECT *
        FROM rides
        WHERE telegram_id=?
          AND status=?
        ORDER BY id DESC
    """, (
        message.from_user.id,
        RIDE_ACTIVE,
    ), fetchall=True)

    if not rides:
        await message.answer(
            "Faol safaringiz yo‘q."
        )
        return

    rows = []

    for ride in rides:
        rows.append([
            InlineKeyboardButton(
                text=(
                    f"#{ride['id']} "
                    f"{ride['from_city']} → {ride['to_city']}"
                ),
                callback_data=f"cancel_ride:{ride['id']}",
            )
        ])

    await message.answer(
        "❌ Qaysi safarni bekor qilasiz?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )


@dp.callback_query(F.data.startswith("cancel_ride:"))
async def cancel_ride(callback: CallbackQuery):
    ride_id = int(callback.data.split(":")[1])

    ride = await db_execute("""
        SELECT *
        FROM rides
        WHERE id=?
          AND telegram_id=?
          AND status=?
    """, (
        ride_id,
        callback.from_user.id,
        RIDE_ACTIVE,
    ), fetchone=True)

    if not ride:
        await callback.answer(
            "Safar topilmadi.",
            show_alert=True,
        )
        return

    await db_execute("""
        UPDATE rides
        SET status=?
        WHERE id=?
    """, (
        RIDE_CANCELLED,
        ride_id,
    ))

    bookings = await db_execute("""
        SELECT *
        FROM bookings
        WHERE ride_id=?
          AND status NOT IN (
              'cancelled',
              'rejected',
              'completed'
          )
    """, (
        ride_id,
    ), fetchall=True)

    for booking in bookings:

        await db_execute("""
            UPDATE bookings
            SET status=?
            WHERE id=?
        """, (
            BOOKING_CANCELLED,
            booking["id"],
        ))

        await db_execute("""
            UPDATE passenger_requests
            SET status='cancelled'
            WHERE id=?
        """, (
            booking["request_id"],
        ))

        try:
            await bot.send_message(
                booking["passenger_id"],
                "❌ Haydovchi safarni bekor qildi.\n\n"
                "Boshqa taksini qidirishingiz mumkin.",
                reply_markup=main_menu(),
            )
        except Exception:
            pass

    await callback.message.answer(
        "✅ Safar bekor qilindi.",
        reply_markup=main_menu(),
    )

    await callback.answer("Safar bekor qilindi.")


# =========================================================
# HELP
# =========================================================

@dp.message(F.text == "📞 Yordam")
async def help_command(message: Message):
    await message.answer(
        "📞 <b>OPPER TAXI yordam</b>\n\n"
        "🚕 Haydovchi bo‘lish — hujjat topshirish va safar joylash.\n"
        "👤 Yo‘lovchi bo‘lish — taksi buyurtma qilish.\n"
        "🔎 Safar qidirish — mavjud taksilarni ko‘rish.\n"
        "📍 Lokatsiyam — lokatsiyani yuborish.\n"
        "📋 Mening safarlarim — buyurtmalarni ko‘rish.\n\n"
        "Muammo bo‘lsa administratorga murojaat qiling.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================================================
# ADMIN COMMAND
# =========================================================

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Ruxsat yo‘q.")
        return

    pending = await db_execute("""
        SELECT *
        FROM driver_profiles
        WHERE status=?
        ORDER BY created_at DESC
    """, (
        DRIVER_PENDING,
    ), fetchall=True)

    active_rides = await db_execute("""
        SELECT COUNT(*) AS count
        FROM rides
        WHERE status=?
    """, (
        RIDE_ACTIVE,
    ), fetchone=True)

    bookings = await db_execute("""
        SELECT COUNT(*) AS count
        FROM bookings
        WHERE status IN (
            'pending_driver',
            'accepted',
            'arriving',
            'arrived',
            'onboard',
            'in_progress'
        )
    """, fetchone=True)

    text = (
        "👨‍💼 <b>ADMIN PANEL</b>\n\n"
        f"🚕 Faol safarlar: {active_rides['count']}\n"
        f"📦 Faol buyurtmalar: {bookings['count']}\n"
        f"⏳ Kutilayotgan haydovchilar: {len(pending)}\n"
    )

    await message.answer(
        text,
        parse_mode="HTML",
    )

    for driver in pending:
        await message.answer(
            "⏳ <b>Kutilayotgan haydovchi</b>\n\n"
            f"🆔 <code>{driver['telegram_id']}</code>\n"
            f"🚗 {html.escape(driver['car'])}\n"
            f"🔢 {html.escape(driver['car_number'])}",
            parse_mode="HTML",
            reply_markup=admin_driver_keyboard(
                driver["telegram_id"]
            ),
        )


# =========================================================
# ADMIN VERIFY COMMANDS
# =========================================================

@dp.message(Command("verify"))
async def verify_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Format: /verify TELEGRAM_ID"
        )
        return

    try:
        driver_id = int(parts[1])
    except Exception:
        await message.answer("ID noto‘g‘ri.")
        return

    await db_execute("""
        UPDATE driver_profiles
        SET status=?
        WHERE telegram_id=?
    """, (
        DRIVER_VERIFIED,
        driver_id,
    ))

    await message.answer("✅ Tasdiqlandi.")

    try:
        await bot.send_message(
            driver_id,
            "🎉 Haydovchi profilingiz tasdiqlandi!\n"
            "Endi safar joylashingiz mumkin.",
            reply_markup=main_menu(),
        )
    except Exception:
        pass


@dp.message(Command("reject"))
async def reject_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Format: /reject TELEGRAM_ID"
        )
        return

    driver_id = int(parts[1])

    await db_execute("""
        UPDATE driver_profiles
        SET status=?
        WHERE telegram_id=?
    """, (
        DRIVER_REJECTED,
        driver_id,
    ))

    await message.answer("❌ Rad etildi.")


@dp.message(Command("block"))
async def block_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Format: /block TELEGRAM_ID"
        )
        return

    driver_id = int(parts[1])

    await db_execute("""
        UPDATE driver_profiles
        SET status=?
        WHERE telegram_id=?
    """, (
        DRIVER_BLOCKED,
        driver_id,
    ))

    await db_execute("""
        UPDATE rides
        SET status=?
        WHERE telegram_id=?
          AND status=?
    """, (
        RIDE_CANCELLED,
        driver_id,
        RIDE_ACTIVE,
    ))

    await message.answer("🚫 Bloklandi.")


@dp.message(Command("unblock"))
async def unblock_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Format: /unblock TELEGRAM_ID"
        )
        return

    driver_id = int(parts[1])

    await db_execute("""
        UPDATE driver_profiles
        SET status=?
        WHERE telegram_id=?
    """, (
        DRIVER_VERIFIED,
        driver_id,
    ))

    await message.answer("✅ Blokdan chiqarildi.")


# =========================================================
# FALLBACK
# =========================================================

@dp.message()
async def fallback(message: Message):
    await ensure_user(message)

    await message.answer(
        "Men bu buyruqni tushunmadim.\n\n"
        "Iltimos, menyudagi tugmalardan foydalaning.",
        reply_markup=main_menu(),
    )


# =========================================================
# RUN
# =========================================================

async def main():
    await init_db()

    print("OPPER TAXI BOT IS RUNNING...")

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


if __name__ == "__main__":
    asyncio.run(main())
