from datetime import datetime, timezone

from database.database import execute, fetchall, fetchone


# =========================================================
# TIME
# =========================================================

def now_str():
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# VALID RATING
# =========================================================

def valid_rating(value: int) -> bool:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return False

    return 1 <= value <= 5


# =========================================================
# CREATE RATING
# =========================================================

async def create_rating(
    ride_id: int,
    from_telegram_id: int,
    to_telegram_id: int,
    rating: int,
    comment: str = "",
):
    """
    Foydalanuvchi boshqa foydalanuvchiga baho beradi.

    Muhim:
    Bir xil safar bo'yicha bir foydalanuvchi
    bir odamga qayta-qayta baho bera olmaydi.
    """

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return {
            "success": False,
            "error": "invalid_rating",
        }

    if not valid_rating(rating):
        return {
            "success": False,
            "error": "invalid_rating",
        }

    if int(from_telegram_id) == int(
        to_telegram_id
    ):
        return {
            "success": False,
            "error": "cannot_rate_self",
        }

    # -----------------------------------------------------
    # SAFARNI TEKSHIRISH
    # -----------------------------------------------------

    ride = await fetchone(
        """
        SELECT
            id,
            driver_telegram_id,
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

    # -----------------------------------------------------
    # RATING QILUVCHI SAFARDA BORMI?
    # -----------------------------------------------------

    participant = await fetchone(
        """
        SELECT id
        FROM orders
        WHERE
            ride_id = ?
            AND passenger_telegram_id = ?
            AND status IN (?, ?)
        LIMIT 1
        """,
        (
            ride_id,
            from_telegram_id,
            "accepted",
            "finished",
        ),
    )

    is_driver = (
        int(
            ride["driver_telegram_id"]
        )
        == int(from_telegram_id)
    )

    if not participant and not is_driver:
        return {
            "success": False,
            "error": "not_participant",
        }

    # -----------------------------------------------------
    # KIMGA BAHO BERILYAPTI?
    # -----------------------------------------------------

    valid_recipient = False

    if is_driver:
        # Haydovchi yo'lovchiga baho bermoqchi.
        passenger = await fetchone(
            """
            SELECT id
            FROM orders
            WHERE
                ride_id = ?
                AND passenger_telegram_id = ?
                AND status IN (?, ?)
            LIMIT 1
            """,
            (
                ride_id,
                to_telegram_id,
                "accepted",
                "finished",
            ),
        )

        valid_recipient = (
            passenger is not None
        )

    else:
        # Yo'lovchi haydovchiga baho bermoqchi.
        valid_recipient = (
            int(
                ride["driver_telegram_id"]
            )
            == int(to_telegram_id)
        )

    if not valid_recipient:
        return {
            "success": False,
            "error": "invalid_recipient",
        }

    # -----------------------------------------------------
    # OLDINGI RATING
    # -----------------------------------------------------

    existing = await fetchone(
        """
        SELECT
            id,
            rating,
            comment,
            created_at
        FROM ratings
        WHERE
            ride_id = ?
            AND from_telegram_id = ?
            AND to_telegram_id = ?
        LIMIT 1
        """,
        (
            ride_id,
            from_telegram_id,
            to_telegram_id,
        ),
    )

    if existing:
        return {
            "success": False,
            "error": "already_rated",
            "rating": existing,
        }

    # -----------------------------------------------------
    # RATING SAQLASH
    # -----------------------------------------------------

    rating_id = await execute(
        """
        INSERT INTO ratings (
            ride_id,
            from_telegram_id,
            to_telegram_id,
            rating,
            comment,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ride_id,
            from_telegram_id,
            to_telegram_id,
            rating,
            comment,
            now_str(),
        ),
    )

    return {
        "success": True,
        "rating": await get_rating_by_id(
            rating_id
        ),
    }


# =========================================================
# GET RATING
# =========================================================

async def get_rating_by_id(
    rating_id: int,
):
    return await fetchone(
        """
        SELECT
            id,
            ride_id,
            from_telegram_id,
            to_telegram_id,
            rating,
            comment,
            created_at
        FROM ratings
        WHERE id = ?
        """,
        (rating_id,),
    )


# =========================================================
# GET USER RATINGS
# =========================================================

async def get_user_ratings(
    telegram_id: int,
):
    """
    Foydalanuvchiga berilgan barcha baholar.
    """

    return await fetchall(
        """
        SELECT
            r.id,
            r.ride_id,
            r.from_telegram_id,
            r.to_telegram_id,
            r.rating,
            r.comment,
            r.created_at,

            u.first_name AS from_first_name,
            u.last_name AS from_last_name,
            u.username AS from_username

        FROM ratings r

        LEFT JOIN users u
            ON u.telegram_id = r.from_telegram_id

        WHERE r.to_telegram_id = ?

        ORDER BY
            r.id DESC
        """,
        (telegram_id,),
    )


# =========================================================
# GET AVERAGE RATING
# =========================================================

async def get_user_rating_summary(
    telegram_id: int,
):
    """
    Foydalanuvchining o'rtacha reytingi.
    """

    result = await fetchone(
        """
        SELECT
            COUNT(*) AS total_ratings,
            COALESCE(
                ROUND(
                    AVG(rating),
                    2
                ),
                0
            ) AS average_rating
        FROM ratings
        WHERE to_telegram_id = ?
        """,
        (telegram_id,),
    )

    if not result:
        return {
            "total_ratings": 0,
            "average_rating": 0,
        }

    return {
        "total_ratings": int(
            result.get("total_ratings") or 0
        ),
        "average_rating": float(
            result.get("average_rating") or 0
        ),
    }


# =========================================================
# CHECK USER ALREADY RATED
# =========================================================

async def has_rated(
    ride_id: int,
    from_telegram_id: int,
    to_telegram_id: int,
):
    """
    Foydalanuvchi oldin baho berganmi?
    """

    rating = await fetchone(
        """
        SELECT id
        FROM ratings
        WHERE
            ride_id = ?
            AND from_telegram_id = ?
            AND to_telegram_id = ?
        LIMIT 1
        """,
        (
            ride_id,
            from_telegram_id,
            to_telegram_id,
        ),
    )

    return rating is not None


# =========================================================
# GET RIDE RATINGS
# =========================================================

async def get_ride_ratings(
    ride_id: int,
):
    """
    Bitta safarga tegishli baholar.
    """

    return await fetchall(
        """
        SELECT
            r.id,
            r.ride_id,
            r.from_telegram_id,
            r.to_telegram_id,
            r.rating,
            r.comment,
            r.created_at,

            u.first_name AS from_first_name,
            u.last_name AS from_last_name,
            u.username AS from_username

        FROM ratings r

        LEFT JOIN users u
            ON u.telegram_id = r.from_telegram_id

        WHERE r.ride_id = ?

        ORDER BY
            r.id DESC
        """,
        (ride_id,),
    )
