# 🚗 Информационная система платной парковки у университета

## 📌 Описание
Веб-приложение для автоматизации учёта и оплаты парковок на территории университета.  
Водитель сканирует QR-код → авторизуется → оплачивает сессию → получает статус выезда.

## 🛠 Стек
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Pydantic
- **Frontend:** Jinja2, HTMX, Alpine.js, мобильная адаптивная вёрстка
- **БД:** PostgreSQL 15
- **Инфраструктура:** Docker, Docker Compose, Gunicorn/Uvicorn
- **Документация:** PlantUML, Swagger/OpenAPI

## 🚀 Быстрый старт
```bash
# 1. Скопируйте окружение
cp .env.example .env

# 2. Запустите контейнеры
docker compose up -d --build

# 3. Откройте
- API Swagger: http://localhost:8000/docs
- Frontend: http://localhost:8000/