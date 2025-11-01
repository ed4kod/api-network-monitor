import subprocess
import platform
import threading
import time
import os
from datetime import datetime
from dotenv import load_dotenv

from app.models.device import Device
from app import db

# Загрузка переменных окружения
load_dotenv()

class DeviceMonitor:
    def __init__(self):
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "5"))  # Интервал из .env
        self.ping_timeout = float(os.getenv("PING_TIMEOUT", "0.5"))  # Таймаут из .env
        self.devices = {}
        self.monitoring_status = {}
        self.monitoring_threads = {}

    def ping_host(self, ip):
        is_windows = platform.system().lower() == "windows"
        
        if is_windows:
            # В Windows используем другой формат команды
            # Для Windows таймаут указывается в миллисекундах
            timeout_ms = int(self.ping_timeout * 1000)
            command = f"ping -n 1 -w {timeout_ms} {ip}"
        else:
            # Для Linux/Mac таймаут указывается в секундах
            command = f"ping -c 1 -W {self.ping_timeout} {ip}"

        try:
            if is_windows:
                # Для Windows используем shell=True и кодировку cp866
                output = subprocess.check_output(
                    command, stderr=subprocess.STDOUT,
                    shell=True, text=True, encoding='cp866',
                    timeout=self.ping_timeout * 2  # Общий таймаут процесса
                )
            else:
                # Для Linux/Mac
                output = subprocess.check_output(
                    command, stderr=subprocess.STDOUT,
                    shell=True, universal_newlines=True,
                    timeout=self.ping_timeout * 2  # Общий таймаут процесса
                )
            
            # Проверяем результат пинга
            if "TTL=" in output or "ttl=" in output:
                return True
            return False
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def monitor_device(self, device_id):
        device = self.get_device(device_id)
        if not device:
            return
        
        # Создаем отдельный поток для каждого устройства
        while self.monitoring_status.get(device_id, False):
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            is_online = self.ping_host(device.ip)

            # Сохраняем результат
            device.last_check = current_time
            
            # Всегда обновляем статус устройства
            device.is_online = is_online

            # Добавляем записи в историю при изменении статуса
            if device.is_online is None:
                # Первая проверка
                status = "ДОСТУПЕН" if is_online else "НЕДОСТУПЕН"
                message = f"[{current_time}] Начальный статус: {status}"
                device.results.append({"time": current_time, "status": status, "message": message})
            elif not is_online:
                # Устройство недоступно
                message = f"[{current_time}] ⚠️ Устройство {device.ip} НЕДОСТУПНО"
                device.results.append({"time": current_time, "status": "НЕДОСТУПЕН", "message": message})
            elif is_online:
                # Устройство доступно
                message = f"[{current_time}] ✅ Устройство {device.ip} ДОСТУПНО"
                device.results.append({"time": current_time, "status": "ДОСТУПЕН", "message": message})
            
            # Сохраняем изменения в БД
            device.save()
            
            # Используем интервал из настроек
            time.sleep(self.check_interval)

    def add_device(self, device):
        # Сохраняем устройство в БД
        device.save()
        # Добавляем в кэш
        self.devices[device.id] = device
        return device

    def get_device(self, device_id):
        # Сначала проверяем кэш
        if device_id in self.devices:
            return self.devices[device_id]
        
        # Если нет в кэше, ищем в БД
        device = Device.get_by_id(device_id)
        if device:
            self.devices[device_id] = device
        return device

    def get_all_devices(self):
        # Получаем все устройства из БД
        devices_list = Device.get_all()
        
        # Обновляем кэш
        for device in devices_list:
            self.devices[device.id] = device
            
        # Возвращаем список устройств для совместимости с шаблоном
        return devices_list

    def update_device(self, device_id, ip=None, name=None, description=None):
        device = self.get_device(device_id)
        if not device:
            return None

        if ip:
            device.ip = ip
        if name:
            device.name = name
        if description is not None:
            device.description = description

        # Сохраняем изменения в БД
        device.save()
        return device

    def delete_device(self, device_id):
        device = self.get_device(device_id)
        if not device:
            return False
            
        # Останавливаем мониторинг, если он запущен
        if self.monitoring_status.get(device_id, False):
            self.stop_monitoring(device_id)
        
        # Удаляем устройство из БД
        device.delete()
        
        # Удаляем из кэша
        if device_id in self.devices:
            del self.devices[device_id]
            
        return True

    def start_monitoring(self, device_id):
        if device_id not in self.devices:
            return False
        
        if self.monitoring_status.get(device_id, False):
            return True  # Уже запущен
        
        self.monitoring_status[device_id] = True
        thread = threading.Thread(target=self.monitor_device, args=(device_id,))
        thread.daemon = True
        thread.start()
        self.monitoring_threads[device_id] = thread
        return True

    def stop_monitoring(self, device_id):
        if device_id not in self.devices:
            return False
        
        # Устанавливаем флаг остановки
        self.monitoring_status[device_id] = False
        
        # Ждем завершения потока (максимум 2 секунды)
        if device_id in self.monitoring_threads:
            thread = self.monitoring_threads[device_id]
            if thread and thread.is_alive():
                thread.join(timeout=2)
                # Удаляем поток из словаря
                del self.monitoring_threads[device_id]
                
        return True

    def start_all_monitoring(self):
        for device_id in self.devices:
            self.start_monitoring(device_id)
        return True

    def stop_all_monitoring(self):
        for device_id in self.devices:
            self.stop_monitoring(device_id)
        return True

# Создаем глобальный экземпляр монитора
device_monitor = DeviceMonitor()