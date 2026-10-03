from datetime import datetime, timezone

from database.database import execute, fetchall, fetchone


# =========================================================
# RIDE STATUS
# =========================================================

RIDE_ACTIVE = "active"
RIDE_FULL = "full"
RIDE_CANCELLED = "cancelled"
RIDE_FINISHED = "finished"


# =========================================================
# TIME
# =========================================================

def now_str():
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# CREATE RIDE
# =========================================================

async def create_ride(
    driver_telegram_id: int,
    from_region: str,
    from_district: str,
    to_region: str,
    to_district: str,
    travel_date: str,
    travel_time: str,
    price: int,
    seats: int,
    car_id: int = None,
    note: str = "",
):
    """
    Yangi safar yaratadi.
    """

    created_at = now_str()

    ride_id = await execute(
        """
        INSERT INTO rides (
            driver_telegram_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            price,
            seats,
            available_seats,
            car_id,
            note,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            driver_telegram_id,
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            price,
            seats,
            seats,
            car_id,
            note,
            RIDE_ACTIVE,
            created_at,
            created_at,
        ),
    )

    return await get_ride_by_id(ride_id)


# =========================================================
# GET RIDE
# =========================================================

async def get_ride_by_id(
    ride_id: int,
):
    """
    ID orqali safarni olish.
    """

    return await fetchone(
        """
        SELECT
            r.id,
            r.driver_telegram_id,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price,
            r.seats,
            r.available_seats,
            r.car_id,
            r.note,
            r.status,
            r.created_at,
            r.updated_at,

            u.first_name AS driver_first_name,
            u.last_name AS driver_last_name,
            u.username AS driver_username,
            u.phone AS driver_phone,

            d.full_name AS driver_full_name,
            d.status AS driver_status,

            c.brand AS car_brand,
            c.model AS car_model,
            c.color AS car_color,
            c.plate AS car_plate,
            c.seats AS car_seats

        FROM rides r

        LEFT JOIN users u
            ON u.telegram_id = r.driver_telegram_id

        LEFT JOIN drivers d
            ON d.telegram_id = r.driver_telegram_id

        LEFT JOIN cars c
            ON c.id = r.car_id

        WHERE r.id = ?
        """,
        (ride_id,),
    )


# =========================================================
# SEARCH RIDES
# =========================================================

async def search_rides(
    from_region: str = "",
    from_district: str = "",
    to_region: str = "",
    to_district: str = "",
    travel_date: str = "",
):
    """
    Faol va tasdiqlangan haydovchilarning
    safarlarini qidiradi.
    """

    query = """
        SELECT
            r.id,
            r.driver_telegram_id,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price,
            r.seats,
            r.available_seats,
            r.car_id,
            r.note,
            r.status,
            r.created_at,
            r.updated_at,

            u.first_name AS driver_first_name,
            u.last_name AS driver_last_name,
            u.username AS driver_username,
            u.phone AS driver_phone,

            d.full_name AS driver_full_name,
            d.status AS driver_status,

            c.brand AS car_brand,
            c.model AS car_model,
            c.color AS car_color,
            c.plate AS car_plate,
            c.seats AS car_seats

        FROM rides r

        LEFT JOIN users u
            ON u.telegram_id = r.driver_telegram_id

        LEFT JOIN drivers d
            ON d.telegram_id = r.driver_telegram_id

        LEFT JOIN cars c
            ON c.id = r.car_id

        WHERE
            r.status = ?
            AND r.available_seats > 0
            AND d.status = ?
    """

    params = [
        RIDE_ACTIVE,
        "approved",
    ]

    # -----------------------------------------------------
    # FROM REGION
    # -----------------------------------------------------

    if from_region:
        query += """
            AND r.from_region = ?
        """
        params.append(from_region)

    # -----------------------------------------------------
    # FROM DISTRICT
    # -----------------------------------------------------

    if from_district:
        query += """
            AND r.from_district = ?
        """
        params.append(from_district)

    # -----------------------------------------------------
    # TO REGION
    # -----------------------------------------------------

    if to_region:
        query += """
            AND r.to_region = ?
        """
        params.append(to_region)

    # -----------------------------------------------------
    # TO DISTRICT
    # -----------------------------------------------------

    if to_district:
        query += """
            AND r.to_district = ?
        """
        params.append(to_district)

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    if travel_date:
        query += """
            AND r.travel_date = ?
        """
        params.append(travel_date)

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    query += """
        ORDER BY
            r.travel_date ASC,
            r.travel_time ASC,
            r.id DESC
    """

    return await fetchall(
        query,
        tuple(params),
    )


# =========================================================
# GET DRIVER RIDES
# =========================================================

async def get_driver_rides(
    driver_telegram_id: int,
):
    """
    Haydovchining barcha safarlarini olish.
    """

    return await fetchall(
        """
        SELECT
            r.id,
            r.driver_telegram_id,
            r.from_region,
            r.from_district,
            r.to_region,
            r.to_district,
            r.travel_date,
            r.travel_time,
            r.price,
            r.seats,
            r.available_seats,
            r.car_id,
            r.note,
            r.status,
            r.created_at,
            r.updated_at,

            c.brand AS car_brand,
            c.model AS car_model,
            c.color AS car_color,
            c.plate AS car_plate,
            c.seats AS car_seats

        FROM rides r

        LEFT JOIN cars c
            ON c.id = r.car_id

        WHERE r.driver_telegram_id = ?

        ORDER BY
            r.travel_date DESC,
            r.travel_time DESC,
            r.id DESC
        """,
        (driver_telegram_id,),
    )


# =========================================================
# UPDATE AVAILABLE SEATS
# =========================================================

async def update_available_seats(
    ride_id: int,
    available_seats: int,
):
    """
    Safardagi bo'sh joylar sonini yangilaydi.
    """

    ride = await get_ride_by_id(
        ride_id
    )

    if not ride:
        return None

    total_seats = int(
        ride.get("seats") or 0
    )

    available_seats = max(
        0,
        min(
            available_seats,
            total_seats,
        ),
    )

    status = RIDE_ACTIVE

    if available_seats <= 0:
        status = RIDE_FULL

    await execute(
        """
        UPDATE rides
        SET
            available_seats = ?,
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            available_seats,
            status,
            now_str(),
            ride_id,
        ),
    )

    return await get_ride_by_id(
        ride_id
    )


# =========================================================
# DECREASE SEATS
# =========================================================

async def decrease_available_seats(
    ride_id: int,
    seats: int,
):
    """
    Safardan joy kamaytiradi.
    """

    ride = await get_ride_by_id(
        ride_id
    )

    if not ride:
        return None

    available = int(
        ride.get("available_seats") or 0
    )

    seats = int(seats)

    if seats <= 0:
        return None

    if available < seats:
        return None

    new_available = available - seats

    return await update_available_seats(
        ride_id,
        new_available,
    )


# =========================================================
# INCREASE SEATS
# =========================================================

async def increase_available_seats(
    ride_id: int,
    seats: int,
):
    """
    Bekor qilingan buyurtmadan keyin
    joylarni qaytaradi.
    """

    ride = await get_ride_by_id(
        ride_id
    )

    if not ride:
        return None

    available = int(
        ride.get("available_seats") or 0
    )

    total = int(
        ride.get("seats") or 0
    )

    seats = int(seats)

    if seats <= 0:
        return None

    new_available = min(
        total,
        available + seats,
    )

    return await update_available_seats(
        ride_id,
        new_available,
    )


# =========================================================
# CANCEL RIDE
# =========================================================

async def cancel_ride(
    ride_id: int,
    driver_telegram_id: int,
):
    """
    Haydovchi o'z safarini bekor qiladi.
    """

    ride = await get_ride_by_id(
        ride_id
    )

    if not ride:
        return None

    if int(
        ride.get("driver_telegram_id")
    ) != int(driver_telegram_id):

        return None

    await execute(
        """
        UPDATE rides
        SET
            status = ?,
            updated_at = ?
        WHERE
            id = ?
            AND driver_telegram_id = ?
        """,
        (
            RIDE_CANCELLED,
            now_str(),
            ride_id,
            driver_telegram_id,
        ),
    )

    return await get_ride_by_id(
        ride_id
    )


# =========================================================
# FINISH RIDE
# =========================================================

async def finish_ride(
    ride_id: int,
    driver_telegram_id: int,
):
    """
    Haydovchi safarni tugallangan holatga o'tkazadi.
    """

    ride = await get_ride_by_id(
        ride_id
    )

    if not ride:
        return None

    if int(
        ride.get("driver_telegram_id")
    ) != int(driver_telegram_id):

        return None

    await execute(
        """
        UPDATE rides
        SET
            status = ?,
            updated_at = ?
        WHERE
            id = ?
            AND driver_telegram_id = ?
        """,
        (
            RIDE_FINISHED,
            now_str(),
            ride_id,
            driver_telegram_id,
        ),
    )

    return await get_ride_by_id(
        ride_id
    )


# =========================================================
# UPDATE RIDE
# =========================================================

async def update_ride(
    ride_id: int,
    driver_telegram_id: int,
    from_region: str,
    from_district: str,
    to_region: str,
    to_district: str,
    travel_date: str,
    travel_time: str,
    price: int,
    seats: int,
    note: str = "",
):
    """
    Haydovchi o'z safarini tahrirlaydi.
    """

    ride = await get_ride_by_id(
        ride_id
    )

    if not ride:
        return None

    if int(
        ride.get("driver_telegram_id")
    ) != int(driver_telegram_id):

        return None

    old_seats = int(
        ride.get("seats") or 0
    )

    old_available = int(
        ride.get("available_seats") or 0
    )

    used_seats = max(
        0,
        old_seats - old_available,
    )

    seats = int(seats)

    if seats < used_seats:
        return None

    new_available = seats - used_seats

    status = RIDE_ACTIVE

    if new_available <= 0:
        status = RIDE_FULL

    await execute(
        """
        UPDATE rides
        SET
            from_region = ?,
            from_district = ?,
            to_region = ?,
            to_district = ?,
            travel_date = ?,
            travel_time = ?,
            price = ?,
            seats = ?,
            available_seats = ?,
            note = ?,
            status = ?,
            updated_at = ?
        WHERE
            id = ?
            AND driver_telegram_id = ?
        """,
        (
            from_region,
            from_district,
            to_region,
            to_district,
            travel_date,
            travel_time,
            price,
            seats,
            new_available,
            note,
            status,
            now_str(),
            ride_id,
            driver_telegram_id,
        ),
    )

    return await get_ride_by_id(
        ride_id
    )
