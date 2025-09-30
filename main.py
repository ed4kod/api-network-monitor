from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import subprocess
import platform
import threading
from datetime import datetime
from collections import deque
import uuid
import json
from typing import List, Dict
import time

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Хранилище устройств и результатов мониторинга
devices = {}
monitoring_status = {}
monitoring_threads = {}


class Device:
    def __init__(self, id, ip, name, description=""):
        self.id = id
        self.ip = ip
        self.name = name
        self.description = description
        self.results = deque(maxlen=100)
        self.is_online = None
        self.last_check = None


class DeviceMonitor:
    def __init__(self):
        self.check_interval = 60000

    def ping_host(self, ip):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", ip]

        try:
            if platform.system().lower() == "windows":
                output = subprocess.check_output(
                    command, stderr=subprocess.STDOUT,
                    shell=True, text=True, encoding='cp866'
                )
            else:
                output = subprocess.check_output(
                    command, stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
            return True
        except subprocess.CalledProcessError:
            return False

    def monitor_device(self, device_id):
        device = devices[device_id]

        while monitoring_status.get(device_id, False):
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            is_online = self.ping_host(device.ip)

            # Сохраняем результат
            device.last_check = current_time

            if device.is_online is None:
                # Первая проверка
                status = "ДОСТУПЕН" if is_online else "НЕДОСТУПЕН"
                message = f"[{current_time}] Начальный статус: {status}"
                device.results.append({"time": current_time, "status": status, "message": message})
            elif device.is_online and not is_online:
                # Связь пропала
                message = f"[{current_time}] ⚠️ ПРЕРВАНО соединение с {device.ip}"
                device.results.append({"time": current_time, "status": "ПРЕРВАНО", "message": message})
            elif not device.is_online and is_online:
                # Связь восстановилась
                message = f"[{current_time}] ✅ ВОССТАНОВЛЕНО соединение с {device.ip}"
                device.results.append({"time": current_time, "status": "ВОССТАНОВЛЕНО", "message": message})

            device.is_online = is_online
            time.sleep(self.check_interval)


# Глобальный монитор
monitor = DeviceMonitor()


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "devices": devices,
        "monitoring_status": monitoring_status
    })


@app.post("/add_device")
async def add_device(
    request: Request,
    ip: str = Form(...),
    name: str = Form(...),
    description: str = Form("")
):
    device_id = str(uuid.uuid4())
    devices[device_id] = Device(device_id, ip, name, description)
    monitoring_status[device_id] = False  # Добавляем статус мониторинга
    return RedirectResponse(url="/", status_code=303)


@app.post("/edit_device/{device_id}")
async def edit_device(
        request: Request,
        device_id: str,
        ip: str = Form(...),
        name: str = Form(...),
        description: str = Form("")
):
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Устройство не найдено")

    devices[device_id].ip = ip
    devices[device_id].name = name
    devices[device_id].description = description

    return RedirectResponse(url="/", status_code=303)


@app.get("/delete_device/{device_id}")
async def delete_device(request: Request, device_id: str):
    if device_id in devices:
        # Останавливаем мониторинг если активен
        if device_id in monitoring_status and monitoring_status[device_id]:
            monitoring_status[device_id] = False
            if device_id in monitoring_threads:
                monitoring_threads[device_id].join(timeout=1.0)
                del monitoring_threads[device_id]

        # Удаляем устройство и его статус
        del devices[device_id]
        if device_id in monitoring_status:
            del monitoring_status[device_id]

    return RedirectResponse(url="/", status_code=303)


@app.get("/start_monitoring/{device_id}")
async def start_monitoring(device_id: str):
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Устройство не найдено")

    if not monitoring_status.get(device_id, False):
        monitoring_status[device_id] = True
        thread = threading.Thread(target=monitor.monitor_device, args=(device_id,), daemon=True)
        monitoring_threads[device_id] = thread
        thread.start()

    return RedirectResponse(url="/", status_code=303)


@app.get("/stop_monitoring/{device_id}")
async def stop_monitoring(device_id: str):
    if device_id in monitoring_status:
        monitoring_status[device_id] = False
        if device_id in monitoring_threads:
            monitoring_threads[device_id].join(timeout=1.0)
            del monitoring_threads[device_id]

    return RedirectResponse(url="/", status_code=303)


@app.get("/start_all_monitoring")
async def start_all_monitoring():
    for device_id in devices:
        if not monitoring_status.get(device_id, False):
            monitoring_status[device_id] = True
            thread = threading.Thread(target=monitor.monitor_device, args=(device_id,), daemon=True)
            monitoring_threads[device_id] = thread
            thread.start()

    return RedirectResponse(url="/", status_code=303)


@app.get("/stop_all_monitoring")
async def stop_all_monitoring():
    for device_id in list(monitoring_status.keys()):
        monitoring_status[device_id] = False
        if device_id in monitoring_threads:
            monitoring_threads[device_id].join(timeout=1.0)
            del monitoring_threads[device_id]

    return RedirectResponse(url="/", status_code=303)


@app.get("/device_results/{device_id}")
async def get_device_results(device_id: str):
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Устройство не найдено")

    device = devices[device_id]
    return {
        "device_id": device_id,
        "results": list(device.results),
        "is_online": device.is_online,
        "last_check": device.last_check,
        "is_monitoring": monitoring_status.get(device_id, False)
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)