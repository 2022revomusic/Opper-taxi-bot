import os
import asyncio
import re
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


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "653914246").split(",")
    if x.strip().isdigit()
}

DB_PATH = "oper_taxi.db"

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


# ============================================================
# BOT
# ============================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# STATES
# ============================================================

class PassengerState(StatesGroup):
    from_city = State()
    to_city = State()
    time = State()
    seats = State()
    name = State()
    phone = State()
    location = State()


class DriverRegisterState(StatesGroup):
    name = State()
    phone = State()
    car_model = State()
    car_number = State()


class DriverRideState(StatesGroup):
    from_city = State()
    to_city = State()
    time = State()
    seats = State()


# ============================================================
# KEYBOARDS
# ============================================================

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
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True,
    )


def city_keyboard():
    rows = []

    for i in range(0, len(CITIES), 2):
        rows.append(
            [
                KeyboardButton(text=city)
                for city in CITIES[i:i + 2]
            ]
        )

    rows.append(
        [KeyboardButton(text="❌ Bekor qilish")]
    )

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )


def time_keyboard():
    rows = []

    for i in range(0, len(TIMES), 4):
        rows.append(
            [
                KeyboardButton(text=t)
                for t in TIMES[i:i + 4]
            ]
        )

    rows.append(
        [KeyboardButton(text="❌ Bekor qilish")]
    )

    return ReplyKeyboardMarkup(
        keyboard=rows,
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
                KeyboardButton(
                    text="⏭ Lokatsiyasiz davom etish"
                )
            ],
            [
                KeyboardButton(
                    text="❌ Bekor qilish"
                )
            ],
        ],
        resize_keyboard=True,
    )


def driver_request_keyboard(request_id: int):
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


def passenger_cancel_keyboard(request_id: int):
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


def booking_driver_keyboard(booking_id: int):
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
                    text="🚕 Yetib keldim",
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


def passenger_booking_keyboard(booking_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 Haydovchini ko‘rish",
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


def admin_driver_keyboard(user_id: int):
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


# ============================================================
# DATABASE
# ============================================================

async def db_execute(
    query,
    params=(),
    fetch=False,
    fetchone=False,
):
    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            query,
            params,
        )

        if fetchone:
            return await cursor.fetchone()

        if fetch:
            return await cursor.fetchall()

        await db.commit()

        return cursor.lastrowid


async def column_exists(table_name, column_name):

    rows = await db_execute(
        f"PRAGMA table_info({table_name})",
        fetch=True,
    )

    return any(
        row["name"] == column_name
        for row in rows
    )


async def add_column_if_missing(
    table_name,
    column_name,
    column_type,
):

    if not await column_exists(
        table_name,
        column_name,
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name} {column_type}
                """
            )

            await db.commit()


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

        await db.execute("""
        CREATE TABLE IF NOT EXISTS group_messages (
            chat_id INTEGER,
            message_id INTEGER,
            processed_at TEXT,
            PRIMARY KEY(chat_id, message_id)
        )
        """)

        await db.commit()

    # ========================================================
    # ESKI DATABASE UCHUN MIGRATION
    # ========================================================

    await add_column_if_missing(
        "rides",
        "source_chat_id",
        "INTEGER",
    )

    await add_column_if_missing(
        "rides",
        "source_message_id",
        "INTEGER",
    )

    await add_column_if_missing(
        "rides",
        "source_text",
        "TEXT",
    )

    await add_column_if_missing(
        "passenger_requests",
        "source_chat_id",
        "INTEGER",
    )

    await add_column_if_missing(
        "passenger_requests",
        "source_message_id",
        "INTEGER",
    )

    await add_column_if_missing(
        "passenger_requests",
        "source_text",
        "TEXT",
    )


# ============================================================
# HELPERS
# ============================================================

async def save_user(message: Message):

    user = message.from_user

    await db_execute(
        """
        INSERT INTO users
        (
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
            user.id,
            user.full_name,
            user.username,
            datetime.now().isoformat(),
        ),
    )


async def save_user_phone(
    user_id,
    phone,
):

    await db_execute(
        """
        UPDATE users
        SET phone=?
        WHERE user_id=?
        """,
        (
            phone,
            user_id,
        ),
    )


async def get_user(user_id):

    return await db_execute(
        """
        SELECT *
        FROM users
        WHERE user_id=?
        """,
        (user_id,),
        fetchone=True,
    )


async def get_driver(driver_id):

    return await db_execute(
        """
        SELECT *
        FROM driver_profiles
        WHERE user_id=?
        """,
        (driver_id,),
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


async def safe_send(
    user_id,
    text,
    **kwargs,
):

    try:

        await bot.send_message(
            user_id,
            text,
            **kwargs,
        )

        return True

    except Exception as e:

        print(
            f"SEND ERROR {user_id}: {e}"
        )

        return False


async def notify_admins(
    text,
    **kwargs,
):

    for admin_id in ADMIN_IDS:

        await safe_send(
            admin_id,
            text,
            **kwargs,
        )


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.replace(
        "’",
        "'",
    )

    text = text.replace(
        "‘",
        "'",
    )

    text = text.replace(
        "ʻ",
        "'",
    )

    text = text.replace(
        "ʼ",
        "'",
    )

    text = text.replace(
        "–",
        "-",
    )

    text = text.replace(
        "—",
        "-",
    )

    return " ".join(
        text.lower().split()
    )


CITY_ALIASES = {
    "toshkent": "Toshkent",
    "tashkent": "Toshkent",

    "namangan": "Namangan",

    "andijon": "Andijon",
    "andijan": "Andijon",

    "fargona": "Farg‘ona",
    "fergana": "Farg‘ona",
    "ferghana": "Farg‘ona",

    "qoqon": "Qo‘qon",
    "kokand": "Qo‘qon",
    "qoqand": "Qo‘qon",

    "margilon": "Marg‘ilon",
    "margilan": "Marg‘ilon",
}


def extract_cities(text):

    normalized = normalize_text(text)

    found = []

    for alias, city in CITY_ALIASES.items():

        pattern = rf"\b{re.escape(alias)}\b"

        match = re.search(
            pattern,
            normalized,
        )

        if match:

            found.append(
                (
                    match.start(),
                    city,
                )
            )

    found.sort(
        key=lambda x: x[0]
    )

    result = []

    for _, city in found:

        if city not in result:

            result.append(city)

    return result[:2]


def extract_time(text):

    normalized = normalize_text(text)

    patterns = [
        r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b",
        r"\b([01]?\d|2[0-3])\s+([0-5]\d)\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized,
        )

        if match:

            hour = int(match.group(1))
            minute = int(match.group(2))

            return f"{hour:02d}:{minute:02d}"

    return None


def extract_seats(text):

    normalized = normalize_text(text)

    patterns = [
        r"\b(\d+)\s*(?:kishi|kishiга|kishiга|odam|yo['']lovchi)\b",
        r"\b(\d+)\s*(?:ta\s*)?(?:joy|mashina|o'rin|orin)\b",
        r"\b(\d+)\s*(?:ta)?\s*(?:yo['']lovchi)\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized,
        )

        if match:

            value = int(
                match.group(1)
            )

            if 1 <= value <= 8:
                return value

    # "2 kishi" uchun oddiy fallback
    match = re.search(
        r"\b(\d+)\s*kishi\b",
        normalized,
    )

    if match:

        value = int(
            match.group(1)
        )

        if 1 <= value <= 8:
            return value

    return None


def normalize_phone(raw):

    if not raw:
        return None

    digits = re.sub(
        r"\D",
        "",
        raw,
    )

    if digits.startswith("998"):
        return "+" + digits

    if digits.startswith("8") and len(digits) == 11:
        return "+998" + digits[1:]

    if len(digits) == 9:
        return "+998" + digits

    return None


def extract_phone(text):

    patterns = [
        r"\+?998[\s\-()]?\d[\d\s\-()]{7,12}",
        r"\b\d{9}\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
        )

        if match:

            phone = normalize_phone(
                match.group(0)
            )

            if phone:
                return phone

    return None


def is_passenger_message(text):

    normalized = normalize_text(text)

    keywords = [
        "taksi kerak",
        "taksi kerek",
        "mashina kerak",
        "mashina kerek",
        "joy kerak",
        "joy kerek",
        "olib keting",
        "olib ketish",
        "yo'lovchi",
        "yo'lovchiga",
        "chiqaman",
        "ketaman",
        "kerak",
        "kerek",
        "izlayapman",
        "izlayman",
        "olib borish",
    ]

    return any(
        word in normalized
        for word in keywords
    )


def is_driver_message(text):

    normalized = normalize_text(text)

    keywords = [
        "joy bor",
        "bo'sh joy",
        "bosh joy",
        "bo'sh",
        "olaman",
        "taksi bor",
        "mashina bor",
        "mashina chiqadi",
        "taksi chiqadi",
        "ketaman",
        "yo'lga chiqaman",
        "joy mavjud",
    ]

    return any(
        word in normalized
        for word in keywords
    )


def clean_person_name(name):

    if not name:
        return "Guruh yo‘lovchisi"

    name = name.strip()

    if len(name) > 80:
        name = name[:80]

    return name


def extract_name_from_message(message: Message):

    if message.from_user:

        if message.from_user.full_name:
            return clean_person_name(
                message.from_user.full_name
            )

    return "Guruh yo‘lovchisi"


# ============================================================
# GROUP MESSAGE DUPLICATE CHECK
# ============================================================

async def group_message_already_processed(
    chat_id,
    message_id,
):

    row = await db_execute(
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

    return row is not None


async def mark_group_message_processed(
    chat_id,
    message_id,
):

    await db_execute(
        """
        INSERT OR IGNORE INTO group_messages
        (
            chat_id,
            message_id,
            processed_at
        )
        VALUES (?, ?, ?)
        """,
        (
            chat_id,
            message_id,
            datetime.now().isoformat(),
        ),
    )


# ============================================================
# SEND REQUEST TO DRIVERS
# ============================================================

async def send_request_to_matching_drivers(
    request_id,
):

    request = await get_request(
        request_id
    )

    if not request:
        return 0

    drivers = await db_execute(
        """
        SELECT
            d.*,
            r.id AS ride_id,
            r.available_seats
        FROM driver_profiles d
        JOIN rides r
            ON r.driver_id=d.user_id
        WHERE d.status='approved'
          AND r.status='active'
          AND r.from_city=?
          AND r.to_city=?
          AND r.ride_time=?
          AND r.available_seats >= ?
        ORDER BY r.id DESC
        """,
        (
            request["from_city"],
            request["to_city"],
            request["ride_time"],
            request["seats"],
        ),
        fetch=True,
    )

    sent_count = 0

    already_sent = set()

    for driver in drivers:

        if driver["user_id"] in already_sent:
            continue

        already_sent.add(
            driver["user_id"]
        )

        text = (
            "🚕 <b>YANGI YO‘LOVCHI BUYURTMASI!</b>\n\n"
            f"📍 <b>{request['from_city']} → "
            f"{request['to_city']}</b>\n"
            f"🕐 Vaqt: <b>{request['ride_time']}</b>\n"
            f"👥 Yo‘lovchi: <b>{request['seats']} kishi</b>\n\n"
            "Buyurtmani qabul qilasizmi?"
        )

        ok = await safe_send(
            driver["user_id"],
            text,
            reply_markup=driver_request_keyboard(
                request_id
            ),
            parse_mode="HTML",
        )

        if ok:
            sent_count += 1

    return sent_count


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await save_user(message)

    await message.answer(
        "🚕 <b>OPPER TAXI</b>\n\n"
        "Assalomu alaykum!\n"
        "Taksi xizmatidan foydalanish uchun "
        "menyudan kerakli bo‘limni tanlang.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


# ============================================================
# CANCEL
# ============================================================

@dp.message(Command("cancel"))
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


# ============================================================
# PASSENGER START
# ============================================================

@dp.message(F.text == "🚕 Taksi chaqirish")
async def passenger_start(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await save_user(message)

    await state.set_state(
        PassengerState.from_city
    )

    await message.answer(
        "📍 Qayerdan ketasiz?",
        reply_markup=city_keyboard(),
    )


@dp.message(PassengerState.from_city)
async def passenger_from_city(
    message: Message,
    state: FSMContext,
):

    if message.text not in CITIES:

        await message.answer(
            "Iltimos, ro‘yxatdan shaharni tanlang.",
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
        "📍 Qayerga borasiz?",
        reply_markup=city_keyboard(),
    )


@dp.message(PassengerState.to_city)
async def passenger_to_city(
    message: Message,
    state: FSMContext,
):

    if message.text not in CITIES:

        await message.answer(
            "Iltimos, ro‘yxatdan shaharni tanlang.",
            reply_markup=city_keyboard(),
        )

        return

    data = await state.get_data()

    if message.text == data["from_city"]:

        await message.answer(
            "❗ Qayerdan va qayerga shaharlar "
            "bir xil bo‘lishi mumkin emas.",
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
        "🕐 Qaysi vaqtda ketasiz?",
        reply_markup=time_keyboard(),
    )


@dp.message(PassengerState.time)
async def passenger_time(
    message: Message,
    state: FSMContext,
):

    if message.text not in TIMES:

        await message.answer(
            "Iltimos, vaqtni tugmalardan tanlang.",
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
        "👥 Nechta yo‘lovchi bo‘ladi?\n\n"
        "1 dan 4 gacha son kiriting.",
        reply_markup=cancel_keyboard(),
    )


@dp.message(PassengerState.seats)
async def passenger_seats(
    message: Message,
    state: FSMContext,
):

    try:
        seats = int(
            message.text
        )

    except Exception:

        await message.answer(
            "❗ Faqat son kiriting. Masalan: 2"
        )

        return

    if seats < 1 or seats > PASSENGER_LIMIT:

        await message.answer(
            "❗ Yo‘lovchilar soni 1–4 oralig‘ida."
        )

        return

    await state.update_data(
        seats=seats
    )

    await state.set_state(
        PassengerState.name
    )

    await message.answer(
        "👤 Ismingizni kiriting:",
        reply_markup=cancel_keyboard(),
    )


@dp.message(PassengerState.name)
async def passenger_name(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        name=message.text.strip()
    )

    await state.set_state(
        PassengerState.phone
    )

    await message.answer(
        "📞 Telefon raqamingizni kiriting:\n\n"
        "Masalan: +998901234567",
        reply_markup=cancel_keyboard(),
    )


@dp.message(PassengerState.phone)
async def passenger_phone(
    message: Message,
    state: FSMContext,
):

    phone = normalize_phone(
        message.text
    )

    if not phone:

        await message.answer(
            "❗ Telefon raqam noto‘g‘ri.\n"
            "Masalan: +998901234567"
        )

        return

    await state.update_data(
        phone=phone
    )

    await save_user_phone(
        message.from_user.id,
        phone,
    )

    await state.set_state(
        PassengerState.location
    )

    await message.answer(
        "📍 Olish joyingiz lokatsiyasini yuboring.",
        reply_markup=location_keyboard(),
    )


# ============================================================
# PASSENGER LOCATION
# ============================================================

@dp.message(
    PassengerState.location,
    F.location
)
async def passenger_location(
    message: Message,
    state: FSMContext,
):

    location = message.location

    await finish_passenger_request(
        message,
        state,
        location.latitude,
        location.longitude,
    )


@dp.message(
    PassengerState.location,
    F.text == "⏭ Lokatsiyasiz davom etish"
)
async def passenger_without_location(
    message: Message,
    state: FSMContext,
):

    await finish_passenger_request(
        message,
        state,
        None,
        None,
    )


async def finish_passenger_request(
    message: Message,
    state: FSMContext,
    latitude,
    longitude,
    source_chat_id=None,
    source_message_id=None,
    source_text=None,
):

    data = await state.get_data()

    request_id = await db_execute(
        """
        INSERT INTO passenger_requests
        (
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
            created_at,
            source_chat_id,
            source_message_id,
            source_text
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, 'searching', ?,
            ?, ?, ?
        )
        """,
        (
            message.from_user.id,
            data["from_city"],
            data["to_city"],
            data["ride_time"],
            data["seats"],
            data["name"],
            data["phone"],
            latitude,
            longitude,
            datetime.now().isoformat(),
            source_chat_id,
            source_message_id,
            source_text,
        ),
    )

    await state.clear()

    await message.answer(
        "🔎 <b>Buyurtmangiz yaratildi!</b>\n\n"
        f"📍 {data['from_city']} → {data['to_city']}\n"
        f"🕐 {data['ride_time']}\n"
        f"👥 {data['seats']} kishi\n\n"
        "🚕 Mos taksichilar qidirilmoqda...",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

    sent_count = await send_request_to_matching_drivers(
        request_id
    )

    if sent_count:

        await message.answer(
            f"🚕 <b>{sent_count} ta taksichiga</b> "
            "buyurtma yuborildi.\n\n"
            "Taksichi qabul qilishi bilan "
            "sizga avtomatik xabar keladi.",
            parse_mode="HTML",
        )

    else:

        await message.answer(
            "😔 Hozircha bu yo‘nalish va vaqt bo‘yicha "
            "bo‘sh taksi topilmadi.\n\n"
            "Buyurtmangiz qidiruvda qoladi."
        )


# ============================================================
# DRIVER REGISTRATION
# ============================================================

@dp.message(F.text == "🚗 Haydovchi bo‘lish")
async def driver_start(
    message: Message,
    state: FSMContext,
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
                "🚗 <b>Yangi safar e’lon qilish</b>\n\n"
                "Qaysi shahardan yo‘lovchi olasiz?",
                reply_markup=city_keyboard(),
                parse_mode="HTML",
            )

            return

        if driver["status"] == "pending":

            await message.answer(
                "⏳ Sizning haydovchilik profilingiz "
                "admin tasdig‘ini kutmoqda.",
                reply_markup=main_menu(),
            )

            return

        if driver["status"] == "rejected":

            await message.answer(
                "❌ Haydovchilik profilingiz rad etilgan.\n\n"
                "Administrator bilan bog‘laning.",
                reply_markup=main_menu(),
            )

            return

    await state.set_state(
        DriverRegisterState.name
    )

    await message.answer(
        "🚗 <b>Haydovchi ro‘yxatdan o‘tishi</b>\n\n"
        "Ism-familiyangizni kiriting:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )


@dp.message(DriverRegisterState.name)
async def driver_register_name(
    message: Message,
    state: FSMContext,
):

    name = message.text.strip()

    if len(name) < 2:

        await message.answer(
            "❗ Ismni to‘liqroq kiriting."
        )

        return

    await state.update_data(
        name=name
    )

    await state.set_state(
        DriverRegisterState.phone
    )

    await message.answer(
        "📞 Telefon raqamingizni kiriting:",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DriverRegisterState.phone)
async def driver_register_phone(
    message: Message,
    state: FSMContext,
):

    phone = normalize_phone(
        message.text
    )

    if not phone:

        await message.answer(
            "❗ Telefon raqam noto‘g‘ri.\n"
            "Masalan: +998901234567"
        )

        return

    await state.update_data(
        phone=phone
    )

    await save_user_phone(
        message.from_user.id,
        phone,
    )

    await state.set_state(
        DriverRegisterState.car_model
    )

    await message.answer(
        "🚗 Mashina markasi/modelini kiriting:\n\n"
        "Masalan: Chevrolet Cobalt",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DriverRegisterState.car_model)
async def driver_register_car_model(
    message: Message,
    state: FSMContext,
):

    car_model = message.text.strip()

    await state.update_data(
        car_model=car_model
    )

    await state.set_state(
        DriverRegisterState.car_number
    )

    await message.answer(
        "🔢 Mashina davlat raqamini kiriting:\n\n"
        "Masalan: 01 A 123 BC",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DriverRegisterState.car_number)
async def driver_register_car_number(
    message: Message,
    state: FSMContext,
):

    car_number = message.text.strip()

    data = await state.get_data()

    await db_execute(
        """
        INSERT INTO driver_profiles
        (
            user_id,
            full_name,
            phone,
            car_model,
            car_number,
            seats,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, 4, 'pending', ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            full_name=excluded.full_name,
            phone=excluded.phone,
            car_model=excluded.car_model,
            car_number=excluded.car_number,
            status='pending'
        """,
        (
            message.from_user.id,
            data["name"],
            data["phone"],
            data["car_model"],
            car_number,
            datetime.now().isoformat(),
        ),
    )

    await state.clear()

    await message.answer(
        "✅ <b>Haydovchilik arizangiz yuborildi!</b>\n\n"
        f"👤 {data['name']}\n"
        f"📞 {data['phone']}\n"
        f"🚗 {data['car_model']}\n"
        f"🔢 {car_number}\n\n"
        "⏳ Administrator tasdiqlashini kuting.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

    # ADMINLARGA AVTOMATIK XABAR

    admin_text = (
        "🚗 <b>YANGI HAYDOVCHI ARIZASI!</b>\n\n"
        f"👤 {data['name']}\n"
        f"📞 {data['phone']}\n"
        f"🚗 {data['car_model']}\n"
        f"🔢 {car_number}\n"
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>"
    )

    await notify_admins(
        admin_text,
        reply_markup=admin_driver_keyboard(
            message.from_user.id
        ),
        parse_mode="HTML",
    )


# ============================================================
# DRIVER RIDE
# ============================================================

@dp.message(DriverRideState.from_city)
async def driver_from_city(
    message: Message,
    state: FSMContext,
):

    if message.text not in CITIES:

        await message.answer(
            "Shaharni tugmalardan tanlang.",
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
        "📍 Qaysi shaharga borasiz?",
        reply_markup=city_keyboard(),
    )


@dp.message(DriverRideState.to_city)
async def driver_to_city(
    message: Message,
    state: FSMContext,
):

    if message.text not in CITIES:

        await message.answer(
            "Shaharni tugmalardan tanlang.",
            reply_markup=city_keyboard(),
        )

        return

    data = await state.get_data()

    if message.text == data["from_city"]:

        await message.answer(
            "❗ Yo‘nalish shaharlari bir xil bo‘lishi mumkin emas."
        )

        return

    await state.update_data(
        to_city=message.text
    )

    await state.set_state(
        DriverRideState.time
    )

    await message.answer(
        "🕐 Qaysi vaqtda yo‘lga chiqasiz?",
        reply_markup=time_keyboard(),
    )


@dp.message(DriverRideState.time)
async def driver_time(
    message: Message,
    state: FSMContext,
):

    if message.text not in TIMES:

        await message.answer(
            "Vaqtni tugmalardan tanlang.",
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
        "💺 Nechta bo‘sh joy bor?\n\n"
        "1–4 oralig‘ida son kiriting.",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DriverRideState.seats)
async def driver_seats(
    message: Message,
    state: FSMContext,
):

    try:

        seats = int(
            message.text
        )

    except Exception:

        await message.answer(
            "Faqat son kiriting."
        )

        return

    if seats < 1 or seats > 4:

        await message.answer(
            "Bo‘sh joylar 1–4 oralig‘ida bo‘lishi kerak."
        )

        return

    driver = await get_driver(
        message.from_user.id
    )

    if not driver or driver["status"] != "approved":

        await state.clear()

        await message.answer(
            "❗ Siz hali tasdiqlangan haydovchi emassiz.",
            reply_markup=main_menu(),
        )

        return

    data = await state.get_data()

    ride_id = await db_execute(
        """
        INSERT INTO rides
        (
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
            datetime.now().isoformat(),
        ),
    )

    await state.clear()

    await message.answer(
        "✅ <b>Safaringiz e’lon qilindi!</b>\n\n"
        f"📍 {data['from_city']} → {data['to_city']}\n"
        f"🕐 {data['ride_time']}\n"
        f"💺 Bo‘sh joy: {seats} ta\n\n"
        "Yo‘lovchi buyurtmasi kelganda "
        "sizga avtomatik xabar keladi.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


# ============================================================
# DRIVER ACCEPT
# ============================================================

@dp.callback_query(
    F.data.startswith("accept_request:")
)
async def accept_request(
    callback: CallbackQuery,
):

    request_id = int(
        callback.data.split(":")[1]
    )

    driver_id = callback.from_user.id

    request = await get_request(
        request_id
    )

    if not request:

        await callback.answer(
            "Buyurtma topilmadi.",
            show_alert=True,
        )

        return

    if request["status"] != "searching":

        await callback.answer(
            "Bu buyurtma allaqachon yopilgan.",
            show_alert=True,
        )

        try:
            await callback.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        return

    driver = await get_driver(
        driver_id
    )

    if not driver or driver["status"] != "approved":

        await callback.answer(
            "Siz tasdiqlangan haydovchi emassiz.",
            show_alert=True,
        )

        return

    ride = await db_execute(
        """
        SELECT *
        FROM rides
        WHERE driver_id=?
          AND from_city=?
          AND to_city=?
          AND ride_time=?
          AND status='active'
          AND available_seats >= ?
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
        fetchone=True,
    )

    if not ride:

        await callback.answer(
            "❌ Sizda yetarli bo‘sh joyli safar topilmadi.",
            show_alert=True,
        )

        return

    booking_id = None

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        try:

            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cur = await db.execute(
                """
                SELECT *
                FROM passenger_requests
                WHERE id=?
                """,
                (request_id,),
            )

            req = await cur.fetchone()

            if not req:

                await db.rollback()

                await callback.answer(
                    "Buyurtma topilmadi.",
                    show_alert=True,
                )

                return

            if req["status"] != "searching":

                await db.rollback()

                await callback.answer(
                    "Bu buyurtma boshqa taksichi tomonidan qabul qilingan.",
                    show_alert=True,
                )

                return

            cur = await db.execute(
                """
                SELECT *
                FROM rides
                WHERE id=?
                """,
                (ride["id"],),
            )

            ride_now = await cur.fetchone()

            if not ride_now:

                await db.rollback()

                await callback.answer(
                    "Safar topilmadi.",
                    show_alert=True,
                )

                return

            available = ride_now["available_seats"]

            if available < req["seats"]:

                await db.rollback()

                await callback.answer(
                    "❌ Bo‘sh joy yetarli emas.",
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
                SET available_seats =
                    available_seats - ?
                WHERE id=?
                """,
                (
                    req["seats"],
                    ride["id"],
                ),
            )

            cur = await db.execute(
                """
                INSERT INTO bookings
                (
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
                    req["passenger_id"],
                    driver_id,
                    req["seats"],
                    datetime.now().isoformat(),
                ),
            )

            booking_id = cur.lastrowid

            await db.commit()

        except Exception as e:

            await db.rollback()

            print(
                "ACCEPT ERROR:",
                e,
            )

            await callback.answer(
                "❌ Xatolik yuz berdi.",
                show_alert=True,
            )

            return

    await callback.answer(
        "✅ Buyurtma qabul qilindi!",
        show_alert=True,
    )

    try:

        await callback.message.edit_text(
            "✅ <b>BUYURTMA QABUL QILINDI</b>\n\n"
            f"📍 {request['from_city']} → {request['to_city']}\n"
            f"🕐 {request['ride_time']}\n"
            f"👥 {request['seats']} kishi\n\n"
            "Yo‘lovchiga avtomatik xabar yuborildi.",
            parse_mode="HTML",
        )

    except Exception:
        pass

    passenger_text = (
        "✅ <b>TAKSICHINGIZ BUYURTMANI QABUL QILDI!</b>\n\n"
        f"🚕 Haydovchi: <b>{driver['full_name']}</b>\n"
        f"📞 Telefon: <b>{driver['phone'] or 'mavjud emas'}</b>\n"
        f"🚗 Mashina: <b>{driver['car_model'] or 'mavjud emas'}</b>\n"
        f"🔢 Raqam: <b>{driver['car_number'] or 'mavjud emas'}</b>\n\n"
        f"📍 {request['from_city']} → {request['to_city']}\n"
        f"🕐 {request['ride_time']}\n\n"
        "Haydovchi siz bilan bog‘lanadi."
    )

    await safe_send(
        request["passenger_id"],
        passenger_text,
        reply_markup=passenger_booking_keyboard(
            booking_id
        ),
        parse_mode="HTML",
    )

    # QOLGAN HAYDOVCHILARGA YOPILDI

    other_drivers = await db_execute(
        """
        SELECT DISTINCT d.user_id
        FROM driver_profiles d
        JOIN rides r
            ON r.driver_id=d.user_id
        WHERE d.status='approved'
          AND r.from_city=?
          AND r.to_city=?
          AND r.ride_time=?
          AND d.user_id != ?
        """,
        (
            request["from_city"],
            request["to_city"],
            request["ride_time"],
            driver_id,
        ),
        fetch=True,
    )

    for other in other_drivers:

        await safe_send(
            other["user_id"],
            "ℹ️ <b>Buyurtma yopildi.</b>\n\n"
            "Ushbu yo‘lovchi boshqa taksichi "
            "tomonidan qabul qilindi.",
            parse_mode="HTML",
        )


# ============================================================
# DRIVER REJECT
# ============================================================

@dp.callback_query(
    F.data.startswith("reject_request:")
)
async def reject_request(
    callback: CallbackQuery,
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

    await callback.answer(
        "❌ Buyurtma rad etildi."
    )

    try:

        await callback.message.edit_text(
            "❌ <b>BUYURTMA RAD ETILDI</b>\n\n"
            "Siz ushbu buyurtmani rad etdingiz.",
            parse_mode="HTML",
        )

    except Exception:
        pass


# ============================================================
# PASSENGER CANCEL REQUEST
# ============================================================

@dp.callback_query(
    F.data.startswith("cancel_request:")
)
async def cancel_request(
    callback: CallbackQuery,
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

    if request["status"] not in (
        "searching",
        "accepted",
    ):

        await callback.answer(
            "Buyurtmani bekor qilib bo‘lmaydi.",
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
            SET available_seats =
                available_seats + ?
            WHERE id=?
            """,
            (
                booking["seats"],
                booking["ride_id"],
            ),
        )

        await safe_send(
            booking["driver_id"],
            "❌ <b>Yo‘lovchi buyurtmani bekor qildi.</b>\n\n"
            "Ushbu buyurtma endi faol emas.",
            parse_mode="HTML",
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


# ============================================================
# DRIVER LOCATION BUTTON
# ============================================================

@dp.callback_query(
    F.data.startswith("driver_location:")
)
async def driver_location(
    callback: CallbackQuery,
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:

        await callback.answer(
            "Safar topilmadi.",
            show_alert=True,
        )

        return

    if booking["driver_id"] != callback.from_user.id:

        await callback.answer(
            "Bu safar sizniki emas.",
            show_alert=True,
        )

        return

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📍 Hozirgi lokatsiyamni yuborish",
                    request_location=True,
                )
            ],
            [
                KeyboardButton(
                    text="❌ Bekor qilish"
                )
            ],
        ],
        resize_keyboard=True,
    )

    await callback.message.answer(
        "📍 Hozirgi lokatsiyangizni yuboring:",
        reply_markup=kb,
    )

    await callback.answer()


# ============================================================
# UNIVERSAL LOCATION
# ============================================================

@dp.message(F.location)
async def universal_location(
    message: Message,
):

    driver_id = message.from_user.id

    location = message.location

    # FSM passenger bo'lsa, passenger handler ishlaydi.
    current_booking = await db_execute(
        """
        SELECT *
        FROM bookings
        WHERE driver_id=?
          AND status IN (
              'accepted',
              'arriving',
              'arrived',
              'onboard'
          )
        ORDER BY id DESC
        LIMIT 1
        """,
        (driver_id,),
        fetchone=True,
    )

    if not current_booking:

        await message.answer(
            "📍 Lokatsiyangiz qabul qilindi."
        )

        return

    await db_execute(
        """
        UPDATE bookings
        SET driver_latitude=?,
            driver_longitude=?
        WHERE id=?
        """,
        (
            location.latitude,
            location.longitude,
            current_booking["id"],
        ),
    )

    await message.answer(
        "✅ Lokatsiyangiz yo‘lovchiga yuborildi.",
        reply_markup=main_menu(),
    )

    await safe_send(
        current_booking["passenger_id"],
        "📍 <b>Haydovchi lokatsiyasini yubordi.</b>",
        parse_mode="HTML",
    )

    try:

        await bot.send_location(
            current_booking["passenger_id"],
            latitude=location.latitude,
            longitude=location.longitude,
        )

    except Exception as e:

        print(
            "SEND LOCATION ERROR:",
            e,
        )


# ============================================================
# DRIVER ARRIVED
# ============================================================

@dp.callback_query(
    F.data.startswith("driver_arrived:")
)
async def driver_arrived(
    callback: CallbackQuery,
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:

        await callback.answer(
            "Safar topilmadi.",
            show_alert=True,
        )

        return

    if booking["driver_id"] != callback.from_user.id:

        await callback.answer(
            "Bu safar sizniki emas.",
            show_alert=True,
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

    await callback.answer(
        "Yo‘lovchiga xabar yuborildi."
    )

    await safe_send(
        booking["passenger_id"],
        "🚕 <b>Haydovchi yetib keldi!</b>\n\n"
        "Taksini kutib oling.",
        parse_mode="HTML",
    )


# ============================================================
# DRIVER ONBOARD
# ============================================================

@dp.callback_query(
    F.data.startswith("driver_onboard:")
)
async def driver_onboard(
    callback: CallbackQuery,
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:

        await callback.answer(
            "Safar topilmadi.",
            show_alert=True,
        )

        return

    if booking["driver_id"] != callback.from_user.id:

        await callback.answer(
            "Bu safar sizniki emas.",
            show_alert=True,
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

    await callback.answer(
        "Safar boshlandi."
    )

    await safe_send(
        booking["passenger_id"],
        "🚕 <b>Sizni haydovchi olib ketdi.</b>\n\n"
        "Xavfsiz safar tilaymiz!",
        parse_mode="HTML",
    )


# ============================================================
# DRIVER COMPLETE
# ============================================================

@dp.callback_query(
    F.data.startswith("driver_complete:")
)
async def driver_complete(
    callback: CallbackQuery,
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:

        await callback.answer(
            "Safar topilmadi.",
            show_alert=True,
        )

        return

    if booking["driver_id"] != callback.from_user.id:

        await callback.answer(
            "Bu safar sizniki emas.",
            show_alert=True,
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
        "Safar tugadi."
    )

    await safe_send(
        booking["passenger_id"],
        "🏁 <b>Safar tugadi.</b>\n\n"
        "Rahmat! Xavfsiz yetib boring.",
        parse_mode="HTML",
    )


# ============================================================
# DRIVER CANCEL
# ============================================================

@dp.callback_query(
    F.data.startswith("driver_cancel:")
)
async def driver_cancel(
    callback: CallbackQuery,
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:

        await callback.answer(
            "Safar topilmadi.",
            show_alert=True,
        )

        return

    if booking["driver_id"] != callback.from_user.id:

        await callback.answer(
            "Bu safar sizniki emas.",
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
        SET status='searching'
        WHERE id=?
        """,
        (booking["request_id"],),
    )

    await db_execute(
        """
        UPDATE rides
        SET available_seats =
            available_seats + ?
        WHERE id=?
        """,
        (
            booking["seats"],
            booking["ride_id"],
        ),
    )

    await callback.answer(
        "Safar bekor qilindi."
    )

    await safe_send(
        booking["passenger_id"],
        "❌ <b>Haydovchi safarni bekor qildi.</b>\n\n"
        "Yangi taksi qidirilmoqda.",
        parse_mode="HTML",
    )

    # QAYTA MOS TAKSILARGA YUBORISH

    await send_request_to_matching_drivers(
        booking["request_id"]
    )


# ============================================================
# TRACK DRIVER
# ============================================================

@dp.callback_query(
    F.data.startswith("track_driver:")
)
async def track_driver(
    callback: CallbackQuery,
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:

        await callback.answer(
            "Safar topilmadi.",
            show_alert=True,
        )

        return

    if booking["passenger_id"] != callback.from_user.id:

        await callback.answer(
            "Bu safar sizniki emas.",
            show_alert=True,
        )

        return

    if booking["driver_latitude"] is None:

        await callback.answer(
            "Haydovchi hali lokatsiyasini yubormagan.",
            show_alert=True,
        )

        return

    await callback.message.answer(
        "📍 <b>Haydovchi lokatsiyasi:</b>",
        parse_mode="HTML",
    )

    await bot.send_location(
        callback.from_user.id,
        latitude=booking["driver_latitude"],
        longitude=booking["driver_longitude"],
    )

    await callback.answer()


# ============================================================
# PASSENGER CANCEL BOOKING
# ============================================================

@dp.callback_query(
    F.data.startswith("passenger_cancel:")
)
async def passenger_cancel_booking(
    callback: CallbackQuery,
):

    booking_id = int(
        callback.data.split(":")[1]
    )

    booking = await get_booking(
        booking_id
    )

    if not booking:

        await callback.answer(
            "Safar topilmadi.",
            show_alert=True,
        )

        return

    if booking["passenger_id"] != callback.from_user.id:

        await callback.answer(
            "Bu safar sizniki emas.",
            show_alert=True,
        )

        return

    if booking["status"] in (
        "completed",
        "cancelled",
    ):

        await callback.answer(
            "Safar allaqachon yopilgan.",
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
        SET available_seats =
            available_seats + ?
        WHERE id=?
        """,
        (
            booking["seats"],
            booking["ride_id"],
        ),
    )

    await safe_send(
        booking["driver_id"],
        "❌ <b>Yo‘lovchi safarni bekor qildi.</b>",
        parse_mode="HTML",
    )

    await callback.answer(
        "Safar bekor qilindi."
    )


# ============================================================
# MY BOOKINGS
# ============================================================

@dp.message(F.text == "📋 Buyurtmalarim")
async def my_bookings(
    message: Message,
):

    rows = await db_execute(
        """
        SELECT
            b.*,
            r.from_city,
            r.to_city,
            r.ride_time
        FROM bookings b
        JOIN rides r
            ON r.id=b.ride_id
        WHERE b.passenger_id=?
        ORDER BY b.id DESC
        LIMIT 10
        """,
        (message.from_user.id,),
        fetch=True,
    )

    if not rows:

        await message.answer(
            "📋 Hozircha buyurtmalaringiz yo‘q."
        )

        return

    text = "📋 <b>Buyurtmalarim</b>\n\n"

    for row in rows:

        text += (
            f"#{row['id']} "
            f"{row['from_city']} → {row['to_city']}\n"
            f"🕐 {row['ride_time']}\n"
            f"📌 {row['status']}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML",
    )


# ============================================================
# SEARCH
# ============================================================

@dp.message(F.text == "🔎 Taksilarni qidirish")
async def search_taxis(
    message: Message,
):

    rows = await db_execute(
        """
        SELECT
            r.*,
            d.full_name,
            d.phone,
            d.car_model,
            d.car_number,
            d.rating
        FROM rides r
        JOIN driver_profiles d
            ON d.user_id=r.driver_id
        WHERE r.status='active'
          AND d.status='approved'
          AND r.available_seats>0
        ORDER BY r.id DESC
        LIMIT 20
        """,
        fetch=True,
    )

    if not rows:

        await message.answer(
            "🚕 Hozircha faol taksilar topilmadi."
        )

        return

    text = "🚕 <b>Faol taksilar:</b>\n\n"

    for row in rows:

        text += (
            f"🚗 <b>{row['car_model'] or 'Mashina'}</b>\n"
            f"🔢 {row['car_number'] or '-'}\n"
            f"👤 {row['full_name']}\n"
            f"📍 {row['from_city']} → {row['to_city']}\n"
            f"🕐 {row['ride_time']}\n"
            f"💺 Bo‘sh joy: {row['available_seats']}\n"
            f"⭐ {float(row['rating'] or 5):.1f}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML",
    )


# ============================================================
# PROFILE
# ============================================================

@dp.message(F.text == "👤 Profil")
async def profile(
    message: Message,
):

    user = await get_user(
        message.from_user.id
    )

    driver = await get_driver(
        message.from_user.id
    )

    text = (
        "👤 <b>Profil</b>\n\n"
        f"Ism: "
        f"{user['full_name'] if user else '-'}\n"
        f"Username: "
        f"@{user['username'] if user and user['username'] else '-'}\n"
        f"Telefon: "
        f"{user['phone'] if user and user['phone'] else '-'}\n"
    )

    if driver:

        text += (
            "\n🚕 <b>Haydovchi profili</b>\n"
            f"🚗 Mashina: "
            f"{driver['car_model'] or '-'}\n"
            f"🔢 Raqam: "
            f"{driver['car_number'] or '-'}\n"
            f"⭐ Reyting: "
            f"{float(driver['rating'] or 5):.1f}\n"
            f"🏁 Safarlar: "
            f"{driver['trips']}\n"
            f"📌 Holat: "
            f"{driver['status']}\n"
        )

    await message.answer(
        text,
        parse_mode="HTML",
    )


# ============================================================
# HELP
# ============================================================

@dp.message(F.text == "ℹ️ Yordam")
async def help_handler(
    message: Message,
):

    await message.answer(
        "ℹ️ <b>OPPER TAXI</b>\n\n"
        "🚕 Taksi chaqirish — yo‘lovchi buyurtmasi.\n\n"
        "🚗 Haydovchi bo‘lish — haydovchi ro‘yxatdan o‘tishi "
        "va safar e’lon qilishi.\n\n"
        "🔎 Taksilarni qidirish — faol safarlarni ko‘rish.\n\n"
        "📋 Buyurtmalarim — buyurtmalar holati.\n\n"
        "📍 Haydovchi lokatsiyasi — yo‘lovchiga yuboriladi.\n\n"
        "💬 Bot qo‘shilgan guruhlarda taxi buyurtmalarini "
        "avtomatik aniqlash ham ishlaydi.",
        parse_mode="HTML",
    )


# ============================================================
# ADMIN APPROVE
# ============================================================

@dp.callback_query(
    F.data.startswith("admin_approve:")
)
async def admin_approve(
    callback: CallbackQuery,
):

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

    await safe_send(
        user_id,
        "🎉 <b>Haydovchilik profilingiz tasdiqlandi!</b>\n\n"
        "Endi «🚗 Haydovchi bo‘lish» orqali "
        "safar e’lon qilishingiz mumkin.",
        parse_mode="HTML",
    )

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:
        pass


# ============================================================
# ADMIN REJECT
# ============================================================

@dp.callback_query(
    F.data.startswith("admin_reject:")
)
async def admin_reject(
    callback: CallbackQuery,
):

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

    await safe_send(
        user_id,
        "❌ Haydovchilik profilingiz tasdiqlanmadi.\n\n"
        "Administrator bilan bog‘lanishingiz mumkin.",
    )

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:
        pass


# ============================================================
# ADMIN /DRIVERS
# ============================================================

@dp.message(Command("drivers"))
async def admin_drivers(
    message: Message,
):

    if message.from_user.id not in ADMIN_IDS:
        return

    rows = await db_execute(
        """
        SELECT *
        FROM driver_profiles
        WHERE status='pending'
        ORDER BY created_at
        """,
        fetch=True,
    )

    if not rows:

        await message.answer(
            "⏳ Tasdiqlashni kutayotgan haydovchilar yo‘q."
        )

        return

    for driver in rows:

        text = (
            "🚗 <b>YANGI HAYDOVCHI</b>\n\n"
            f"👤 {driver['full_name']}\n"
            f"📞 {driver['phone']}\n"
            f"🚗 {driver['car_model']}\n"
            f"🔢 {driver['car_number']}\n"
            f"💺 {driver['seats']} joy\n"
            f"🆔 <code>{driver['user_id']}</code>"
        )

        await message.answer(
            text,
            reply_markup=admin_driver_keyboard(
                driver["user_id"]
            ),
            parse_mode="HTML",
        )


# ============================================================
# ADMIN PANEL
# ============================================================

@dp.message(Command("admin"))
async def admin_panel(
    message: Message,
):

    if message.from_user.id not in ADMIN_IDS:
        return

    users = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM users
        """,
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

    active_rides = await db_execute(
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
        SELECT COUNT(DISTINCT chat_id) AS c
        FROM group_messages
        """,
        fetchone=True,
    )

    await message.answer(
        "👑 <b>ADMIN PANEL</b>\n\n"
        f"👥 Foydalanuvchilar: {users['c']}\n"
        f"🚕 Tasdiqlangan haydovchilar: {drivers['c']}\n"
        f"🚗 Faol safarlar: {active_rides['c']}\n"
        f"🔎 Faol buyurtmalar: {requests['c']}\n"
        f"💬 Guruhlar: {groups['c']}\n\n"
        "/drivers — haydovchilarni tasdiqlash",
        parse_mode="HTML",
    )


# ============================================================
# GROUP TAXI PARSER
# ============================================================

async def create_group_passenger_request(
    message: Message,
    from_city,
    to_city,
    ride_time,
    seats,
    phone,
):

    user_id = message.from_user.id

    name = extract_name_from_message(
        message
    )

    # Telefon bo‘lsa user profiliga saqlaymiz

    if phone:

        await save_user_phone(
            user_id,
            phone,
        )

    request_id = await db_execute(
        """
        INSERT INTO passenger_requests
        (
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
            created_at,
            source_chat_id,
            source_message_id,
            source_text
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, NULL, NULL,
            'searching', ?, ?, ?, ?
        )
        """,
        (
            user_id,
            from_city,
            to_city,
            ride_time,
            seats,
            name,
            phone,
            datetime.now().isoformat(),
            message.chat.id,
            message.message_id,
            message.text,
        ),
    )

    sent_count = await send_request_to_matching_drivers(
        request_id
    )

    return request_id, sent_count


async def create_group_driver_ride(
    message: Message,
    from_city,
    to_city,
    ride_time,
    seats,
):

    driver = await get_driver(
        message.from_user.id
    )

    if not driver:

        return None, "not_registered"

    if driver["status"] != "approved":

        return None, "not_approved"

    ride_id = await db_execute(
        """
        INSERT INTO rides
        (
            driver_id,
            from_city,
            to_city,
            ride_time,
            seats,
            available_seats,
            reserved_seats,
            status,
            created_at,
            source_chat_id,
            source_message_id,
            source_text
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, 0, 'active', ?,
            ?, ?, ?
        )
        """,
        (
            message.from_user.id,
            from_city,
            to_city,
            ride_time,
            seats,
            seats,
            datetime.now().isoformat(),
            message.chat.id,
            message.message_id,
            message.text,
        ),
    )

    return ride_id, "created"


@dp.message(
    F.chat.type.in_(
        {"group", "supergroup"}
    )
)
async def group_message_handler(
    message: Message,
):

    # BOT XABARLARINI E'TIBORSIZ QOLDIRAMIZ

    if message.from_user and message.from_user.is_bot:
        return

    if not message.text:
        return

    text = message.text.strip()

    if not text:
        return

    # COMMANDLARNI PARSE QILMAYMIZ

    if text.startswith("/"):
        return

    # DUPLICATE

    if await group_message_already_processed(
        message.chat.id,
        message.message_id,
    ):

        return

    await mark_group_message_processed(
        message.chat.id,
        message.message_id,
    )

    normalized = normalize_text(
        text
    )

    # TAXI KALIT SO'ZLARINI TEKSHIRISH

    taxi_words = [
        "taksi",
        "taxi",
        "mashina",
        "yo'lovchi",
        "yo'lovchilar",
        "joy",
        "ketaman",
        "kerak",
        "kerek",
        "olaman",
        "olib keting",
    ]

    has_taxi_word = any(
        word in normalized
        for word in taxi_words
    )

    if not has_taxi_word:
        return

    cities = extract_cities(
        text
    )

    if len(cities) < 2:
        return

    from_city = cities[0]
    to_city = cities[1]

    if from_city == to_city:
        return

    ride_time = extract_time(
        text
    )

    seats = extract_seats(
        text
    )

    phone = extract_phone(
        text
    )

    # ========================================================
    # VAQT YO‘Q BO‘LSA — GURUHDA ANIQLASHTIRISH
    # ========================================================

    if not ride_time:

        await message.reply(
            "🚕 Buyurtmani tushundim, lekin vaqt ko‘rsatilmagan.\n\n"
            "Masalan:\n"
            "<b>Toshkentdan Farg‘onaga 2 kishi, "
            "18:00 ga taksi kerak.</b>",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # YO‘LOVCHI ANIQLASH
    # ========================================================

    passenger = is_passenger_message(
        text
    )

    driver_message = is_driver_message(
        text
    )

    # ========================================================
    # AGAR IKKALASI HAM ANIQLANMASA
    # ========================================================

    if not passenger and not driver_message:

        return

    # ========================================================
    # HAYDOVCHI XABARI
    # ========================================================

    if driver_message and not passenger:

        # Guruhdan haydovchini faqat Telegram user ID
        # orqali aniqlaymiz.

        driver = await get_driver(
            message.from_user.id
        )

        if not driver:

            await message.reply(
                "🚗 Safar e’lon qilish uchun avval "
                "OPPER TAXI botida haydovchi sifatida "
                "ro‘yxatdan o‘ting.",
            )

            return

        if driver["status"] != "approved":

            await message.reply(
                "⏳ Sizning haydovchilik profilingiz "
                "hali admin tomonidan tasdiqlanmagan."
            )

            return

        if not seats:

            seats = 1

        if seats > 4:

            seats = 4

        ride_id, result = await create_group_driver_ride(
            message,
            from_city,
            to_city,
            ride_time,
            seats,
        )

        if result != "created":
            return

        await message.reply(
            "🚗 <b>Safar avtomatik ro‘yxatga olindi!</b>\n\n"
            f"📍 {from_city} → {to_city}\n"
            f"🕐 {ride_time}\n"
            f"💺 Bo‘sh joy: {seats} ta\n\n"
            "Yo‘lovchi buyurtmalari sizga "
            "avtomatik yuboriladi.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # YO‘LOVCHI XABARI
    # ========================================================

    if passenger:

        if not seats:

            await message.reply(
                "👥 Nechta yo‘lovchi ekanini ham yozing.\n\n"
                "Masalan: <b>2 kishi</b>",
                parse_mode="HTML",
            )

            return

        if seats > PASSENGER_LIMIT:

            await message.reply(
                f"❗ Hozircha bir buyurtmada "
                f"1–{PASSENGER_LIMIT} kishi qabul qilinadi."
            )

            return

        request_id, sent_count = await create_group_passenger_request(
            message,
            from_city,
            to_city,
            ride_time,
            seats,
            phone,
        )

        # ====================================================
        # GURUHGA NORMALIZATSIYA QILINGAN XABAR
        # ====================================================

        if sent_count:

            phone_text = (
                "📞 Telefon raqami qabul qilindi."
                if phone
                else
                "📞 Telefon raqami topilmadi."
            )

            await message.reply(
                "🚕 <b>BUYURTMA QABUL QILINDI</b>\n\n"
                f"📍 Yo‘nalish: "
                f"<b>{from_city} → {to_city}</b>\n"
                f"🕐 Vaqt: <b>{ride_time}</b>\n"
                f"👥 Yo‘lovchi: <b>{seats} kishi</b>\n"
                f"{phone_text}\n\n"
                f"🚕 <b>{sent_count} ta taksichiga</b> "
                "avtomatik yuborildi.\n\n"
                "Taksichi buyurtmani qabul qilganda "
                "yo‘lovchiga avtomatik xabar yuboriladi.",
                parse_mode="HTML",
            )

        else:

            await message.reply(
                "🔎 <b>Buyurtma ro‘yxatga olindi.</b>\n\n"
                f"📍 {from_city} → {to_city}\n"
                f"🕐 {ride_time}\n"
                f"👥 {seats} kishi\n\n"
                "😔 Hozircha mos bo‘sh taksi topilmadi.\n"
                "Buyurtma qidiruvda qoladi.",
                parse_mode="HTML",
            )


# ============================================================
# ADMIN GROUP INFO
# ============================================================

@dp.message(Command("groupid"))
async def group_id(
    message: Message,
):

    if message.from_user.id not in ADMIN_IDS:
        return

    await message.answer(
        f"💬 <b>Chat ID:</b>\n"
        f"<code>{message.chat.id}</code>",
        parse_mode="HTML",
    )


# ============================================================
# ADMIN BROADCAST
# ============================================================

@dp.message(Command("stats"))
async def stats_command(
    message: Message,
):

    if message.from_user.id not in ADMIN_IDS:
        return

    users = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM users
        """,
        fetchone=True,
    )

    drivers = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM driver_profiles
        """,
        fetchone=True,
    )

    requests = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM passenger_requests
        """,
        fetchone=True,
    )

    rides = await db_execute(
        """
        SELECT COUNT(*) AS c
        FROM rides
        """,
        fetchone=True,
    )

    groups = await db_execute(
        """
        SELECT COUNT(DISTINCT chat_id) AS c
        FROM group_messages
        """,
        fetchone=True,
    )

    await message.answer(
        "📊 <b>OPPER TAXI STATISTIKA</b>\n\n"
        f"👥 Users: {users['c']}\n"
        f"🚗 Drivers: {drivers['c']}\n"
        f"🔎 Requests: {requests['c']}\n"
        f"🚕 Rides: {rides['c']}\n"
        f"💬 Groups: {groups['c']}",
        parse_mode="HTML",
    )


# ============================================================
# FALLBACK
# ============================================================

@dp.message()
async def fallback(
    message: Message,
):

    await message.answer(
        "❓ Buyruqni tushunmadim.\n\n"
        "Iltimos, menyudagi tugmalardan foydalaning.",
        reply_markup=main_menu(),
    )


# ============================================================
# RAILWAY WEB SERVER
# ============================================================

async def health_handler(
    request,
):

    return web.Response(
        text="OPPER TAXI BOT OK"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health_handler,
    )

    port = int(
        os.getenv(
            "PORT",
            "8080",
        )
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port,
    )

    await site.start()

    print(
        f"WEB SERVER RUNNING ON PORT {port}"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "======================================"
    )

    print(
        "OPPER TAXI BOT STARTING..."
    )

    print(
        "======================================"
    )

    await init_db()

    print(
        "DATABASE READY"
    )

    await start_web_server()

    print(
        "WEB SERVER READY"
    )

    print(
        "BOT POLLING STARTED"
    )

    await dp.start_polling(
        bot,
        allowed_updates=
        dp.resolve_used_update_types(),
    )


if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "BOT STOPPED"
        )
