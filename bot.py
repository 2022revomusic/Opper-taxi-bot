import os
import asyncio
from datetime import datetime, timedelta

import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB = "oper_taxi.db"


# =========================
# DATABASE
# =========================

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT
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
                seats TEXT,
                price TEXT
            )
        """)

        await db.commit()


# =========================
# MENUS
# =========================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🚕 Haydovchi bo‘lish"),
            KeyboardButton(text="👤 Yo‘lovchi bo‘lish")
        ],
        [
            KeyboardButton(text="🔎 Safar qidirish"),
            KeyboardButton(text="📋 Mening safarlarim")
        ],
        [
            KeyboardButton(text="👤 Profilim"),
            KeyboardButton(text="📞 Yordam")
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
        ]
    ],
    resize_keyboard=True
)


# =========================
# DATE BUTTONS
# =========================

def date_keyboard():
    buttons = []

    for i in range(7):
        date = datetime.now() + timedelta(days=i)
        date_text = date.strftime("%d.%m.%Y")

        buttons.append([
            KeyboardButton(text=date_text)
        ])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


# =========================
# STATES
# =========================

class DriverState(StatesGroup):
    name = State()
    phone = State()
    from_city = State()
    to_city = State()
    date = State()
    time = State()
    car = State()
    seats = State()
    price = State()


class PassengerState(StatesGroup):
    name = State()
    phone = State()
    from_city = State()
    to_city = State()
    date = State()
    time = State()
    passengers = State()


class SearchState(StatesGroup):
    from_city = State()
    to_city = State()
    date = State()


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
            (message.from_user.id,)
        )
        await db.commit()

    await message.answer(
        "🚕 <b>OPER TAXI</b>\n\n"
        "Vodiy ↔ Toshkent yo‘nalishida haydovchi va yo‘lovchilarni bog‘lovchi xizmat.\n\n"
        "Kerakli bo‘limni tanlang 👇",
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================
# DRIVER
# =========================

@dp.message(F.text == "🚕 Haydovchi bo‘lish")
async def driver_start(message: Message, state: FSMContext):
    await state.set_state(DriverState.name)

    await message.answer(
        "🚕 <b>Haydovchi e’loni</b>\n\n"
        "Ismingizni yozing:",
        parse_mode="HTML"
    )


@dp.message(DriverState.name)
async def driver_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)

    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, name)
            VALUES (?, ?)
            ON CONFLICT(telegram_id)
            DO UPDATE SET name = excluded.name
        """, (
            message.from_user.id,
            message.text
        ))
        await db.commit()

    await state.set_state(DriverState.phone)

    await message.answer(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📱 Telefon raqamimni yuborish",
                        request_contact=True
                    )
                ]
            ],
            resize_keyboard=True
        )
    )


@dp.message(DriverState.phone, F.contact)
async def driver_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number

    await state.update_data(phone=phone)

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET phone = ? WHERE telegram_id = ?",
            (phone, message.from_user.id)
        )
        await db.commit()

    await state.set_state(DriverState.from_city)

    await message.answer(
        "📍 Qayerdan yo‘lga chiqasiz?",
        reply_markup=cities
    )


@dp.message(DriverState.phone)
async def driver_phone_text(message: Message, state: FSMContext):
    phone = message.text

    await state.update_data(phone=phone)

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET phone = ? WHERE telegram_id = ?",
            (phone, message.from_user.id)
        )
        await db.commit()

    await state.set_state(DriverState.from_city)

    await message.answer(
        "📍 Qayerdan yo‘lga chiqasiz?",
        reply_markup=cities
    )


@dp.message(DriverState.from_city)
async def driver_from(message: Message, state: FSMContext):
    await state.update_data(from_city=message.text)
    await state.set_state(DriverState.to_city)

    await message.answer(
        "📍 Qayerga borasiz?",
        reply_markup=cities
    )


@dp.message(DriverState.to_city)
async def driver_to(message: Message, state: FSMContext):
    await state.update_data(to_city=message.text)
    await state.set_state(DriverState.date)

    await message.answer(
        "📅 Safar sanasini tanlang:",
        reply_markup=date_keyboard()
    )


@dp.message(DriverState.date)
async def driver_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await state.set_state(DriverState.time)

    await message.answer(
        "⏰ Jo‘nash vaqtini yozing.\n\n"
        "Masalan: 08:00"
    )


@dp.message(DriverState.time)
async def driver_time(message: Message, state: FSMContext):
    await state.update_data(time=message.text)
    await state.set_state(DriverState.car)

    await message.answer(
        "🚗 Mashinangizni yozing.\n\n"
        "Masalan: Cobalt, Nexia 3, Malibu"
    )


@dp.message(DriverState.car)
async def driver_car(message: Message, state: FSMContext):
    await state.update_data(car=message.text)
    await state.set_state(DriverState.seats)

    await message.answer(
        "💺 Nechta bo‘sh joy bor?\n\n"
        "Masalan: 3"
    )


@dp.message(DriverState.seats)
async def driver_seats(message: Message, state: FSMContext):
    await state.update_data(seats=message.text)
    await state.set_state(DriverState.price)

    await message.answer(
        "💰 Bir yo‘lovchi uchun narx qancha?\n\n"
        "Masalan: 150000 so‘m"
    )


@dp.message(DriverState.price)
async def driver_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text)

    data = await state.get_data()

    try:
        driver_seats = int(data["seats"])
    except (ValueError, TypeError):
        await state.clear()

        await message.answer(
            "❗ Bo‘sh joy sonini faqat raqam bilan yozing.\n\n"
            "Masalan: 3",
            reply_markup=main_menu
        )
        return

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            INSERT INTO rides
            (telegram_id, name, phone, role, from_city, to_city,
             date, time, car, seats, price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data["seats"],
            data["price"]
        ))

        await db.commit()

        cursor = await db.execute("""
            SELECT telegram_id, name, phone, from_city, to_city,
                   date, time, seats
            FROM rides
            WHERE role = 'passenger'
            AND from_city = ?
            AND to_city = ?
            AND date = ?
        """, (
            data["from_city"],
            data["to_city"],
            data["date"]
        ))

        all_passengers = await cursor.fetchall()

    passengers = []

    for passenger in all_passengers:
        try:
            passenger_count = int(passenger[7])

            if passenger_count <= driver_seats:
                passengers.append(passenger)

        except (ValueError, TypeError):
            continue

    await state.clear()

    text = (
        "✅ <b>E’loningiz joylandi!</b>\n\n"
        f"🚕 {data['from_city']} → {data['to_city']}\n"
        f"📅 {data['date']}\n"
        f"⏰ {data['time']}\n"
        f"🚗 {data['car']}\n"
        f"💺 Bo‘sh joy: {data['seats']}\n"
        f"💰 Narx: {data['price']}\n"
    )

    if passengers:
        text += "\n👤 <b>Sizga mos yo‘lovchilar:</b>\n\n"

        for i, passenger in enumerate(passengers, 1):
            (
                passenger_id,
                name,
                phone,
                from_city,
                to_city,
                date,
                time,
                passenger_seats
            ) = passenger

            text += (
                f"<b>{i}. {name}</b>\n"
                f"📍 {from_city} → {to_city}\n"
                f"📅 {date} | ⏰ {time}\n"
                f"👥 Yo‘lovchilar: {passenger_seats}\n"
                f"📱 {phone}\n\n"
            )

            try:
                await bot.send_message(
                    passenger_id,
                    "🚕 <b>Sizga mos haydovchi topildi!</b>\n\n"
                    f"📍 {data['from_city']} → {data['to_city']}\n"
                    f"📅 {data['date']}\n"
                    f"⏰ {data['time']}\n"
                    f"🚗 {data['car']}\n"
                    f"💺 Bo‘sh joy: {data['seats']}\n"
                    f"💰 Narx: {data['price']}\n"
                    f"👤 Haydovchi: {data['name']}\n"
                    f"📱 {data['phone']}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    else:
        text += "\n😔 Hozircha shu safarga mos yo‘lovchi topilmadi."

    await message.answer(
        text,
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================
# PASSENGER
# =========================

@dp.message(F.text == "👤 Yo‘lovchi bo‘lish")
async def passenger_start(message: Message, state: FSMContext):
    await state.set_state(PassengerState.name)

    await message.answer(
        "👤 <b>Yo‘lovchi</b>\n\n"
        "Ismingizni yozing:",
        parse_mode="HTML"
    )


@dp.message(PassengerState.name)
async def passenger_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET name = ? WHERE telegram_id = ?",
            (message.text, message.from_user.id)
        )
        await db.commit()

    await state.set_state(PassengerState.phone)

    await message.answer(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📱 Telefon raqamimni yuborish",
                        request_contact=True
                    )
                ]
            ],
            resize_keyboard=True
        )
    )


@dp.message(PassengerState.phone, F.contact)
async def passenger_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number

    await state.update_data(phone=phone)

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET phone = ? WHERE telegram_id = ?",
            (phone, message.from_user.id)
        )
        await db.commit()

    await state.set_state(PassengerState.from_city)

    await message.answer(
        "📍 Qayerdan ketasiz?",
        reply_markup=cities
    )


@dp.message(PassengerState.phone)
async def passenger_phone_text(message: Message, state: FSMContext):
    phone = message.text

    await state.update_data(phone=phone)

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET phone = ? WHERE telegram_id = ?",
            (phone, message.from_user.id)
        )
        await db.commit()

    await state.set_state(PassengerState.from_city)

    await message.answer(
        "📍 Qayerdan ketasiz?",
        reply_markup=cities
    )


@dp.message(PassengerState.from_city)
async def passenger_from(message: Message, state: FSMContext):
    await state.update_data(from_city=message.text)
    await state.set_state(PassengerState.to_city)

    await message.answer(
        "📍 Qayerga borasiz?",
        reply_markup=cities
    )


@dp.message(PassengerState.to_city)
async def passenger_to(message: Message, state: FSMContext):
    await state.update_data(to_city=message.text)
    await state.set_state(PassengerState.date)

    await message.answer(
        "📅 Safar sanasini tanlang:",
        reply_markup=date_keyboard()
    )


@dp.message(PassengerState.date)
async def passenger_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await state.set_state(PassengerState.time)

    await message.answer(
        "⏰ Qaysi vaqtda ketmoqchisiz?\n\n"
        "Masalan: 08:00"
    )


@dp.message(PassengerState.time)
async def passenger_time(message: Message, state: FSMContext):
    await state.update_data(time=message.text)
    await state.set_state(PassengerState.passengers)

    await message.answer(
        "👥 Nechta yo‘lovchi bor?\n\n"
        "Masalan: 2"
    )


# =========================
# PASSENGER FINISH
# =========================

@dp.message(PassengerState.passengers)
async def passenger_finish(message: Message, state: FSMContext):
    await state.update_data(passengers=message.text)

    data = await state.get_data()

    try:
        passenger_count = int(data["passengers"])
    except (ValueError, TypeError):
        await state.clear()

        await message.answer(
            "❗ Yo‘lovchilar sonini faqat raqam bilan yozing.\n\n"
            "Masalan: 2",
            reply_markup=main_menu
        )
        return

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
            INSERT INTO rides
            (telegram_id, name, phone, role, from_city, to_city,
             date, time, seats)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.from_user.id,
            data["name"],
            data["phone"],
            "passenger",
            data["from_city"],
            data["to_city"],
            data["date"],
            data["time"],
            data["passengers"]
        ))

        await db.commit()

        cursor = await db.execute("""
            SELECT telegram_id, name, phone, from_city, to_city,
                   date, time, car, seats, price
            FROM rides
            WHERE role = 'driver'
            AND from_city = ?
            AND to_city = ?
            AND date = ?
        """, (
            data["from_city"],
            data["to_city"],
            data["date"]
        ))

        all_drivers = await cursor.fetchall()

    drivers = []

    for driver in all_drivers:
        try:
            driver_seats = int(driver[8])

            if driver_seats >= passenger_count:
                drivers.append(driver)

        except (ValueError, TypeError):
            continue

    await state.clear()

    if not drivers:
        await message.answer(
            "✅ <b>Safar so‘rovingiz saqlandi!</b>\n\n"
            f"📍 {data['from_city']} → {data['to_city']}\n"
            f"📅 {data['date']}\n"
            f"⏰ {data['time']}\n"
            f"👥 Yo‘lovchilar: {data['passengers']}\n\n"
            "😔 Hozircha sizga mos bo‘sh joyga ega haydovchi topilmadi.\n"
            "Keyinroq yana tekshirib ko‘ring.",
            reply_markup=main_menu,
            parse_mode="HTML"
        )
        return

    text = (
        "✅ <b>Safar so‘rovingiz saqlandi!</b>\n\n"
        f"📍 {data['from_city']} → {data['to_city']}\n"
        f"📅 {data['date']}\n"
        f"⏰ {data['time']}\n"
        f"👥 Yo‘lovchilar: {data['passengers']}\n\n"
        "🚕 <b>Sizga mos haydovchilar:</b>\n\n"
    )

    for i, driver in enumerate(drivers, 1):
        (
            driver_id,
            name,
            phone,
            from_city,
            to_city,
            date,
            time,
            car,
            seats,
            price
        ) = driver

        text += (
            f"<b>{i}. {name}</b>\n"
            f"📍 {from_city} → {to_city}\n"
            f"📅 {date} | ⏰ {time}\n"
            f"🚗 {car}\n"
            f"💺 Bo‘sh joy: {seats}\n"
            f"💰 Narx: {price}\n"
            f"📱 {phone}\n\n"
        )

        try:
            await bot.send_message(
                driver_id,
                "👤 <b>Sizga mos yo‘lovchi topildi!</b>\n\n"
                f"📍 {data['from_city']} → {data['to_city']}\n"
                f"📅 {data['date']}\n"
                f"⏰ {data['time']}\n"
                f"👥 Yo‘lovchilar: {data['passengers']}\n"
                f"👤 Yo‘lovchi: {data['name']}\n"
                f"📱 Telefon: {data['phone']}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await message.answer(
        text,
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================
# SEARCH
# =========================

@dp.message(F.text == "🔎 Safar qidirish")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(SearchState.from_city)

    await message.answer(
        "🔎 <b>Safar qidirish</b>\n\n"
        "📍 Qayerdan?",
        reply_markup=cities,
        parse_mode="HTML"
    )


@dp.message(SearchState.from_city)
async def search_from(message: Message, state: FSMContext):
    await state.update_data(from_city=message.text)
    await state.set_state(SearchState.to_city)

    await message.answer(
        "📍 Qayerga?",
        reply_markup=cities
    )


@dp.message(SearchState.to_city)
async def search_to(message: Message, state: FSMContext):
    await state.update_data(to_city=message.text)
    await state.set_state(SearchState.date)

    keyboard = date_keyboard()

    keyboard.keyboard.append([
        KeyboardButton(text="⬅️ Bekor qilish")
    ])

    await message.answer(
        "📅 Safar sanasini tanlang:",
        reply_markup=keyboard
    )


@dp.message(SearchState.date)
async def search_date(message: Message, state: FSMContext):
    if message.text == "⬅️ Bekor qilish":
        await state.clear()

        await message.answer(
            "Bekor qilindi.",
            reply_markup=main_menu
        )
        return

    data = await state.get_data()

    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("""
            SELECT name, phone, from_city, to_city, date,
                   time, car, seats, price
            FROM rides
            WHERE role = 'driver'
            AND from_city = ?
            AND to_city = ?
            AND date = ?
        """, (
            data["from_city"],
            data["to_city"],
            message.text
        ))

        rides = await cursor.fetchall()

    await state.clear()

    if not rides:
        await message.answer(
            "😔 Hozircha mos haydovchi topilmadi.\n\n"
            "Keyinroq yana tekshirib ko‘ring.",
            reply_markup=main_menu
        )
        return

    text = "🚕 <b>Topilgan haydovchilar:</b>\n\n"

    for i, ride in enumerate(rides, 1):
        (
            name,
            phone,
            from_city,
            to_city,
            date,
            time,
            car,
            seats,
            price
        ) = ride

        text += (
            f"<b>{i}. {name}</b>\n"
            f"📍 {from_city} → {to_city}\n"
            f"📅 {date} | ⏰ {time}\n"
            f"🚗 {car}\n"
            f"💺 Bo‘sh joy: {seats}\n"
            f"💰 {price}\n"
            f"📱 {phone}\n\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu
    )


# =========================
# MY RIDES
# =========================

@dp.message(F.text == "📋 Mening safarlarim")
async def my_rides(message: Message):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("""
            SELECT role, from_city, to_city, date, time,
                   car, seats, price
            FROM rides
            WHERE telegram_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (message.from_user.id,))

        rides = await cursor.fetchall()

    if not rides:
        await message.answer(
            "📋 Sizda hozircha e’lon yoki safar yo‘q.",
            reply_markup=main_menu
        )
        return

    text = "📋 <b>Mening safarlarim:</b>\n\n"

    for ride in rides:
        role, from_city, to_city, date, time, car, seats, price = ride

        icon = "🚕" if role == "driver" else "👤"

        text += (
            f"{icon} {from_city} → {to_city}\n"
            f"📅 {date} | ⏰ {time}\n"
        )

        if role == "driver":
            text += (
                f"🚗 {car}\n"
                f"💺 {seats} | 💰 {price}\n\n"
            )
        else:
            text += f"👥 {seats}\n\n"

    await message.answer(
        text,
        reply_markup=main_menu
    )


# =========================
# PROFILE
# =========================

@dp.message(F.text == "👤 Profilim")
async def profile(message: Message):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT name, phone FROM users WHERE telegram_id = ?",
            (message.from_user.id,)
        )

        user = await cursor.fetchone()

    if not user:
        await message.answer(
            "Profil topilmadi.",
            reply_markup=main_menu
        )
        return

    name, phone = user

    await message.answer(
        "👤 <b>Profilim</b>\n\n"
        f"👤 Ism: {name or 'Kiritilmagan'}\n"
        f"📱 Telefon: {phone or 'Kiritilmagan'}",
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================
# HELP
# =========================

@dp.message(F.text == "📞 Yordam")
async def help_message(message: Message):
    await message.answer(
        "📞 <b>OPER TAXI yordam</b>\n\n"
        "🚕 Haydovchi bo‘lsangiz — «Haydovchi bo‘lish»ni tanlang.\n"
        "👤 Yo‘lovchi bo‘lsangiz — «Yo‘lovchi bo‘lish»ni tanlang.\n"
        "🔎 Kerakli yo‘nalish bo‘yicha safar qidiring.\n\n"
        "Savollar bo‘lsa, bot administratori bilan bog‘laning.",
        reply_markup=main_menu,
        parse_mode="HTML"
    )


# =========================
# START BOT
# =========================

async def main():
    await init_db()

    print("OPER TAXI bot ishga tushdi...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
