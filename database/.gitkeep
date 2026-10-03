from pathlib import Path
import aiosqlite


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "oper_taxi.db"


async def connect_db():
    return await aiosqlite.connect(DB_PATH)


async def execute(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid


async def fetchone(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        return row


async def fetchall(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return rows


async def init_database():
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                username TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                phone TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                car_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER NOT NULL,
                from_region TEXT NOT NULL,
                from_district TEXT NOT NULL,
                to_region TEXT NOT NULL,
                to_district TEXT NOT NULL,
                travel_date TEXT NOT NULL,
                travel_time TEXT NOT NULL,
                seats INTEGER NOT NULL,
                available_seats INTEGER NOT NULL,
                price INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (driver_id) REFERENCES drivers(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER NOT NULL,
                passenger_id INTEGER NOT NULL,
                seats INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (ride_id) REFERENCES rides(id),
                FOREIGN KEY (passenger_id) REFERENCES users(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ride_id INTEGER NOT NULL,
                order_id INTEGER,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (ride_id) REFERENCES rides(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_telegram
            ON users(telegram_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_drivers_user
            ON drivers(user_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rides_driver
            ON rides(driver_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rides_status
            ON rides(status)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_ride
            ON orders(ride_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_passenger
            ON orders(passenger_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_user
            ON notifications(user_id)
        """)

        await db.commit()
