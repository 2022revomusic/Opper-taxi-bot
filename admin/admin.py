from database.database import fetchall, fetchone
from database.database import execute


# =========================================================
# DRIVER APPLICATIONS
# =========================================================

async def get_pending_drivers():
    """
    Tasdiqlashni kutayotgan haydovchilar.
    """

    return await fetchall(
        """
        SELECT
            d.id,
            d.telegram_id,
            d.full_name,
            d.phone,
            d.region,
            d.district,
            d.passport_file,
            d.driver_license_file,
            d.status,
            d.created_at,
            d.updated_at,

            u.username,
            u.first_name,
            u.last_name

        FROM drivers d

        LEFT JOIN users u
            ON u.telegram_id = d.telegram_id

        WHERE d.status = ?

        ORDER BY d.id DESC
        """,
        ("pending",),
    )


# =========================================================
# GET DRIVER
# =========================================================

async def get_driver(
    driver_id: int,
):
    """
    Driver ID orqali haydovchi ma'lumotlarini olish.
    """

    return await fetchone(
        """
        SELECT
            d.id,
            d.telegram_id,
            d.full_name,
            d.phone,
            d.region,
            d.district,
            d.passport_file,
            d.driver_license_file,
            d.status,
            d.created_at,
            d.updated_at,

            u.username,
            u.first_name,
            u.last_name

        FROM drivers d

        LEFT JOIN users u
            ON u.telegram_id = d.telegram_id

        WHERE d.id = ?
        """,
        (driver_id,),
    )


# =========================================================
# APPROVE DRIVER
# =========================================================

async def approve_driver(
    driver_id: int,
):
    """
    Haydovchini tasdiqlash.
    """

    driver = await get_driver(
        driver_id
    )

    if not driver:
        return {
            "success": False,
            "error": "driver_not_found",
        }

    await execute(
        """
        UPDATE drivers
        SET
            status = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            "approved",
            driver_id,
        ),
    )

    return {
        "success": True,
        "driver": await get_driver(
            driver_id
        ),
    }


# =========================================================
# REJECT DRIVER
# =========================================================

async def reject_driver(
    driver_id: int,
):
    """
    Haydovchi arizasini rad etish.
    """

    driver = await get_driver(
        driver_id
    )

    if not driver:
        return {
            "success": False,
            "error": "driver_not_found",
        }

    await execute(
        """
        UPDATE drivers
        SET
            status = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            "rejected",
            driver_id,
        ),
    )

    return {
        "success": True,
        "driver": await get_driver(
            driver_id
        ),
    }


# =========================================================
# DRIVER COUNT
# =========================================================

async def get_driver_counts():
    """
    Haydovchilar statistikasi.
    """

    result = await fetchone(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN status = 'pending'
                    THEN 1
                    ELSE 0
                END
            ) AS pending,
            SUM(
                CASE
                    WHEN status = 'approved'
                    THEN 1
                    ELSE 0
                END
            ) AS approved,
            SUM(
                CASE
                    WHEN status = 'rejected'
                    THEN 1
                    ELSE 0
                END
            ) AS rejected
        FROM drivers
        """
    )

    return {
        "total": int(
            result.get("total") or 0
        ),
        "pending": int(
            result.get("pending") or 0
        ),
        "approved": int(
            result.get("approved") or 0
        ),
        "rejected": int(
            result.get("rejected") or 0
        ),
    }


# =========================================================
# USER COUNT
# =========================================================

async def get_user_count():
    """
    Ro'yxatdan o'tgan foydalanuvchilar soni.
    """

    result = await fetchone(
        """
        SELECT COUNT(*) AS count
        FROM users
        """
    )

    return int(
        result.get("count") or 0
    )


# =========================================================
# RIDE COUNT
# =========================================================

async def get_ride_counts():
    """
    Safarlar statistikasi.
    """

    result = await fetchone(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN status = 'active'
                    THEN 1
                    ELSE 0
                END
            ) AS active,
            SUM(
                CASE
                    WHEN status = 'full'
                    THEN 1
                    ELSE 0
                END
            ) AS full,
            SUM(
                CASE
                    WHEN status = 'cancelled'
                    THEN 1
                    ELSE 0
                END
            ) AS cancelled,
            SUM(
                CASE
                    WHEN status = 'finished'
                    THEN 1
                    ELSE 0
                END
            ) AS finished
        FROM rides
        """
    )

    return {
        "total": int(
            result.get("total") or 0
        ),
        "active": int(
            result.get("active") or 0
        ),
        "full": int(
            result.get("full") or 0
        ),
        "cancelled": int(
            result.get("cancelled") or 0
        ),
        "finished": int(
            result.get("finished") or 0
        ),
    }


# =========================================================
# ORDER COUNT
# =========================================================

async def get_order_counts():
    """
    Buyurtmalar statistikasi.
    """

    result = await fetchone(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN status = 'pending'
                    THEN 1
                    ELSE 0
                END
            ) AS pending,
            SUM(
                CASE
                    WHEN status = 'accepted'
                    THEN 1
                    ELSE 0
                END
            ) AS accepted,
            SUM(
                CASE
                    WHEN status = 'rejected'
                    THEN 1
                    ELSE 0
                END
            ) AS rejected,
            SUM(
                CASE
                    WHEN status = 'cancelled'
                    THEN 1
                    ELSE 0
                END
            ) AS cancelled,
            SUM(
                CASE
                    WHEN status = 'finished'
                    THEN 1
                    ELSE 0
                END
            ) AS finished
        FROM orders
        """
    )

    return {
        "total": int(
            result.get("total") or 0
        ),
        "pending": int(
            result.get("pending") or 0
        ),
        "accepted": int(
            result.get("accepted") or 0
        ),
        "rejected": int(
            result.get("rejected") or 0
        ),
        "cancelled": int(
            result.get("cancelled") or 0
        ),
        "finished": int(
            result.get("finished") or 0
        ),
    }


# =========================================================
# RATING STATISTICS
# =========================================================

async def get_rating_statistics():
    """
    Reyting statistikasi.
    """

    result = await fetchone(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(
                ROUND(AVG(rating), 2),
                0
            ) AS average
        FROM ratings
        """
    )

    return {
        "total": int(
            result.get("total") or 0
        ),
        "average": float(
            result.get("average") or 0
        ),
    }


# =========================================================
# ADMIN DASHBOARD
# =========================================================

async def get_dashboard():
    """
    Admin panel uchun umumiy statistika.
    """

    drivers = await get_driver_counts()
    rides = await get_ride_counts()
    orders = await get_order_counts()
    ratings = await get_rating_statistics()

    return {
        "users": await get_user_count(),
        "drivers": drivers,
        "rides": rides,
        "orders": orders,
        "ratings": ratings,
        "pending_drivers": await get_pending_drivers(),
    }


# =========================================================
# ADMIN ACTION LOG
# =========================================================

async def log_admin_action(
    admin_telegram_id: int,
    action: str,
    target_telegram_id: int = None,
    details: str = "",
):
    """
    Admin bajargan amalni yozib boradi.
    """

    await execute(
        """
        INSERT INTO admin_actions (
            admin_telegram_id,
            action,
            target_telegram_id,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (
            admin_telegram_id,
            action,
            target_telegram_id,
            details,
        ),
    )

    return True
