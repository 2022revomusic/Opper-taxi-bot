import os
import json
import hmac
import hashlib
import asyncio
import logging
from pathlib import Path
from datetime import datetime

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
# OPPER TAXI
# FULL BACKEND
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

print("🚕 OPPER TAXI BOT STARTING...")

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable topilmadi!")

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
# CITIES
# =========================================================

CITIES = [
    "Toshkent",
    "Namangan",
    "Andijon",
    "Farg‘ona",
    "Qo‘qon",
    "Marg‘ilon",
]

# =========================================================
# AIROGRAM
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =========================================================
# DATABASE
# =========================================================


async def db_connect():
    db = await aiosqlite.connect(DB_FILE)
    db.row_factory = aiosqlite.Row

    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA journal_mode = WAL")

    return db


async def add_column_if_missing(db, table, column, definition):
    cursor = await db.execute(f"PRAGMA table_info({table})")
    columns = await cursor.fetchall()

    existing = [row["name"] for row in columns]

    if column not in existing:
        await db.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


async def init_db():
    db = await db_connect()

    # =====================================================
    # USERS
    # =====================================================

    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # DRIVER PROFILES
    # =====================================================

    await db.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            full_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            car_model TEXT DEFAULT '',
            car_number TEXT DEFAULT '',
            seats INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # RIDES
    # =====================================================

    await db.execute("""
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            driver_telegram_id INTEGER,
            driver_name TEXT DEFAULT '',
            driver_phone TEXT DEFAULT '',
            from_city TEXT DEFAULT '',
            to_city TEXT DEFAULT '',
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

    # =====================================================
    # ORDERS
    # =====================================================

    await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id INTEGER,
            passenger_telegram_id INTEGER,
            passenger_name TEXT DEFAULT '',
            passenger_phone TEXT DEFAULT '',
            from_city TEXT DEFAULT '',
            to_city TEXT DEFAULT '',
            ride_date TEXT DEFAULT '',
            ride_time TEXT DEFAULT '',
            seats INTEGER DEFAULT 1,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # MIGRATION
    # Eski bazada ustunlar bo‘lsa ham ishlashi uchun
    # =====================================================

    user_columns = [
        ("username", "TEXT DEFAULT ''"),
        ("full_name", "TEXT DEFAULT ''"),
        ("phone", "TEXT DEFAULT ''"),
        ("created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
    ]

    driver_columns = [
        ("telegram_id", "INTEGER"),
        ("full_name", "TEXT DEFAULT ''"),
        ("phone", "TEXT DEFAULT ''"),
        ("car_model", "TEXT DEFAULT ''"),
        ("car_number", "TEXT DEFAULT ''"),
        ("seats", "INTEGER DEFAULT 1"),
        ("created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
    ]

    ride_columns = [
        ("driver_id", "INTEGER"),
        ("driver_telegram_id", "INTEGER"),
        ("driver_name", "TEXT DEFAULT ''"),
        ("driver_phone", "TEXT DEFAULT ''"),
        ("from_city", "TEXT DEFAULT ''"),
        ("to_city", "TEXT DEFAULT ''"),
        ("ride_date", "TEXT DEFAULT ''"),
        ("ride_time", "TEXT DEFAULT ''"),
        ("seats", "INTEGER DEFAULT 1"),
        ("price", "INTEGER DEFAULT 0"),
        ("car_model", "TEXT DEFAULT ''"),
        ("car_number", "TEXT DEFAULT ''"),
        ("status", "TEXT DEFAULT 'active'"),
        ("created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
    ]

    order_columns = [
        ("ride_id", "INTEGER"),
        ("passenger_telegram_id", "INTEGER"),
        ("passenger_name", "TEXT DEFAULT ''"),
        ("passenger_phone", "TEXT DEFAULT ''"),
        ("from_city", "TEXT DEFAULT ''"),
        ("to_city", "TEXT DEFAULT ''"),
        ("ride_date", "TEXT DEFAULT ''"),
        ("ride_time", "TEXT DEFAULT ''"),
        ("seats", "INTEGER DEFAULT 1"),
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("status", "TEXT DEFAULT 'active'"),
        ("created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
    ]

    for column, definition in user_columns:
        await add_column_if_missing(
            db, "users", column, definition
        )

    for column, definition in driver_columns:
        await add_column_if_missing(
            db, "drivers", column, definition
        )

    for column, definition in ride_columns:
        await add_column_if_missing(
            db, "rides", column, definition
        )

    for column, definition in order_columns:
        await add_column_if_missing(
            db, "orders", column, definition
        )

    # =====================================================
    # INDEXES
    # =====================================================

    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_rides_route
        ON rides(from_city, to_city)
    """)

    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_rides_date
        ON rides(ride_date)
    """)

    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_rides_status
        ON rides(status)
    """)

    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_passenger
        ON orders(passenger_telegram_id)
    """)

    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_ride
        ON orders(ride_id)
    """)

    await db.commit()
    await db.close()

    print("✅ DATABASE READY")


# =========================================================
# HELPERS
# =========================================================


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def normalize_city(value):
    """
    Shahar nomini bir xil formatga keltiradi.
    """

    value = clean_text(value)

    if not value:
        return ""

    replacements = {
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

    if value in replacements:
        return replacements[value]

    lower = value.lower()

    for city in CITIES:
        if city.lower() == lower:
            return city

    for old, new in replacements.items():
        if old.lower() == lower:
            return new

    return value


def valid_city(value):
    city = normalize_city(value)

    return city in CITIES


def normalize_phone(value):
    value = clean_text(value)

    if not value:
        return ""

    return value


def parse_int(value, default=0):
    try:
        return int(str(value).strip())
    except Exception:
        return default


def format_price(value):
    number = parse_int(value)

    return f"{number:,}".replace(",", " ")


def get_init_data_user(init_data):
    """
    Telegram Mini App initData ichidan Telegram user ID oladi.
    """

    if not init_data:
        return None

    try:
        params = {}

        for part in init_data.split("&"):
            if "=" not in part:
                continue

            key, value = part.split("=", 1)

            from urllib.parse import unquote

            params[key] = unquote(value)

        user_json = params.get("user")

        if not user_json:
            return None

        user = json.loads(user_json)

        telegram_id = user.get("id")

        if telegram_id:
            return int(telegram_id)

    except Exception as e:
        logging.warning("init_data user parse error: %s", e)

    return None


def validate_init_data(init_data):
    """
    Telegram WebApp initData HMAC tekshiruvi.
    """

    if not init_data:
        return None

    try:
        from urllib.parse import unquote

        pairs = []

        received_hash = None

        for item in init_data.split("&"):
            if "=" not in item:
                continue

            key, value = item.split("=", 1)

            if key == "hash":
                received_hash = value
            else:
                pairs.append(
                    f"{key}={unquote(value)}"
                )

        if not received_hash:
            return None

        pairs.sort()

        data_check_string = "\n".join(pairs)

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
            logging.warning("❌ Telegram initData hash noto‘g‘ri")
            return None

        return get_init_data_user(init_data)

    except Exception as e:
        logging.error("init_data validation error: %s", e)
        return None


async def get_request_data(request):
    """
    POST JSON yoki GET query.
    """

    if request.method == "GET":
        return dict(request.query)

    try:
        return await request.json()
    except Exception:
        return {}


async def get_telegram_user(request, data=None):
    """
    Frontend yuborgan init_data orqali Telegram user ID.
    """

    if data is None:
        data = await get_request_data(request)

    init_data = clean_text(data.get("init_data"))

    telegram_id = validate_init_data(init_data)

    return telegram_id


async def ensure_user(
    telegram_id,
    username="",
    full_name="",
    phone=""
):
    db = await db_connect()

    cursor = await db.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    user = await cursor.fetchone()

    if user:
        await db.execute(
            """
            UPDATE users
            SET
                username = CASE
                    WHEN ? != '' THEN ?
                    ELSE username
                END,
                full_name = CASE
                    WHEN ? != '' THEN ?
                    ELSE full_name
                END,
                phone = CASE
                    WHEN ? != '' THEN ?
                    ELSE phone
                END,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                username,
                username,
                full_name,
                full_name,
                phone,
                phone,
                now_text(),
                telegram_id,
            )
        )
    else:
        await db.execute(
            """
            INSERT INTO users (
                telegram_id,
                username,
                full_name,
                phone,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                username,
                full_name,
                phone,
                now_text(),
                now_text(),
            )
        )

    await db.commit()
    await db.close()


async def get_user(telegram_id):
    db = await db_connect()

    cursor = await db.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    row = await cursor.fetchone()

    await db.close()

    return dict(row) if row else None


async def json_response(data, status=200):
    return web.json_response(
        data,
        status=status,
        dumps=lambda obj: json.dumps(
            obj,
            ensure_ascii=False
        )
    )


# =========================================================
# WEB
# =========================================================


async def web_index(request):
    if not INDEX_FILE.exists():
        return web.Response(
            status=500,
            text="web/index.html topilmadi"
        )

    return web.FileResponse(INDEX_FILE)


async def health_handler(request):
    return await json_response({
        "ok": True,
        "service": "OPPER TAXI",
        "status": "running"
    })


# =========================================================
# API: DRIVER REGISTER
# =========================================================


async def web_driver_register(request):
    try:
        data = await get_request_data(request)

        telegram_id = await get_telegram_user(
            request,
            data
        )

        if not telegram_id:
            return await json_response(
                {
                    "error": "Telegram foydalanuvchisi aniqlanmadi."
                },
                401
            )

        full_name = clean_text(data.get("full_name"))
        phone = normalize_phone(data.get("phone"))
        car_model = clean_text(data.get("car_model"))
        car_number = clean_text(data.get("car_number"))
        seats = parse_int(data.get("seats"), 1)

        if not full_name:
            return await json_response(
                {"error": "F.I.Sh. kiriting."},
                400
            )

        if not phone:
            return await json_response(
                {"error": "Telefon raqamini kiriting."},
                400
            )

        if not car_model:
            return await json_response(
                {"error": "Mashina modelini kiriting."},
                400
            )

        if not car_number:
            return await json_response(
                {"error": "Mashina raqamini kiriting."},
                400
            )

        if seats < 1 or seats > 8:
            return await json_response(
                {
                    "error": "O‘rindiqlar soni 1 dan 8 gacha bo‘lishi kerak."
                },
                400
            )

        await ensure_user(
            telegram_id=telegram_id,
            full_name=full_name,
            phone=phone
        )

        db = await db_connect()

        cursor = await db.execute(
            """
            SELECT id
            FROM drivers
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        existing = await cursor.fetchone()

        if existing:
            await db.execute(
                """
                UPDATE drivers
                SET
                    full_name = ?,
                    phone = ?,
                    car_model = ?,
                    car_number = ?,
                    seats = ?,
                    updated_at = ?
                WHERE telegram_id = ?
                """,
                (
                    full_name,
                    phone,
                    car_model,
                    car_number,
                    seats,
                    now_text(),
                    telegram_id,
                )
            )
        else:
            await db.execute(
                """
                INSERT INTO drivers (
                    telegram_id,
                    full_name,
                    phone,
                    car_model,
                    car_number,
                    seats,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_id,
                    full_name,
                    phone,
                    car_model,
                    car_number,
                    seats,
                    now_text(),
                    now_text(),
                )
            )

        await db.commit()
        await db.close()

        return await json_response({
            "ok": True,
            "message": "Haydovchi ma’lumotlari saqlandi.",
        })

    except Exception as e:
        logging.exception("driver register error")

        return await json_response(
            {
                "error": f"Server xatosi: {str(e)}"
            },
            500
        )


# =========================================================
# API: DRIVER ADD RIDE
# =========================================================


async def web_driver_ride(request):
    try:
        data = await get_request_data(request)

        telegram_id = await get_telegram_user(
            request,
            data
        )

        if not telegram_id:
            return await json_response(
                {
                    "error": "Telegram foydalanuvchisi aniqlanmadi."
                },
                401
            )

        from_city = normalize_city(
            data.get("from_city")
        )

        to_city = normalize_city(
            data.get("to_city")
        )

        ride_date = clean_text(
            data.get("ride_date")
        )

        ride_time = clean_text(
            data.get("ride_time")
            or data.get("time")
        )

        seats = parse_int(
            data.get("seats"),
            1
        )

        price = parse_int(
            data.get("price"),
            0
        )

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not valid_city(from_city):
            return await json_response(
                {
                    "error": "Qayerdan shahri noto‘g‘ri."
                },
                400
            )

        if not valid_city(to_city):
            return await json_response(
                {
                    "error": "Qayerga shahri noto‘g‘ri."
                },
                400
            )

        if from_city == to_city:
            return await json_response(
                {
                    "error": "Qayerdan va Qayerga bir xil bo‘lishi mumkin emas."
                },
                400
            )

        if not ride_date:
            return await json_response(
                {
                    "error": "Safar sanasini tanlang."
                },
                400
            )

        if not ride_time:
            return await json_response(
                {
                    "error": "Safar vaqtini tanlang."
                },
                400
            )

        if seats < 1 or seats > 8:
            return await json_response(
                {
                    "error": "Bo‘sh joylar 1 dan 8 gacha bo‘lishi kerak."
                },
                400
            )

        if price < 0:
            return await json_response(
                {
                    "error": "Narx noto‘g‘ri."
                },
                400
            )

        # -------------------------------------------------
        # DRIVER
        # -------------------------------------------------

        db = await db_connect()

        cursor = await db.execute(
            """
            SELECT *
            FROM drivers
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        driver = await cursor.fetchone()

        if not driver:
            await db.close()

            return await json_response(
                {
                    "error": "Avval haydovchi sifatida ro‘yxatdan o‘ting."
                },
                400
            )

        driver = dict(driver)

        # -------------------------------------------------
        # USER
        # -------------------------------------------------

        await ensure_user(
            telegram_id=telegram_id,
            full_name=driver.get("full_name", ""),
            phone=driver.get("phone", "")
        )

        # -------------------------------------------------
        # SAVE RIDE
        # -------------------------------------------------

        cursor = await db.execute(
            """
            INSERT INTO rides (
                driver_id,
                driver_telegram_id,
                driver_name,
                driver_phone,
                from_city,
                to_city,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                driver["id"],
                telegram_id,
                driver.get("full_name", ""),
                driver.get("phone", ""),
                from_city,
                to_city,
                ride_date,
                ride_time,
                seats,
                price,
                driver.get("car_model", ""),
                driver.get("car_number", ""),
                "active",
                now_text(),
                now_text(),
            )
        )

        ride_id = cursor.lastrowid

        await db.commit()
        await db.close()

        # -------------------------------------------------
        # ADMIN NOTIFICATION
        # -------------------------------------------------

        try:
            await bot.send_message(
                ADMIN_ID,
                (
                    "🚕 <b>Yangi safar qo‘shildi</b>\n\n"
                    f"👤 {driver.get('full_name', '')}\n"
                    f"📞 {driver.get('phone', '')}\n"
                    f"🚗 {driver.get('car_model', '')}\n"
                    f"🔢 {driver.get('car_number', '')}\n\n"
                    f"📍 {from_city} → {to_city}\n"
                    f"📅 {ride_date}\n"
                    f"🕐 {ride_time}\n"
                    f"💺 {seats} ta joy\n"
                    f"💰 {format_price(price)} so‘m"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

        return await json_response({
            "ok": True,
            "ride_id": ride_id,
            "message": "Safar muvaffaqiyatli qo‘shildi.",
        })

    except Exception as e:
        logging.exception("driver ride error")

        return await json_response(
            {
                "error": f"Server xatosi: {str(e)}"
            },
            500
        )


# =========================================================
# API: SEARCH RIDES
# =========================================================


async def web_rides(request):
    try:
        data = await get_request_data(request)

        from_city = normalize_city(
            data.get("from_city")
        )

        to_city = normalize_city(
            data.get("to_city")
        )

        ride_date = clean_text(
            data.get("ride_date")
        )

        telegram_id = await get_telegram_user(
            request,
            data
        )

        db = await db_connect()

        query = """
            SELECT
                r.*,

                COALESCE(
                    (
                        SELECT SUM(o.seats)
                        FROM orders o
                        WHERE
                            o.ride_id = r.id
                            AND o.status = 'active'
                    ),
                    0
                ) AS booked_seats

            FROM rides r

            WHERE r.status = 'active'
        """

        params = []

        if from_city:
            query += """
                AND r.from_city = ?
            """
            params.append(from_city)

        if to_city:
            query += """
                AND r.to_city = ?
            """
            params.append(to_city)

        if ride_date:
            query += """
                AND r.ride_date = ?
            """
            params.append(ride_date)

        query += """
            ORDER BY
                r.ride_date ASC,
                r.ride_time ASC,
                r.id DESC
            LIMIT 100
        """

        cursor = await db.execute(
            query,
            params
        )

        rows = await cursor.fetchall()

        rides = []

        for row in rows:
            item = dict(row)

            total_seats = parse_int(
                item.get("seats"),
                0
            )

            booked_seats = parse_int(
                item.get("booked_seats"),
                0
            )

            available_seats = max(
                0,
                total_seats - booked_seats
            )

            if available_seats <= 0:
                continue

            rides.append({
                "id": item["id"],
                "driver_id": item.get("driver_id"),
                "driver_telegram_id": item.get(
                    "driver_telegram_id"
                ),
                "driver_name": item.get(
                    "driver_name",
                    ""
                ),
                "driver_phone": item.get(
                    "driver_phone",
                    ""
                ),
                "from_city": item.get(
                    "from_city",
                    ""
                ),
                "to_city": item.get(
                    "to_city",
                    ""
                ),
                "ride_date": item.get(
                    "ride_date",
                    ""
                ),
                "ride_time": item.get(
                    "ride_time",
                    ""
                ),
                "seats": total_seats,
                "booked_seats": booked_seats,
                "available_seats": available_seats,
                "price": parse_int(
                    item.get("price"),
                    0
                ),
                "car_model": item.get(
                    "car_model",
                    ""
                ),
                "car_number": item.get(
                    "car_number",
                    ""
                ),
                "status": item.get(
                    "status",
                    "active"
                ),
            })

        await db.close()

        return await json_response({
            "ok": True,
            "rides": rides,
            "count": len(rides),
            "cities": CITIES,
            "user_id": telegram_id,
        })

    except Exception as e:
        logging.exception("rides search error")

        return await json_response(
            {
                "error": f"Server xatosi: {str(e)}"
            },
            500
        )


# =========================================================
# API: PASSENGER ORDER
# =========================================================


async def web_passenger_order(request):
    try:
        data = await get_request_data(request)

        telegram_id = await get_telegram_user(
            request,
            data
        )

        if not telegram_id:
            return await json_response(
                {
                    "error": "Telegram foydalanuvchisi aniqlanmadi."
                },
                401
            )

        ride_id = parse_int(
            data.get("ride_id"),
            0
        )

        from_city = normalize_city(
            data.get("from_city")
        )

        to_city = normalize_city(
            data.get("to_city")
        )

        ride_date = clean_text(
            data.get("ride_date")
        )

        ride_time = clean_text(
            data.get("ride_time")
            or data.get("time")
        )

        passenger_phone = normalize_phone(
            data.get("phone")
        )

        seats = parse_int(
            data.get("seats"),
            1
        )

        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if ride_id <= 0:
            return await json_response(
                {
                    "error": "Safar tanlanmagan."
                },
                400
            )

        if seats < 1 or seats > 8:
            return await json_response(
                {
                    "error": "O‘rindiqlar soni noto‘g‘ri."
                },
                400
            )

        db = await db_connect()

        # -------------------------------------------------
        # RIDE
        # -------------------------------------------------

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
            await db.close()

            return await json_response(
                {
                    "error": "Bu safar topilmadi yoki yopilgan."
                },
                404
            )

        ride = dict(ride)

        # -------------------------------------------------
        # O‘Z SAFARIGA BUYURTMA BERA OLMAYDI
        # -------------------------------------------------

        if ride.get("driver_telegram_id") == telegram_id:
            await db.close()

            return await json_response(
                {
                    "error": "O‘zingiz qo‘shgan safarga buyurtma bera olmaysiz."
                },
                400
            )

        # -------------------------------------------------
        # ALREADY ORDER
        # -------------------------------------------------

        cursor = await db.execute(
            """
            SELECT *
            FROM orders
            WHERE
                ride_id = ?
                AND passenger_telegram_id = ?
                AND status = 'active'
            """,
            (
                ride_id,
                telegram_id,
            )
        )

        existing_order = await cursor.fetchone()

        if existing_order:
            await db.close()

            return await json_response(
                {
                    "error": "Bu safarga allaqachon buyurtma bergansiz."
                },
                400
            )

        # -------------------------------------------------
        # BOOKED SEATS
        # -------------------------------------------------

        cursor = await db.execute(
            """
            SELECT
                COALESCE(SUM(seats), 0) AS booked
            FROM orders
            WHERE
                ride_id = ?
                AND status = 'active'
            """,
            (ride_id,)
        )

        booked_row = await cursor.fetchone()

        booked = parse_int(
            booked_row["booked"],
            0
        )

        available = (
            parse_int(ride.get("seats"), 0)
            - booked
        )

        if seats > available:
            await db.close()

            return await json_response(
                {
                    "error": (
                        f"Bu safarda faqat "
                        f"{available} ta bo‘sh joy bor."
                    )
                },
                400
            )

        # -------------------------------------------------
        # PASSENGER
        # -------------------------------------------------

        user = await get_user(telegram_id)

        passenger_name = ""

        if user:
            passenger_name = user.get(
                "full_name",
                ""
            )

            if not passenger_phone:
                passenger_phone = user.get(
                    "phone",
                    ""
                )

        if not passenger_phone:
            await db.close()

            return await json_response(
                {
                    "error": "Telefon raqamingizni kiriting."
                },
                400
            )

        await ensure_user(
            telegram_id=telegram_id,
            full_name=passenger_name,
            phone=passenger_phone
        )

        # -------------------------------------------------
        # ORDER
        # -------------------------------------------------

        cursor = await db.execute(
            """
            INSERT INTO orders (
                ride_id,
                passenger_telegram_id,
                passenger_name,
                passenger_phone,
                from_city,
                to_city,
                ride_date,
                ride_time,
                seats,
                latitude,
                longitude,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ride_id,
                telegram_id,
                passenger_name,
                passenger_phone,
                ride.get("from_city", ""),
                ride.get("to_city", ""),
                ride.get("ride_date", ""),
                ride.get("ride_time", ""),
                seats,
                latitude,
                longitude,
                "active",
                now_text(),
                now_text(),
            )
        )

        order_id = cursor.lastrowid

        await db.commit()
        await db.close()

        # -------------------------------------------------
        # DRIVER NOTIFICATION
        # -------------------------------------------------

        driver_telegram_id = ride.get(
            "driver_telegram_id"
        )

        if driver_telegram_id:
            try:
                await bot.send_message(
                    driver_telegram_id,
                    (
                        "👤 <b>Yangi yo‘lovchi!</b>\n\n"
                        f"📍 {ride.get('from_city')} → "
                        f"{ride.get('to_city')}\n"
                        f"📅 {ride.get('ride_date')}\n"
                        f"🕐 {ride.get('ride_time')}\n\n"
                        f"👤 {passenger_name or 'Yo‘lovchi'}\n"
                        f"📞 {passenger_phone}\n"
                        f"💺 {seats} ta joy"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.warning(
                    "Driver notification error: %s",
                    e
                )

        return await json_response({
            "ok": True,
            "order_id": order_id,
            "message": "Buyurtmangiz qabul qilindi.",
            "driver_phone": ride.get(
                "driver_phone",
                ""
            ),
        })

    except Exception as e:
        logging.exception("passenger order error")

        return await json_response(
            {
                "error": f"Server xatosi: {str(e)}"
            },
            500
        )


# =========================================================
# API: MY ORDERS / MY RIDES
# =========================================================


async def web_orders(request):
    try:
        data = await get_request_data(request)

        telegram_id = await get_telegram_user(
            request,
            data
        )

        if not telegram_id:
            return await json_response(
                {
                    "error": "Telegram foydalanuvchisi aniqlanmadi."
                },
                401
            )

        db = await db_connect()

        # =================================================
        # DRIVER RIDES
        # =================================================

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

        driver_rows = await cursor.fetchall()

        driver_rides = []

        for row in driver_rows:
            item = dict(row)

            cursor2 = await db.execute(
                """
                SELECT
                    COALESCE(SUM(seats), 0) AS booked
                FROM orders
                WHERE
                    ride_id = ?
                    AND status = 'active'
                """,
                (item["id"],)
            )

            booked_row = await cursor2.fetchone()

            booked = parse_int(
                booked_row["booked"],
                0
            )

            total = parse_int(
                item.get("seats"),
                0
            )

            driver_rides.append({
                "id": item["id"],
                "type": "driver",
                "from_city": item.get(
                    "from_city",
                    ""
                ),
                "to_city": item.get(
                    "to_city",
                    ""
                ),
                "ride_date": item.get(
                    "ride_date",
                    ""
                ),
                "ride_time": item.get(
                    "ride_time",
                    ""
                ),
                "seats": total,
                "booked_seats": booked,
                "available_seats": max(
                    0,
                    total - booked
                ),
                "price": parse_int(
                    item.get("price"),
                    0
                ),
                "car_model": item.get(
                    "car_model",
                    ""
                ),
                "car_number": item.get(
                    "car_number",
                    ""
                ),
                "status": item.get(
                    "status",
                    "active"
                ),
            })

        # =================================================
        # PASSENGER ORDERS
        # =================================================

        cursor = await db.execute(
            """
            SELECT
                o.*,

                r.driver_name,
                r.driver_phone,
                r.car_model,
                r.car_number,
                r.price AS ride_price,
                r.status AS ride_status

            FROM orders o

            LEFT JOIN rides r
                ON r.id = o.ride_id

            WHERE
                o.passenger_telegram_id = ?

            ORDER BY o.id DESC

            LIMIT 100
            """,
            (telegram_id,)
        )

        passenger_rows = await cursor.fetchall()

        passenger_orders = []

        for row in passenger_rows:
            item = dict(row)

            passenger_orders.append({
                "id": item["id"],
                "order_id": item["id"],
                "ride_id": item.get(
                    "ride_id"
                ),
                "type": "passenger",
                "from_city": item.get(
                    "from_city",
                    ""
                ),
                "to_city": item.get(
                    "to_city",
                    ""
                ),
                "ride_date": item.get(
                    "ride_date",
                    ""
                ),
                "ride_time": item.get(
                    "ride_time",
                    ""
                ),
                "seats": parse_int(
                    item.get("seats"),
                    1
                ),
                "driver_name": item.get(
                    "driver_name",
                    ""
                ),
                "driver_phone": item.get(
                    "driver_phone",
                    ""
                ),
                "car_model": item.get(
                    "car_model",
                    ""
                ),
                "car_number": item.get(
                    "car_number",
                    ""
                ),
                "price": parse_int(
                    item.get("ride_price"),
                    0
                ),
                "status": item.get(
                    "status",
                    "active"
                ),
                "ride_status": item.get(
                    "ride_status",
                    ""
                ),
            })

        await db.close()

        return await json_response({
            "ok": True,
            "driver_rides": driver_rides,
            "passenger_orders": passenger_orders,
            "rides": driver_rides,
            "orders": passenger_orders,
        })

    except Exception as e:
        logging.exception("orders error")

        return await json_response(
            {
                "error": f"Server xatosi: {str(e)}"
            },
            500
        )


# =========================================================
# API: PROFILE
# =========================================================


async def web_profile(request):
    try:
        data = await get_request_data(request)

        telegram_id = await get_telegram_user(
            request,
            data
        )

        if not telegram_id:
            return await json_response(
                {
                    "error": "Telegram foydalanuvchisi aniqlanmadi."
                },
                401
            )

        user = await get_user(
            telegram_id
        )

        db = await db_connect()

        cursor = await db.execute(
            """
            SELECT *
            FROM drivers
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        driver = await cursor.fetchone()

        await db.close()

        return await json_response({
            "ok": True,
            "profile": user or {},
            "user": user or {},
            "driver": dict(driver) if driver else None,
        })

    except Exception as e:
        logging.exception("profile error")

        return await json_response(
            {
                "error": f"Server xatosi: {str(e)}"
            },
            500
        )


# =========================================================
# API: PROFILE UPDATE
# =========================================================


async def web_profile_update(request):
    try:
        data = await get_request_data(request)

        telegram_id = await get_telegram_user(
            request,
            data
        )

        if not telegram_id:
            return await json_response(
                {
                    "error": "Telegram foydalanuvchisi aniqlanmadi."
                },
                401
            )

        full_name = clean_text(
            data.get("full_name")
        )

        phone = normalize_phone(
            data.get("phone")
        )

        username = clean_text(
            data.get("username")
        )

        await ensure_user(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            phone=phone
        )

        db = await db_connect()

        await db.execute(
            """
            UPDATE drivers
            SET
                full_name = ?,
                phone = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                full_name,
                phone,
                now_text(),
                telegram_id,
            )
        )

        await db.commit()
        await db.close()

        return await json_response({
            "ok": True,
            "message": "Profil yangilandi."
        })

    except Exception as e:
        logging.exception("profile update error")

        return await json_response(
            {
                "error": f"Server xatosi: {str(e)}"
            },
            500
        )


# =========================================================
# API: CANCEL ORDER
# =========================================================


async def web_order_cancel(request):
    try:
        data = await get_request_data(request)

        telegram_id = await get_telegram_user(
            request,
            data
        )

        if not telegram_id:
            return await json_response(
                {
                    "error": "Telegram foydalanuvchisi aniqlanmadi."
                },
                401
            )

        order_id = parse_int(
            data.get("order_id"),
            0
        )

        ride_id = parse_int(
            data.get("ride_id"),
            0
        )

        db = await db_connect()

        if order_id > 0:

            cursor = await db.execute(
                """
                SELECT *
                FROM orders
                WHERE
                    id = ?
                    AND passenger_telegram_id = ?
                """,
                (
                    order_id,
                    telegram_id,
                )
            )

            order = await cursor.fetchone()

            if not order:
                await db.close()

                return await json_response(
                    {
                        "error": "Buyurtma topilmadi."
                    },
                    404
                )

            await db.execute(
                """
                UPDATE orders
                SET
                    status = 'cancelled',
                    updated_at = ?
                WHERE
                    id = ?
                    AND passenger_telegram_id = ?
                """,
                (
                    now_text(),
                    order_id,
                    telegram_id,
                )
            )

        elif ride_id > 0:

            cursor = await db.execute(
                """
                SELECT *
                FROM rides
                WHERE
                    id = ?
                    AND driver_telegram_id = ?
                """,
                (
                    ride_id,
                    telegram_id,
                )
            )

            ride = await cursor.fetchone()

            if not ride:
                await db.close()

                return await json_response(
                    {
                        "error": "Safar topilmadi."
                    },
                    404
                )

            await db.execute(
                """
                UPDATE rides
                SET
                    status = 'cancelled',
                    updated_at = ?
                WHERE
                    id = ?
                    AND driver_telegram_id = ?
                """,
                (
                    now_text(),
                    ride_id,
                    telegram_id,
                )
            )

        else:
            await db.close()

            return await json_response(
                {
                    "error": "Buyurtma yoki safar ID kerak."
                },
                400
            )

        await db.commit()
        await db.close()

        return await json_response({
            "ok": True,
            "message": "Muvaffaqiyatli bekor qilindi."
        })

    except Exception as e:
        logging.exception("cancel error")

        return await json_response(
            {
                "error": f"Server xatosi: {str(e)}"
            },
            500
        )


# =========================================================
# TELEGRAM BOT MENU
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
            ],
            [
                KeyboardButton(
                    text="📋 Mening safarlarim"
                ),
                KeyboardButton(
                    text="👤 Profilim"
                ),
            ],
            [
                KeyboardButton(
                    text="📞 Yordam"
                )
            ]
        ],
        resize_keyboard=True
    )


# =========================================================
# /START
# =========================================================


@dp.message(CommandStart())
async def start_handler(message: Message):

    full_name = (
        message.from_user.full_name
        if message.from_user
        else ""
    )

    username = (
        message.from_user.username
        if message.from_user
        else ""
    )

    telegram_id = (
        message.from_user.id
        if message.from_user
        else None
    )

    if telegram_id:
        await ensure_user(
            telegram_id=telegram_id,
            username=username or "",
            full_name=full_name or ""
        )

    await message.answer(
        (
            "🚕 <b>OPPER TAXI</b>\n\n"
            "Toshkent va viloyatlar o‘rtasida "
            "safar toping yoki o‘zingizga yo‘lovchi oling.\n\n"
            "🚗 Haydovchi — safar qo‘shadi\n"
            "👤 Yo‘lovchi — safar qidiradi\n"
            "🔎 Kerakli yo‘nalishni topadi\n"
            "📞 Haydovchi bilan bog‘lanadi\n\n"
            "Quyidagi <b>OPPER TAXI</b> tugmasini bosing."
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# SIMPLE MENU BUTTONS
# =========================================================


@dp.message(F.text == "🚕 OPPER TAXI")
async def open_app_handler(message: Message):
    await message.answer(
        "🚕 OPPER TAXI ilovasini oching:",
        reply_markup=main_keyboard()
    )


@dp.message(F.text == "🚕 Haydovchi bo‘lish")
async def driver_handler(message: Message):
    await message.answer(
        (
            "🚗 <b>Haydovchi bo‘lish</b>\n\n"
            "OPPER TAXI ilovasini ochib:\n"
            "1️⃣ Haydovchi bo‘lish\n"
            "2️⃣ Ma’lumotlarni kiriting\n"
            "3️⃣ Safar qo‘shish\n"
            "4️⃣ Qayerdan → Qayerga\n"
            "5️⃣ Sana va vaqt\n"
            "6️⃣ Bo‘sh joy\n"
            "7️⃣ Narx\n\n"
            "Shundan keyin safaringiz yo‘lovchilarga "
            "ko‘rinadi."
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "👤 Yo‘lovchi bo‘lish")
async def passenger_handler(message: Message):
    await message.answer(
        (
            "👤 <b>Yo‘lovchi</b>\n\n"
            "OPPER TAXI ilovasini oching va "
            "kerakli yo‘nalishni tanlang.\n\n"
            "🔎 Mavjud safarlar chiqadi."
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "🔎 Safar qidirish")
async def search_handler(message: Message):
    await message.answer(
        (
            "🔎 <b>Safar qidirish</b>\n\n"
            "OPPER TAXI ilovasini oching va "
            "Qayerdan → Qayerga yo‘nalishini tanlang."
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "📋 Mening safarlarim")
async def my_rides_handler(message: Message):
    await message.answer(
        (
            "📋 <b>Mening safarlarim</b>\n\n"
            "Haydovchi sifatida qo‘shgan safarlaringiz "
            "va yo‘lovchi sifatida bergan buyurtmalaringiz "
            "ilova ichida ko‘rsatiladi."
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "👤 Profilim")
async def profile_handler(message: Message):
    await message.answer(
        (
            "👤 <b>Profil</b>\n\n"
            "Profilingizni OPPER TAXI ilovasi ichidan "
            "ko‘rishingiz va o‘zgartirishingiz mumkin."
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "📞 Yordam")
async def help_handler(message: Message):
    await message.answer(
        (
            "📞 <b>OPPER TAXI yordam</b>\n\n"
            "Muammo bo‘lsa administratorga murojaat qiling.\n\n"
            "🚕 OPPER TAXI"
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# WEB ROUTES
# =========================================================


def create_web_app():

    app = web.Application(
        client_max_size=20 * 1024 * 1024
    )

    # -----------------------------------------------------
    # FRONTEND
    # -----------------------------------------------------

    app.router.add_get(
        "/",
        web_index
    )

    app.router.add_get(
        "/app",
        web_index
    )

    # -----------------------------------------------------
    # HEALTH
    # -----------------------------------------------------

    app.router.add_get(
        "/health",
        health_handler
    )

    # -----------------------------------------------------
    # API
    # -----------------------------------------------------

    app.router.add_post(
        "/api/driver/register",
        web_driver_register
    )

    app.router.add_post(
        "/api/driver/ride",
        web_driver_ride
    )

    app.router.add_post(
        "/api/passenger/order",
        web_passenger_order
    )

    app.router.add_post(
        "/api/rides",
        web_rides
    )

    app.router.add_get(
        "/api/rides",
        web_rides
    )

    app.router.add_post(
        "/api/orders",
        web_orders
    )

    app.router.add_get(
        "/api/orders",
        web_orders
    )

    app.router.add_post(
        "/api/profile",
        web_profile
    )

    app.router.add_get(
        "/api/profile",
        web_profile
    )

    app.router.add_post(
        "/api/profile/update",
        web_profile_update
    )

    app.router.add_post(
        "/api/order/cancel",
        web_order_cancel
    )

    return app


# =========================================================
# TELEGRAM SETUP
# =========================================================


async def setup_bot():

    try:
        await bot.set_my_commands([
            BotCommand(
                command="start",
                description="OPPER TAXI ni ochish"
            ),
        ])
    except Exception as e:
        logging.warning(
            "Bot commands error: %s",
            e
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

        print(
            "✅ Telegram Mini App menu button o‘rnatildi."
        )

    except Exception as e:
        logging.error(
            "Mini App menu button error: %s",
            e
        )


# =========================================================
# START WEB SERVER
# =========================================================


async def start_web_server():

    app = create_web_app()

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=PORT
    )

    await site.start()

    print(
        f"🌐 WEB SERVER RUNNING: {PORT}"
    )

    print(
        f"📱 MINI APP: {MINI_APP_URL}/"
    )

    return runner


# =========================================================
# MAIN
# =========================================================


async def main():

    await init_db()

    await setup_bot()

    await start_web_server()

    print(
        "🤖 BOT POLLING STARTED"
    )

    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    finally:

        await bot.session.close()


# =========================================================
# RUN
# =========================================================


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "🛑 BOT STOPPED"
        )

    except Exception as e:

        logging.exception(
            "❌ FATAL ERROR: %s",
            e
        )
