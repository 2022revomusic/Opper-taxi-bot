from datetime import datetime, timezone

from database.database import execute, fetchone, fetchall


# =========================================================
# OPPER TAXI — RIDES API
# =========================================================

RIDE_ACTIVE = "active"
RIDE_FULL = "full"
RIDE_CANCELLED = "cancelled"
RIDE_FINISHED = "finished"

MIN_SEATS = 1
MAX_SEATS = 4


def now_str():
    return datetime.now(timezone.utc).isoformat()


def valid_seats(seats: int) -> bool:
    return MIN_SEATS <= seats <= MAX_SEATS


async def get_ride_by_id(ride_id: int):
    return await fetchone(
        """
        SELECT
            id,
            driver_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            seats,
            available_seats,
            price,
            status,
            created_at
        FROM rides
        WHERE id = ?
        """,
        (ride_id,),
    )


async def create_ride(
    driver_id: int,
    from_region: str,
    from_district: str,
    to_region: str,
    to_district: str,
    travel_date: str,
    travel_time: str,
    seats: int,
    price: int,
):
    """
    Yangi safar yaratadi.
    """

    if not valid_seats(seats):
        return {
            "success": False,
            "error": "O'rinlar soni 1–4 oralig'ida bo'lishi kerak.",
        }

    if price <= 0:
        return {
            "success": False,
            "error": "Safar narxi noto'g'ri.",
        }

    if not from_region or not from_district:
        return {
            "success": False,
            "error": "Qayerdan ma'lumoti to'liq emas.",
        }

    if not to_region or not to_district:
        return {
            "success": False,
            "error": "Qayerga ma'lumoti to'liq emas.",
        }

    if not travel_date:
        return {
            "success": False,
            "error": "Safar sanasi kiritilmagan.",
        }

    if not travel_time:
        return {
            "success": False,
            "error": "Safar vaqti kiritilmagan.",
        }

    created_at = now_str()

    ride_id = await execute(
        """
        INSERT INTO rides (
            driver_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            seats,
            available_seats,
            price,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            driver_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            seats,
            seats,
            price,
            RIDE_ACTIVE,
            created_at,
        ),
    )

    ride = await get_ride_by_id(ride_id)

    return {
        "success": True,
        "ride": ride,
    }


async def search_rides(
    from_region: str = "",
    from_district: str = "",
    to_region: str = "",
    to_district: str = "",
    travel_date: str = "",
):
    """
    Yo'lovchi uchun faol safarlarni qidiradi.
    Faqat available_seats > 0 bo'lgan safarlar chiqadi.
    """

    query = """
        SELECT
            r.id,
            r.driver_id,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.seats,
            r.available_seats,
            r.price,
            r.status,
            r.created_at,
            u.first_name,
            u.last_name,
            u.username
        FROM rides r
        JOIN drivers d
            ON d.id = r.driver_id
        JOIN users u
            ON u.id = d.user_id
        WHERE r.status = ?
          AND r.available_seats > 0
    """

    params = [RIDE_ACTIVE]

    if from_region:
        query += """
            AND r.from_region = ?
        """
        params.append(from_region)

    if from_district:
        query += """
            AND r.from_district = ?
        """
        params.append(from_district)

    if to_region:
        query += """
            AND r.to_region = ?
        """
        params.append(to_region)

    if to_district:
        query += """
            AND r.to_district = ?
        """
        params.append(to_district)

    if travel_date:
        query += """
            AND r.travel_date = ?
        """
        params.append(travel_date)

    query += """
        ORDER BY
            r.travel_date ASC,
            r.travel_time ASC,
            r.id DESC
    """

    return await fetchall(query, tuple(params))


async def get_driver_rides(driver_id: int):
    """
    Haydovchining barcha safarlari.
    """

    return await fetchall(
        """
        SELECT
            id,
            driver_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            seats,
            available_seats,
            price,
            status,
            created_at
        FROM rides
        WHERE driver_id = ?
        ORDER BY id DESC
        """,
        (driver_id,),
    )


async def get_active_driver_rides(driver_id: int):
    """
    Haydovchining faqat faol safarlari.
    """

    return await fetchall(
        """
        SELECT
            id,
            driver_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            seats,
            available_seats,
            price,
            status,
            created_at
        FROM rides
        WHERE driver_id = ?
          AND status = ?
        ORDER BY
            travel_date ASC,
            travel_time ASC
        """,
        (
            driver_id,
            RIDE_ACTIVE,
        ),
    )


async def update_available_seats(
    ride_id: int,
    available_seats: int,
):
    """
    Safardagi bo'sh o'rinlarni yangilaydi.
    """

    ride = await get_ride_by_id(ride_id)

    if not ride:
        return None

    total_seats = ride[8]

    if available_seats < 0:
        available_seats = 0

    if available_seats > total_seats:
        available_seats = total_seats

    if available_seats == 0:
        status = RIDE_FULL
    else:
        status = RIDE_ACTIVE

    await execute(
        """
        UPDATE rides
        SET
            available_seats = ?,
            status = ?
        WHERE id = ?
        """,
        (
            available_seats,
            status,
            ride_id,
        ),
    )

    return await get_ride_by_id(ride_id)


async def cancel_ride(ride_id: int):
    """
    Safarni bekor qiladi.
    """

    await execute(
        """
        UPDATE rides
        SET
            status = ?
        WHERE id = ?
          AND status = ?
        """,
        (
            RIDE_CANCELLED,
            ride_id,
            RIDE_ACTIVE,
        ),
    )

    return await get_ride_by_id(ride_id)


async def finish_ride(ride_id: int):
    """
    Safarni tugallangan holatga o'tkazadi.
    """

    await execute(
        """
        UPDATE rides
        SET
            status = ?
        WHERE id = ?
          AND status IN (?, ?)
        """,
        (
            RIDE_FINISHED,
            ride_id,
            RIDE_ACTIVE,
            RIDE_FULL,
        ),
    )

    return await get_ride_by_id(ride_id)


async def get_available_rides():
    """
    Barcha faol va bo'sh o'rinli safarlar.
    """

    return await fetchall(
        """
        SELECT
            r.id,
            r.driver_id,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.seats,
            r.available_seats,
            r.price,
            r.status,
            r.created_at,
            u.first_name,
            u.last_name,
            u.username
        FROM rides r
        JOIN drivers d
            ON d.id = r.driver_id
        JOIN users u
            ON u.id = d.user_id
        WHERE r.status = ?
          AND r.available_seats > 0
        ORDER BY
            r.travel_date ASC,
            r.travel_time ASC
        """,
        (RIDE_ACTIVE,),
    )
