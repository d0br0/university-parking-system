# 🚗 Информационная система платной парковки у университета

## 📌 Описание
Веб-приложение для автоматизации учёта и оплаты парковок на территории университета.  
Водитель сканирует QR-код → авторизуется → оплачивает сессию → получает статус выезда.

Полный пользовательский сценарий работает (авторизация, QR-въезд, оплата, выезд). Используется httpOnly JWT для безопасности. Оплата реализована через mock-сервис.

Админ-панель доступна только пользователям с флагом `is_admin=True`. Включает управление тарифами, просмотр сессий и статистики.

## 🛠 Стек
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Pydantic
- **Frontend:** Jinja2, HTMX, Alpine.js, мобильная адаптивная вёрстка
- **БД:** PostgreSQL 15 (в разработке можно использовать SQLite)
- **Инфраструктура:** Docker, Docker Compose, Gunicorn/Uvicorn
- **Документация:** PlantUML, Swagger/OpenAPI
- **Тестирование:** pytest, httpx, TestClient, in-memory SQLite

## 🚀 Быстрый старт

### 1. Клонирование и настройка окружения
```bash
git clone <repository-url>
cd university-parking-system
cp .env.example .env
# Отредактируйте .env при необходимости (по умолчанию используется SQLite для разработки)
```

### 2. Запуск через Docker (рекомендуется)
```bash
docker compose up -d --build
```

### 3. Запуск вручную (без Docker)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # для Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Доступ к приложению
- **Frontend (пользовательский интерфейс):** http://localhost:8000/
- **API Swagger документация:** http://localhost:8000/docs
- **Админ-панель:** http://localhost:8000/admin (требуются права администратора)
- **Health check:** http://localhost:8000/health

## 🔐 Учётные данные по умолчанию
При первом запуске автоматически создаётся администратор и тариф:
- **Администратор:** email `admin@univ.edu`, пароль `admin123`
- **Обычный пользователь:** можно зарегистрировать через форму регистрации
- **Тариф:** "standard" — 150 ₽/час, дневной лимит 1200 ₽

## 🧪 Тестирование
Тесты используют in-memory SQLite и переопределение зависимостей.

### Запуск всех тестов
```bash
cd backend
pytest tests/ -v --tb=short
```

### Запуск конкретных тестовых модулей
```bash
pytest tests/test_auth.py -v
pytest tests/test_sessions.py -v
```

### Покрытие кода (опционально)
```bash
pytest --cov=app --cov-report=html tests/
```

## 📊 Админ-панель
Админ-панель доступна по маршруту `/admin` и предоставляет:
- **Управление тарифами:** просмотр, добавление новых тарифов
- **Просмотр сессий:** фильтрация по статусу и дате
- **Статистика:** общая выручка, активные сессии, посещения сегодня

Все админ-роуты защищены зависимостью `require_admin`, которая проверяет флаг `is_admin` у пользователя.

## 🛡 Глобальная обработка ошибок
Приложение включает централизованный обработчик исключений:
- **HTTPException:** возвращает стандартизированный JSON с кодом ошибки
- **SQLAlchemyError:** логирует ошибку БД, в debug-режиме показывает детали
- **Прочие исключения:** логируются с traceback, в production возвращается общее сообщение

Формат ответа об ошибке:
```json
{
  "detail": "Сообщение об ошибке",
  "error_code": "HTTP_404"
}
```

## 🔧 Конфигурация
Настройки приложения загружаются из `.env` файла (см. `.env.example`):

```env
DATABASE_URL=postgresql://user:pass@db:5432/parking
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=False
CORS_ORIGINS=["http://localhost:8000"]
```

### CORS
CORS настроен на разрешение credentials и origins из конфига. Для разработки разрешены все локальные origins.

## 🐳 Docker/Dev полировка
- **`.dockerignore`** исключает ненужные файлы при сборке образа
- **Проверка подключения к БД** при старте приложения
- **Автоматическое сидирование** тарифов и администратора
- **Логирование** успешного запуска и ошибок

## 💳 Mock-оплата
Вместо реальной платежной системы используется mock-сервис (`app/services/mock_payment.py`). Он имитирует:
- Создание платежа с статусом `pending`
- Завершение платежа с статусом `completed` после короткой задержки
- Возврат `transaction_id` для отслеживания

Интеграция с реальным платежным шлюзом может быть добавлена путём замены этого сервиса.

## 📈 Диаграммы архитектуры (заглушки)
- **Схема базы данных:** `docs/db_schema.puml`
- **Диаграмма компонентов:** `docs/component_diagram.puml`
- **Пользовательские сценарии:** `docs/user_flow.puml`

*(Диаграммы будут доработаны в следующей итерации)*

## 📁 Структура проекта
```
university-parking-system/
├── backend/
│   ├── app/
│   │   ├── routers/          # Маршруты API (auth, sessions, payments, admin)
│   │   ├── services/         # Бизнес-логика (cost, mock_payment)
│   │   ├── models.py         # SQLAlchemy модели
│   │   ├── schemas.py        # Pydantic схемы
│   │   ├── auth.py           # Аутентификация и авторизация
│   │   ├── database.py       # Подключение к БД
│   │   ├── config.py         # Конфигурация
│   │   └── main.py           # Точка входа FastAPI
│   ├── tests/                # Модульные и интеграционные тесты
│   │   ├── conftest.py       # Фикстуры pytest
│   │   ├── test_auth.py      # Тесты аутентификации
│   │   └── test_sessions.py  # Тесты сессий парковки
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── templates/            # Jinja2 шаблоны (включая admin.html)
│   └── static/               # CSS, JS, изображения
├── docker-compose.yml
├── .env.example
├── .dockerignore
└── README.MD
```

## 🚧 Разработка
### Добавление нового функционала
1. Создайте модель в `app/models.py` (при необходимости)
2. Добавьте Pydantic схемы в `app/schemas.py`
3. Реализуйте роутер в `app/routers/`
4. Напишите тесты в `tests/`
5. Обновите документацию

### Миграции базы данных
В текущей версии используется `Base.metadata.create_all()` для создания таблиц. Для production рекомендуется использовать Alembic.

## 📄 Лицензия
Проект распространяется под лицензией MIT. Подробности см. в файле LICENSE.

---
**Готово к демонстрации!** 🎉