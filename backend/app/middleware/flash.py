"""
Flash-уведомления через cookie.

Использование в endpoint'ах:
    from app.middleware.flash import flash, FlashType
    
    flash(response, "Операция успешна!", FlashType.SUCCESS)
"""

import json
import urllib.parse
from enum import Enum
from typing import Optional
from fastapi import Response


class FlashType(str, Enum):
    """Типы flash-уведомлений"""
    SUCCESS = "success"    # Зелёный - успех
    ERROR = "error"        # Красный - ошибка
    WARNING = "warning"    # Жёлтый - предупреждение
    INFO = "info"          # Синий - информация


class FlashMessage:
    """Модель flash-сообщения"""
    def __init__(self, message: str, type: FlashType, id: Optional[str] = None):
        self.message = message
        self.type = type
        self.id = id or f"flash_{hash(message + type.value) & 0xFFFFFFFF}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "type": self.type.value
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def flash(response: Response, message: str, type: FlashType = FlashType.INFO) -> None:
    """
    Добавить flash-сообщение в cookie.
    
    Args:
        response: HTTP Response объект
        message: Текст сообщения
        type: Тип сообщения (success, error, warning, info)
    """
    flash_msg = FlashMessage(message, type)
    # URL-кодируем JSON для безопасного хранения в cookie
    encoded = urllib.parse.quote(flash_msg.to_json())
    
    response.set_cookie(
        key="flash_message",
        value=encoded,
        max_age=30,  # 30 секунд - достаточно для обработки
        httponly=False,  # Доступно для JavaScript
        samesite="lax"
    )


def get_flash_message(request) -> Optional[FlashMessage]:
    """
    Получить flash-сообщение из cookie запроса.
    
    Args:
        request: HTTP Request объект
        
    Returns:
        FlashMessage или None
    """
    flash_cookie = request.cookies.get("flash_message")
    if not flash_cookie:
        return None
    
    try:
        decoded = urllib.parse.unquote(flash_cookie)
        data = json.loads(decoded)
        return FlashMessage(
            message=data["message"],
            type=FlashType(data["type"]),
            id=data.get("id")
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def clear_flash_cookie(response: Response) -> None:
    """
    Очистить flash-cookie (вызывать после отображения сообщения).
    
    Args:
        response: HTTP Response объект
    """
    response.delete_cookie(key="flash_message")