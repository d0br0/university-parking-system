import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Session as ParkingSession, Payment, Tariff
from app.services.cost import calculate_cost

logger = logging.getLogger(__name__)


def init_payment(session_id: UUID, db: Session, user_id: UUID) -> Payment:
    """
    Инициирует mock-платёж для сессии.

    Проверяет:
    - Сессия существует и принадлежит пользователю.
    - Статус сессии "pending".
    - Сессия ещё не оплачена (нет успешного платежа).

    Создаёт запись Payment со статусом "pending".

    Параметры:
        session_id: UUID сессии
        db: сессия БД
        user_id: UUID пользователя (для проверки владения)

    Возвращает:
        Объект Payment

    Исключения:
        HTTPException (должны быть обработаны на уровне роутера)
    """
    # Получаем сессию с проверкой владения
    session = db.query(ParkingSession).filter(
        ParkingSession.id == session_id,
        ParkingSession.user_id == user_id,
    ).first()
    if not session:
        logger.warning(f"Сессия {session_id} не найдена или не принадлежит пользователю {user_id}")
        raise ValueError("Сессия не найдена или доступ запрещён")

    if session.status not in ["pending", "closed"]:
        logger.warning(f"Невозможно инициировать платёж для сессии {session_id} со статусом {session.status}")
        raise ValueError("Сессия не находится в статусе pending или closed")

    # Проверяем, нет ли уже успешного платежа для этой сессии
    existing_success = db.query(Payment).filter(
        Payment.session_id == session_id,
        Payment.status == "completed",
    ).first()
    if existing_success:
        logger.warning(f"Для сессии {session_id} уже существует успешный платёж {existing_success.id}")
        raise ValueError("Сессия уже оплачена")

    # Рассчитываем стоимость (если exit_time отсутствует, используем текущее время)
    exit_time = session.exit_time or datetime.now(timezone.utc)
    # Получаем тариф (берём первый из базы, в реальной системе должен быть привязан к сессии)
    tariff = db.query(Tariff).first()
    if not tariff:
        logger.error("В базе отсутствуют тарифы")
        raise RuntimeError("Тарифы не настроены")

    amount = calculate_cost(session.entry_time, exit_time, tariff)

    # Создаём платёж
    payment = Payment(
        session_id=session_id,
        amount=Decimal(str(amount)),
        status="pending",
        transaction_id=None,
        paid_at=None,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    logger.info(f"Создан mock-платёж {payment.id} для сессии {session_id} на сумму {amount}")
    return payment


def confirm_payment(payment_id: UUID, db: Session, user_id: UUID) -> dict:
    """
    Подтверждает mock-платёж (имитация успешной оплаты).

    Действия:
    - Находит платёж по ID.
    - Проверяет, что платёж в статусе "pending".
    - Проверяет, что связанная сессия принадлежит пользователю.
    - Устанавливает статус платежа "completed", paid_at = текущее время.
    - Пересчитывает стоимость сессии (используя текущий тариф).
    - Обновляет стоимость сессии и меняет её статус на "paid".
    - Фиксирует изменения в БД.

    Параметры:
        payment_id: UUID платежа
        db: сессия БД
        user_id: UUID пользователя (для проверки владения)

    Возвращает:
        Словарь с ключами:
            success: bool
            payment_id: UUID
            session_id: UUID
            amount: float
            message: str
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        logger.warning(f"Платёж {payment_id} не найден")
        raise ValueError("Платёж не найден")

    # Проверяем владение через связанную сессию
    session = db.query(ParkingSession).filter(ParkingSession.id == payment.session_id).first()
    if not session or session.user_id != user_id:
        logger.warning(f"Платёж {payment_id} не принадлежит пользователю {user_id}")
        raise ValueError("Доступ к платежу запрещён")

    if payment.status != "pending":
        logger.warning(f"Платёж {payment_id} имеет статус {payment.status}, а не pending")
        raise ValueError("Платёж уже обработан")

    # Получаем тариф для пересчёта
    tariff = db.query(Tariff).first()
    if not tariff:
        logger.error("В базе отсутствуют тарифы")
        raise RuntimeError("Тарифы не настроены")

    # Пересчитываем стоимость сессии
    exit_time = session.exit_time or datetime.now(timezone.utc)
    new_cost = calculate_cost(session.entry_time, exit_time, tariff)

    # Обновляем платёж
    payment.status = "completed"
    payment.paid_at = datetime.now(timezone.utc)
    payment.amount = Decimal(str(new_cost))  # обновляем сумму на актуальную
    db.add(payment)

    # Обновляем сессию
    session.cost = Decimal(str(new_cost))
    session.status = "paid"
    db.add(session)

    db.commit()
    logger.info(f"Платёж {payment_id} подтверждён. Сессия {session.id} переведена в paid со стоимостью {new_cost}")

    return {
        "success": True,
        "payment_id": payment_id,
        "session_id": session.id,
        "amount": new_cost,
        "message": "Оплата успешно завершена",
    }