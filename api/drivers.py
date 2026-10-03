from datetime import datetime, timezone

from database.database import execute, fetchone


# =========================================================
# OPPER TAXI — DRIVERS API
# =========================================================

DRIVER_PENDING = "pending"
DRIVER_APPROVED = "approved"
DRIVER_REJECTED = "rejected"


def now_str():
    return datetime.now(timezone.utc).isoformat()


async def get_driver_by_user_id(user_id: int):
    return await fetchone(
        """
        SELECT
            id,
            user_id,
            phone,
            status,
            car_id,
            created_at,
            updated_at
        FROM drivers
        WHERE user_id = ?
        """,
        (user_id,),
    )


async def get_driver_by_id(driver_id: int):
    return await fetchone(
        """
        SELECT
            id,
            user_id,
            phone,
            status,
            car_id,
            created_at,
            updated_at
        FROM drivers
        WHERE id = ?
        """,
        (driver_id,),
    )


async def submit_driver_application(
    user_id: int,
    phone: str,
):
    """
    Haydovchi arizasini yuborish.

    Agar foydalanuvchida oldindan ariza mavjud bo'lsa,
    ikkinchi marta yangi ariza yaratmaydi.
    """

    existing = await get_driver_by_user_id(user_id)

    if existing:
        return {
            "success": False,
            "already_exists": True,
            "driver": existing,
        }

    created_at = now_str()

    driver_id = await execute(
        """
        INSERT INTO drivers (
            user_id,
            phone,
            status,
            car_id,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, NULL, ?, ?)
        """,
        (
            user_id,
            phone,
            DRIVER_PENDING,
            created_at,
            created_at,
        ),
    )

    driver = await get_driver_by_id(driver_id)

    return {
        "success": True,
        "already_exists": False,
        "driver": driver,
    }


async def get_driver_status(user_id: int):
    """
    Haydovchining hozirgi statusini qaytaradi.
    """

    driver = await get_driver_by_user_id(user_id)

    if not driver:
        return {
            "exists": False,
            "status": None,
            "driver": None,
        }

    return {
        "exists": True,
        "status": driver[3],
        "driver": driver,
    }


async def approve_driver(driver_id: int):
    """
    Admin haydovchini tasdiqlaydi.
    """

    await execute(
        """
        UPDATE drivers
        SET
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            DRIVER_APPROVED,
            now_str(),
            driver_id,
        ),
    )

    return await get_driver_by_id(driver_id)


async def reject_driver(driver_id: int):
    """
    Admin haydovchi arizasini rad etadi.
    """

    await execute(
        """
        UPDATE drivers
        SET
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            DRIVER_REJECTED,
            now_str(),
            driver_id,
        ),
    )

    return await get_driver_by_id(driver_id)


async def reset_driver_application(driver_id: int):
    """
    Faqat kerak bo'lganda admin tomonidan
    rad etilgan arizani qayta topshirishga imkon beradi.
    """

    await execute(
        """
        UPDATE drivers
        SET
            status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            DRIVER_PENDING,
            now_str(),
            driver_id,
        ),
    )

    return await get_driver_by_id(driver_id)
