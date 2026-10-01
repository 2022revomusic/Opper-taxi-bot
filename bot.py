import os
import re
import json
import time
import hmac
import hashlib
import logging
from pathlib import Path
from urllib.parse import parse_qsl

import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    MenuButtonWebApp,
    WebAppInfo,
    FSInputFile,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID = int(os.getenv("ADMIN_ID", "653914246"))

# Railway Variables'da o'zingiz qo'yasiz
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

# Admin session uchun maxfiy kalit
ADMIN_SESSION_SECRET = os.getenv(
    "ADMIN_SESSION_SECRET",
    ""
).strip()

PORT = int(os.getenv("PORT", "8080"))

BASE_DIR = Path(__file__).resolve().parent

WEB_DIR = BASE_DIR / "web"
INDEX_FILE = WEB_DIR / "index.html"

DB_PATH = BASE_DIR / "oper_taxi.db"

UPLOAD_DIR = BASE_DIR / "uploads" / "drivers"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

RAILWAY_DOMAIN = os.getenv(
    "RAILWAY_PUBLIC_DOMAIN",
    ""
).strip()

MINI_APP_URL = os.getenv(
    "MINI_APP_URL",
    ""
).strip()

if not MINI_APP_URL and RAILWAY_DOMAIN:
    MINI_APP_URL = f"https://{RAILWAY_DOMAIN}"

if not MINI_APP_URL:
    MINI_APP_URL = (
        "https://opper-taxi-bot-production.up.railway.app"
    )

if not ADMIN_SESSION_SECRET:
    ADMIN_SESSION_SECRET = hashlib.sha256(
        f"{BOT_TOKEN}|OPER_TAXI_ADMIN".encode()
    ).hexdigest()

ADMIN_SESSION_TTL = 24 * 60 * 60

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("oper_taxi")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN Railway Variables'da mavjud emas!"
    )


# =========================================================
# BOT
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# O'ZBEKISTON VILOYAT / TUMANLAR
# =========================================================

REGIONS = {
    "Toshkent shahri": [
        "Bektemir",
        "Chilonzor",
        "Mirobod",
        "Mirzo Ulug‘bek",
        "Olmazor",
        "Sergeli",
        "Shayxontohur",
        "Uchtepa",
        "Yakkasaroy",
        "Yunusobod",
        "Yashnobod",
        "Yangihayot",
    ],

    "Toshkent viloyati": [
        "Angren",
        "Bekobod",
        "Bo‘ka",
        "Chinoz",
        "Ohangaron",
        "Oqqo‘rg‘on",
        "Olmaliq",
        "Parkent",
        "Piskent",
        "Quyi Chirchiq",
        "Yuqori Chirchiq",
        "Zangiota",
        "Yangiyo‘l",
        "Chirchiq",
    ],

    "Farg‘ona viloyati": [
        "Farg‘ona shahri",
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
        "Quvasoy",
    ],

    "Andijon viloyati": [
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
        "Xonobod",
    ],

    "Namangan viloyati": [
        "Namangan shahri",
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
    ],

    "Samarqand viloyati": [
        "Samarqand shahri",
        "Bulung‘ur",
        "Ishtixon",
        "Jomboy",
        "Kattaqo‘rg‘on",
        "Kattaqo‘rg‘on tumani",
        "Narpay",
        "Nurobod",
        "Oqdaryo",
        "Pastdarg‘om",
        "Paxtachi",
        "Payariq",
        "Qo‘shrabot",
        "Samarqand tumani",
        "Toyloq",
        "Urgut",
    ],

    "Buxoro viloyati": [
        "Buxoro shahri",
        "Buxoro tumani",
        "G‘ijduvon",
        "Jondor",
        "Kogon",
        "Kogon tumani",
        "Olot",
        "Peshku",
        "Qorako‘l",
        "Qorovulbozor",
        "Romitan",
        "Shofirkon",
        "Vobkent",
    ],

    "Jizzax viloyati": [
        "Jizzax shahri",
        "Arnasoy",
        "Baxmal",
        "Do‘stlik",
        "Forish",
        "G‘allaorol",
        "Mirzacho‘l",
        "Paxtakor",
        "Sharof Rashidov",
        "Yangiobod",
        "Zomin",
        "Zarbdor",
    ],

    "Qashqadaryo viloyati": [
        "Qarshi shahri",
        "Chiroqchi",
        "Dehqonobod",
        "G‘uzor",
        "Kasbi",
        "Kitob",
        "Koson",
        "Ko‘kdala",
        "Mirishkor",
        "Muborak",
        "Nishon",
        "Qamashi",
        "Qarshi tumani",
        "Shahrisabz",
        "Shahrisabz tumani",
        "Yakkabog‘",
    ],

    "Navoiy viloyati": [
        "Navoiy shahri",
        "Karmana",
        "Konimex",
        "Navbahor",
        "Nurota",
        "Qiziltepa",
        "Tomdi",
        "Uchquduq",
        "Xatirchi",
        "Zarafshon",
    ],

    "Surxondaryo viloyati": [
        "Termiz shahri",
        "Angor",
        "Bandixon",
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
        "Uzun",
    ],

    "Sirdaryo viloyati": [
        "Guliston shahri",
        "Boyovut",
        "Guliston tumani",
        "Mirzaobod",
        "Oqoltin",
        "Sayxunobod",
        "Sardoba",
        "Shirin",
        "Yangiyer",
    ],

    "Xorazm viloyati": [
        "Urganch shahri",
        "Bog‘ot",
        "Gurlan",
        "Hazorasp",
        "Qo‘shko‘pir",
        "Shovot",
        "Tuproqqal’a",
        "Urganch tumani",
        "Xiva",
        "Xiva tumani",
        "Yangibozor",
        "Yangiariq",
    ],

    "Qoraqalpog‘iston Respublikasi": [
        "Nukus shahri",
        "Amudaryo",
        "Beruniy",
        "Bo‘zatov",
        "Chimboy",
        "Ellikqal’a",
        "Kegeyli",
        "Mo‘ynoq",
        "Nukus tumani",
        "Qanliko‘l",
        "Qo‘ng‘irot",
        "Qorao‘zak",
        "Shumanay",
        "Taxtako‘pir",
        "To‘rtko‘l",
        "Xo‘jayli",
    ],
}


REGION_NAMES = list(REGIONS.keys())


# =========================================================
# HELPERS
# =========================================================

def now():
    return int(time.time())


def clean_text(value, max_len=500):
    if value is None:
        return ""

    value = str(value).strip()

    return value[:max_len]


def clean_phone(value):
    if not value:
        return ""

    value = str(value).strip()

    return re.sub(r"[^\d+]", "", value)


def valid_phone(phone):
    phone = clean_phone(phone)

    digits = re.sub(r"\D", "", phone)

    return 9 <= len(digits) <= 15


def normalize_city(value):
    value = clean_text(value, 100)

    aliases = {
        "Toshkent": "Toshkent shahri",
        "Toshkent shahar": "Toshkent shahri",
        "Fargona": "Farg‘ona viloyati",
        "Farg‘ona": "Farg‘ona viloyati",
        "Andijon": "Andijon viloyati",
        "Namangan": "Namangan viloyati",
        "Samarqand": "Samarqand viloyati",
        "Buxoro": "Buxoro viloyati",
        "Jizzax": "Jizzax viloyati",
        "Qashqadaryo": "Qashqadaryo viloyati",
        "Navoiy": "Navoiy viloyati",
        "Surxondaryo": "Surxondaryo viloyati",
        "Sirdaryo": "Sirdaryo viloyati",
        "Xorazm": "Xorazm viloyati",
    }

    return aliases.get(value, value)


def json_ok(data):
    return web.json_response(
        data,
        dumps=lambda x: json.dumps(
            x,
            ensure_ascii=False,
        ),
    )


def error_response(message, status=400):
    return json_ok(
        {
            "ok": False,
            "error": message,
        }
    ).clone(status=status)


# =========================================================
# TELEGRAM WEB APP INIT DATA
# =========================================================

def validate_init_data(init_data: str):
    if not init_data:
        return None

    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))

        received_hash = data.pop("hash", None)

        if not received_hash:
            return None

        auth_date = data.get("auth_date")

        if not auth_date:
            return None

        try:
            auth_date = int(auth_date)
        except Exception:
            return None

        if now() - auth_date > 86400:
            return None

        data_check_string = "\n".join(
            f"{key}={data[key]}"
            for key in sorted(data.keys())
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

        user_json = data.get("user")

        if not user_json:
            return None

        return json.loads(user_json)

    except Exception:
        logger.exception("init_data validation error")
        return None


async def get_telegram_user(request):
    init_data = ""

    if request.method.upper() == "GET":
        init_data = request.query.get(
            "init_data",
            "",
        )

    elif request.content_type == "application/json":
        try:
            body = await request.json()
            init_data = body.get(
                "init_data",
                "",
            )
        except Exception:
            init_data = ""

    user = validate_init_data(init_data)

    return user


# =========================================================
# DATABASE
# =========================================================

async def db_connect():
    db = await aiosqlite.connect(DB_PATH)

    db.row_factory = aiosqlite.Row

    return db


async def add_column_if_missing(
    db,
    table,
    column,
    definition,
):
    cursor = await db.execute(
        f"PRAGMA table_info({table})"
    )

    rows = await cursor.fetchall()

    columns = {
        row["name"]
        for row in rows
    }

    if column not in columns:
        await db.execute(
            f"ALTER TABLE {table} ADD COLUMN "
            f"{column} {definition}"
        )


async def init_db():

    async with await db_connect() as db:

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                created_at INTEGER NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                car_model TEXT DEFAULT '',
                car_number TEXT DEFAULT '',
                seats INTEGER DEFAULT 1,

                passport_file TEXT DEFAULT '',
                license_file TEXT DEFAULT '',
                car_registration_file TEXT DEFAULT '',
                car_photo_file TEXT DEFAULT '',

                approval_status TEXT DEFAULT 'pending',
                rejection_reason TEXT DEFAULT '',

                created_at INTEGER NOT NULL,
                approved_at INTEGER
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER NOT NULL,

                from_city TEXT DEFAULT '',
                to_city TEXT DEFAULT '',

                from_region TEXT DEFAULT '',
                from_district TEXT DEFAULT '',
                from_address TEXT DEFAULT '',

                to_region TEXT DEFAULT '',
                to_district TEXT DEFAULT '',
                to_address TEXT DEFAULT '',

                ride_date TEXT DEFAULT '',
                ride_time TEXT DEFAULT '',

                seats INTEGER DEFAULT 1,
                price INTEGER DEFAULT 0,

                status TEXT DEFAULT 'active',

                created_at INTEGER NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ride_id INTEGER NOT NULL,

                passenger_id INTEGER NOT NULL,

                passenger_phone TEXT DEFAULT '',

                address TEXT DEFAULT '',
                from_address TEXT DEFAULT '',

                latitude REAL,
                longitude REAL,

                seats INTEGER DEFAULT 1,

                status TEXT DEFAULT 'pending',

                created_at INTEGER NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS passenger_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                passenger_id INTEGER NOT NULL,

                from_city TEXT DEFAULT '',
                to_city TEXT DEFAULT '',

                from_region TEXT DEFAULT '',
                from_district TEXT DEFAULT '',

                to_region TEXT DEFAULT '',
                to_district TEXT DEFAULT '',

                phone TEXT DEFAULT '',
                comment TEXT DEFAULT '',

                status TEXT DEFAULT 'open',

                created_at INTEGER NOT NULL
            )
            """

        # -------------------------------------------------
        # MIGRATIONS
        # -------------------------------------------------

        driver_columns = [
            (
                "passport_file",
                "TEXT DEFAULT ''",
            ),
            (
                "license_file",
                "TEXT DEFAULT ''",
            ),
            (
                "car_registration_file",
                "TEXT DEFAULT ''",
            ),
            (
                "car_photo_file",
                "TEXT DEFAULT ''",
            ),
            (
                "approval_status",
                "TEXT DEFAULT 'pending'",
            ),
            (
                "rejection_reason",
                "TEXT DEFAULT ''",
            ),
            (
                "approved_at",
                "INTEGER",
            ),
        ]

        for column, definition in driver_columns:
            await add_column_if_missing(
                db,
                "drivers",
                column,
                definition,
            )

        ride_columns = [
            ("from_region", "TEXT DEFAULT ''"),
            ("from_district", "TEXT DEFAULT ''"),
            ("from_address", "TEXT DEFAULT ''"),
            ("to_region", "TEXT DEFAULT ''"),
            ("to_district", "TEXT DEFAULT ''"),
            ("to_address", "TEXT DEFAULT ''"),
        ]

        for column, definition in ride_columns:
            await add_column_if_missing(
                db,
                "rides",
                column,
                definition,
            )

        order_columns = [
            ("address", "TEXT DEFAULT ''"),
            ("from_address", "TEXT DEFAULT ''"),
            ("latitude", "REAL"),
            ("longitude", "REAL"),
            ("seats", "INTEGER DEFAULT 1"),
        ]

        for column, definition in order_columns:
            await add_column_if_missing(
                db,
                "orders",
                column,
                definition,
            )

        request_columns = [
            ("from_region", "TEXT DEFAULT ''"),
            ("from_district", "TEXT DEFAULT ''"),
            ("to_region", "TEXT DEFAULT ''"),
            ("to_district", "TEXT DEFAULT ''"),
            ("phone", "TEXT DEFAULT ''"),
            ("comment", "TEXT DEFAULT ''"),
        ]

        for column, definition in request_columns:
            await add_column_if_missing(
                db,
                "passenger_requests",
                column,
                definition,
            )

        await db.commit()

    logger.info("DATABASE READY")


# =========================================================
# USERS
# =========================================================

async def ensure_user(
    telegram_id,
    username="",
    full_name="",
    phone="",
):
    async with await db_connect() as db:

        await db.execute(
            """
            INSERT INTO users (
                telegram_id,
                username,
                full_name,
                phone,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                username=excluded.username,
                full_name=CASE
                    WHEN excluded.full_name != ''
                    THEN excluded.full_name
                    ELSE users.full_name
                END,
                phone=CASE
                    WHEN excluded.phone != ''
                    THEN excluded.phone
                    ELSE users.phone
                END
            """,
            (
                telegram_id,
                username or "",
                full_name or "",
                phone or "",
                now(),
            ),
        )

        await db.commit()


async def require_user(request):

    user = await get_telegram_user(request)

    if not user:
        raise web.HTTPUnauthorized(
            text="Telegram WebApp tasdiqlanmadi"
        )

    telegram_id = int(user["id"])

    await ensure_user(
        telegram_id,
        user.get("username", ""),
        (
            f"{user.get('first_name', '')} "
            f"{user.get('last_name', '')}"
        ).strip(),
    )

    return user


async def get_driver(telegram_id):

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM drivers
            WHERE telegram_id=?
            """,
            (telegram_id,),
        )

        return await cursor.fetchone()


async def require_approved_driver(request):

    user = await require_user(request)

    driver = await get_driver(
        int(user["id"])
    )

    if not driver:
        raise web.HTTPForbidden(
            text="Haydovchi sifatida ro‘yxatdan o‘tilmagan"
        )

    if driver["approval_status"] != "approved":
        raise web.HTTPForbidden(
            text="Haydovchi hali admin tomonidan tasdiqlanmagan"
        )

    return user, driver


# =========================================================
# ADMIN SESSION
# =========================================================

def create_admin_token():

    timestamp = str(now())

    signature = hmac.new(
        ADMIN_SESSION_SECRET.encode(),
        timestamp.encode(),
        hashlib.sha256,
    ).hexdigest()

    return f"{timestamp}.{signature}"


def validate_admin_token(token):

    if not token or "." not in token:
        return False

    try:
        timestamp, signature = token.split(
            ".",
            1,
        )

        timestamp = int(timestamp)

        if now() - timestamp > ADMIN_SESSION_TTL:
            return False

        expected = hmac.new(
            ADMIN_SESSION_SECRET.encode(),
            str(timestamp).encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            signature,
            expected,
        )

    except Exception:
        return False


def is_admin_session(request):

    token = request.cookies.get(
        "opper_admin_session",
        "",
    )

    return validate_admin_token(token)


async def require_admin(request):

    if not is_admin_session(request):
        raise web.HTTPUnauthorized(
            text="Admin login required"
        )

    return True


# =========================================================
# ADMIN PANEL HTML
# =========================================================

ADMIN_HTML = r"""
<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width,initial-scale=1.0">

<title>OPER TAXI — Admin</title>

<style>
*{
    box-sizing:border-box;
}

body{
    margin:0;
    font-family:-apple-system,BlinkMacSystemFont,
    "Segoe UI",Roboto,Arial,sans-serif;
    background:#f5f5f5;
    color:#111;
}

.header{
    background:#111;
    color:#ffd400;
    padding:18px;
    font-size:22px;
    font-weight:800;
}

.container{
    max-width:1100px;
    margin:auto;
    padding:18px;
}

.card{
    background:white;
    border-radius:18px;
    padding:18px;
    margin-bottom:16px;
    box-shadow:0 5px 20px rgba(0,0,0,.07);
}

input{
    width:100%;
    padding:14px;
    border:1px solid #ddd;
    border-radius:12px;
    font-size:16px;
    margin-bottom:12px;
}

button{
    border:0;
    padding:13px 18px;
    border-radius:12px;
    font-weight:700;
    cursor:pointer;
}

.login-btn{
    background:#ffd400;
    color:#111;
    width:100%;
}

.approve{
    background:#16a34a;
    color:white;
}

.reject{
    background:#dc2626;
    color:white;
}

.logout{
    background:#222;
    color:white;
    float:right;
}

.stats{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:12px;
}

.stat{
    background:#111;
    color:white;
    border-radius:16px;
    padding:18px;
}

.stat b{
    display:block;
    font-size:28px;
    color:#ffd400;
}

.driver{
    border:1px solid #eee;
    border-radius:16px;
    padding:15px;
    margin-top:12px;
}

.actions{
    display:flex;
    gap:10px;
    margin-top:12px;
}

.actions button{
    flex:1;
}

.hidden{
    display:none;
}

.error{
    color:#dc2626;
    margin-top:10px;
}

.success{
    color:#16a34a;
}

@media(max-width:700px){
    .stats{
        grid-template-columns:repeat(2,1fr);
    }

    .actions{
        flex-direction:column;
    }
}
</style>
</head>

<body>

<div class="header">
    🚕 OPER TAXI
    <button
        id="logoutBtn"
        class="logout hidden"
        onclick="logout()">
        Chiqish
    </button>
</div>

<div class="container">

<div id="loginBox" class="card">

    <h2>🔐 Admin panel</h2>

    <p>
        Admin parolini kiriting.
    </p>

    <input
        id="password"
        type="password"
        placeholder="Admin paroli">

    <button
        class="login-btn"
        onclick="login()">
        Kirish
    </button>

    <div id="loginError"
         class="error"></div>

</div>


<div id="panel" class="hidden">

    <div class="stats">

        <div class="stat">
            Foydalanuvchilar
            <b id="users">0</b>
        </div>

        <div class="stat">
            Haydovchilar
            <b id="drivers">0</b>
        </div>

        <div class="stat">
            Safarlar
            <b id="rides">0</b>
        </div>

        <div class="stat">
            Buyurtmalar
            <b id="orders">0</b>
        </div>

    </div>


    <div class="card">

        <h2>⏳ Tasdiqlanishi kutilayotgan haydovchilar</h2>

        <div id="pendingDrivers">
            Yuklanmoqda...
        </div>

    </div>


    <div class="card">

        <h2>🚕 So‘nggi safarlar</h2>

        <div id="rideList">
            Yuklanmoqda...
        </div>

    </div>


    <div class="card">

        <h2>📦 So‘nggi buyurtmalar</h2>

        <div id="orderList">
            Yuklanmoqda...
        </div>

    </div>

</div>

</div>


<script>

async function api(url, options={}){

    const response = await fetch(
        url,
        {
            credentials:"same-origin",
            ...options
        }
    );

    if(!response.ok){

        let text = "";

        try{
            text = await response.text();
        }catch(e){}

        throw new Error(
            text || ("HTTP " + response.status)
        );
    }

    return response.json();
}


async function login(){

    const password =
        document.getElementById("password").value;

    const box =
        document.getElementById("loginError");

    box.textContent = "";

    try{

        await api(
            "/api/admin/login",
            {
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify({
                    password:password
                })
            }
        );

        document
            .getElementById("loginBox")
            .classList.add("hidden");

        document
            .getElementById("panel")
            .classList.remove("hidden");

        document
            .getElementById("logoutBtn")
            .classList.remove("hidden");

        loadDashboard();

    }catch(e){

        box.textContent =
            "Parol noto‘g‘ri yoki server xatosi.";
    }
}


async function logout(){

    try{
        await api(
            "/api/admin/logout",
            {
                method:"POST"
            }
        );
    }catch(e){}

    location.reload();
}


async function loadDashboard(){

    try{

        const stats =
            await api("/api/admin/stats");

        document.getElementById("users")
            .textContent = stats.users;

        document.getElementById("drivers")
            .textContent = stats.drivers;

        document.getElementById("rides")
            .textContent = stats.rides;

        document.getElementById("orders")
            .textContent = stats.orders;


        const drivers =
            await api("/api/admin/drivers");

        const box =
            document.getElementById("pendingDrivers");

        if(!drivers.drivers.length){

            box.innerHTML =
                "<p>Hozircha kutilayotgan haydovchi yo‘q.</p>";

        }else{

            box.innerHTML =
                drivers.drivers.map(d => `

                <div class="driver">

                    <b>${escapeHtml(d.full_name)}</b>

                    <p>
                        📞 ${escapeHtml(d.phone)}
                    </p>

                    <p>
                        🚗 ${escapeHtml(d.car_model)}
                    </p>

                    <p>
                        🔢 ${escapeHtml(d.car_number)}
                    </p>

                    <p>
                        💺 ${d.seats} o‘rin
                    </p>

                    <div class="actions">

                        <button
                            class="approve"
                            onclick="driverAction(${d.telegram_id}, 'approve')">
                            ✅ Tasdiqlash
                        </button>

                        <button
                            class="reject"
                            onclick="driverAction(${d.telegram_id}, 'reject')">
                            ❌ Rad etish
                        </button>

                    </div>

                </div>

                `).join("");
        }


        const rides =
            await api("/api/admin/rides");

        document.getElementById("rideList")
            .innerHTML =
            rides.rides.map(r => `

            <div class="driver">

                🚕
                <b>
                ${escapeHtml(r.from_city)}
                →
                ${escapeHtml(r.to_city)}
                </b>

                <p>
                📅 ${escapeHtml(r.ride_date)}
                ${escapeHtml(r.ride_time)}
                </p>

                <p>
                💰 ${r.price.toLocaleString()} so‘m
                </p>

            </div>

            `).join("") || "Safarlar yo‘q";


        const orders =
            await api("/api/admin/orders");

        document.getElementById("orderList")
            .innerHTML =
            orders.orders.map(o => `

            <div class="driver">

                📦 Buyurtma #${o.id}

                <p>
                🚕
                ${escapeHtml(o.from_city)}
                →
                ${escapeHtml(o.to_city)}
                </p>

                <p>
                📞
                ${escapeHtml(o.passenger_phone)}
                </p>

                <p>
                Holat:
                ${escapeHtml(o.status)}
                </p>

            </div>

            `).join("") || "Buyurtmalar yo‘q";

    }catch(e){

        if(e.message.includes("401")){
            location.reload();
        }
    }
}


async function driverAction(id, action){

    let reason = "";

    if(action === "reject"){

        reason = prompt(
            "Rad etish sababini yozing:"
        ) || "Admin tomonidan rad etildi.";
    }

    try{

        await api(
            "/api/admin/driver/action",
            {
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify({
                    telegram_id:id,
                    action:action,
                    reason:reason
                })
            }
        );

        loadDashboard();

    }catch(e){

        alert(
            "Amalni bajarishda xatolik."
        );
    }
}


function escapeHtml(text){

    return String(text ?? "")
        .replaceAll("&","&amp;")
        .replaceAll("<","&lt;")
        .replaceAll(">","&gt;")
        .replaceAll('"',"&quot;")
        .replaceAll("'","&#039;");
}


api("/api/admin/me")
.then(() => {

    document
        .getElementById("loginBox")
        .classList.add("hidden");

    document
        .getElementById("panel")
        .classList.remove("hidden");

    document
        .getElementById("logoutBtn")
        .classList.remove("hidden");

    loadDashboard();

})
.catch(() => {});

</script>

</body>
</html>
"""


# =========================================================
# ADMIN WEB
# =========================================================

async def admin_page(request):

    return web.Response(
        text=ADMIN_HTML,
        content_type="text/html",
    )


async def admin_login(request):

    if not ADMIN_PASSWORD:
        return error_response(
            "ADMIN_PASSWORD Railway Variables'da sozlanmagan.",
            500,
        )

    try:
        data = await request.json()
    except Exception:
        return error_response(
            "Noto‘g‘ri JSON",
            400,
        )

    password = str(
        data.get("password", "")
    )

    if not hmac.compare_digest(
        password,
        ADMIN_PASSWORD,
    ):
        return error_response(
            "Parol noto‘g‘ri",
            401,
        )

    token = create_admin_token()

    response = json_ok(
        {
            "ok": True
        }
    )

    response.set_cookie(
        "opper_admin_session",
        token,
        max_age=ADMIN_SESSION_TTL,
        httponly=True,
        secure=True,
        samesite="Strict",
        path="/",
    )

    return response


async def admin_logout(request):

    response = json_ok(
        {
            "ok": True
        }
    )

    response.del_cookie(
        "opper_admin_session",
        path="/",
    )

    return response


async def admin_me(request):

    await require_admin(request)

    return json_ok(
        {
            "ok": True,
            "admin": True,
        }
    )


async def admin_stats(request):

    await require_admin(request)

    async with await db_connect() as db:

        async def count(table):
            cursor = await db.execute(
                f"SELECT COUNT(*) AS c FROM {table}"
            )

            row = await cursor.fetchone()

            return row["c"]

        return json_ok(
            {
                "ok": True,
                "users": await count("users"),
                "drivers": await count("drivers"),
                "rides": await count("rides"),
                "orders": await count("orders"),
            }
        )


async def admin_drivers(request):

    await require_admin(request)

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM drivers
            WHERE approval_status='pending'
            ORDER BY created_at DESC
            """
        )

        rows = await cursor.fetchall()

        drivers = [
            dict(row)
            for row in rows
        ]

    return json_ok(
        {
            "ok": True,
            "drivers": drivers,
        }
    )


async def admin_rides(request):

    await require_admin(request)

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM rides
            ORDER BY created_at DESC
            LIMIT 50
            """
        )

        rows = await cursor.fetchall()

    return json_ok(
        {
            "ok": True,
            "rides": [
                dict(row)
                for row in rows
            ],
        }
    )


async def admin_orders(request):

    await require_admin(request)

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT
                o.*,
                r.from_city,
                r.to_city
            FROM orders o
            LEFT JOIN rides r
                ON r.id=o.ride_id
            ORDER BY o.created_at DESC
            LIMIT 50
            """
        )

        rows = await cursor.fetchall()

    return json_ok(
        {
            "ok": True,
            "orders": [
                dict(row)
                for row in rows
            ],
        }
    )


# =========================================================
# ADMIN DRIVER ACTION
# =========================================================

async def set_driver_status(
    telegram_id,
    status,
    reason="",
):
    async with await db_connect() as db:

        await db.execute(
            """
            UPDATE drivers

            SET
                approval_status=?,
                rejection_reason=?,
                approved_at=?

            WHERE telegram_id=?
            """,
            (
                status,
                reason,
                now() if status == "approved" else None,
                telegram_id,
            ),
        )

        await db.commit()


async def notify_driver_status(
    telegram_id,
    status,
    reason="",
):

    try:

        if status == "approved":

            await bot.send_message(
                telegram_id,
                (
                    "🎉 <b>Tabriklaymiz!</b>\n\n"
                    "Sizning haydovchi profilingiz "
                    "admin tomonidan tasdiqlandi.\n\n"
                    "🚕 Endi OPER TAXI'da "
                    "haydovchi sifatida safar "
                    "qo‘shishingiz mumkin."
                ),
                parse_mode="HTML",
            )

        elif status == "rejected":

            await bot.send_message(
                telegram_id,
                (
                    "❌ <b>Haydovchi arizangiz rad etildi.</b>\n\n"
                    f"Sabab: {reason or 'Admin tomonidan rad etildi.'}"
                ),
                parse_mode="HTML",
            )

    except Exception:
        logger.exception(
            "Driver notification failed"
        )


async def admin_driver_action(request):

    await require_admin(request)

    try:
        data = await request.json()
    except Exception:
        return error_response(
            "Noto‘g‘ri JSON",
            400,
        )

    telegram_id = int(
        data.get("telegram_id", 0)
    )

    action = data.get(
        "action",
        "",
    )

    reason = clean_text(
        data.get("reason", ""),
        500,
    )

    if telegram_id <= 0:
        return error_response(
            "telegram_id noto‘g‘ri",
            400,
        )

    if action == "approve":

        await set_driver_status(
            telegram_id,
            "approved",
            "",
        )

        await notify_driver_status(
            telegram_id,
            "approved",
        )

        return json_ok(
            {
                "ok": True,
                "status": "approved",
            }
        )

    if action == "reject":

        if not reason:
            reason = "Admin tomonidan rad etildi."

        await set_driver_status(
            telegram_id,
            "rejected",
            reason,
        )

        await notify_driver_status(
            telegram_id,
            "rejected",
            reason,
        )

        return json_ok(
            {
                "ok": True,
                "status": "rejected",
            }
        )

    return error_response(
        "Noto‘g‘ri action",
        400,
    )


# =========================================================
# PROFILE
# =========================================================

async def api_config(request):

    await require_user(request)

    return json_ok(
        {
            "ok": True,
            "regions": REGIONS,
            "cities": REGION_NAMES,
            "mini_app_url": MINI_APP_URL,
        }
    )


async def api_profile(request):

    user = await require_user(request)

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM users
            WHERE telegram_id=?
            """,
            (int(user["id"]),),
        )

        row = await cursor.fetchone()

    driver = await get_driver(
        int(user["id"])
    )

    return json_ok(
        {
            "ok": True,
            "profile": dict(row) if row else {},
            "driver": dict(driver) if driver else None,
        }
    )


async def api_profile_update(request):

    user = await require_user(request)

    try:
        data = await request.json()
    except Exception:
        return error_response(
            "Noto‘g‘ri JSON",
            400,
        )

    full_name = clean_text(
        data.get("full_name", ""),
        200,
    )

    phone = clean_phone(
        data.get("phone", "")
    )

    if phone and not valid_phone(phone):
        return error_response(
            "Telefon raqami noto‘g‘ri",
            400,
        )

    async with await db_connect() as db:

        await db.execute(
            """
            UPDATE users
            SET full_name=?, phone=?
            WHERE telegram_id=?
            """,
            (
                full_name,
                phone,
                int(user["id"]),
            ),
        )

        await db.commit()

    return json_ok(
        {
            "ok": True
        }
    )


# =========================================================
# DRIVER STATUS
# =========================================================

async def api_driver_status(request):

    user = await require_user(request)

    driver = await get_driver(
        int(user["id"])
    )

    if not driver:

        return json_ok(
            {
                "ok": True,
                "registered": False,
                "status": "not_registered",
            }
        )

    return json_ok(
        {
            "ok": True,
            "registered": True,
            "status": driver["approval_status"],
            "driver": dict(driver),
        }
    )


# =========================================================
# FILE SAVE
# =========================================================

async def save_upload(
    upload,
    folder,
    prefix,
):
    if not upload:
        return ""

    content = await upload.read()

    if not content:
        return ""

    original_name = Path(
        upload.filename or "file"
    ).name

    extension = Path(
        original_name
    ).suffix.lower()

    allowed = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".pdf",
    }

    if extension not in allowed:
        extension = ".bin"

    filename = (
        f"{prefix}_"
        f"{int(time.time() * 1000)}"
        f"{extension}"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = folder / filename

    path.write_bytes(content)

    return str(
        path.relative_to(BASE_DIR)
    )


# =========================================================
# DRIVER REGISTER
# =========================================================

async def api_driver_register(request):

    if request.content_type != "multipart/form-data":
        return error_response(
            "Haydovchi ro‘yxatdan o‘tishda "
            "multipart/form-data kerak.",
            400,
        )

    try:

        reader = await request.multipart()

        fields = {}
        files = {}

        async for part in reader:

            name = part.name

            if not name:
                continue

            if part.filename:

                content = await part.read()

                files[name] = {
                    "filename": part.filename,
                    "content_type": part.headers.get(
                        "Content-Type",
                        "",
                    ),
                    "content": content,
                }

            else:

                value = await part.text()

                fields[name] = value

        init_data = fields.get(
            "init_data",
            "",
        )

        user = validate_init_data(
            init_data
        )

        if not user:
            return error_response(
                "Telegram ma'lumotlari tasdiqlanmadi.",
                401,
            )

        telegram_id = int(
            user["id"]
        )

        full_name = clean_text(
            fields.get("full_name", ""),
            200,
        )

        phone = clean_phone(
            fields.get("phone", "")
        )

        car_model = clean_text(
            fields.get("car_model", ""),
            100,
        )

        car_number = clean_text(
            fields.get("car_number", ""),
            50,
        )

        try:
            seats = int(
                fields.get("seats", "1")
            )
        except Exception:
            seats = 1

        if not full_name:
            return error_response(
                "F.I.Sh. kiritilmagan",
                400,
            )

        if not valid_phone(phone):
            return error_response(
                "Telefon raqami noto‘g‘ri",
                400,
            )

        if not car_model:
            return error_response(
                "Mashina modeli kiritilmagan",
                400,
            )

        if not car_number:
            return error_response(
                "Mashina raqami kiritilmagan",
                400,
            )

        if seats < 1 or seats > 20:
            return error_response(
                "O‘rinlar soni noto‘g‘ri",
                400,
            )

        passport = (
            files.get("passport_file")
            or files.get("passport")
        )

        license_file = (
            files.get("license_file")
            or files.get("license")
        )

        car_doc = (
            files.get("car_registration_file")
            or files.get("car_doc")
        )

        car_photo = (
            files.get("car_photo_file")
            or files.get("car_photo")
        )

        if not passport:
            return error_response(
                "Passport/ID fayli yuborilmagan.",
                400,
            )

        if not license_file:
            return error_response(
                "Haydovchilik guvohnomasi yuborilmagan.",
                400,
            )

        if not car_doc:
            return error_response(
                "Texpasport fayli yuborilmagan.",
                400,
            )

        if not car_photo:
            return error_response(
                "Mashina rasmi yuborilmagan.",
                400,
            )

        await ensure_user(
            telegram_id,
            user.get("username", ""),
            full_name,
            phone,
        )

        folder = (
            UPLOAD_DIR /
            str(telegram_id)
        )

        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        def make_upload_file(data):
            class Upload:
                pass

            obj = Upload()

            obj.filename = data["filename"]

            async def read():
                return data["content"]

            obj.read = read

            return obj

        passport_path = await save_upload(
            make_upload_file(passport),
            folder,
            "passport",
        )

        license_path = await save_upload(
            make_upload_file(license_file),
            folder,
            "license",
        )

        car_doc_path = await save_upload(
            make_upload_file(car_doc),
            folder,
            "car_doc",
        )

        car_photo_path = await save_upload(
            make_upload_file(car_photo),
            folder,
            "car_photo",
        )

        async with await db_connect() as db:

            await db.execute(
                """
                INSERT INTO drivers (
                    telegram_id,
                    full_name,
                    phone,
                    car_model,
                    car_number,
                    seats,

                    passport_file,
                    license_file,
                    car_registration_file,
                    car_photo_file,

                    approval_status,
                    rejection_reason,
                    created_at
                )

                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    'pending',
                    '',
                    ?
                )

                ON CONFLICT(telegram_id)
                DO UPDATE SET

                    full_name=excluded.full_name,
                    phone=excluded.phone,
                    car_model=excluded.car_model,
                    car_number=excluded.car_number,
                    seats=excluded.seats,

                    passport_file=excluded.passport_file,
                    license_file=excluded.license_file,
                    car_registration_file=excluded.car_registration_file,
                    car_photo_file=excluded.car_photo_file,

                    approval_status='pending',
                    rejection_reason='',
                    created_at=excluded.created_at,

                    approved_at=NULL
                """,
                (
                    telegram_id,
                    full_name,
                    phone,
                    car_model,
                    car_number,
                    seats,

                    passport_path,
                    license_path,
                    car_doc_path,
                    car_photo_path,

                    now(),
                ),
            )

            await db.commit()

        # -------------------------------------------------
        # ADMIN TELEGRAM
        # -------------------------------------------------

        admin_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ TASDIQLASH",
                        callback_data=(
                            f"approve_driver:{telegram_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        text="❌ RAD ETISH",
                        callback_data=(
                            f"reject_driver:{telegram_id}"
                        ),
                    ),
                ]
            ]
        )

        admin_text = (
            "🚕 <b>YANGI HAYDOVCHI ARIZASI</b>\n\n"
            f"👤 <b>F.I.Sh:</b> {full_name}\n"
            f"📞 <b>Telefon:</b> {phone}\n"
            f"🚗 <b>Mashina:</b> {car_model}\n"
            f"🔢 <b>Raqam:</b> {car_number}\n"
            f"💺 <b>O‘rin:</b> {seats}\n"
            f"🆔 <b>Telegram ID:</b> {telegram_id}\n\n"
            "Quyidagi tugma orqali qaror qiling."
        )

        try:

            await bot.send_message(
                ADMIN_ID,
                admin_text,
                parse_mode="HTML",
                reply_markup=admin_keyboard,
            )

            saved_files = [
                (
                    "🪪 Passport / ID",
                    passport_path,
                ),
                (
                    "📄 Haydovchilik guvohnomasi",
                    license_path,
                ),
                (
                    "📄 Texpasport",
                    car_doc_path,
                ),
            ]

            for title, relative_path in saved_files:

                if relative_path:

                    absolute = (
                        BASE_DIR /
                        relative_path
                    )

                    if absolute.exists():

                        await bot.send_document(
                            ADMIN_ID,
                            FSInputFile(
                                absolute
                            ),
                            caption=title,
                        )

            if car_photo_path:

                absolute = (
                    BASE_DIR /
                    car_photo_path
                )

                if absolute.exists():

                    try:

                        await bot.send_photo(
                            ADMIN_ID,
                            FSInputFile(
                                absolute
                            ),
                            caption="🚗 Mashina rasmi",
                        )

                    except TelegramBadRequest:

                        await bot.send_document(
                            ADMIN_ID,
                            FSInputFile(
                                absolute
                            ),
                            caption="🚗 Mashina rasmi",
                        )

        except Exception:

            logger.exception(
                "Admin notification error"
            )

        return json_ok(
            {
                "ok": True,
                "status": "pending",
                "message": (
                    "Arizangiz qabul qilindi. "
                    "Admin tasdig‘i kutilmoqda."
                ),
            }
        )

    except Exception as e:

        logger.exception(
            "DRIVER REGISTER ERROR"
        )

        return error_response(
            f"Server xatosi: {str(e)}",
            500,
        )


# =========================================================
# ADMIN INLINE BUTTONS
# =========================================================

@dp.callback_query(
    F.data.startswith("approve_driver:")
)
async def callback_approve_driver(
    callback: CallbackQuery,
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Siz admin emassiz.",
            show_alert=True,
        )

        return

    try:

        telegram_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

        driver = await get_driver(
            telegram_id
        )

        if not driver:

            await callback.answer(
                "Haydovchi topilmadi.",
                show_alert=True,
            )

            return

        await set_driver_status(
            telegram_id,
            "approved",
            "",
        )

        await notify_driver_status(
            telegram_id,
            "approved",
        )

        try:

            await callback.message.edit_reply_markup(
                reply_markup=None
            )

        except Exception:
            pass

        await callback.answer(
            "Haydovchi tasdiqlandi ✅"
        )

        await callback.message.answer(
            f"✅ Haydovchi <b>{telegram_id}</b> tasdiqlandi.",
            parse_mode="HTML",
        )

    except Exception:

        logger.exception(
            "Approve callback error"
        )

        await callback.answer(
            "Xatolik yuz berdi.",
            show_alert=True,
        )


@dp.callback_query(
    F.data.startswith("reject_driver:")
)
async def callback_reject_driver(
    callback: CallbackQuery,
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Siz admin emassiz.",
            show_alert=True,
        )

        return

    try:

        telegram_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

        driver = await get_driver(
            telegram_id
        )

        if not driver:

            await callback.answer(
                "Haydovchi topilmadi.",
                show_alert=True,
            )

            return

        reason = (
            "Admin tomonidan rad etildi."
        )

        await set_driver_status(
            telegram_id,
            "rejected",
            reason,
        )

        await notify_driver_status(
            telegram_id,
            "rejected",
            reason,
        )

        try:

            await callback.message.edit_reply_markup(
                reply_markup=None
            )

        except Exception:
            pass

        await callback.answer(
            "Haydovchi rad etildi ❌"
        )

        await callback.message.answer(
            f"❌ Haydovchi <b>{telegram_id}</b> rad etildi.",
            parse_mode="HTML",
        )

    except Exception:

        logger.exception(
            "Reject callback error"
        )

        await callback.answer(
            "Xatolik yuz berdi.",
            show_alert=True,
        )


# =========================================================
# DRIVER RIDE
# =========================================================

async def api_driver_ride(request):

    user, driver = await require_approved_driver(
        request
    )

    try:
        data = await request.json()
    except Exception:
        return error_response(
            "Noto‘g‘ri JSON",
            400,
        )

    from_city = normalize_city(
        data.get(
            "from_city",
            data.get("from_region", ""),
        )
    )

    to_city = normalize_city(
        data.get(
            "to_city",
            data.get("to_region", ""),
        )
    )

    from_region = clean_text(
        data.get("from_region", from_city),
        100,
    )

    to_region = clean_text(
        data.get("to_region", to_city),
        100,
    )

    from_district = clean_text(
        data.get("from_district", ""),
        100,
    )

    to_district = clean_text(
        data.get("to_district", ""),
        100,
    )

    from_address = clean_text(
        data.get(
            "from_address",
            data.get("address", ""),
        ),
        500,
    )

    to_address = clean_text(
        data.get("to_address", ""),
        500,
    )

    ride_date = clean_text(
        data.get("ride_date", ""),
        30,
    )

    ride_time = clean_text(
        data.get("ride_time", ""),
        30,
    )

    try:
        seats = int(
            data.get("seats", 1)
        )
    except Exception:
        seats = 1

    try:
        price = int(
            data.get("price", 0)
        )
    except Exception:
        price = 0

    if not from_city or not to_city:
        return error_response(
            "Qayerdan va qayerga kiritilishi kerak.",
            400,
        )

    if seats < 1 or seats > driver["seats"]:
        return error_response(
            "O‘rinlar soni noto‘g‘ri.",
            400,
        )

    if price < 0:
        return error_response(
            "Narx noto‘g‘ri.",
            400,
        )

    async with await db_connect() as db:

        await db.execute(
            """
            INSERT INTO rides (
                driver_id,

                from_city,
                to_city,

                from_region,
                from_district,
                from_address,

                to_region,
                to_district,
                to_address,

                ride_date,
                ride_time,

                seats,
                price,

                status,
                created_at
            )

            VALUES (
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                'active',
                ?
            )
            """,
            (
                int(driver["telegram_id"]),

                from_city,
                to_city,

                from_region,
                from_district,
                from_address,

                to_region,
                to_district,
                to_address,

                ride_date,
                ride_time,

                seats,
                price,

                now(),
            ),
        )

        await db.commit()

    return json_ok(
        {
            "ok": True,
            "message": "Safar qo‘shildi.",
        }
    )


# =========================================================
# RIDES SEARCH
# =========================================================

async def api_rides(request):

    await require_user(request)

    from_city = normalize_city(
        request.query.get(
            "from_city",
            request.query.get("from", ""),
        )
    )

    to_city = normalize_city(
        request.query.get(
            "to_city",
            request.query.get("to", ""),
        )
    )

    ride_date = clean_text(
        request.query.get(
            "ride_date",
            request.query.get("date", ""),
        ),
        30,
    )

    ride_time = clean_text(
        request.query.get(
            "ride_time",
            request.query.get("time", ""),
        ),
        30,
    )

    from_district = clean_text(
        request.query.get(
            "from_district",
            "",
        ),
        100,
    )

    to_district = clean_text(
        request.query.get(
            "to_district",
            "",
        ),
        100,
    )

    conditions = [
        "r.status='active'"
    ]

    params = []

    if from_city:
        conditions.append(
            "(r.from_city=? OR r.from_region=?)"
        )

        params.extend([
            from_city,
            from_city,
        ])

    if to_city:
        conditions.append(
            "(r.to_city=? OR r.to_region=?)"
        )

        params.extend([
            to_city,
            to_city,
        ])

    if ride_date:
        conditions.append(
            "r.ride_date=?"
        )

        params.append(
            ride_date
        )

    if ride_time:
        conditions.append(
            "r.ride_time=?"
        )

        params.append(
            ride_time
        )

    if from_district:
        conditions.append(
            "r.from_district=?"
        )

        params.append(
            from_district
        )

    if to_district:
        conditions.append(
            "r.to_district=?"
        )

        params.append(
            to_district
        )

    where = " AND ".join(
        conditions
    )

    async with await db_connect() as db:

        cursor = await db.execute(
            f"""
            SELECT
                r.*,
                d.full_name AS driver_name,
                d.phone AS driver_phone,
                d.car_model,
                d.car_number,

                COALESCE(
                    (
                        SELECT SUM(o.seats)
                        FROM orders o
                        WHERE
                            o.ride_id=r.id
                            AND o.status IN (
                                'pending',
                                'accepted'
                            )
                    ),
                    0
                ) AS booked_seats

            FROM rides r

            JOIN drivers d
                ON d.telegram_id=r.driver_id

            WHERE
                {where}
                AND d.approval_status='approved'

            ORDER BY
                r.ride_date ASC,
                r.ride_time ASC,
                r.created_at DESC

            LIMIT 100
            """,
            params,
        )

        rows = await cursor.fetchall()

    rides = []

    for row in rows:

        item = dict(row)

        booked = int(
            item.get(
                "booked_seats",
                0,
            ) or 0
        )

        total = int(
            item.get(
                "seats",
                0,
            ) or 0
        )

        item["available_seats"] = max(
            total - booked,
            0,
        )

        if item["available_seats"] <= 0:
            continue

        rides.append(item)

    return json_ok(
        {
            "ok": True,
            "rides": rides,
        }
    )


# =========================================================
# DRIVER RIDES
# =========================================================

async def api_driver_rides(request):

    user, driver = await require_approved_driver(
        request
    )

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT
                r.*,

                COALESCE(
                    (
                        SELECT SUM(o.seats)
                        FROM orders o
                        WHERE
                            o.ride_id=r.id
                            AND o.status IN (
                                'pending',
                                'accepted'
                            )
                    ),
                    0
                ) AS booked_seats

            FROM rides r

            WHERE
                r.driver_id=?

            ORDER BY
                r.created_at DESC
            """,
            (
                int(driver["telegram_id"]),
            ),
        )

        rows = await cursor.fetchall()

    rides = []

    for row in rows:

        item = dict(row)

        booked = int(
            item.get(
                "booked_seats",
                0,
            ) or 0
        )

        item["available_seats"] = max(
            int(item["seats"]) - booked,
            0,
        )

        rides.append(item)

    return json_ok(
        {
            "ok": True,
            "rides": rides,
        }
    )


# =========================================================
# PASSENGER ORDER
# =========================================================

async def api_passenger_order(request):

    user = await require_user(request)

    telegram_id = int(
        user["id"]
    )

    try:
        data = await request.json()
    except Exception:
        return error_response(
            "Noto‘g‘ri JSON",
            400,
        )

    try:
        ride_id = int(
            data.get("ride_id", 0)
        )
    except Exception:
        ride_id = 0

    phone = clean_phone(
        data.get(
            "passenger_phone",
            data.get("phone", ""),
        )
    )

    address = clean_text(
        data.get(
            "address",
            data.get("from_address", ""),
        ),
        500,
    )

    try:
        latitude = (
            float(data["latitude"])
            if data.get("latitude") is not None
            else None
        )
    except Exception:
        latitude = None

    try:
        longitude = (
            float(data["longitude"])
            if data.get("longitude") is not None
            else None
        )
    except Exception:
        longitude = None

    try:
        seats = int(
            data.get("seats", 1)
        )
    except Exception:
        seats = 1

    if ride_id <= 0:
        return error_response(
            "Safar tanlanmagan.",
            400,
        )

    if not valid_phone(phone):
        return error_response(
            "Telefon raqami noto‘g‘ri.",
            400,
        )

    if seats < 1:
        return error_response(
            "O‘rinlar soni noto‘g‘ri.",
            400,
        )

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM rides
            WHERE
                id=?
                AND status='active'
            """,
            (ride_id,),
        )

        ride = await cursor.fetchone()

        if not ride:
            return error_response(
                "Safar topilmadi.",
                404,
            )

        if int(ride["driver_id"]) == telegram_id:
            return error_response(
                "O‘zingizning safaringizga "
                "buyurtma bera olmaysiz.",
                400,
            )

        cursor = await db.execute(
            """
            SELECT
                COALESCE(
                    SUM(seats),
                    0
                ) AS booked
            FROM orders
            WHERE
                ride_id=?
                AND status IN (
                    'pending',
                    'accepted'
                )
            """,
            (ride_id,),
        )

        booked_row = await cursor.fetchone()

        booked = int(
            booked_row["booked"] or 0
        )

        available = (
            int(ride["seats"]) - booked
        )

        if seats > available:

            return error_response(
                f"Faqat {available} ta "
                "bo‘sh o‘rin bor.",
                400,
            )

        cursor = await db.execute(
            """
            SELECT id
            FROM orders
            WHERE
                ride_id=?
                AND passenger_id=?
                AND status IN (
                    'pending',
                    'accepted'
                )
            """,
            (
                ride_id,
                telegram_id,
            ),
        )

        existing = await cursor.fetchone()

        if existing:
            return error_response(
                "Bu safarga allaqachon "
                "buyurtma bergansiz.",
                400,
            )

        await db.execute(
            """
            INSERT INTO orders (
                ride_id,
                passenger_id,
                passenger_phone,

                address,
                from_address,

                latitude,
                longitude,

                seats,
                status,
                created_at
            )

            VALUES (
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?,
                'pending',
                ?
            )
            """,
            (
                ride_id,
                telegram_id,
                phone,

                address,
                address,

                latitude,
                longitude,

                seats,

                now(),
            ),
        )

        await db.commit()

    # Driverga xabar
    try:

        await bot.send_message(
            int(ride["driver_id"]),
            (
                "🔔 <b>Yangi yo‘lovchi buyurtmasi!</b>\n\n"
                f"📞 Telefon: {phone}\n"
                f"💺 O‘rin: {seats}\n"
                f"📍 Manzil: {address or 'Ko‘rsatilmagan'}\n\n"
                "Buyurtmani OPER TAXI ilovasidagi "
                "«Buyurtmalarim» bo‘limidan boshqaring."
            ),
            parse_mode="HTML",
        )

        if (
            latitude is not None
            and longitude is not None
        ):

            await bot.send_location(
                int(ride["driver_id"]),
                latitude=latitude,
                longitude=longitude,
            )

    except Exception:

        logger.exception(
            "Driver order notification failed"
        )

    return json_ok(
        {
            "ok": True,
            "message": (
                "Buyurtma yuborildi. "
                "Haydovchi tasdig‘i kutilmoqda."
            ),
        }
    )


# =========================================================
# DRIVER ORDERS
# =========================================================

async def api_driver_orders(request):

    user, driver = await require_approved_driver(
        request
    )

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT
                o.*,

                r.from_city,
                r.to_city,
                r.from_region,
                r.from_district,
                r.to_region,
                r.to_district,
                r.ride_date,
                r.ride_time,
                r.price

            FROM orders o

            JOIN rides r
                ON r.id=o.ride_id

            WHERE
                r.driver_id=?

            ORDER BY
                o.created_at DESC
            """,
            (
                int(driver["telegram_id"]),
            ),
        )

        rows = await cursor.fetchall()

    return json_ok(
        {
            "ok": True,
            "orders": [
                dict(row)
                for row in rows
            ],
        }
    )


# =========================================================
# DRIVER ORDER ACTION
# =========================================================

async def api_driver_order_action(request):

    user, driver = await require_approved_driver(
        request
    )

    try:
        data = await request.json()
    except Exception:
        return error_response(
            "Noto‘g‘ri JSON",
            400,
        )

    try:
        order_id = int(
            data.get("order_id", 0)
        )
    except Exception:
        order_id = 0

    action = clean_text(
        data.get("action", ""),
        30,
    ).lower()

    if order_id <= 0:
        return error_response(
            "Buyurtma topilmadi.",
            400,
        )

    if action not in (
        "accept",
        "reject",
    ):
        return error_response(
            "Action noto‘g‘ri.",
            400,
        )

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT
                o.*,
                r.driver_id,
                r.seats AS ride_seats

            FROM orders o

            JOIN rides r
                ON r.id=o.ride_id

            WHERE
                o.id=?
                AND r.driver_id=?
            """,
            (
                order_id,
                int(driver["telegram_id"]),
            ),
        )

        order = await cursor.fetchone()

        if not order:
            return error_response(
                "Buyurtma topilmadi.",
                404,
            )

        if order["status"] != "pending":
            return error_response(
                "Bu buyurtma allaqachon ko‘rib chiqilgan.",
                400,
            )

        if action == "accept":

            cursor = await db.execute(
                """
                SELECT
                    COALESCE(
                        SUM(seats),
                        0
                    ) AS booked
                FROM orders
                WHERE
                    ride_id=?
                    AND status='accepted'
                """,
                (
                    order["ride_id"],
                ),
            )

            booked_row = await cursor.fetchone()

            booked = int(
                booked_row["booked"] or 0
            )

            if (
                booked + int(order["seats"])
                > int(order["ride_seats"])
            ):
                return error_response(
                    "Bo‘sh joy qolmagan.",
                    400,
                )

            new_status = "accepted"

        else:

            new_status = "rejected"

        await db.execute(
            """
            UPDATE orders
            SET status=?
            WHERE id=?
            """,
            (
                new_status,
                order_id,
            ),
        )

        await db.commit()

    try:

        if new_status == "accepted":

            await bot.send_message(
                int(order["passenger_id"]),
                (
                    "✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
                    "Haydovchi buyurtmangizni tasdiqladi.\n"
                    f"📞 Haydovchi: {driver['phone']}\n"
                    f"🚗 Mashina: {driver['car_model']}\n"
                    f"🔢 Raqam: {driver['car_number']}"
                ),
                parse_mode="HTML",
            )

        else:

            await bot.send_message(
                int(order["passenger_id"]),
                (
                    "❌ Haydovchi buyurtmangizni "
                    "qabul qilmadi."
                ),
            )

    except Exception:

        logger.exception(
            "Passenger notification failed"
        )

    return json_ok(
        {
            "ok": True,
            "status": new_status,
        }
    )


# =========================================================
# PASSENGER ORDERS
# =========================================================

async def api_orders(request):

    user = await require_user(request)

    telegram_id = int(
        user["id"]
    )

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT
                o.*,

                r.from_city,
                r.to_city,
                r.from_region,
                r.from_district,
                r.to_region,
                r.to_district,
                r.ride_date,
                r.ride_time,
                r.price,

                d.full_name AS driver_name,
                d.phone AS driver_phone,
                d.car_model,
                d.car_number

            FROM orders o

            JOIN rides r
                ON r.id=o.ride_id

            LEFT JOIN drivers d
                ON d.telegram_id=r.driver_id

            WHERE
                o.passenger_id=?

            ORDER BY
                o.created_at DESC
            """,
            (
                telegram_id,
            ),
        )

        rows = await cursor.fetchall()

    return json_ok(
        {
            "ok": True,
            "orders": [
                dict(row)
                for row in rows
            ],
        }
    )


# =========================================================
# PASSENGER OPEN REQUEST
# =========================================================

async def api_passenger_request(request):

    user = await require_user(request)

    telegram_id = int(
        user["id"]
    )

    try:
        data = await request.json()
    except Exception:
        return error_response(
            "Noto‘g‘ri JSON",
            400,
        )

    from_city = normalize_city(
        data.get(
            "from_city",
            data.get("from_region", ""),
        )
    )

    to_city = normalize_city(
        data.get(
            "to_city",
            data.get("to_region", ""),
        )
    )

    from_region = clean_text(
        data.get("from_region", from_city),
        100,
    )

    to_region = clean_text(
        data.get("to_region", to_city),
        100,
    )

    from_district = clean_text(
        data.get("from_district", ""),
        100,
    )

    to_district = clean_text(
        data.get("to_district", ""),
        100,
    )

    phone = clean_phone(
        data.get("phone", "")
    )

    comment = clean_text(
        data.get("comment", ""),
        500,
    )

    if not from_city or not to_city:
        return error_response(
            "Yo‘nalish tanlanmagan.",
            400,
        )

    if not valid_phone(phone):
        return error_response(
            "Telefon raqami noto‘g‘ri.",
            400,
        )

    async with await db_connect() as db:

        await db.execute(
            """
            INSERT INTO passenger_requests (
                passenger_id,

                from_city,
                to_city,

                from_region,
                from_district,

                to_region,
                to_district,

                phone,
                comment,

                status,
                created_at
            )

            VALUES (
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                'open',
                ?
            )
            """,
            (
                telegram_id,

                from_city,
                to_city,

                from_region,
                from_district,

                to_region,
                to_district,

                phone,
                comment,

                now(),
            ),
        )

        await db.commit()

    try:

        await bot.send_message(
            ADMIN_ID,
            (
                "📢 <b>YANGI YO‘LOVCHI SO‘ROVI</b>\n\n"
                f"👤 Telegram ID: {telegram_id}\n"
                f"📍 {from_city} / {from_district}\n"
                f"➡️ {to_city} / {to_district}\n"
                f"📞 {phone}\n"
                f"💬 {comment or '-'}"
            ),
            parse_mode="HTML",
        )

    except Exception:

        logger.exception(
            "Passenger request admin notification failed"
        )

    return json_ok(
        {
            "ok": True,
            "message": (
                "So‘rovingiz qabul qilindi."
            ),
        }
    )


# =========================================================
# PASSENGER REQUESTS
# =========================================================

async def api_passenger_requests(request):

    user = await require_user(request)

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM passenger_requests
            WHERE passenger_id=?
            ORDER BY created_at DESC
            """,
            (
                int(user["id"]),
            ),
        )

        rows = await cursor.fetchall()

    return json_ok(
        {
            "ok": True,
            "requests": [
                dict(row)
                for row in rows
            ],
        }
    )


# =========================================================
# CANCEL ORDER / RIDE
# =========================================================

async def api_order_cancel(request):

    user = await require_user(request)

    try:
        data = await request.json()
    except Exception:
        return error_response(
            "Noto‘g‘ri JSON",
            400,
        )

    try:
        order_id = int(
            data.get("order_id", 0)
        )
    except Exception:
        order_id = 0

    if order_id <= 0:
        return error_response(
            "Order ID noto‘g‘ri.",
            400,
        )

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM orders
            WHERE
                id=?
                AND passenger_id=?
            """,
            (
                order_id,
                int(user["id"]),
            ),
        )

        order = await cursor.fetchone()

        if not order:
            return error_response(
                "Buyurtma topilmadi.",
                404,
            )

        if order["status"] not in (
            "pending",
            "accepted",
        ):
            return error_response(
                "Bu buyurtmani bekor qilib bo‘lmaydi.",
                400,
            )

        await db.execute(
            """
            UPDATE orders
            SET status='cancelled'
            WHERE id=?
            """,
            (
                order_id,
            ),
        )

        await db.commit()

    return json_ok(
        {
            "ok": True,
            "status": "cancelled",
        }
    )


# =========================================================
# ADMIN COMMANDS
# =========================================================

@dp.message(Command("admin"))
async def cmd_admin(message: Message):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ Siz admin emassiz."
        )

        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔐 Admin panelini ochish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL.rstrip("/") + "/admin"
                    ),
                )
            ]
        ]
    )

    await message.answer(
        (
            "🔐 <b>OPER TAXI ADMIN</b>\n\n"
            "Admin paneliga kirish uchun "
            "quyidagi tugmani bosing.\n\n"
            "Panel alohida parol bilan himoyalangan."
        ),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@dp.message(Command("approve_driver"))
async def cmd_approve_driver(message: Message):

    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "⛔ Siz admin emassiz."
        )
        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Foydalanish:\n"
            "/approve_driver TELEGRAM_ID"
        )

        return

    try:
        telegram_id = int(parts[1])
    except Exception:

        await message.answer(
            "Telegram ID noto‘g‘ri."
        )

        return

    driver = await get_driver(
        telegram_id
    )

    if not driver:

        await message.answer(
            "Haydovchi topilmadi."
        )

        return

    await set_driver_status(
        telegram_id,
        "approved",
        "",
    )

    await notify_driver_status(
        telegram_id,
        "approved",
    )

    await message.answer(
        "✅ Haydovchi tasdiqlandi."
    )


@dp.message(Command("reject_driver"))
async def cmd_reject_driver(message: Message):

    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "⛔ Siz admin emassiz."
        )
        return

    parts = message.text.split(
        maxsplit=2
    )

    if len(parts) < 2:

        await message.answer(
            "Foydalanish:\n"
            "/reject_driver TELEGRAM_ID [sabab]"
        )

        return

    try:
        telegram_id = int(parts[1])
    except Exception:

        await message.answer(
            "Telegram ID noto‘g‘ri."
        )

        return

    reason = (
        parts[2]
        if len(parts) >= 3
        else "Admin tomonidan rad etildi."
    )

    driver = await get_driver(
        telegram_id
    )

    if not driver:

        await message.answer(
            "Haydovchi topilmadi."
        )

        return

    await set_driver_status(
        telegram_id,
        "rejected",
        reason,
    )

    await notify_driver_status(
        telegram_id,
        "rejected",
        reason,
    )

    await message.answer(
        "❌ Haydovchi rad etildi."
    )


@dp.message(Command("pending_drivers"))
async def cmd_pending_drivers(message: Message):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ Siz admin emassiz."
        )

        return

    async with await db_connect() as db:

        cursor = await db.execute(
            """
            SELECT
                telegram_id,
                full_name,
                phone,
                car_model,
                car_number,
                seats
            FROM drivers
            WHERE approval_status='pending'
            ORDER BY created_at DESC
            """
        )

        rows = await cursor.fetchall()

    if not rows:

        await message.answer(
            "⏳ Kutilayotgan haydovchilar yo‘q."
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
            f"🆔 {row['telegram_id']}\n"
            f"💺 {row['seats']}\n"
            "────────────\n"
        )

    await message.answer(
        text,
        parse_mode="HTML",
    )


# =========================================================
# BOT KEYBOARD
# =========================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🚕 Haydovchi bo‘lish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    ),
                )
            ],
            [
                KeyboardButton(
                    text="👤 Yo‘lovchi bo‘lish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    ),
                )
            ],
            [
                KeyboardButton(
                    text="🔎 Safar qidirish",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    ),
                )
            ],
            [
                KeyboardButton(
                    text="📋 Mening safarlarim",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    ),
                )
            ],
            [
                KeyboardButton(
                    text="👤 Profilim",
                    web_app=WebAppInfo(
                        url=MINI_APP_URL
                    ),
                ),
            ],
            [
                KeyboardButton(
                    text="📞 Yordam",
                )
            ],
        ],
        resize_keyboard=True,
    )


# =========================================================
# START
# =========================================================

@dp.message(Command("start"))
async def cmd_start(message: Message):

    user = message.from_user

    await ensure_user(
        user.id,
        user.username or "",
        (
            f"{user.first_name or ''} "
            f"{user.last_name or ''}"
        ).strip(),
    )

    text = (
        "🚕 <b>OPER TAXI</b>\n\n"
        "Vodiy ↔ Toshkent yo‘nalishlarida "
        "haydovchi va yo‘lovchilarni bog‘laydigan "
        "qulay taxi platforma.\n\n"
        "👇 Quyidagi menyudan kerakli bo‘limni tanlang."
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def cmd_help(message: Message):

    text = (
        "🚕 <b>OPER TAXI — YORDAM</b>\n\n"

        "🚕 <b>Haydovchi bo‘lish</b>\n"
        "Haydovchi sifatida ro‘yxatdan o‘tasiz. "
        "Hujjatlar admin tomonidan tekshiriladi.\n\n"

        "👤 <b>Yo‘lovchi bo‘lish</b>\n"
        "Mavjud safarlardan o‘zingizga mosini "
        "topib buyurtma berasiz.\n\n"

        "🔎 <b>Safar qidirish</b>\n"
        "Viloyat, tuman, sana va vaqt bo‘yicha "
        "safar qidirish mumkin.\n\n"

        "📋 <b>Mening safarlarim</b>\n"
        "Haydovchi sifatida qo‘shgan safarlaringiz.\n\n"

        "📞 <b>Yordam</b>\n"
        "Muammo bo‘lsa admin bilan bog‘laning."
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


# =========================================================
# HELP BUTTON
# =========================================================

@dp.message(
    F.text == "📞 Yordam"
)
async def help_button(message: Message):

    await message.answer(
        (
            "📞 <b>OPER TAXI YORDAM</b>\n\n"
            "Bot yoki buyurtma bilan muammo bo‘lsa "
            "admin bilan bog‘laning.\n\n"
            "🚕 OPER TAXI"
        ),
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


# =========================================================
# FALLBACK
# =========================================================

@dp.message()
async def fallback(message: Message):

    await message.answer(
        (
            "🚕 OPER TAXI\n\n"
            "Kerakli bo‘limni menyudan tanlang.\n"
            "Yordam uchun /help ni bosing."
        ),
        reply_markup=main_keyboard(),
    )


# =========================================================
# HTTP SERVER
# =========================================================

async def health(request):

    return web.json_response(
        {
            "ok": True,
            "service": "OPER TAXI",
            "bot": "running",
            "time": now(),
        }
    )


async def serve_index(request):

    if not INDEX_FILE.exists():

        return web.Response(
            text=(
                "web/index.html topilmadi."
            ),
            status=404,
        )

    return web.FileResponse(
        INDEX_FILE
    )


# =========================================================
# ROUTES
# =========================================================

def create_app():

    app = web.Application(
        client_max_size=25 * 1024 * 1024
    )

    # Health
    app.router.add_get(
        "/health",
        health,
    )

    # Frontend
    app.router.add_get(
        "/",
        serve_index,
    )

    # Admin
    app.router.add_get(
        "/admin",
        admin_page,
    )

    app.router.add_post(
        "/api/admin/login",
        admin_login,
    )

    app.router.add_post(
        "/api/admin/logout",
        admin_logout,
    )

    app.router.add_get(
        "/api/admin/me",
        admin_me,
    )

    app.router.add_get(
        "/api/admin/stats",
        admin_stats,
    )

    app.router.add_get(
        "/api/admin/drivers",
        admin_drivers,
    )

    app.router.add_get(
        "/api/admin/rides",
        admin_rides,
    )

    app.router.add_get(
        "/api/admin/orders",
        admin_orders,
    )

    app.router.add_post(
        "/api/admin/driver/action",
        admin_driver_action,
    )

    # Config / profile
    app.router.add_get(
        "/api/config",
        api_config,
    )

    app.router.add_post(
        "/api/profile",
        api_profile,
    )

    app.router.add_post(
        "/api/profile/update",
        api_profile_update,
    )

    # Driver
    app.router.add_post(
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

    app.router.add_post(
        "/api/driver/rides",
        api_driver_rides,
    )

    app.router.add_post(
        "/api/driver/orders",
        api_driver_orders,
    )

    app.router.add_post(
        "/api/driver/order/action",
        api_driver_order_action,
    )

    # Rides
    app.router.add_get(
        "/api/rides",
        api_rides,
    )

    # Passenger
    app.router.add_post(
        "/api/passenger/order",
        api_passenger_order,
    )

    app.router.add_post(
        "/api/passenger/request",
        api_passenger_request,
    )

    app.router.add_post(
        "/api/passenger/requests",
        api_passenger_requests,
    )

    app.router.add_post(
        "/api/orders",
        api_orders,
    )

    app.router.add_post(
        "/api/order/cancel",
        api_order_cancel,
    )

    # Static web
    if WEB_DIR.exists():

        app.router.add_static(
            "/static/",
            WEB_DIR,
        )

    return app


# =========================================================
# BOT STARTUP
# =========================================================

async def setup_bot():

    commands = [
        {
            "command": "start",
            "description": "OPER TAXI ni ochish",
        },
        {
            "command": "help",
            "description": "Yordam",
        },
    ]

    if ADMIN_ID:
        commands.extend([
            {
                "command": "admin",
                "description": "Admin panel",
            },
            {
                "command": "pending_drivers",
                "description": "Kutilayotgan haydovchilar",
            },
            {
                "command": "approve_driver",
                "description": "Haydovchini tasdiqlash",
            },
            {
                "command": "reject_driver",
                "description": "Haydovchini rad etish",
            },
        ])

    from aiogram.types import BotCommand

    await bot.set_my_commands(
        [
            BotCommand(
                command=item["command"],
                description=item["description"],
            )
            for item in commands
        ]
    )

    try:

        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🚕 OPER TAXI",
                web_app=WebAppInfo(
                    url=MINI_APP_URL
                ),
            )
        )

    except Exception:

        logger.exception(
            "Menu button setup error"
        )


# =========================================================
# MAIN
# =========================================================

async def main():

    logger.info(
        "=========================================="
    )

    logger.info(
        "OPER TAXI STARTING..."
    )

    logger.info(
        "PORT: %s",
        PORT,
    )

    logger.info(
        "MINI APP: %s",
        MINI_APP_URL,
    )

    logger.info(
        "ADMIN ID: %s",
        ADMIN_ID,
    )

    logger.info(
        "ADMIN PASSWORD: %s",
        "SET" if ADMIN_PASSWORD else "NOT SET",
    )

    await init_db()

    await setup_bot()

    app = create_app()

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=PORT,
    )

    await site.start()

    logger.info(
        "WEB SERVER STARTED"
    )

    logger.info(
        "BOT POLLING STARTED"
    )

    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    except Exception:

        logger.exception(
            "BOT POLLING STOPPED"
        )

        raise

    finally:

        await runner.cleanup()

        await bot.session.close()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    import asyncio

    asyncio.run(
        main()
    )
