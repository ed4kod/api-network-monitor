from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from app.database import Database

# Инициализируем базу данных как синглтон
db = Database()

app = FastAPI(title="API Network Monitor", description="Мониторинг сетевых устройств")

# Проверяем существование директории static и создаем её при необходимости
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Обработчики событий для корректного закрытия соединения с БД
@app.on_event("shutdown")
async def shutdown_db_client():
    db.close()

# Импортируем маршруты
from app.routes import device_routes

# Регистрируем маршруты
app.include_router(device_routes.router)