from datetime import datetime, timezone

from database.database import fetchone, fetchall, execute


def now_str():
    return datetime.now(timezone.utc).isoformat()


async def get_dashboard_stats():
    users = await fetchone(
        """
        SELECT COUNT(*)
        FROM users
        """
    )

    drivers = await fetchone(
        """
        SELECT COUNT(*)
        FROM drivers
        """
    )

    pending_drivers = await fetchone(
        """
        SELECT COUNT(*)
        FROM drivers
        WHERE status = 'pending'
        """
    )

    approved_drivers = await fetchone(
        """
        SELECT COUNT(*)
        FROM drivers
        WHERE status = 'approved'
        """
    )

    active_rides = await fetchone(
        """
        SELECT COUNT(*)
        FROM rides
        WHERE status = 'active'
        """
    )

    total_rides = await fetchone(
        """
        SELECT COUNT(*)
        FROM rides
        """
    )

    pending_orders = await fetchone(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'pending'
        """
    )

    total_orders = await fetchone(
        """
        SELECT COUNT(*)
        FROM orders
        """
    )

    total_ratings = await fetchone(
        """
        SELECT COUNT(*)
        FROM ratings
        """
    )

    unread_notifications = await fetchone(
        """
        SELECT COUNT(*)
        FROM notifications
        WHERE is_read = 0
        """
    )

    return {
        "users": users[0] if users else 0,
        "drivers": drivers[0] if drivers else 0,
        "pending_drivers": pending_drivers[0] if pending_drivers else 0,
        "approved_drivers": approved_drivers[0] if approved_drivers else 0,
        "active_rides": active_rides[0] if active_rides else 0,
        "total_rides": total_rides[0] if total_rides else 0,
        "pending_orders": pending_orders[0] if pending_orders else 0,
        "total_orders": total_orders[0] if total_orders else 0,
        "total_ratings": total_ratings[0] if total_ratings else 0,
        "unread_notifications": (
            unread_notifications[0]
            if unread_notifications
            else 0
        ),
    }


async def get_pending_drivers():
    return await fetchall(
        """
        SELECT
            d.id,
            d.user_id,
            d.phone,
            d.status,
            d.car_id,
            d.created_at,
            d.updated_at,
            u.telegram_id,
            u.first_name,
            u.last_name,
            u.username,
            u.phone
        FROM drivers d
        JOIN users u
            ON u.id = d.user_id
        WHERE d.status = 'pending'
        ORDER BY d.id DESC
        """
    )


async def get_all_drivers():
    return await fetchall(
        """
        SELECT
            d.id,
            d.user_id,
            d.phone,
            d.status,
            d.car_id,
            d.created_at,
            d.updated_at,
            u.telegram_id,
            u.first_name,
            u.last_name,
            u.username,
            u.phone
        FROM drivers d
        JOIN users u
            ON u.id = d.user_id
        ORDER BY d.id DESC
        """
    )


async def get_driver_details(driver_id: int):
    return await fetchone(
        """
        SELECT
            d.id,
            d.user_id,
            d.phone,
            d.status,
            d.car_id,
            d.created_at,
            d.updated_at,
            u.telegram_id,
            u.first_name,
            u.last_name,
            u.username,
            u.phone
        FROM drivers d
        JOIN users u
            ON u.id = d.user_id
        WHERE d.id = ?
        """,
        (driver_id,),
    )


async def approve_driver(driver_id: int):
    driver = await get_driver_details(driver_id)

    if not driver:
        return {
            "success": False,
            "error": "Haydovchi topilmadi.",
        }

    await execute(
        """
        UPDATE drivers
        SET
            status = 'approved',
            updated_at = ?
        WHERE id = ?
        """,
        (
            now_str(),
            driver_id,
        ),
    )

    return {
        "success": True,
        "driver": await get_driver_details(driver_id),
    }


async def reject_driver(
    driver_id: int,
    reason: str = "",
):
    driver = await get_driver_details(driver_id)

    if not driver:
        return {
            "success": False,
            "error": "Haydovchi topilmadi.",
        }

    await execute(
        """
        UPDATE drivers
        SET
            status = 'rejected',
            updated_at = ?
        WHERE id = ?
        """,
        (
            now_str(),
            driver_id,
        ),
    )

    return {
        "success": True,
        "driver": await get_driver_details(driver_id),
        "reason": reason[:500],
    }


async def reset_driver(driver_id: int):
    driver = await get_driver_details(driver_id)

    if not driver:
        return {
            "success": False,
            "error": "Haydovchi topilmadi.",
        }

    await execute(
        """
        UPDATE drivers
        SET
            status = 'pending',
            updated_at = ?
        WHERE id = ?
        """,
        (
            now_str(),
            driver_id,
        ),
    )

    return {
        "success": True,
        "driver": await get_driver_details(driver_id),
    }


async def get_users(limit: int = 100):
    limit = max(1, min(int(limit), 500))

    return await fetchall(
        f"""
        SELECT
            id,
            telegram_id,
            first_name,
            last_name,
            username,
            phone,
            created_at,
            updated_at
        FROM users
        ORDER BY id DESC
        LIMIT {limit}
        """
    )


async def get_user_details(user_id: int):
    return await fetchone(
        """
        SELECT
            id,
            telegram_id,
            first_name,
            last_name,
            username,
            phone,
            created_at,
            updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )


async def get_all_rides(limit: int = 200):
    limit = max(1, min(int(limit), 1000))

    return await fetchall(
        f"""
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
        ORDER BY r.id DESC
        LIMIT {limit}
        """
    )


async def get_all_orders(limit: int = 200):
    limit = max(1, min(int(limit), 1000))

    return await fetchall(
        f"""
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
        JOIN users u
            ON u.id = o.passenger_id
        JOIN rides r
            ON r.id = o.ride_id
        ORDER BY o.id DESC
        LIMIT {limit}
        """
    )


async def get_all_ratings(limit: int = 200):
    limit = max(1, min(int(limit), 1000))

    return await fetchall(
        f"""
        SELECT
            r.id,
            r.ride_id,
            r.order_id,
            r.from_user_id,
            r.to_user_id,
            r.rating,
            r.comment,
            r.created_at,
            sender.first_name,
            sender.last_name,
            sender.username,
            receiver.first_name,
            receiver.last_name,
            receiver.username
        FROM ratings r
        JOIN users sender
            ON sender.id = r.from_user_id
        JOIN users receiver
            ON receiver.id = r.to_user_id
        ORDER BY r.id DESC
        LIMIT {limit}
        """
    )


async def delete_ride(ride_id: int):
    ride = await fetchone(
        """
        SELECT id, status
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

    await execute(
        """
        UPDATE rides
        SET status = 'cancelled'
        WHERE id = ?
        """,
        (ride_id,),
    )

    return {
        "success": True,
        "ride_id": ride_id,
    }


async def get_recent_activity(limit: int = 50):
    limit = max(1, min(int(limit), 200))

    users = await fetchall(
        f"""
        SELECT
            'user' AS type,
            id,
            first_name,
            last_name,
            created_at
        FROM users
        ORDER BY id DESC
        LIMIT {limit}
        """
    )

    drivers = await fetchall(
        f"""
        SELECT
            'driver' AS type,
            id,
            status,
            '',
            created_at
        FROM drivers
        ORDER BY id DESC
        LIMIT {limit}
        """
    )

    rides = await fetchall(
        f"""
        SELECT
            'ride' AS type,
            id,
            status,
            from_region || ' → ' || to_region,
            created_at
        FROM rides
        ORDER BY id DESC
        LIMIT {limit}
        """
    )

    orders = await fetchall(
        f"""
        SELECT
            'order' AS type,
            id,
            status,
            '',
            created_at
        FROM orders
        ORDER BY id DESC
        LIMIT {limit}
        """
    )

    return {
        "users": users,
        "drivers": drivers,
        "rides": rides,
        "orders": orders,
    }
