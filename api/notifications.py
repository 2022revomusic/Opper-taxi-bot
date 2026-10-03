from datetime import datetime, timezone

from database.database import execute, fetchone, fetchall


NOTIFICATION_ORDER = "order"
NOTIFICATION_RIDE = "ride"
NOTIFICATION_DRIVER = "driver"
NOTIFICATION_SYSTEM = "system"
NOTIFICATION_RATING = "rating"


def now_str():
    return datetime.now(timezone.utc).isoformat()


async def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
):
    created_at = now_str()

    notification_id = await execute(
        """
        INSERT INTO notifications (
            user_id,
            type,
            title,
            message,
            is_read,
            created_at
        )
        VALUES (?, ?, ?, ?, 0, ?)
        """,
        (
            user_id,
            notification_type,
            title,
            message,
            created_at,
        ),
    )

    return await get_notification_by_id(notification_id)


async def get_notification_by_id(notification_id: int):
    return await fetchone(
        """
        SELECT
            id,
            user_id,
            type,
            title,
            message,
            is_read,
            created_at
        FROM notifications
        WHERE id = ?
        """,
        (notification_id,),
    )


async def get_user_notifications(
    user_id: int,
    limit: int = 50,
):
    limit = max(1, min(int(limit), 100))

    return await fetchall(
        f"""
        SELECT
            id,
            user_id,
            type,
            title,
            message,
            is_read,
            created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT {limit}
        """,
        (user_id,),
    )


async def get_unread_notifications(user_id: int):
    return await fetchall(
        """
        SELECT
            id,
            user_id,
            type,
            title,
            message,
            is_read,
            created_at
        FROM notifications
        WHERE user_id = ?
          AND is_read = 0
        ORDER BY id DESC
        """,
        (user_id,),
    )


async def get_unread_count(user_id: int):
    row = await fetchone(
        """
        SELECT COUNT(*)
        FROM notifications
        WHERE user_id = ?
          AND is_read = 0
        """,
        (user_id,),
    )

    return row[0] if row else 0


async def mark_notification_read(
    notification_id: int,
    user_id: int,
):
    await execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE id = ?
          AND user_id = ?
        """,
        (
            notification_id,
            user_id,
        ),
    )

    return await get_notification_by_id(notification_id)


async def mark_all_notifications_read(user_id: int):
    await execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
          AND is_read = 0
        """,
        (user_id,),
    )

    return {
        "success": True,
        "unread_count": await get_unread_count(user_id),
    }


async def delete_notification(
    notification_id: int,
    user_id: int,
):
    await execute(
        """
        DELETE FROM notifications
        WHERE id = ?
          AND user_id = ?
        """,
        (
            notification_id,
            user_id,
        ),
    )

    return {
        "success": True,
        "unread_count": await get_unread_count(user_id),
    }


async def delete_read_notifications(user_id: int):
    await execute(
        """
        DELETE FROM notifications
        WHERE user_id = ?
          AND is_read = 1
        """,
        (user_id,),
    )

    return {
        "success": True,
        "unread_count": await get_unread_count(user_id),
    }


async def notify_new_order(
    driver_user_id: int,
    passenger_name: str,
    from_location: str,
    to_location: str,
):
    return await create_notification(
        user_id=driver_user_id,
        notification_type=NOTIFICATION_ORDER,
        title="🚕 Yangi buyurtma",
        message=(
            f"{passenger_name} sizning safaringizga buyurtma yubordi. "
            f"{from_location} → {to_location}"
        ),
    )


async def notify_order_accepted(
    passenger_user_id: int,
    driver_name: str,
    from_location: str,
    to_location: str,
):
    return await create_notification(
        user_id=passenger_user_id,
        notification_type=NOTIFICATION_ORDER,
        title="✅ Buyurtma qabul qilindi",
        message=(
            f"{driver_name} buyurtmangizni qabul qildi. "
            f"{from_location} → {to_location}"
        ),
    )


async def notify_order_rejected(
    passenger_user_id: int,
    driver_name: str,
):
    return await create_notification(
        user_id=passenger_user_id,
        notification_type=NOTIFICATION_ORDER,
        title="❌ Buyurtma rad etildi",
        message=(
            f"{driver_name} buyurtmangizni rad etdi."
        ),
    )


async def notify_order_cancelled(
    user_id: int,
    message: str = "Buyurtma bekor qilindi.",
):
    return await create_notification(
        user_id=user_id,
        notification_type=NOTIFICATION_ORDER,
        title="⚠️ Buyurtma bekor qilindi",
        message=message,
    )


async def notify_driver_approved(
    user_id: int,
):
    return await create_notification(
        user_id=user_id,
        notification_type=NOTIFICATION_DRIVER,
        title="✅ Haydovchi tasdiqlandi",
        message=(
            "Tabriklaymiz! Haydovchilik arizangiz tasdiqlandi. "
            "Endi safar joylashingiz mumkin."
        ),
    )


async def notify_driver_rejected(
    user_id: int,
    reason: str = "",
):
    message = "Haydovchilik arizangiz rad etildi."

    if reason:
        message += f" Sabab: {reason}"

    return await create_notification(
        user_id=user_id,
        notification_type=NOTIFICATION_DRIVER,
        title="❌ Haydovchi arizasi rad etildi",
        message=message,
    )


async def notify_ride_created(
    user_id: int,
    from_location: str,
    to_location: str,
    travel_date: str,
    travel_time: str,
):
    return await create_notification(
        user_id=user_id,
        notification_type=NOTIFICATION_RIDE,
        title="🚕 Safar joylandi",
        message=(
            f"Safaringiz muvaffaqiyatli joylandi: "
            f"{from_location} → {to_location}. "
            f"{travel_date} {travel_time}"
        ),
    )


async def notify_ride_cancelled(
    user_id: int,
    from_location: str,
    to_location: str,
):
    return await create_notification(
        user_id=user_id,
        notification_type=NOTIFICATION_RIDE,
        title="⚠️ Safar bekor qilindi",
        message=(
            f"Sizning safaringiz bekor qilindi: "
            f"{from_location} → {to_location}"
        ),
    )


async def notify_rating_received(
    user_id: int,
    rating: int,
    comment: str = "",
):
    message = f"Sizga ⭐ {rating}/5 baho berildi."

    if comment:
        message += f" Izoh: {comment}"

    return await create_notification(
        user_id=user_id,
        notification_type=NOTIFICATION_RATING,
        title="⭐ Yangi baho",
        message=message,
    )


async def notify_system(
    user_id: int,
    title: str,
    message: str,
):
    return await create_notification(
        user_id=user_id,
        notification_type=NOTIFICATION_SYSTEM,
        title=title,
        message=message,
    )
