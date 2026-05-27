"""
Роутер для управления парковочными зонами.

CRUD операции для зон парковки.
Доступ: публичный (чтение), админ (модификация).
"""

import uuid
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/zones", tags=["Парковочные зоны"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    """Проверка прав администратора."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user


@router.get("/", response_model=List[schemas.ZoneOut])
def list_zones(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Получить список парковочных зон.
    
    - **active_only**: Показывать только активные зоны
    """
    query = db.query(models.ParkingZone)
    
    if active_only:
        query = query.filter(models.ParkingZone.is_active == True)
    
    zones = query.order_by(models.ParkingZone.name).all()
    
    return zones


@router.get("/{zone_id}", response_model=schemas.ZoneOut)
def get_zone(
    zone_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Получить детальную информацию о зоне.
    """
    zone = db.query(models.ParkingZone).filter(models.ParkingZone.id == zone_id).first()
    
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Зона не найдена"
        )
    
    return zone


@router.get("/{zone_id}/availability")
def get_zone_availability(
    zone_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Получить информацию о доступности мест в зоне.
    
    Возвращает:
    - total_spots: Всего мест
    - occupied_spots: Занято мест
    - available_spots: Свободно мест
    - occupancy_rate: Процент заполненности
    """
    zone = db.query(models.ParkingZone).filter(
        models.ParkingZone.id == zone_id,
        models.ParkingZone.is_active == True
    ).first()
    
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Зона не найдена или неактивна"
        )
    
    # Подсчёт активных сессий в зоне
    active_sessions_count = db.query(models.Session).filter(
        models.Session.zone_id == zone_id,
        models.Session.status.in_(["pending", "paid"])
    ).count()
    
    total_spots = int(zone.total_spots) if zone.total_spots else 0
    occupied = min(active_sessions_count, total_spots) if total_spots > 0 else active_sessions_count
    available = max(0, total_spots - occupied) if total_spots > 0 else 0
    occupancy_rate = (occupied / total_spots * 100) if total_spots > 0 else 0
    
    return {
        "zone_id": zone_id,
        "zone_name": zone.name,
        "total_spots": total_spots,
        "occupied_spots": occupied,
        "available_spots": available,
        "occupancy_rate": round(occupancy_rate, 2),
        "is_full": available == 0 and total_spots > 0,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }


# ===== ADMIN ENDPOINTS =====

@router.post("/", response_model=schemas.ZoneOut, status_code=status.HTTP_201_CREATED)
def create_zone(
    zone_data: schemas.ZoneCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    """
    Создать новую парковочную зону.
    
    Требуются права администратора.
    """
    # Проверка уникальности имени
    existing = db.query(models.ParkingZone).filter(
        models.ParkingZone.name == zone_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Зона с названием '{zone_data.name}' уже существует"
        )
    
    # Создание зоны
    new_zone = models.ParkingZone(
        name=zone_data.name,
        description=zone_data.description,
        location=zone_data.location,
        total_spots=zone_data.total_spots,
        is_active=zone_data.is_active,
        tariff_id=zone_data.tariff_id
    )
    
    db.add(new_zone)
    db.commit()
    db.refresh(new_zone)
    
    return new_zone


@router.put("/{zone_id}", response_model=schemas.ZoneOut)
def update_zone(
    zone_id: uuid.UUID,
    zone_data: schemas.ZoneUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    """
    Обновить парковочную зону.
    
    Требуются права администратора.
    """
    zone = db.query(models.ParkingZone).filter(models.ParkingZone.id == zone_id).first()
    
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Зона не найдена"
        )
    
    # Проверка уникальности имени, если оно меняется
    if zone_data.name and zone_data.name != zone.name:
        existing = db.query(models.ParkingZone).filter(
            models.ParkingZone.name == zone_data.name
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Зона с названием '{zone_data.name}' уже существует"
            )
    
    # Обновление полей
    update_data = zone_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)
    
    db.commit()
    db.refresh(zone)
    
    return zone


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    zone_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    """
    Удалить парковочную зону (soft delete через деактивацию).
    
    Требуются права администратора.
    """
    zone = db.query(models.ParkingZone).filter(models.ParkingZone.id == zone_id).first()
    
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Зона не найдена"
        )
    
    # Soft delete - деактивация
    zone.is_active = False
    db.commit()