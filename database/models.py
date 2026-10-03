from dataclasses import dataclass
from typing import Optional


# =========================================================
# OPPER TAXI — DATABASE MODELS
# =========================================================


@dataclass
class User:
    id: int
    telegram_id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    phone: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Driver:
    id: int
    user_id: int
    phone: str = ""
    status: str = "pending"
    car_id: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Ride:
    id: int
    driver_id: int
    from_region: str
    from_district: str
    to_region: str
    to_district: str
    travel_date: str
    travel_time: str
    seats: int
    available_seats: int
    price: int
    status: str = "active"
    created_at: str = ""


@dataclass
class Order:
    id: int
    ride_id: int
    passenger_id: int
    seats: int = 1
    status: str = "pending"
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Rating:
    id: int
    ride_id: int
    order_id: Optional[int]
    from_user_id: int
    to_user_id: int
    rating: int
    comment: str = ""
    created_at: str = ""


@dataclass
class Notification:
    id: int
    user_id: int
    type: str
    title: str
    message: str
    is_read: int = 0
    created_at: str = ""


# =========================================================
# STATUS CONSTANTS
# =========================================================

# Driver
DRIVER_PENDING = "pending"
DRIVER_APPROVED = "approved"
DRIVER_REJECTED = "rejected"


# Ride
RIDE_ACTIVE = "active"
RIDE_FULL = "full"
RIDE_CANCELLED = "cancelled"
RIDE_FINISHED = "finished"


# Order
ORDER_PENDING = "pending"
ORDER_ACCEPTED = "accepted"
ORDER_REJECTED = "rejected"
ORDER_CANCELLED = "cancelled"
ORDER_FINISHED = "finished"


# Notification
NOTIFICATION_ORDER = "order"
NOTIFICATION_RIDE = "ride"
NOTIFICATION_DRIVER = "driver"
NOTIFICATION_SYSTEM = "system"
NOTIFICATION_RATING = "rating"


# =========================================================
# VALIDATION
# =========================================================

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
