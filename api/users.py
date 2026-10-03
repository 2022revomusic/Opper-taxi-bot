from datetime import datetime, timezone

from database.database import execute, fetchone


def now_str():
    return datetime.now(timezone.utc).isoformat()


async def get_or_create_user(
    telegram_id: int,
    first_name: str = "",
    last_name: str = "",
    username: str = "",
    phone: str = "",
):
    """
    Telegram foydalanuvchisini topadi.
    Agar mavjud bo'lmasa, yangi user yaratadi.
    """

    user = await fetchone(
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
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    if user:
        await execute(
            """
            UPDATE users
            SET
                first_name = ?,
                last_name = ?,
                username = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                first_name,
                last_name,
                username,
                now_str(),
                telegram_id,
            ),
        )

        return await get_user_by_telegram_id(telegram_id)

    created_at = now_str()

    user_id = await execute(
        """
        INSERT INTO users (
            telegram_id,
            first_name,
            last_name,
            username,
            phone,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            first_name,
            last_name,
            username,
            phone,
            created_at,
            created_at,
        ),
    )

    return await get_user_by_id(user_id)


async def get_user_by_id(user_id: int):
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


async def get_user_by_telegram_id(telegram_id: int):
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
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )


async def update_user_phone(
    telegram_id: int,
    phone: str,
):
    await execute(
        """
        UPDATE users
        SET
            phone = ?,
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            phone,
            now_str(),
            telegram_id,
        ),
    )

    return await get_user_by_telegram_id(telegram_id)


async def update_user_profile(
    telegram_id: int,
    first_name: str,
    last_name: str,
    username: str,
):
    await execute(
        """
        UPDATE users
        SET
            first_name = ?,
            last_name = ?,
            username = ?,
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            first_name,
            last_name,
            username,
            now_str(),
            telegram_id,
        ),
    )

    return await get_user_by_telegram_id(telegram_id)
