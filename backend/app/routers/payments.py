import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Tariff
from app.services.cost import calculate_cost
from app.services.mock_payment import init_payment, confirm_payment

router = APIRouter(prefix="/payments", tags=["Платежи"])

logger = logging.getLogger(__name__)


@router.get("/init/{session_id}")
async def payment_init(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Инициирует mock-платёж для указанной сессии.

    Возвращает:
        {
            "payment_id": UUID,
            "amount": float,
            "mock_url": str
        }
    """
    try:
        payment = init_payment(session_id, db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Ошибка при инициировании платежа: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервиса оплаты",
        )

    # Рассчитываем сумму для отображения (можно использовать amount из платежа)
    # Но payment.amount уже содержит рассчитанную сумму
    amount = float(payment.amount)

    # Формируем mock URL для подтверждения (роут callback)
    mock_url = f"/api/payments/callback/{payment.id}"

    logger.info(f"Платёж инициирован: {payment.id} для сессии {session_id}, сумма {amount}")

    return {
        "payment_id": payment.id,
        "amount": amount,
        "mock_url": mock_url,
    }


@router.get("/callback/{payment_id}")
async def payment_callback(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Подтверждает mock-платёж и перенаправляет на страницу сессии.

    В реальном шлюзе это endpoint, куда шлюз отправляет после успешной оплаты.
    Здесь мы просто вызываем confirm_payment и делаем редирект.
    """
    try:
        result = confirm_payment(payment_id, db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Ошибка при подтверждении платежа: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервиса оплаты",
        )

    # Редирект на страницу сессии с параметром paid=true
    from fastapi.responses import RedirectResponse

    redirect_url = f"/session/{result['session_id']}?paid=true"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)