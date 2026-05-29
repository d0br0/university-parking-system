from datetime import timedelta
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, UserOut, Message

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": Message, "description": "Пользователь с таким email уже существует"},
    },
)
async def register(
    email: str = Form(...),
    password: str = Form(...),
    phone: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Регистрация нового пользователя."""
    # Проверка существования пользователя с таким email
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже зарегистрирован",
        )

    # Хеширование пароля
    hashed_password = get_password_hash(password)

    # Создание пользователя
    user = User(
        email=email,
        phone=phone,
        password_hash=hashed_password,
        is_admin=False,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка при создании пользователя",
        )

    return user


@router.post("/logout")
async def logout(response: Response):
    """Выход из системы (удаление cookie)."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE
    )
    return {"message": "Успешный выход"}


@router.post(
    "/login",
    response_model=UserOut,
    responses={
        401: {"model": Message, "description": "Неверный email или пароль"},
    },
)
async def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Аутентификация пользователя и установка JWT в httpOnly cookie."""
    # Поиск пользователя
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    # Создание JWT токена
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Установка токена в httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return user


@router.get(
    "/me",
    response_model=UserOut,
    responses={
        401: {"model": Message, "description": "Требуется аутентификация"},
    },
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Возвращает информацию о текущем аутентифицированном пользователе."""
    return current_user


@router.post(
    "/logout",
    response_model=Message,
)
async def logout(response: Response):
    """Выход пользователя (удаление cookie)."""
    response.delete_cookie(key="access_token", path="/")
    return Message(detail="Успешный выход")