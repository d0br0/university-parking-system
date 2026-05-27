from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Vehicle
from app.schemas import VehicleCreate, VehicleOut, Message

router = APIRouter(prefix="/vehicles", tags=["Транспортные средства"])


@router.get("/", response_model=List[VehicleOut])
async def get_vehicles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Возвращает список активных транспортных средств текущего пользователя."""
    return db.query(Vehicle).filter(
        Vehicle.user_id == current_user.id,
        Vehicle.is_active == True
    ).all()


@router.post("/", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    license_plate: str = Form(...),
    model: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Регистрация нового транспортного средства."""
    # Проверка на дубликат номера
    existing = db.query(Vehicle).filter(Vehicle.license_plate == license_plate).first()
    if existing:
        if existing.user_id == current_user.id:
            if not existing.is_active:
                existing.is_active = True
                db.commit()
                db.refresh(existing)
                return existing
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Это транспортное средство уже зарегистрировано за вами"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Транспортное средство с таким номером уже зарегистрировано в системе"
        )

    vehicle = Vehicle(
        user_id=current_user.id,
        license_plate=license_plate,
        model=model,
        color=color,
        is_active=True
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", response_model=Message)
async def delete_vehicle(
    vehicle_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Деактивация транспортного средства (мягкое удаление)."""
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.user_id == current_user.id
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транспортное средство не найдено"
        )
        
    vehicle.is_active = False
    db.commit()
    return Message(detail="Транспортное средство удалено")
