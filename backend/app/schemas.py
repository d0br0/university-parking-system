import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Union
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


from enum import Enum as PyEnum

# ---------- User ----------
class UserBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(UserBase):
    id: UUID
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Vehicle ----------
class VehicleBase(BaseModel):
    license_plate: str = Field(..., max_length=20)


class VehicleCreate(VehicleBase):
    @field_validator("license_plate")
    @classmethod
    def validate_license_plate(cls, v: str) -> str:
        # Регулярное выражение для российских номеров:
        # одна буква (A-Z или А-Я), три цифры, две буквы, две или три цифры
        pattern = r"^[A-ZА-Я]{1}\d{3}[A-ZА-Я]{2}\d{2,3}$"
        if not re.match(pattern, v.upper()):
            raise ValueError(
                "Номер должен соответствовать формату: одна буква, три цифры, две буквы, две или три цифры"
            )
        return v.upper()


class VehicleOut(VehicleBase):
    id: UUID
    user_id: UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ---------- Tariff ----------
class TariffBase(BaseModel):
    name: str = Field(..., max_length=100)
    price_per_hour: Decimal = Field(..., ge=0)
    daily_cap: Decimal = Field(..., ge=0)


class TariffOut(TariffBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


# ---------- Session ----------
class SessionStatus(str, PyEnum):
    PENDING = "pending"
    PAID = "paid"
    CLOSED = "closed"


class SessionBase(BaseModel):
    vehicle_id: UUID


class SessionCreate(SessionBase):
    zone_id: Optional[UUID] = None


class SessionOut(BaseModel):
    id: UUID
    user_id: UUID
    vehicle_id: UUID
    zone_id: Optional[UUID] = None
    zone_name: Optional[str] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    status: SessionStatus
    cost: Decimal
    
    # Поля для фронтенда (dashboard)
    started_at: Optional[datetime] = None
    current_cost: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class SessionEnd(BaseModel):
    pass


# ---------- Payment ----------
class PaymentBase(BaseModel):
    amount: Decimal = Field(..., ge=0)
    status: str


class PaymentOut(PaymentBase):
    id: UUID
    session_id: UUID
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Token ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Session History ----------
class SessionHistoryItem(BaseModel):
    """Элемент истории сессий"""
    id: UUID
    vehicle: VehicleOut
    entry_time: datetime
    exit_time: Optional[datetime] = None
    status: str
    total_cost: Decimal
    duration_minutes: int
    zone_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SessionHistoryListResponse(BaseModel):
    """Ответ со списком истории сессий"""
    items: List[SessionHistoryItem]
    total: int
    page: int
    per_page: int
    total_pages: int


# ---------- Session Receipt ----------
class SessionReceiptResponse(BaseModel):
    """Детали сессии для чека/квитанции"""
    session_id: UUID
    vehicle_plate: str
    vehicle_type: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    duration_minutes: int
    hours_charged: int
    hourly_rate: Decimal
    total_cost: Decimal
    paid_at: Optional[datetime] = None
    status: str
    
    model_config = ConfigDict(from_attributes=True)


# ---------- Flash Message ----------
class FlashMessage(BaseModel):
    """Flash-сообщение для отображения"""
    id: str
    message: str
    type: str  # success, error, warning, info


# ---------- Parking Zone ----------
class ZoneBase(BaseModel):
    """Базовая схема парковочной зоны"""
    name: str = Field(..., min_length=1, max_length=50, description="Название зоны")
    description: Optional[str] = Field(None, max_length=500, description="Описание зоны")
    location: Optional[str] = Field(None, max_length=255, description="Адрес или координаты")
    total_spots: int = Field(default=0, ge=0, description="Общее количество мест")
    is_active: bool = Field(default=True, description="Активна ли зона")


class ZoneCreate(ZoneBase):
    """Схема создания зоны"""
    tariff_id: Optional[UUID] = Field(None, description="ID тарифа")


class ZoneUpdate(BaseModel):
    """Схема обновления зоны"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    total_spots: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    tariff_id: Optional[UUID] = None


class ZoneOut(ZoneBase):
    """Схема вывода зоны"""
    id: UUID
    tariff_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Generic ----------
class Message(BaseModel):
    detail: str
