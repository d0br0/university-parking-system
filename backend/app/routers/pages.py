"""
Роутер для страниц фронтенда.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import get_current_user, require_admin

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = BASE_DIR / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, user=Depends(get_current_user)):
    """Страница истории парковок."""
    return templates.TemplateResponse("history.html", {"request": request, "user": user})


@router.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports_page(request: Request, admin=Depends(require_admin)):
    """Страница отчётов администратора."""
    return templates.TemplateResponse("admin_reports.html", {"request": request, "user": admin})


@router.get("/admin/zones", response_class=HTMLResponse)
async def admin_zones_page(request: Request, admin=Depends(require_admin)):
    """Страница управления зонами парковки."""
    return templates.TemplateResponse("admin_zones.html", {"request": request, "user": admin})
