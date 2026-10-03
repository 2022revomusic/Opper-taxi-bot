from dataclasses import dataclass
from typing import Optional


# =========================
# USER
# =========================

@dataclass
class User:
    id: int
    telegram_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    created_at: str = ""
    updated_at: str = ""


# =========================
# DRIVER
# =========================

@dataclass
class Driver:
    id: int
    telegram_id: int
    full_name: str = ""
    phone: str = ""
    region: str = ""
    district: str = ""
    passport_file: str = ""
    driver_license_file: str = ""
    status: str = "pending"
    created_at: str = ""
    updated_at: str = ""


# =========================
# CAR
# =========================

@dataclass
class Car:
    id: int
    driver_telegram_id: int
    brand: str = ""
    model: str = ""
    color: str = ""
    plate: str = ""
    seats: int = 4
    created_at: str = ""


# =========================
# RIDE
# =========================

@dataclass
class Ride:
    id: int
    driver_telegram_id: int
    from_region: str
    from_district: str
    to_region: str
    to_district: str
    travel_date: str
    travel_time: str
    price: int
    seats: int
    available_seats: int
    car_id: Optional[int] = None
    note: str = ""
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""


# =========================
# ORDER
# =========================

@dataclass
class Order:
    id: int
    ride_id: int
    passenger_telegram_id: int
    driver_telegram_id: int
    seats: int = 1
    phone: str = ""
    note: str = ""
    status: str = "pending"
    created_at: str = ""
    updated_at: str = ""


# =========================
# RATING
# =========================

@dataclass
class Rating:
    id: int
    ride_id: Optional[int]
    from_telegram_id: int
    to_telegram_id: int
    rating: int
    comment: str = ""
    created_at: str = ""


# =========================
# NOTIFICATION
# =========================

@dataclass
class Notification:
    id: int
    telegram_id: int
    title: str = ""
    message: str = ""
    type: str = "info"
    is_read: int = 0
    created_at: str = ""


# =========================
# PASSENGER REQUEST
# =========================

@dataclass
class PassengerRequest:
    id: int
    passenger_telegram_id: int
    from_region: str
    from_district: str
    to_region: str
    to_district: str
    travel_date: str
    travel_time: str = ""
    seats: int = 1
    price: int = 0
    note: str = ""
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""


# =========================
# REPORT
# =========================

@dataclass
class Report:
    id: int
    reporter_telegram_id: int
    target_telegram_id: Optional[int] = None
    ride_id: Optional[int] = None
    order_id: Optional[int] = None
    reason: str = ""
    status: str = "new"
    created_at: str = ""


# =========================
# ADMIN ACTION
# =========================

@dataclass
class AdminAction:
    id: int
    admin_telegram_id: int
    action: str
    target_telegram_id: Optional[int] = None
    details: str = ""
    created_at: str = ""


# =========================
# DRIVER STATUS
# =========================

DRIVER_PENDING = "pending"
DRIVER_APPROVED = "approved"
DRIVER_REJECTED = "rejected"


# =========================
# RIDE STATUS
# =========================

RIDE_ACTIVE = "active"
RIDE_FULL = "full"
RIDE_CANCELLED = "cancelled"
RIDE_FINISHED = "finished"


# =========================
# ORDER STATUS
# =========================

ORDER_PENDING = "pending"
ORDER_ACCEPTED = "accepted"
ORDER_REJECTED = "rejected"
ORDER_CANCELLED = "cancelled"
ORDER_FINISHED = "finished"


# =========================
# NOTIFICATION TYPES
# =========================

NOTIFICATION_ORDER = "order"
NOTIFICATION_RIDE = "ride"
NOTIFICATION_DRIVER = "driver"
NOTIFICATION_SYSTEM = "system"
NOTIFICATION_RATING = "rating"


# =========================
# VALIDATION
# =========================

def valid_rating(value: int) -> bool:
    return 1 <= value <= 5


def valid_seats(value: int) -> bool:
    return 1 <= value <= 4


def valid_driver_status(value: str) -> bool:
    return value in {
        DRIVER_PENDING,
        DRIVER_APPROVED,
        DRIVER_REJECTED,
    }


def valid_ride_status(value: str) -> bool:
    return value in {
        RIDE_ACTIVE,
        RIDE_FULL,
        RIDE_CANCELLED,
        RIDE_FINISHED,
    }


def valid_order_status(value: str) -> bool:
    return value in {
        ORDER_PENDING,
        ORDER_ACCEPTED,
        ORDER_REJECTED,
        ORDER_CANCELLED,
        ORDER_FINISHED,
    }
