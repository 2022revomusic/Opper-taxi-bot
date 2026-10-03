from datetime import datetime, timezone

from database.database import execute, fetchall, fetchone


# =========================================================
# ORDER STATUS
# =========================================================

ORDER_PENDING = "pending"
ORDER_ACCEPTED = "accepted"
ORDER_REJECTED = "rejected"
ORDER_CANCELLED = "cancelled"
ORDER_FINISHED = "finished"


# =========================================================
# TIME
# =========================================================

def now_str():
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# GET ORDER
# =========================================================

async def get_order_by_id(
    order_id: int,
):
    """
    Buyurtmani ID orqali olish.
    """

    return await fetchone(
        """
        SELECT
            o.id,
            o.ride_id,
            o.passenger_telegram_id,
            o.driver_telegram_id,
            o.seats,
            o.phone,
            o.note,
            o.status,
            o.created_at,
            o.updated_at,

            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price,
            r.available_seats,
            r.status AS ride_status,

            pu.first_name AS passenger_first_name,
            pu.last_name AS passenger_last_name,
            pu.username AS passenger_username,

            du.first_name AS driver_first_name,
            du.last_name AS driver_last_name,
            du.username AS driver_username,

            d.full_name AS driver_full_name

        FROM orders o

        LEFT JOIN rides r
            ON r.id = o.ride_id

        LEFT JOIN users pu
            ON pu.telegram_id = o.passenger_telegram_id

        LEFT JOIN users du
            ON du.telegram_id = o.driver_telegram_id

        LEFT JOIN drivers d
            ON d.telegram_id = o.driver_telegram_id

        WHERE o.id = ?
        """,
        (order_id,),
    )


# =========================================================
# CREATE ORDER
# =========================================================

async def create_order(
    ride_id: int,
    passenger_telegram_id: int,
    driver_telegram_id: int,
    seats: int = 1,
    phone: str = "",
    note: str = "",
):
    """
    Yo'lovchi safarga buyurtma beradi.
    """

    seats = int(seats)

    if seats < 1 or seats > 4:
        return {
            "success": False,
            "error": "invalid_seats",
        }

    # -----------------------------------------------------
    # SAFARNI TEKSHIRISH
    # -----------------------------------------------------

    ride = await fetchone(
        """
        SELECT
            id,
            driver_telegram_id,
            available_seats,
            status
        FROM rides
        WHERE id = ?
        """,
        (ride_id,),
    )

    if not ride:
        return {
            "success": False,
            "error": "ride_not_found",
        }

    if ride["status"] != "active":
        return {
            "success": False,
            "error": "ride_not_active",
        }

    if int(ride["available_seats"]) < seats:
        return {
            "success": False,
            "error": "not_enough_seats",
        }

    # -----------------------------------------------------
    # DRIVER ID
    # -----------------------------------------------------

    real_driver_id = int(
        ride["driver_telegram_id"]
    )

    # Frontend yuborgan driver ID noto'g'ri bo'lsa,
    # safarning haqiqiy driver ID'sidan foydalanamiz.
    driver_telegram_id = real_driver_id

    # -----------------------------------------------------
    # TAKRORIY BUYURTMA
    # -----------------------------------------------------

    existing = await fetchone(
        """
        SELECT
            id,
            status
        FROM orders
        WHERE
            ride_id = ?
            AND passenger_telegram_id = ?
            AND status IN (?, ?)
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            ride_id,
            passenger_telegram_id,
            ORDER_PENDING,
            ORDER_ACCEPTED,
        ),
    )

    if existing:
        return {
            "success": False,
            "error": "already_ordered",
            "order": await get_order_by_id(
                existing["id"]
            ),
        }

    # -----------------------------------------------------
    # BUYURTMA YARATISH
    # -----------------------------------------------------

    created_at = now_str()

    order_id = await execute(
        """
        INSERT INTO orders (
            ride_id,
            passenger_telegram_id,
            driver_telegram_id,
            seats,
            phone,
            note,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ride_id,
            passenger_telegram_id,
            driver_telegram_id,
            seats,
            phone,
            note,
            ORDER_PENDING,
            created_at,
            created_at,
        ),
    )

    return {
        "success": True,
        "order": await get_order_by_id(
            order_id
        ),
    }


# =========================================================
# PASSENGER ORDERS
# =========================================================

async def get_passenger_orders(
    passenger_telegram_id: int,
):
    """
    Yo'lovchining buyurtmalari.
    """

    return await fetchall(
        """
        SELECT
            o.id,
            o.ride_id,
            o.passenger_telegram_id,
            o.driver_telegram_id,
            o.seats,
            o.phone,
            o.note,
            o.status,
            o.created_at,
            o.updated_at,

            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price,
            r.available_seats,
            r.status AS ride_status,

            du.first_name AS driver_first_name,
            du.last_name AS driver_last_name,
            du.username AS driver_username,

            d.full_name AS driver_full_name

        FROM orders o

        LEFT JOIN rides r
            ON r.id = o.ride_id

        LEFT JOIN users du
            ON du.telegram_id = o.driver_telegram_id

        LEFT JOIN drivers d
            ON d.telegram_id = o.driver_telegram_id

        WHERE o.passenger_telegram_id = ?

        ORDER BY
            o.id DESC
        """,
        (passenger_telegram_id,),
    )


# =========================================================
# DRIVER ORDERS
# =========================================================

async def get_driver_orders(
    driver_telegram_id: int,
):
    """
    Haydovchining buyurtmalari.
    """

    return await fetchall(
        """
        SELECT
            o.id,
            o.ride_id,
            o.passenger_telegram_id,
            o.driver_telegram_id,
            o.seats,
            o.phone,
            o.note,
            o.status,
            o.created_at,
            o.updated_at,

            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price,
            r.available_seats,
            r.status AS ride_status,

            pu.first_name AS passenger_first_name,
            pu.last_name AS passenger_last_name,
            pu.username AS passenger_username,
            pu.phone AS passenger_profile_phone

        FROM orders o

        LEFT JOIN rides r
            ON r.id = o.ride_id

        LEFT JOIN users pu
            ON pu.telegram_id = o.passenger_telegram_id

        WHERE o.driver_telegram_id = ?

        ORDER BY
            o.id DESC
        """,
        (driver_telegram_id,),
    )


# =========================================================
# ACCEPT ORDER
# =========================================================

async def accept_order(
    order_id: int,
    driver_telegram_id: int,
):
    """
    Haydovchi buyurtmani qabul qiladi.

    Muhim:
    BEGIN IMMEDIATE orqali parallel buyurtmalarda
    joylar noto'g'ri hisoblanishining oldini oladi.
    """

    async with __import__(
        "aiosqlite"
    ).connect(
        __import__(
            "database.database",
            fromlist=["DB_PATH"]
        ).DB_PATH
    ) as db:

        db.row_factory = __import__(
            "aiosqlite"
        ).Row

        try:

            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                SELECT
                    o.id,
                    o.ride_id,
                    o.seats,
                    o.status,
                    o.driver_telegram_id,

                    r.available_seats,
                    r.status AS ride_status

                FROM orders o

                JOIN rides r
                    ON r.id = o.ride_id

                WHERE
                    o.id = ?
                    AND o.driver_telegram_id = ?

                LIMIT 1
                """,
                (
                    order_id,
                    driver_telegram_id,
                ),
            )

            order = await cursor.fetchone()

            if not order:
                await db.rollback()

                return {
                    "success": False,
                    "error": "order_not_found",
                }

            if order["status"] != ORDER_PENDING:
                await db.rollback()

                return {
                    "success": False,
                    "error": "order_not_pending",
                }

            if order["ride_status"] not in (
                "active",
                "full",
            ):
                await db.rollback()

                return {
                    "success": False,
                    "error": "ride_not_active",
                }

            requested_seats = int(
                order["seats"]
            )

            available_seats = int(
                order["available_seats"]
            )

            if available_seats < requested_seats:
                await db.rollback()

                return {
                    "success": False,
                    "error": "not_enough_seats",
                }

            new_available = (
                available_seats
                - requested_seats
            )

            new_ride_status = (
                ORDER_ACCEPTED
                if new_available > 0
                else "full"
            )

            # -------------------------------------------------
            # UPDATE RIDE
            # -------------------------------------------------

            await db.execute(
                """
                UPDATE rides
                SET
                    available_seats = ?,
                    status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    new_available,
                    new_ride_status,
                    now_str(),
                    order["ride_id"],
                ),
            )

            # -------------------------------------------------
            # ACCEPT ORDER
            # -------------------------------------------------

            await db.execute(
                """
                UPDATE orders
                SET
                    status = ?,
                    updated_at = ?
                WHERE
                    id = ?
                    AND driver_telegram_id = ?
                """,
                (
                    ORDER_ACCEPTED,
                    now_str(),
                    order_id,
                    driver_telegram_id,
                ),
            )

            await db.commit()

        except Exception:

            await db.rollback()
            raise

    return {
        "success": True,
        "order": await get_order_by_id(
            order_id
        ),
    }


# =========================================================
# REJECT ORDER
# =========================================================

async def reject_order(
    order_id: int,
    driver_telegram_id: int,
):
    """
    Haydovchi buyurtmani rad etadi.
    """

    order = await fetchone(
        """
        SELECT
            id,
            status
        FROM orders
        WHERE
            id = ?
            AND driver_telegram_id = ?
        """,
        (
            order_id,
            driver_telegram_id,
        ),
    )

    if not order:
        return None

    if order["status"] != ORDER_PENDING:
        return await get_order_by_id(
            order_id
        )

    await execute(
        """
        UPDATE orders
        SET
            status = ?,
            updated_at = ?
        WHERE
            id = ?
            AND driver_telegram_id = ?
        """,
        (
            ORDER_REJECTED,
            now_str(),
            order_id,
            driver_telegram_id,
        ),
    )

    return await get_order_by_id(
        order_id
    )


# =========================================================
# CANCEL ORDER
# =========================================================

async def cancel_order(
    order_id: int,
    telegram_id: int,
):
    """
    Yo'lovchi yoki haydovchi buyurtmani bekor qiladi.

    Agar buyurtma accepted bo'lsa,
    joy safarga qaytariladi.
    """

    async with __import__(
        "aiosqlite"
    ).connect(
        __import__(
            "database.database",
            fromlist=["DB_PATH"]
        ).DB_PATH
    ) as db:

        db.row_factory = __import__(
            "aiosqlite"
        ).Row

        try:

            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                SELECT
                    o.id,
                    o.ride_id,
                    o.seats,
                    o.status,
                    o.passenger_telegram_id,
                    o.driver_telegram_id,

                    r.available_seats,
                    r.seats AS total_seats

                FROM orders o

                JOIN rides r
                    ON r.id = o.ride_id

                WHERE o.id = ?

                LIMIT 1
                """,
                (order_id,),
            )

            order = await cursor.fetchone()

            if not order:
                await db.rollback()

                return {
                    "success": False,
                    "error": "order_not_found",
                }

            is_passenger = (
                int(
                    order["passenger_telegram_id"]
                )
                == int(telegram_id)
            )

            is_driver = (
                int(
                    order["driver_telegram_id"]
                )
                == int(telegram_id)
            )

            if not (
                is_passenger
                or is_driver
            ):
                await db.rollback()

                return {
                    "success": False,
                    "error": "not_allowed",
                }

            if order["status"] in (
                ORDER_CANCELLED,
                ORDER_REJECTED,
                ORDER_FINISHED,
            ):
                await db.rollback()

                return {
                    "success": False,
                    "error": "already_closed",
                }

            # -------------------------------------------------
            # QABUL QILINGAN BUYURTMA
            # -------------------------------------------------

            if order["status"] == ORDER_ACCEPTED:

                available = int(
                    order["available_seats"]
                )

                total = int(
                    order["total_seats"]
                )

                restored = min(
                    total,
                    available
                    + int(order["seats"]),
                )

                ride_status = (
                    "full"
                    if restored <= 0
                    else "active"
                )

                await db.execute(
                    """
                    UPDATE rides
                    SET
                        available_seats = ?,
                        status = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        restored,
                        ride_status,
                        now_str(),
                        order["ride_id"],
                    ),
                )

            # -------------------------------------------------
            # CANCEL ORDER
            # -------------------------------------------------

            await db.execute(
                """
                UPDATE orders
                SET
                    status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    ORDER_CANCELLED,
                    now_str(),
                    order_id,
                ),
            )

            await db.commit()

        except Exception:

            await db.rollback()
            raise

    return {
        "success": True,
        "order": await get_order_by_id(
            order_id
        ),
    }


# =========================================================
# FINISH ORDER
# =========================================================

async def finish_order(
    order_id: int,
    telegram_id: int,
):
    """
    Buyurtmani tugallangan holatga o'tkazadi.
    """

    order = await fetchone(
        """
        SELECT
            id,
            passenger_telegram_id,
            driver_telegram_id,
            status
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    )

    if not order:
        return None

    allowed = (
        int(
            order["passenger_telegram_id"]
        )
        == int(telegram_id)
        or
        int(
            order["driver_telegram_id"]
        )
        == int(telegram_id)
    )

    if not allowed:
        return None

    if order["status"] != ORDER_ACCEPTED:
        return await get_order_by_id(
            order_id
        )

    await execute(
        """
        UPDATE orders
        SET
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            ORDER_FINISHED,
            now_str(),
            order_id,
        ),
    )

    return await get_order_by_id(
        order_id
    )


# =========================================================
# GET ACTIVE ORDERS FOR RIDE
# =========================================================

async def get_ride_orders(
    ride_id: int,
):
    """
    Bitta safarga tegishli buyurtmalar.
    """

    return await fetchall(
        """
        SELECT
            o.id,
            o.ride_id,
            o.passenger_telegram_id,
            o.driver_telegram_id,
            o.seats,
            o.phone,
            o.note,
            o.status,
            o.created_at,
            o.updated_at,

            u.first_name AS passenger_first_name,
            u.last_name AS passenger_last_name,
            u.username AS passenger_username,
            u.phone AS passenger_profile_phone

        FROM orders o

        LEFT JOIN users u
            ON u.telegram_id = o.passenger_telegram_id

        WHERE o.ride_id = ?

        ORDER BY
            o.id DESC
        """,
        (ride_id,),
    )
