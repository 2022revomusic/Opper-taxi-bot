from pathlib import Path
import aiosqlite


# =========================================================
# DATABASE PATH
# =========================================================

# Muhim:
# Eski ishlab turgan bot.py ham aynan root papkadagi
# oper_taxi.db faylidan foydalanadi.
#
# Shuning uchun yangi database moduli ham shu bazaga ulanadi.
#
# database/database.py
#        ↓
# OPPER TAXI/
#        └── oper_taxi.db

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "oper_taxi.db"


# =========================================================
# CONNECTION
# =========================================================

async def connect_db():
    """
    OPPER TAXI asosiy bazasiga ulanish.
    """
    return await aiosqlite.connect(DB_PATH)


# =========================================================
# EXECUTE
# =========================================================

async def execute(
    query,
    params=(),
):
    """
    INSERT / UPDATE / DELETE uchun.
    """
    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute(
            query,
            params,
        )

        await db.commit()

        lastrowid = cursor.lastrowid

        await cursor.close()

        return lastrowid


# =========================================================
# FETCH ONE
# =========================================================

async def fetchone(
    query,
    params=(),
):
    """
    Bitta qatorni olish.
    """

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            query,
            params,
        )

        row = await cursor.fetchone()

        await cursor.close()

        if row:
            return dict(row)

        return None


# =========================================================
# FETCH ALL
# =========================================================

async def fetchall(
    query,
    params=(),
):
    """
    Bir nechta qatorni olish.
    """

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            query,
            params,
        )

        rows = await cursor.fetchall()

        await cursor.close()

        return [
            dict(row)
            for row in rows
        ]


# =========================================================
# DATABASE INIT
# =========================================================

async def init_database():
    """
    Yangi tizim uchun kerakli jadvallarni mavjud
    oper_taxi.db ichida yaratadi.

    Muhim:
    IF NOT EXISTS ishlatilgani sababli mavjud
    jadvallar o'chirilmaydi.
    """

    async with aiosqlite.connect(DB_PATH) as db:

        # -------------------------------------------------
        # USERS
        # -------------------------------------------------

        await db.execute(
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
            )
            """
        )

        # -------------------------------------------------
        # DRIVERS
        # -------------------------------------------------

        await db.execute(
            """
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
            )
            """
        )

        # -------------------------------------------------
        # CARS
        # -------------------------------------------------

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_telegram_id INTEGER NOT NULL,
                brand TEXT DEFAULT '',
                model TEXT DEFAULT '',
                color TEXT DEFAULT '',
                plate TEXT DEFAULT '',
                seats INTEGER DEFAULT 4,
                created_at TEXT NOT NULL
            )
            """
        )

        # -------------------------------------------------
        # RIDES
        # -------------------------------------------------

        await db.execute(
            """
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
            )
            """
        )

        # -------------------------------------------------
        # ORDERS
        # -------------------------------------------------

        await db.execute(
            """
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
            )
            """
        )

        # -------------------------------------------------
        # RATINGS
        # -------------------------------------------------

        await db.execute(
            """
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
            )
            """
        )

        # -------------------------------------------------
        # NOTIFICATIONS
        # -------------------------------------------------

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                title TEXT DEFAULT '',
                message TEXT DEFAULT '',
                type TEXT DEFAULT 'info',
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

        # -------------------------------------------------
        # PASSENGER REQUESTS
        # -------------------------------------------------

        await db.execute(
            """
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
            )
            """
        )

        # -------------------------------------------------
        # REPORTS
        # -------------------------------------------------

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_telegram_id INTEGER NOT NULL,
                target_telegram_id INTEGER,
                ride_id INTEGER,
                order_id INTEGER,
                reason TEXT DEFAULT '',
                status TEXT DEFAULT 'new',
                created_at TEXT NOT NULL
            )
            """
        )

        # -------------------------------------------------
        # ADMIN ACTIONS
        # -------------------------------------------------

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_telegram_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_telegram_id INTEGER,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

        # -------------------------------------------------
        # INDEXES
        # -------------------------------------------------

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_users_telegram
            ON users(telegram_id)
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_drivers_telegram
            ON drivers(telegram_id)
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_rides_driver
            ON rides(driver_telegram_id)
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_rides_status
            ON rides(status)
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_orders_driver
            ON orders(driver_telegram_id)
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_orders_passenger
            ON orders(passenger_telegram_id)
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notifications_user
            ON notifications(telegram_id)
            """
        )

        await db.commit()


# =========================================================
# DATABASE PATH HELPER
# =========================================================

def get_database_path():
    """
    Boshqa modullar kerak bo'lsa,
    asosiy database manzilini olish uchun.
    """
    return DB_PATH
