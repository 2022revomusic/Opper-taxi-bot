from datetime import datetime, timezone

from database.database import execute, fetchall, fetchone


# =========================================================
# NOTIFICATION TYPES
# =========================================================

NOTIFICATION_ORDER = "order"
NOTIFICATION_RIDE = "ride"
NOTIFICATION_DRIVER = "driver"
NOTIFICATION_SYSTEM = "system"
NOTIFICATION_RATING = "rating"


# =========================================================
# TIME
# =========================================================

def now_str():
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# CREATE NOTIFICATION
# =========================================================

async def create_notification(
    telegram_id: int,
    title: str,
    message: str,
    notification_type: str = NOTIFICATION_SYSTEM,
):
    """
    Foydalanuvchiga yangi notification yaratadi.
    """

    notification_id = await execute(
        """
        INSERT INTO notifications (
            telegram_id,
            title,
            message,
            type,
            is_read,
            created_at
        )
        VALUES (?, ?, ?, ?, 0, ?)
        """,
        (
            telegram_id,
            title,
            message,
            notification_type,
            now_str(),
        ),
    )

    return await get_notification_by_id(
        notification_id
    )


# =========================================================
# GET NOTIFICATION
# =========================================================

async def get_notification_by_id(
    notification_id: int,
):
    """
    Bitta notification.
    """

    return await fetchone(
        """
        SELECT
            id,
            telegram_id,
            title,
            message,
            type,
            is_read,
            created_at
        FROM notifications
        WHERE id = ?
        """,
        (notification_id,),
    )


# =========================================================
# GET USER NOTIFICATIONS
# =========================================================

async def get_user_notifications(
    telegram_id: int,
    limit: int = 50,
):
    """
    Foydalanuvchining notificationlari.
    """

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50

    limit = max(
        1,
        min(limit, 100),
    )

    return await fetchall(
        f"""
        SELECT
            id,
            telegram_id,
            title,
            message,
            type,
            is_read,
            created_at
        FROM notifications
        WHERE telegram_id = ?
        ORDER BY id DESC
        LIMIT {limit}
        """,
        (telegram_id,),
    )


# =========================================================
# GET UNREAD NOTIFICATIONS
# =========================================================

async def get_unread_notifications(
    telegram_id: int,
):
    """
    O'qilmagan notificationlar.
    """

    return await fetchall(
        """
        SELECT
            id,
            telegram_id,
            title,
            message,
            type,
            is_read,
            created_at
        FROM notifications
        WHERE
            telegram_id = ?
            AND is_read = 0
        ORDER BY id DESC
        """,
        (telegram_id,),
    )


# =========================================================
# UNREAD COUNT
# =========================================================

async def get_unread_count(
    telegram_id: int,
):
    """
    O'qilmagan notificationlar soni.
    """

    result = await fetchone(
        """
        SELECT
            COUNT(*) AS count
        FROM notifications
        WHERE
            telegram_id = ?
            AND is_read = 0
        """,
        (telegram_id,),
    )

    if not result:
        return 0

    return int(
        result.get("count") or 0
    )


# =========================================================
# MARK ONE AS READ
# =========================================================

async def mark_notification_read(
    notification_id: int,
    telegram_id: int,
):
    """
    Faqat shu foydalanuvchining
    ko'rsatilgan notificationini o'qilgan qiladi.
    """

    notification = await fetchone(
        """
        SELECT
            id,
            telegram_id,
            is_read
        FROM notifications
        WHERE
            id = ?
            AND telegram_id = ?
        """,
        (
            notification_id,
            telegram_id,
        ),
    )

    if not notification:
        return {
            "success": False,
            "error": "notification_not_found",
        }

    await execute(
        """
        UPDATE notifications
        SET
            is_read = 1
        WHERE
            id = ?
            AND telegram_id = ?
        """,
        (
            notification_id,
            telegram_id,
        ),
    )

    return {
        "success": True,
        "notification": await get_notification_by_id(
            notification_id
        ),
    }


# =========================================================
# MARK ALL AS READ
# =========================================================

async def mark_all_notifications_read(
    telegram_id: int,
):
    """
    Foydalanuvchining barcha notificationlarini
    o'qilgan qiladi.
    """

    await execute(
        """
        UPDATE notifications
        SET
            is_read = 1
        WHERE
            telegram_id = ?
            AND is_read = 0
        """,
        (telegram_id,),
    )

    return {
        "success": True,
        "unread_count": 0,
    }


# =========================================================
# DELETE NOTIFICATION
# =========================================================

async def delete_notification(
    notification_id: int,
    telegram_id: int,
):
    """
    Faqat o'z notificationini o'chirish.
    """

    notification = await fetchone(
        """
        SELECT id
        FROM notifications
        WHERE
            id = ?
            AND telegram_id = ?
        """,
        (
            notification_id,
            telegram_id,
        ),
    )

    if not notification:
        return {
            "success": False,
            "error": "notification_not_found",
        }

    await execute(
        """
        DELETE FROM notifications
        WHERE
            id = ?
            AND telegram_id = ?
        """,
        (
            notification_id,
            telegram_id,
        ),
    )

    return {
        "success": True,
    }


# =========================================================
# SEND ORDER NOTIFICATION
# =========================================================

async def notify_order(
    telegram_id: int,
    title: str,
    message: str,
):
    return await create_notification(
        telegram_id=telegram_id,
        title=title,
        message=message,
        notification_type=NOTIFICATION_ORDER,
    )


# =========================================================
# SEND RIDE NOTIFICATION
# =========================================================

async def notify_ride(
    telegram_id: int,
    title: str,
    message: str,
):
    return await create_notification(
        telegram_id=telegram_id,
        title=title,
        message=message,
        notification_type=NOTIFICATION_RIDE,
    )


# =========================================================
# SEND DRIVER NOTIFICATION
# =========================================================

async def notify_driver(
    telegram_id: int,
    title: str,
    message: str,
):
    return await create_notification(
        telegram_id=telegram_id,
        title=title,
        message=message,
        notification_type=NOTIFICATION_DRIVER,
    )


# =========================================================
# SEND SYSTEM NOTIFICATION
# =========================================================

async def notify_system(
    telegram_id: int,
    title: str,
    message: str,
):
    return await create_notification(
        telegram_id=telegram_id,
        title=title,
        message=message,
        notification_type=NOTIFICATION_SYSTEM,
    )


# =========================================================
# SEND RATING NOTIFICATION
# =========================================================

async def notify_rating(
    telegram_id: int,
    title: str,
    message: str,
):
    return await create_notification(
        telegram_id=telegram_id,
        title=title,
        message=message,
        notification_type=NOTIFICATION_RATING,
    )
