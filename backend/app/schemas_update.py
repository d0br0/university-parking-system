"""
Дополнительные схемы для проекта
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ---------- Parking Zone Schemas ----------

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
