from datetime import datetime, timezone

from database.database import execute, fetchone


# =========================================================
# DRIVER STATUS
# =========================================================

DRIVER_PENDING = "pending"
DRIVER_APPROVED = "approved"
DRIVER_REJECTED = "rejected"


# =========================================================
# TIME
# =========================================================

def now_str():
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# GET DRIVER BY TELEGRAM ID
# =========================================================

async def get_driver_by_telegram_id(
    telegram_id: int,
):
    """
    Telegram ID orqali haydovchini olish.
    """

    return await fetchone(
        """
        SELECT
            id,
            telegram_id,
            full_name,
            phone,
            region,
            district,
            passport_file,
            driver_license_file,
            status,
            created_at,
            updated_at
        FROM drivers
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )


# =========================================================
# GET DRIVER BY ID
# =========================================================

async def get_driver_by_id(
    driver_id: int,
):
    """
    Database ID orqali haydovchini olish.
    """

    return await fetchone(
        """
        SELECT
            id,
            telegram_id,
            full_name,
            phone,
            region,
            district,
            passport_file,
            driver_license_file,
            status,
            created_at,
            updated_at
        FROM drivers
        WHERE id = ?
        """,
        (driver_id,),
    )


# =========================================================
# CHECK DRIVER APPLICATION
# =========================================================

async def driver_exists(
    telegram_id: int,
):
    """
    Haydovchi arizasi mavjudligini tekshiradi.
    """

    driver = await get_driver_by_telegram_id(
        telegram_id
    )

    return driver is not None


# =========================================================
# SUBMIT DRIVER APPLICATION
# =========================================================

async def submit_driver_application(
    telegram_id: int,
    full_name: str = "",
    phone: str = "",
    region: str = "",
    district: str = "",
    passport_file: str = "",
    driver_license_file: str = "",
):
    """
    Haydovchi arizasini yuborish.

    Muhim:
    Agar foydalanuvchi oldin ariza bergan bo'lsa,
    ikkinchi marta yangi driver yozuvi yaratilmaydi.
    """

    existing = await get_driver_by_telegram_id(
        telegram_id
    )

    # -----------------------------------------------------
    # OLDIN ARIZA BERGAN
    # -----------------------------------------------------

    if existing:

        return {
            "success": False,
            "already_exists": True,
            "driver": existing,
            "status": existing.get("status"),
        }

    # -----------------------------------------------------
    # YANGI ARIZA
    # -----------------------------------------------------

    created_at = now_str()

    driver_id = await execute(
        """
        INSERT INTO drivers (
            telegram_id,
            full_name,
            phone,
            region,
            district,
            passport_file,
            driver_license_file,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            full_name,
            phone,
            region,
            district,
            passport_file,
            driver_license_file,
            DRIVER_PENDING,
            created_at,
            created_at,
        ),
    )

    driver = await get_driver_by_id(
        driver_id
    )

    return {
        "success": True,
        "already_exists": False,
        "driver": driver,
        "status": DRIVER_PENDING,
    }


# =========================================================
# GET DRIVER STATUS
# =========================================================

async def get_driver_status(
    telegram_id: int,
):
    """
    Haydovchining holatini qaytaradi.
    """

    driver = await get_driver_by_telegram_id(
        telegram_id
    )

    if not driver:

        return {
            "exists": False,
            "registered": False,
            "status": None,
            "driver": None,
        }

    return {
        "exists": True,
        "registered": True,
        "status": driver.get("status"),
        "driver": driver,
    }


# =========================================================
# APPROVE DRIVER
# =========================================================

async def approve_driver(
    driver_id: int,
):
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

    return await get_driver_by_id(
        driver_id
    )


# =========================================================
# REJECT DRIVER
# =========================================================

async def reject_driver(
    driver_id: int,
):
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

    return await get_driver_by_id(
        driver_id
    )


# =========================================================
# RESET DRIVER APPLICATION
# =========================================================

async def reset_driver_application(
    driver_id: int,
):
    """
    Rad etilgan haydovchini qayta pending holatiga o'tkazadi.
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

    return await get_driver_by_id(
        driver_id
    )


# =========================================================
# UPDATE DRIVER
# =========================================================

async def update_driver(
    telegram_id: int,
    full_name: str = "",
    phone: str = "",
    region: str = "",
    district: str = "",
    passport_file: str = "",
    driver_license_file: str = "",
):
    """
    Mavjud haydovchi ma'lumotlarini yangilaydi.
    """

    existing = await get_driver_by_telegram_id(
        telegram_id
    )

    if not existing:
        return None

    await execute(
        """
        UPDATE drivers
        SET
            full_name = ?,
            phone = ?,
            region = ?,
            district = ?,
            passport_file = ?,
            driver_license_file = ?,
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            full_name,
            phone,
            region,
            district,
            passport_file,
            driver_license_file,
            now_str(),
            telegram_id,
        ),
    )

    return await get_driver_by_telegram_id(
        telegram_id
    )


# =========================================================
# DRIVER APPROVED CHECK
# =========================================================

async def is_driver_approved(
    telegram_id: int,
):
    """
    Haydovchi tasdiqlanganmi?
    """

    driver = await get_driver_by_telegram_id(
        telegram_id
    )

    if not driver:
        return False

    return driver.get("status") == DRIVER_APPROVED
