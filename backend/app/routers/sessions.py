from datetime import datetime, timezone, timedelta
from decimal import Decimal
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Vehicle, Session as ParkingSession, Tariff, ParkingZone
from app.schemas import (
    SessionCreate, SessionOut, Message, 
    SessionHistoryListResponse, SessionHistoryItem,
    SessionReceiptResponse, VehicleOut, SessionStatus
)
from app.services.cost import calculate_cost
from app.middleware.flash import flash, FlashType, get_flash_message, clear_flash_cookie

router = APIRouter(prefix="/sessions", tags=["Сессии парковки"])

logger = logging.getLogger(__name__)


@router.post(
    "/start",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": Message, "description": "Транспортное средство не найдено"},
        403: {"model": Message, "description": "Транспортное средство не принадлежит пользователю"},
    },
)
async def start_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Начало новой сессии парковки."""
    # Проверка принадлежности авто пользователю
    logger.info(f"Поиск vehicle_id={session_data.vehicle_id} (type={type(session_data.vehicle_id)}), user_id={current_user.id} (type={type(current_user.id)})")
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == session_data.vehicle_id,
        Vehicle.user_id == current_user.id,
        Vehicle.is_active == True,
    ).first()
    if not vehicle:
        # Уточняем причину
        vehicle_exists = db.query(Vehicle).filter(
            Vehicle.id == session_data.vehicle_id
        ).first()
        logger.info(f"vehicle_exists={vehicle_exists}, vehicle_id in db? {db.query(Vehicle.id).all()}")
        if not vehicle_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Транспортное средство не найдено",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Транспортное средство не принадлежит вам или неактивно",
        )

    # Проверка наличия активной сессии (опционально, можно добавить)
    active_session = db.query(ParkingSession).filter(
        ParkingSession.vehicle_id == vehicle.id,
        ParkingSession.status == "pending",
    ).first()
    if active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У этого транспортного средства уже есть активная сессия",
        )

    # Создание сессии
    new_session = ParkingSession(
        user_id=current_user.id,
        vehicle_id=vehicle.id,
        zone_id=session_data.zone_id,
        entry_time=datetime.now(timezone.utc),
        exit_time=None,
        status="pending",
        cost=Decimal("0.00"),
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return new_session


@router.post(
    "/{session_id}/end",
    response_model=SessionOut,
    responses={
        404: {"model": Message, "description": "Сессия не найдена"},
        403: {"model": Message, "description": "Сессия не принадлежит пользователю"},
        400: {"model": Message, "description": "Сессия уже завершена"},
    },
)
async def end_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Завершение сессии парковки."""
    # Поиск сессии
    session = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )

    # Проверка владения
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Сессия не принадлежит вам",
        )

    # Проверка статуса
    if session.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сессия уже завершена",
        )

    # Сохраняем исходный статус
    original_status = session.status

    # Обновление сессии
    session.exit_time = datetime.now(timezone.utc)
    session.status = "closed"

    # Пересчёт стоимости для pending сессий
    if original_status == "pending":
        # Получаем тариф (берём первый)
        tariff = db.query(Tariff).first()
        if not tariff:
            logger.error("Тарифы не настроены")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка: тарифы не настроены",
            )
        # Рассчитываем стоимость
        cost = calculate_cost(session.entry_time, session.exit_time, tariff)
        session.cost = Decimal(str(cost))
        logger.info(f"Сессия {session.id} пересчитана, стоимость {cost}")
    # Для paid сессий стоимость уже установлена, оставляем как есть

    db.commit()
    db.refresh(session)

    return session


@router.get(
    "/",
    response_model=List[SessionOut],
    responses={
        401: {"model": Message, "description": "Требуется аутентификация"},
    },
)
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Возвращает последние 50 сессий текущего пользователя."""
    sessions = (
        db.query(ParkingSession)
        .filter(ParkingSession.user_id == current_user.id)
        .order_by(desc(ParkingSession.entry_time))
        .limit(50)
        .all()
    )
    return sessions


@router.get(
    "/{session_id}",
    response_model=SessionOut,
    responses={
        404: {"model": Message, "description": "Сессия не найдена"},
        403: {"model": Message, "description": "Сессия не принадлежит пользователю"},
    },
)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получение сессии по ID."""
    session = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Сессия не принадлежит вам",
        )
    return session


@router.get(
    "/active",
    response_model=Optional[SessionOut],
)
async def get_active_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Возвращает текущую активную сессию пользователя (status='pending' или 'paid')."""
    session = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.user_id == current_user.id,
            ParkingSession.status.in_(["pending", "paid"]),
            ParkingSession.exit_time.is_(None),
        )
        .first()
    )
    
    if session:
        # Добавляем zone_name для фронтенда
        if session.zone_id:
            zone = db.query(ParkingZone).filter(ParkingZone.id == session.zone_id).first()
            if zone:
                session.zone_name = zone.name
        
        # Устанавливаем алиасы для фронтенда
        session.started_at = session.entry_time
        session.current_cost = session.cost
        
    return session


@router.get(
    "/history",
    response_model=SessionHistoryListResponse,
    responses={
        401: {"model": Message, "description": "Требуется аутентификация"},
    },
)
async def get_session_history(
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(10, ge=1, le=100, description="Элементов на странице"),
    date_from: Optional[datetime] = Query(None, description="Фильтр: дата начала (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Фильтр: дата окончания (ISO format)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить историю завершённых сессий текущего пользователя с пагинацией.
    """
    from app.schemas import SessionHistoryItem
    
    # Базовый запрос для завершённых сессий пользователя
    query = db.query(ParkingSession).filter(
        ParkingSession.user_id == current_user.id,
        ParkingSession.status.in_(["closed", "paid"])
    )
    
    # Применяем фильтры по дате
    if date_from:
        query = query.filter(ParkingSession.entry_time >= date_from)
    if date_to:
        query = query.filter(ParkingSession.entry_time <= date_to)
    
    # Считаем общее количество для пагинации
    total_count = query.count()
    
    # Получаем сессии для текущей страницы (сортировка по времени входа, новые первые)
    sessions = query.order_by(desc(ParkingSession.entry_time)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    # Формируем ответ
    session_items = []
    for session in sessions:
        vehicle = db.query(Vehicle).filter(
            Vehicle.id == session.vehicle_id
        ).first()
        
        if not vehicle:
            logger.warning(f"Vehicle not found for session {session.id}")
            continue

        # Расчёт длительности
        duration_minutes = 0
        if session.exit_time and session.entry_time:
            duration_minutes = int((session.exit_time - session.entry_time).total_seconds() / 60)
        
        # Конвертируем статус в строку для безопасности или используем Enum
        status_val = session.status
        if hasattr(status_val, 'value'):
            status_val = status_val.value

        # Получаем имя зоны
        zone_name = None
        if session.zone_id:
            zone = db.query(ParkingZone).filter(ParkingZone.id == session.zone_id).first()
            if zone:
                zone_name = zone.name

        session_items.append(SessionHistoryItem(
            id=session.id,
            vehicle=VehicleOut(
                id=vehicle.id,
                user_id=vehicle.user_id,
                license_plate=vehicle.license_plate,
                is_active=vehicle.is_active
            ),
            entry_time=session.entry_time,
            exit_time=session.exit_time,
            status=status_val,
            total_cost=session.cost or Decimal("0"),
            duration_minutes=duration_minutes,
            zone_name=zone_name
        ))
    
    return SessionHistoryListResponse(
        items=session_items,
        total=total_count,
        page=page,
        per_page=per_page,
        total_pages=(total_count + per_page - 1) // per_page if per_page > 0 else 0
    )


@router.get(
    "/history/{session_id}/receipt",
    response_model=SessionReceiptResponse,
    responses={
        404: {"model": Message, "description": "Сессия не найдена"},
        403: {"model": Message, "description": "Сессия не принадлежит пользователю"},
    },
)
async def get_session_receipt(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить детали сессии для чека/квитанции.
    """
    from math import ceil
    
    session = db.query(ParkingSession).filter(
        ParkingSession.id == session_id,
        ParkingSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == session.vehicle_id
    ).first()
    
    # Получаем тариф для расчёта
    tariff = db.query(Tariff).first()
    hourly_rate = tariff.price_per_hour if tariff else Decimal("100")
    
    # Расчёт деталей
    duration_minutes = 0
    hours_charged = 0
    if session.exit_time and session.entry_time:
        duration_minutes = int((session.exit_time - session.entry_time).total_seconds() / 60)
        # Округление до часов как в cost_service
        if duration_minutes > 15:
            hours_charged = ceil((duration_minutes - 15) / 60)
            hours_charged = max(hours_charged, 1)
    
    return SessionReceiptResponse(
        session_id=session.id,
        vehicle_plate=vehicle.license_plate,
        vehicle_type="CAR",  # Упрощённо
        entry_time=session.entry_time,
        exit_time=session.exit_time,
        duration_minutes=duration_minutes,
        hours_charged=hours_charged,
        hourly_rate=hourly_rate,
        total_cost=session.cost or Decimal("0"),
        paid_at=None,  # TODO: брать из payment
        status=session.status
    )