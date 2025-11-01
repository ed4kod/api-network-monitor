from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uuid

from app.services.monitor import device_monitor
from app.models.device import Device

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "devices": device_monitor.get_all_devices(),
        "monitoring_status": device_monitor.monitoring_status
    })

@router.post("/add_device")
async def add_device(
    request: Request,
    ip: str = Form(...),
    name: str = Form(...),
    description: str = Form("")
):
    device_id = str(uuid.uuid4())
    new_device = Device(id=device_id, ip=ip, name=name, description=description)
    device_monitor.add_device(new_device)
    return RedirectResponse(url="/", status_code=303)

@router.post("/edit_device/{device_id}")
async def edit_device(
    request: Request,
    device_id: str,
    ip: str = Form(...),
    name: str = Form(...),
    description: str = Form("")
):
    device = device_monitor.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    
    device_monitor.update_device(device_id, ip=ip, name=name, description=description)
    return RedirectResponse(url="/", status_code=303)

@router.get("/delete_device/{device_id}")
async def delete_device(request: Request, device_id: str):
    if not device_monitor.delete_device(device_id):
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    return RedirectResponse(url="/", status_code=303)

@router.get("/start_monitoring/{device_id}")
async def start_monitoring(request: Request, device_id: str):
    if not device_monitor.start_monitoring(device_id):
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    return RedirectResponse(url="/", status_code=303)

@router.get("/stop_monitoring/{device_id}")
async def stop_monitoring(request: Request, device_id: str):
    if not device_monitor.stop_monitoring(device_id):
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    return RedirectResponse(url="/", status_code=303)

@router.get("/start_all_monitoring")
async def start_all_monitoring(request: Request):
    device_monitor.start_all_monitoring()
    return RedirectResponse(url="/", status_code=303)

@router.get("/stop_all_monitoring")
async def stop_all_monitoring(request: Request):
    device_monitor.stop_all_monitoring()
    return RedirectResponse(url="/", status_code=303)

@router.get("/device_results/{device_id}")
async def device_results(request: Request, device_id: str):
    device = device_monitor.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    
    return {
        "results": list(device.results),
        "is_online": device.is_online,
        "last_check": device.last_check
    }
