import uvicorn
import os
from app import app

if __name__ == "__main__":
    print("Запуск API Network Monitor...")
    print("Сервер доступен по адресу: http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)