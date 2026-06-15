import math
from datetime import datetime, timezone
from decimal import Decimal
from app.models import Tariff


def _ensure_utc(dt: datetime) -> datetime:
    """Преобразует datetime в UTC (aware). Если наивный, предполагает UTC."""
    if dt.tzinfo is None:
        # Наивный datetime, считаем что это UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Aware datetime, конвертируем в UTC
        return dt.astimezone(timezone.utc)


def calculate_cost(entry_time: datetime, exit_time: datetime, tariff: Tariff) -> float:
    """
    Рассчитывает стоимость парковки по тарифу.

    Правила:
    - Первые 15 минут бесплатно.
    - После 15 минут оплата почасово с округлением вверх до целого часа.
    - Пример: 16 минут -> 1 час, 75 минут -> 1 час, 76 минут -> 2 часа.
    - Стоимость = chargeable_hours * tariff.price_per_hour
    - Округление результата до 2 знаков после запятой.
    """
    # Приводим оба времени к UTC aware для корректного сравнения
    entry_utc = _ensure_utc(entry_time)
    exit_utc = _ensure_utc(exit_time)

    if exit_utc <= entry_utc:
        return 0.0

    total_seconds = (exit_utc - entry_utc).total_seconds()
    total_minutes = total_seconds / 60.0

    # Бесплатный период 15 минут
    if total_minutes <= 15:
        return 0.0

    # Оплачиваемые минуты (после первых 15)
    chargeable_minutes = total_minutes - 15
    # Округление до целого часа вверх (минимум 1 час, если просрочено 15 минут)
    chargeable_hours = math.ceil(chargeable_minutes / 60.0)
    chargeable_hours = max(chargeable_hours, 1) if chargeable_minutes > 0 else 0

    # Рассчитываем стоимость
    price_per_hour = Decimal(str(tariff.price_per_hour))
    
    final_cost = Decimal(str(chargeable_hours)) * price_per_hour

    # Округление результата до 2 знаков после запятой
    return float(final_cost.quantize(Decimal("0.01")))