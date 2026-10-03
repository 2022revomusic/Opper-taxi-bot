from datetime import datetime, timezone

from database.database import execute, fetchone, fetchall


def now_str():
    return datetime.now(timezone.utc).isoformat()


def valid_rating(rating: int) -> bool:
    return 1 <= rating <= 5


async def get_rating_by_id(rating_id: int):
    return await fetchone(
        """
        SELECT
            id,
            ride_id,
            order_id,
            from_user_id,
            to_user_id,
            rating,
            comment,
            created_at
        FROM ratings
        WHERE id = ?
        """,
        (rating_id,),
    )


async def get_existing_rating(
    order_id: int,
    from_user_id: int,
    to_user_id: int,
):
    return await fetchone(
        """
        SELECT
            id,
            ride_id,
            order_id,
            from_user_id,
            to_user_id,
            rating,
            comment,
            created_at
        FROM ratings
        WHERE order_id = ?
          AND from_user_id = ?
          AND to_user_id = ?
        LIMIT 1
        """,
        (
            order_id,
            from_user_id,
            to_user_id,
        ),
    )


async def create_rating(
    ride_id: int,
    order_id: int,
    from_user_id: int,
    to_user_id: int,
    rating: int,
    comment: str = "",
):
    if not valid_rating(rating):
        return {
            "success": False,
            "error": "Baho 1 dan 5 gacha bo'lishi kerak.",
        }

    if from_user_id == to_user_id:
        return {
            "success": False,
            "error": "O'zingizga baho bera olmaysiz.",
        }

    order = await fetchone(
        """
        SELECT
            id,
            ride_id,
            passenger_id,
            seats,
            status
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    )

    if not order:
        return {
            "success": False,
            "error": "Buyurtma topilmadi.",
        }

    if order[1] != ride_id:
        return {
            "success": False,
            "error": "Buyurtma va safar mos kelmaydi.",
        }

    if order[4] != "finished":
        return {
            "success": False,
            "error": "Baho faqat safar tugagandan keyin beriladi.",
        }

    ride = await fetchone(
        """
        SELECT
            id,
            driver_id
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

    driver = await fetchone(
        """
        SELECT
            id,
            user_id
        FROM drivers
        WHERE id = ?
        """,
        (ride[1],),
    )

    if not driver:
        return {
            "success": False,
            "error": "Haydovchi topilmadi.",
        }

    passenger_id = order[2]
    driver_user_id = driver[1]

    allowed = {
        passenger_id,
        driver_user_id,
    }

    if from_user_id not in allowed:
        return {
            "success": False,
            "error": "Siz bu safarga baho bera olmaysiz.",
        }

    if to_user_id not in allowed:
        return {
            "success": False,
            "error": "Baho oluvchi noto'g'ri.",
        }

    if (
        from_user_id == passenger_id
        and to_user_id != driver_user_id
    ):
        return {
            "success": False,
            "error": "Yo'nalish noto'g'ri.",
        }

    if (
        from_user_id == driver_user_id
        and to_user_id != passenger_id
    ):
        return {
            "success": False,
            "error": "Yo'nalish noto'g'ri.",
        }

    existing = await get_existing_rating(
        order_id,
        from_user_id,
        to_user_id,
    )

    if existing:
        return {
            "success": False,
            "error": "Siz bu foydalanuvchiga allaqachon baho bergansiz.",
            "rating": existing,
        }

    comment = (comment or "").strip()[:500]

    created_at = now_str()

    rating_id = await execute(
        """
        INSERT INTO ratings (
            ride_id,
            order_id,
            from_user_id,
            to_user_id,
            rating,
            comment,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ride_id,
            order_id,
            from_user_id,
            to_user_id,
            rating,
            comment,
            created_at,
        ),
    )

    return {
        "success": True,
        "rating": await get_rating_by_id(rating_id),
    }


async def get_user_rating_summary(user_id: int):
    row = await fetchone(
        """
        SELECT
            COUNT(*) AS total_ratings,
            COALESCE(AVG(rating), 0) AS average_rating
        FROM ratings
        WHERE to_user_id = ?
        """,
        (user_id,),
    )

    if not row:
        return {
            "total_ratings": 0,
            "average_rating": 0,
        }

    return {
        "total_ratings": row[0],
        "average_rating": round(float(row[1]), 2),
    }


async def get_user_ratings(user_id: int):
    return await fetchall(
        """
        SELECT
            r.id,
            r.ride_id,
            r.order_id,
            r.from_user_id,
            r.to_user_id,
            r.rating,
            r.comment,
            r.created_at,
            u.first_name,
            u.last_name,
            u.username
        FROM ratings r
        JOIN users u
            ON u.id = r.from_user_id
        WHERE r.to_user_id = ?
        ORDER BY r.id DESC
        """,
        (user_id,),
    )


async def get_ride_ratings(ride_id: int):
    return await fetchall(
        """
        SELECT
            r.id,
            r.ride_id,
            r.order_id,
            r.from_user_id,
            r.to_user_id,
            r.rating,
            r.comment,
            r.created_at,
            u.first_name,
            u.last_name,
            u.username
        FROM ratings r
        JOIN users u
            ON u.id = r.from_user_id
        WHERE r.ride_id = ?
        ORDER BY r.id DESC
        """,
        (ride_id,),
    )


async def get_rating_count():
    row = await fetchone(
        """
        SELECT COUNT(*)
        FROM ratings
        """
    )

    return row[0] if row else 0
