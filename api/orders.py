from datetime import datetime, timezone

from database.database import execute, fetchone, fetchall


# =========================================================
# OPPER TAXI — ORDERS API
# =========================================================

ORDER_PENDING = "pending"
ORDER_ACCEPTED = "accepted"
ORDER_REJECTED = "rejected"
ORDER_CANCELLED = "cancelled"
ORDER_FINISHED = "finished"


def now_str():
    return datetime.now(timezone.utc).isoformat()


async def get_order_by_id(order_id: int):
    return await fetchone(
        """
        SELECT
            id,
            ride_id,
            passenger_id,
            seats,
            status,
            created_at,
            updated_at
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    )


async def get_pending_order_for_passenger(
    ride_id: int,
    passenger_id: int,
):
    return await fetchone(
        """
        SELECT
            id,
            ride_id,
            passenger_id,
            seats,
            status,
            created_at,
            updated_at
        FROM orders
        WHERE ride_id = ?
          AND passenger_id = ?
          AND status = ?
        LIMIT 1
        """,
        (
            ride_id,
            passenger_id,
            ORDER_PENDING,
        ),
    )


async def create_order(
    ride_id: int,
    passenger_id: int,
    seats: int = 1,
):
    """
    Yo'lovchi safarga buyurtma beradi.
    """

    if seats < 1:
        return {
            "success": False,
            "error": "O'rinlar soni kamida 1 ta bo'lishi kerak.",
        }

    ride = await fetchone(
        """
        SELECT
            id,
            driver_id,
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
            "error": "Safar topilmadi.",
        }

    driver_id = ride[1]
    available_seats = ride[2]
    ride_status = ride[3]

    if ride_status != "active":
        return {
            "success": False,
            "error": "Bu safar hozir faol emas.",
        }

    if available_seats < seats:
        return {
            "success": False,
            "error": "Yetarli bo'sh o'rin mavjud emas.",
        }

    # Haydovchining o'z safariga o'zi buyurtma bera olmaydi.
    driver_user = await fetchone(
        """
        SELECT user_id
        FROM drivers
        WHERE id = ?
        """,
        (driver_id,),
    )

    if driver_user and driver_user[0] == passenger_id:
        return {
            "success": False,
            "error": "Haydovchi o'z safariga buyurtma bera olmaydi.",
        }

    # Bir xil safarga bir foydalanuvchi qayta-qayta
    # pending buyurtma yubora olmaydi.
    existing = await get_pending_order_for_passenger(
        ride_id,
        passenger_id,
    )

    if existing:
        return {
            "success": False,
            "error": "Siz bu safarga allaqachon buyurtma yuborgansiz.",
            "order": existing,
        }

    created_at = now_str()

    order_id = await execute(
        """
        INSERT INTO orders (
            ride_id,
            passenger_id,
            seats,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ride_id,
            passenger_id,
            seats,
            ORDER_PENDING,
            created_at,
            created_at,
        ),
    )

    order = await get_order_by_id(order_id)

    return {
        "success": True,
        "order": order,
    }


async def get_driver_orders(driver_id: int):
    """
    Haydovchining barcha buyurtmalarini chiqaradi.
    """

    return await fetchall(
        """
        SELECT
            o.id,
            o.ride_id,
            o.passenger_id,
            o.seats,
            o.status,
            o.created_at,
            o.updated_at,
            u.first_name,
            u.last_name,
            u.username,
            u.phone,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        JOIN drivers d
            ON d.id = r.driver_id
        JOIN users u
            ON u.id = o.passenger_id
        WHERE d.id = ?
        ORDER BY o.id DESC
        """,
        (driver_id,),
    )


async def get_passenger_orders(passenger_id: int):
    """
    Yo'lovchining barcha buyurtmalari.
    """

    return await fetchall(
        """
        SELECT
            o.id,
            o.ride_id,
            o.passenger_id,
            o.seats,
            o.status,
            o.created_at,
            o.updated_at,
            r.driver_id,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price
        FROM orders o
        JOIN rides r
            ON r.id = o.ride_id
        WHERE o.passenger_id = ?
        ORDER BY o.id DESC
        """,
        (passenger_id,),
    )


async def accept_order(order_id: int):
    """
    Haydovchi buyurtmani qabul qiladi.

    Qabul qilinganda safardagi bo'sh o'rinlar kamayadi.
    """

    order = await get_order_by_id(order_id)

    if not order:
        return {
            "success": False,
            "error": "Buyurtma topilmadi.",
        }

    if order[4] != ORDER_PENDING:
        return {
            "success": False,
            "error": "Bu buyurtma endi pending holatda emas.",
        }

    ride_id = order[1]
    requested_seats = order[3]

    ride = await fetchone(
        """
        SELECT
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
            "error": "Safar topilmadi.",
        }

    available_seats = ride[0]
    ride_status = ride[1]

    if ride_status != "active":
        return {
            "success": False,
            "error": "Safar faol emas.",
        }

    if available_seats < requested_seats:
        return {
            "success": False,
            "error": "Bo'sh o'rin yetarli emas.",
        }

    new_available_seats = available_seats - requested_seats

    new_ride_status = (
        "full"
        if new_available_seats == 0
        else "active"
    )

    updated_at = now_str()

    await execute(
        """
        UPDATE orders
        SET
            status = ?,
            updated_at = ?
        WHERE id = ?
          AND status = ?
        """,
        (
            ORDER_ACCEPTED,
            updated_at,
            order_id,
            ORDER_PENDING,
        ),
    )

    await execute(
        """
        UPDATE rides
        SET
            available_seats = ?,
            status = ?
        WHERE id = ?
        """,
        (
            new_available_seats,
            new_ride_status,
            ride_id,
        ),
    )

    return {
        "success": True,
        "order": await get_order_by_id(order_id),
    }


async def reject_order(order_id: int):
    """
    Haydovchi buyurtmani rad etadi.
    """

    order = await get_order_by_id(order_id)

    if not order:
        return {
            "success": False,
            "error": "Buyurtma topilmadi.",
        }

    if order[4] != ORDER_PENDING:
        return {
            "success": False,
            "error": "Bu buyurtma endi pending holatda emas.",
        }

    await execute(
        """
        UPDATE orders
        SET
            status = ?,
            updated_at = ?
        WHERE id = ?
          AND status = ?
        """,
        (
            ORDER_REJECTED,
            now_str(),
            order_id,
            ORDER_PENDING,
        ),
    )

    return {
        "success": True,
        "order": await get_order_by_id(order_id),
    }


async def cancel_order(order_id: int):
    """
    Buyurtmani bekor qiladi.

    Agar buyurtma oldin qabul qilingan bo'lsa,
    bo'sh o'rin qayta tiklanadi.
    """

    order = await get_order_by_id(order_id)

    if not order:
        return {
            "success": False,
            "error": "Buyurtma topilmadi.",
        }

    current_status = order[4]

    if current_status in {
        ORDER_CANCELLED,
        ORDER_REJECTED,
        ORDER_FINISHED,
    }:
        return {
            "success": False,
            "error": "Bu buyurtmani bekor qilib bo'lmaydi.",
        }

    ride_id = order[1]
    seats = order[3]

    if current_status == ORDER_ACCEPTED:

        ride = await fetchone(
            """
            SELECT
                available_seats,
                seats
            FROM rides
            WHERE id = ?
            """,
            (ride_id,),
        )

        if ride:

            available_seats = ride[0]
            total_seats = ride[1]

            restored_seats = min(
                available_seats + seats,
                total_seats,
            )

            ride_status = (
                "active"
                if restored_seats > 0
                else "full"
            )

            await execute(
                """
                UPDATE rides
                SET
                    available_seats = ?,
                    status = ?
                WHERE id = ?
                """,
                (
                    restored_seats,
                    ride_status,
                    ride_id,
                ),
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
            ORDER_CANCELLED,
            now_str(),
            order_id,
        ),
    )

    return {
        "success": True,
        "order": await get_order_by_id(order_id),
    }


async def finish_order(order_id: int):
    """
    Buyurtmani tugallangan holatga o'tkazadi.
    """

    order = await get_order_by_id(order_id)

    if not order:
        return {
            "success": False,
            "error": "Buyurtma topilmadi.",
        }

    if order[4] != ORDER_ACCEPTED:
        return {
            "success": False,
            "error": "Faqat qabul qilingan buyurtma tugatiladi.",
        }

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

    return {
        "success": True,
        "order": await get_order_by_id(order_id),
    }
