import os
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
import traceback
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

from app.config import settings
from app.database import engine, Base, get_db
from app.models import User, Tariff
from app.auth import get_password_hash, get_current_admin_user, get_current_user
from app.routers import auth, sessions, payments, admin, vehicles, admin_reports, zones

from pathlib import Path

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "frontend" / "templates"
STATIC_DIR = BASE_DIR / "frontend" / "static"

app = FastAPI(
    title="University Parking System",
    description="Информационная система платной парковки у университета",
    version="1.0.0",
    debug=settings.DEBUG,
)

# CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Шаблоны и статика
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    logger.info(f"✅ Статика смонтирована из {STATIC_DIR}")
else:
    logger.warning(f"⚠️ Директория {STATIC_DIR} не найдена, статика не будет обслуживаться")
    logger.info(f"Текущая рабочая директория: {os.getcwd()}")
    logger.info(f"BASE_DIR определен как: {BASE_DIR}")

# Подключение роутеров
app.include_router(auth.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(vehicles.router, prefix="/api")
app.include_router(admin_reports.router)
app.include_router(zones.router)


# Дополнительные эндпоинты для фронтенда
@app.get("/api/zones/{zone_id}/info")
async def get_zone_info(zone_id: str):
    """Возвращает информацию о зоне парковки (заглушка)."""
    import random
    return {
        "zone_id": zone_id,
        "free_spots": random.randint(0, 50),
        "total_spots": 100,
        "price_per_hour": 150
    }


@app.get("/terms")
async def terms_page(request: Request):
    """Страница правил и тарифов."""
    return templates.TemplateResponse("terms.html", {"request": request})


@app.get("/profile")
async def profile_page(request: Request, current_user: User = Depends(get_current_user)):
    """Страница профиля пользователя."""
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user})


@app.get("/register")
async def register_page(request: Request):
    """Страница регистрации."""
    return templates.TemplateResponse("register.html", {"request": request})


# Глобальные обработчики ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTPException (400, 401, 403, 404, ...)."""
    logger.warning(
        f"HTTPException {exc.status_code}: {exc.detail} "
        f"path={request.url.path} method={request.method}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Обработчик ошибок SQLAlchemy."""
    logger.error(f"SQLAlchemyError: {exc}", exc_info=settings.DEBUG)
    error_detail = "Ошибка базы данных"
    if settings.DEBUG:
        error_detail += f": {exc}"
    return JSONResponse(
        status_code=500,
        content={
            "detail": error_detail,
            "error_code": "DB_ERROR",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик всех остальных исключений."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    error_detail = "Внутренняя ошибка сервера"
    if settings.DEBUG:
        error_detail += f": {exc}\n{traceback.format_exc()}"
    return JSONResponse(
        status_code=500,
        content={
            "detail": error_detail,
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


@app.on_event("startup")
async def startup_event():
    """Логирование при запуске приложения, создание таблиц и сидирование БД."""
    logger.info("🚀 Parking System backend запущен")
    logger.info(f"DEBUG режим: {settings.DEBUG}")
    logger.info(f"База данных: {settings.DATABASE_URL}")

    # ВРЕМЕННО: Удаление всех таблиц для исправления типов данных (UUID vs VARCHAR)
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("🗑️ Все старые таблицы удалены")
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении таблиц: {e}")

    # Создание таблиц (если не существуют)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Таблицы БД созданы/проверены")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        raise

    # Проверка подключения к БД
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Подключение к базе данных успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}")
        raise

    # Сидирование тарифов
    db = next(get_db())
    try:
        # Проверка, пуста ли таблица tariffs
        tariff_count = db.query(Tariff).count()
        if tariff_count == 0:
            standard_tariff = Tariff(
                name="standard",
                price_per_hour=Decimal("150.00"),
                daily_cap=Decimal("1200.00"),
            )
            db.add(standard_tariff)
            db.commit()
            logger.info("✅ Тариф 'standard' добавлен")
        else:
            logger.info("✅ Тарифы уже существуют")
    except Exception as e:
        logger.error(f"❌ Ошибка при сидировании тарифов: {e}")
        db.rollback()
    finally:
        db.close()

    # Сидирование администратора
    db = next(get_db())
    try:
        admin_email = "admin@univ.edu"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            hashed = get_password_hash("admin123")
            admin = User(
                email=admin_email,
                phone="+79991234567",
                password_hash=hashed,
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            logger.info("✅ Администратор создан (admin@univ.edu / admin123)")
        else:
            logger.info("✅ Администратор уже существует")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании администратора: {e}")
        db.rollback()
    finally:
        db.close()


@app.get("/health")
async def health_check():
    """Эндпоинт для проверки здоровья приложения."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "parking-backend",
    }


# Страницы фронтенда
@app.get("/")
async def root(request: Request):
    """Главная страница - логин."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard")
async def dashboard(request: Request):
    """Панель пользователя."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/history")
async def history_page(request: Request, current_user: User = Depends(get_current_user)):
    """Страница истории парковок."""
    return templates.TemplateResponse("history.html", {"request": request, "user": current_user})


@app.get("/session/start")
async def session_start(request: Request, zone: str = None):
    """Страница начала сессии парковки (QR-вход)."""
    return templates.TemplateResponse(
        "session_start.html",
        {"request": request, "zone": zone}
    )


@app.get("/session/{session_id}")
async def session_active(request: Request, session_id: str):
    """Страница активной сессии парковки."""
    return templates.TemplateResponse(
        "session_active.html",
        {"request": request, "session_id": session_id}
    )


@app.get("/admin")
async def admin_panel(request: Request, current_user: User = Depends(get_current_admin_user)):
    """Страница админ-панели."""
    from app.routers.admin import admin_page
    return await admin_page(request, next(get_db()), current_user)