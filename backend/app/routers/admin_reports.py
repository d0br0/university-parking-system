"""
Роутер для административных отчётов.

Предоставляет API для получения аналитических данных
по парковочным сессиям, выручке и загрузке.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/admin/reports", tags=["admin_reports"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    """Проверка прав администратора."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user


class GroupBy(str, Enum):
    """Период группировки для отчётов"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


def get_date_range(date_from: Optional[datetime], date_to: Optional[datetime]) -> tuple:
    """Получить диапазон дат для отчёта"""
    if not date_to:
        date_to = datetime.now(timezone.utc)
    if not date_from:
        date_from = date_to - timedelta(days=30)
    
    return date_from, date_to


@router.get("/overview")
def get_admin_overview(
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Получить сводку для админ-панели.
    
    Требует прав администратора.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Активные сессии (pending)
    active_sessions_count = db.query(models.Session).filter(
        models.Session.status == "pending"
    ).count()
    
    # Сессии за сегодня
    today_sessions = db.query(models.Session).filter(
        models.Session.entry_time >= today_start
    ).count()
    
    # Выручка за сегодня
    today_revenue = db.query(func.sum(models.Session.cost)).filter(
        and_(
            models.Session.entry_time >= today_start,
            models.Session.status.in_(["paid", "closed"])
        )
    ).scalar() or 0
    
    # Выручка за неделю
    week_revenue = db.query(func.sum(models.Session.cost)).filter(
        and_(
            models.Session.entry_time >= week_ago,
            models.Session.status.in_(["paid", "closed"])
        )
    ).scalar() or 0
    
    # Выручка за месяц
    month_revenue = db.query(func.sum(models.Session.cost)).filter(
        and_(
            models.Session.entry_time >= month_ago,
            models.Session.status.in_(["paid", "closed"])
        )
    ).scalar() or 0
    
    # Общее количество пользователей
    total_users = db.query(models.User).count()
    
    # Новые пользователи за неделю
    new_users_week = db.query(models.User).filter(
        models.User.created_at >= week_ago
    ).count()
    
    # Общее количество ТС
    total_vehicles = db.query(models.Vehicle).count()
    
    # Средняя длительность сессии (в минутах)
    avg_duration = db.query(
        func.avg(
            func.julianday(models.Session.exit_time) - func.julianday(models.Session.entry_time)
        ) * 24 * 60
    ).filter(
        and_(
            models.Session.exit_time.isnot(None),
            models.Session.status.in_(["paid", "closed"])
        )
    ).scalar() or 0
    
    return {
        "period": {
            "today": today_start,
            "week_ago": week_ago,
            "month_ago": month_ago
        },
        "sessions": {
            "active_now": active_sessions_count,
            "today": today_sessions
        },
        "revenue": {
            "today": round(float(today_revenue), 2),
            "week": round(float(week_revenue), 2),
            "month": round(float(month_revenue), 2)
        },
        "users": {
            "total": total_users,
            "new_this_week": new_users_week
        },
        "vehicles": {
            "total": total_vehicles
        },
        "statistics": {
            "avg_session_duration_minutes": round(float(avg_duration), 2)
        }
    }
