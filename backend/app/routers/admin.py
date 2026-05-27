from datetime import datetime, timezone
import base64
import io
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
import qrcode
import qrcode.image.svg
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from app.auth import get_current_user
from app.database import get_db
from app.models import Session as ParkingSession, Payment, User
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])

# Инициализация шаблонов (согласно требованию - внутри роутера или импорт)
# Мы инициализируем здесь для избежания циклических импортов
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Зависимость: только для администраторов."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён",
        )
    return current_user

class QRRequest(BaseModel):
    zone: str

@router.get("/page")
async def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Отображение админ-панели со статистикой."""
    # total_revenue = SUM(payments.amount) WHERE status='completed' (в моделях 'completed' вместо 'success')
    total_revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.status == "completed"
    ).scalar()

    # active_sessions = COUNT(sessions) WHERE status IN ('pending', 'paid')
    active_sessions = db.query(func.count(ParkingSession.id)).filter(
        ParkingSession.status.in_(["pending", "paid"])
    ).scalar()

    # today_sessions = COUNT(sessions) WHERE entry_time >= начало текущих суток (UTC)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_sessions = db.query(func.count(ParkingSession.id)).filter(
        ParkingSession.entry_time >= today_start
    ).scalar()

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "total_revenue": total_revenue,
            "active_sessions": active_sessions,
            "today_sessions": today_sessions,
            "user": admin
        }
    )

@router.post("/generate-qr")
async def generate_qr(
    data: QRRequest,
    admin: User = Depends(require_admin)
):
    """Генерация QR-кода для зоны парковки."""
    zone = data.zone
    url = f"{settings.BASE_URL}/session/start?zone={zone}"
    
    # Генерация SVG QR-кода
    factory = qrcode.image.svg.SvgImage
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
        image_factory=factory,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image()
    
    # Преобразование в base64
    stream = io.BytesIO()
    img.save(stream)
    svg_data = stream.getvalue().decode("utf-8")
    base64_svg = base64.b64encode(svg_data.encode("utf-8")).decode("utf-8")
    
    qr_img_tag = f"<img src='data:image/svg+xml;base64,{base64_svg}' class='mx-auto' alt='QR Code'>"
    
    return {
        "zone": zone,
        "url": url,
        "qr_svg": qr_img_tag
    }

@router.get("/download-qr-pdf")
async def download_qr_pdf(
    zone: str,
    admin: User = Depends(require_admin)
):
    """Генерация и скачивание PDF с QR-кодом для печати."""
    url = f"{settings.BASE_URL}/session/start?zone={zone}"
    
    # Генерируем QR для PDF (обычный PIL формат, не SVG)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Сохраняем QR в буфер
    img_byte_arr = io.BytesIO()
    qr_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    # Создаем PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Заголовок
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width/2, height - 40*mm, "University Parking System")
    
    # Зона
    p.setFont("Helvetica", 18)
    p.drawCentredString(width/2, height - 55*mm, f"PARKING ZONE: {zone}")
    
    # QR-код (центр страницы)
    qr_size = 120*mm
    img_byte_arr.seek(0)
    img_reader = ImageReader(img_byte_arr)
    p.drawImage(img_reader, (width-qr_size)/2, (height-qr_size)/2 - 20*mm, width=qr_size, height=qr_size)
    
    # Инструкция
    p.setFont("Helvetica-Oblique", 12)
    p.drawCentredString(width/2, 40*mm, "Scan this QR code with your phone camera to start parking.")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=QR_Zone_{zone}.pdf"}
    )
