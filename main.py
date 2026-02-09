# main.py - ИСПРАВЛЕННАЯ ВЕРСИЯ (2026 ГОД)
from fastapi import FastAPI, Request, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
import json
import httpx
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.utils

load_dotenv()

app = FastAPI(
    title="Пациентский портал",
    description="Веб-сервис для управления здоровьем пациента",
    version="2026.1.0",  # Обновлена версия
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Конфигурация
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8080/api")
SESSION_TOKEN_KEY = "access_token"

# Для работы с сессиями нужно установить middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "your-secret-key-here-change-in-production"),
    session_cookie="patient_session",
    max_age=3600
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Вспомогательные функции
def get_token(request: Request) -> Optional[str]:
    """Получить токен из сессии"""
    return request.session.get(SESSION_TOKEN_KEY)


def is_authenticated(request: Request) -> bool:
    """Проверить авторизацию"""
    return get_token(request) is not None


async def make_api_request(
        method: str,
        endpoint: str,
        token: Optional[str] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
) -> Dict:
    """Универсальный запрос к API"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()

            if response.status_code == 204 or not response.content:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            error_detail = f"API Error {e.response.status_code}: {e.response.text[:200]}"
            print(error_detail)

            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Сессия истекла. Пожалуйста, войдите снова."
                )

            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Ошибка API: {e.response.status_code}"
            )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Таймаут соединения с API"
            )

        except Exception as e:
            print(f"Request Error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Внутренняя ошибка сервера: {str(e)}"
            )


# Dependency для проверки авторизации
async def require_auth(request: Request):
    """Зависимость для защищенных маршрутов"""
    if not is_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return get_token(request)


# Модели форм
class LoginForm:
    def __init__(self, username: str = Form(...), password: str = Form(...)):
        self.username = username
        self.password = password


class RegisterForm:
    def __init__(
            self,
            username: str = Form(...),
            email: str = Form(...),
            full_name: str = Form(...),
            password: str = Form(...)
    ):
        self.username = username
        self.email = email
        self.full_name = full_name
        self.password = password


class MonitoringForm:
    def __init__(
            self,
            measurement_date: date = Form(default_factory=date.today),
            blood_pressure_systolic: Optional[int] = Form(None),
            blood_pressure_diastolic: Optional[int] = Form(None),
            heart_rate: Optional[int] = Form(None),
            body_temperature: Optional[float] = Form(None),
            blood_sugar: Optional[float] = Form(None),
            pain_level: Optional[int] = Form(None),
            fatigue_level: Optional[int] = Form(None),
            mood: Optional[str] = Form(None),
            sleep_hours: Optional[float] = Form(None),
            symptoms: Optional[str] = Form(None),
            notes: Optional[str] = Form(None)
    ):
        self.measurement_date = measurement_date
        self.blood_pressure_systolic = blood_pressure_systolic
        self.blood_pressure_diastolic = blood_pressure_diastolic
        self.heart_rate = heart_rate
        self.body_temperature = body_temperature
        self.blood_sugar = blood_sugar
        self.pain_level = pain_level
        self.fatigue_level = fatigue_level
        self.mood = mood
        self.sleep_hours = sleep_hours
        self.symptoms = symptoms
        self.notes = notes


# Функция для получения текущей даты в 2026 году
def get_current_date_2026() -> date:
    """Возвращает текущую дату в 2026 году"""
    today = date.today()
    # Если текущий год не 2026, используем 2026 год
    if today.year != 2026:
        return date(2026, today.month,
                    min(today.day, 28 if today.month == 2 else 30 if today.month in [4, 6, 9, 11] else 31))
    return today


# Маршруты аутентификации
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница"""
    token = get_token(request)
    if not token:
        return RedirectResponse(url="/login")
    return RedirectResponse(url="/dashboard")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@app.post("/login")
async def login(request: Request, form: LoginForm = Depends()):
    """Авторизация"""
    try:
        data = {
            "username": form.username,
            "password": form.password
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/auth/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                token_data = response.json()
                request.session[SESSION_TOKEN_KEY] = token_data["access_token"]
                return RedirectResponse(url="/dashboard", status_code=303)
            else:
                return templates.TemplateResponse(
                    "auth/login.html",
                    {"request": request, "error": "Неверный логин или пароль"}
                )

    except Exception as e:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": f"Ошибка: {str(e)}"}
        )


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации"""
    return templates.TemplateResponse("auth/register.html", {"request": request})


@app.get("/logout")
async def logout(request: Request):
    """Выход"""
    request.session.pop(SESSION_TOKEN_KEY, None)
    return RedirectResponse(url="/login")


# Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Личный кабинет"""
    token = get_token(request)
    if not token:
        return RedirectResponse(url="/login")

    current_date_2026 = get_current_date_2026()

    context = {
        "request": request,
        "patient": {
            "first_name": "Иван",
            "last_name": "Иванов",
            "email": "ivan@example.com",
            "phone": "+7 999 123-45-67"
        },
        "current_date": current_date_2026.strftime("%d.%m.%Y"),
        "current_year": 2026,  # Явно указываем 2026 год
        "appointments_today": [
            {
                "title": "Прием у терапевта",
                "time": "10:00",
                "doctor": "Доктор Смирнова А.И.",
                "status": "active"
            },
            {
                "title": "Сдача анализов",
                "time": "14:30",
                "location": "Лаборатория №3",
                "status": "pending"
            }
        ],
        "health_metrics": {
            "last_blood_pressure": "120/80",
            "last_heart_rate": "72",
            "last_temperature": "36.6"
        }
    }

    return templates.TemplateResponse("dashboard/dashboard.html", context)


# Страница о системе (с информацией о 2026 годе)
@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """Страница о системе"""
    context = {
        "request": request,
        "current_year": 2026,
        "system_version": "2026.1.0",
        "features": [
            "Искусственный интеллект для анализа показателей",
            "Интеграция с носимой электроникой 2026",
            "Телемедицинские консультации в реальном времени",
            "Персональные рекомендации на основе ИИ"
        ]
    }

    about_html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>О системе - Пациентский портал 2026</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1>Пациентский портал 2026</h1>
            <p class="lead">Инновационная система управления здоровьем</p>

            <div class="card mt-4">
                <div class="card-header bg-info text-white">
                    <h4>Информация о системе</h4>
                </div>
                <div class="card-body">
                    <p><strong>Версия:</strong> 2026.1.0</p>
                    <p><strong>Год разработки:</strong> 2026</p>
                    <p><strong>Текущая дата:</strong> """ + get_current_date_2026().strftime("%d.%m.%Y") + """</p>

                    <h5 class="mt-4">Особенности системы 2026:</h5>
                    <ul>
                        <li>Искусственный интеллект для анализа показателей</li>
                        <li>Интеграция с носимой электроникой нового поколения</li>
                        <li>Телемедицинские консультации в реальном времени</li>
                        <li>Персональные рекомендации на основе ИИ</li>
                        <li>Прогнозирование состояния здоровья</li>
                    </ul>

                    <div class="alert alert-success mt-4">
                        <h6>Технологии 2026 года:</h6>
                        <p>Система использует передовые технологии 2026 года для мониторинга 
                        и прогнозирования состояния здоровья пациентов.</p>
                    </div>
                </div>
            </div>

            <div class="mt-4">
                <a href="/" class="btn btn-primary">На главную</a>
                <a href="/dashboard" class="btn btn-success">В личный кабинет</a>
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=about_html)


# API для получения информации о системе
@app.get("/api/system-info")
async def get_system_info():
    """Информация о системе"""
    return {
        "system_name": "Пациентский портал",
        "version": "2026.1.0",
        "year": 2026,
        "current_date": get_current_date_2026().isoformat(),
        "features": [
            "AI Health Analytics",
            "Wearable Integration 2026",
            "Real-time Telemedicine",
            "Predictive Health Monitoring"
        ],
        "technology_stack": {
            "backend": "FastAPI 2026",
            "frontend": "Modern Web 2026",
            "ai_engine": "Health AI v3.0",
            "database": "Medical DB 2026"
        }
    }


# Простая главная страница (для теста)
@app.get("/simple")
async def simple_home():
    return {
        "message": "Пациентский портал 2026 работает!",
        "year": 2026,
        "current_date": get_current_date_2026().isoformat(),
        "status": "active"
    }


# Обновленный base.html (шаблон)
@app.get("/base-template")
async def get_base_template():
    """Пример базового шаблона с 2026 годом"""
    base_html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Пациентский портал 2026</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
        <style>
            .year-badge {
                background-color: #198754;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="bi bi-heart-pulse"></i> Пациентский портал 
                    <span class="year-badge">2026</span>
                </a>
                <div class="navbar-nav ms-auto">
                    <span class="nav-item text-light">
                        <i class="bi bi-calendar"></i> """ + get_current_date_2026().strftime("%d.%m.%Y") + """
                    </span>
                </div>
            </div>
        </nav>

        <main class="container mt-4">
            {% block content %}{% endblock %}
        </main>

        <footer class="bg-light text-center py-3 mt-5">
            <div class="container">
                <p class="mb-0">
                    © 2024-2026 Пациентский портал. 
                    <span class="text-primary">Версия 2026.1.0</span>
                </p>
                <small class="text-muted">Система управления здоровьем нового поколения</small>
            </div>
        </footer>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=base_html)


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("ПАЦИЕНТСКИЙ ПОРТАЛ 2026")
    print(f"Дата запуска: {get_current_date_2026().strftime('%d.%m.%Y')}")
    print(f"Версия системы: 2026.1.0")
    print("Ссылки:")
    print("  • http://127.0.0.1:8000 - Главная")
    print("  • http://127.0.0.1:8000/dashboard - Личный кабинет")
    print("  • http://127.0.0.1:8000/about - О системе 2026")
    print("  • http://127.0.0.1:8000/api/docs - Документация API")
    print("=" * 60)

    # Запуск без reload
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")