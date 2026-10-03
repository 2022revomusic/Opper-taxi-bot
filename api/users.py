from datetime import datetime, timezone

from database.database import execute, fetchone


# =========================================================
# TIME
# =========================================================

def now_str():
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# GET OR CREATE USER
# =========================================================

async def get_or_create_user(
    telegram_id: int,
    first_name: str = "",
    last_name: str = "",
    username: str = "",
    phone: str = "",
):
    """
    Telegram foydalanuvchisini topadi.
    Agar mavjud bo'lmasa, yaratadi.
    """

    user = await get_user_by_telegram_id(telegram_id)

    # -----------------------------------------------------
    # USER BOR
    # -----------------------------------------------------

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
                first_name or user.get("first_name", ""),
                last_name or user.get("last_name", ""),
                username or user.get("username", ""),
                now_str(),
                telegram_id,
            ),
        )

        # Telefon mavjud bo'lsa, uni yo'qotmaymiz
        if phone:
            await update_user_phone(
                telegram_id=telegram_id,
                phone=phone,
            )

        return await get_user_by_telegram_id(telegram_id)

    # -----------------------------------------------------
    # YANGI USER
    # -----------------------------------------------------

    created_at = now_str()

    await execute(
        """
        INSERT INTO users (
            telegram_id,
            username,
            first_name,
            last_name,
            phone,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            username,
            first_name,
            last_name,
            phone,
            created_at,
            created_at,
        ),
    )

    return await get_user_by_telegram_id(telegram_id)


# =========================================================
# GET USER BY ID
# =========================================================

async def get_user_by_id(
    user_id: int,
):
    """
    Ichki database ID orqali user olish.
    """

    return await fetchone(
        """
        SELECT
            id,
            telegram_id,
            username,
            first_name,
            last_name,
            phone,
            created_at,
            updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )


# =========================================================
# GET USER BY TELEGRAM ID
# =========================================================

async def get_user_by_telegram_id(
    telegram_id: int,
):
    """
    Telegram ID orqali user olish.
    """

    return await fetchone(
        """
        SELECT
            id,
            telegram_id,
            username,
            first_name,
            last_name,
            phone,
            created_at,
            updated_at
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )


# =========================================================
# UPDATE PHONE
# =========================================================

async def update_user_phone(
    telegram_id: int,
    phone: str,
):
    """
    Foydalanuvchi telefon raqamini yangilaydi.
    """

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

    return await get_user_by_telegram_id(
        telegram_id
    )


# =========================================================
# UPDATE PROFILE
# =========================================================

async def update_user_profile(
    telegram_id: int,
    first_name: str = "",
    last_name: str = "",
    username: str = "",
    phone: str = "",
):
    """
    Profil ma'lumotlarini yangilaydi.
    """

    current_user = await get_user_by_telegram_id(
        telegram_id
    )

    if not current_user:
        return None

    await execute(
        """
        UPDATE users
        SET
            first_name = ?,
            last_name = ?,
            username = ?,
            phone = ?,
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            first_name,
            last_name,
            username,
            phone,
            now_str(),
            telegram_id,
        ),
    )

    return await get_user_by_telegram_id(
        telegram_id
    )


# =========================================================
# ENSURE USER
# =========================================================

async def ensure_user(
    telegram_id: int,
    first_name: str = "",
    last_name: str = "",
    username: str = "",
):
    """
    User mavjud bo'lmasa yaratadi.
    Mavjud bo'lsa yangilaydi.
    """

    return await get_or_create_user(
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
    )


# =========================================================
# CHECK USER
# =========================================================

async def user_exists(
    telegram_id: int,
):
    """
    User mavjudligini tekshiradi.
    """

    user = await get_user_by_telegram_id(
        telegram_id
    )

    return user is not None
