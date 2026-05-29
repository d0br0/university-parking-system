import os
import shutil
import uuid
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_password_hash
from app.database import get_db
from app.models import User
from app.schemas import UserUpdate, UserOut, Message

router = APIRouter(prefix="/users", tags=["Пользователи"])

# Путь для сохранения аватаров (внутри статики фронтенда для доступа через /static)
# Определяем базовую директорию проекта (на уровень выше app)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "frontend" / "static" / "uploads" / "avatars"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получить данные текущего пользователя."""
    return current_user

@router.put("/me", response_model=UserOut)
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить профиль пользователя."""
    if user_data.email:
        # Проверяем, не занят ли email другим пользователем
        existing = db.query(User).filter(User.email == user_data.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email уже занят")
        current_user.email = user_data.email
    
    if user_data.phone is not None:
        current_user.phone = user_data.phone
        
    if user_data.password:
        current_user.password_hash = get_password_hash(user_data.password)
        
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Загрузить аватар пользователя."""
    # Проверка типа файла
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")
    
    # Генерация уникального имени
    file_ext = os.path.splitext(file.filename)[1]
    if not file_ext:
        file_ext = ".jpg"
    
    file_name = f"{current_user.id}_{uuid.uuid4().hex}{file_ext}"
    file_path = UPLOAD_DIR / file_name
    
    # Сохранение файла
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Удаление старого аватара, если он был
    if current_user.avatar_url:
        try:
            old_file_name = current_user.avatar_url.split("/")[-1]
            old_file_path = UPLOAD_DIR / old_file_name
            if old_file_path.exists():
                old_file_path.unlink()
        except Exception:
            pass
                
    # Обновление ссылки в БД для фронтенда
    current_user.avatar_url = f"/static/uploads/avatars/{file_name}"
    db.commit()
    db.refresh(current_user)
    
    return current_user