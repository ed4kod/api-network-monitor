from collections import deque
from datetime import datetime
from app import db

class Device:
    def __init__(self, id, ip, name, description="", is_online=None, last_check=None):
        self.id = id
        self.ip = ip
        self.name = name
        self.description = description
        self.results = deque(maxlen=100)
        self.is_online = is_online
        self.last_check = last_check
    
    def to_dict(self):
        return {
            "id": self.id,
            "ip": self.ip,
            "name": self.name,
            "description": self.description,
            "is_online": self.is_online,
            "last_check": self.last_check
        }
    
    @classmethod
    def from_db_row(cls, row):
        """Создает объект Device из строки базы данных"""
        if not row:
            return None
        
        return cls(
            id=row['id'],
            ip=row['ip'],
            name=row['name'],
            description=row['description'],
            is_online=bool(row['is_online']) if row['is_online'] is not None else None,
            last_check=row['last_check']
        )
    
    @classmethod
    def get_by_id(cls, device_id):
        """Получает устройство по ID из базы данных"""
        row = db.fetch_one("SELECT * FROM devices WHERE id = ?", (device_id,))
        return cls.from_db_row(row)
    
    @classmethod
    def get_all(cls):
        """Получает все устройства из базы данных"""
        rows = db.fetch_all("SELECT * FROM devices")
        return [cls.from_db_row(row) for row in rows]
    
    def save(self):
        """Сохраняет устройство в базу данных"""
        device_data = {
            "id": self.id,
            "ip": self.ip,
            "name": self.name,
            "description": self.description,
            "is_online": 1 if self.is_online else 0 if self.is_online is not None else None,
            "last_check": self.last_check
        }
        
        # Проверяем, существует ли устройство
        existing = db.fetch_one("SELECT id FROM devices WHERE id = ?", (self.id,))
        
        if existing:
            # Обновляем существующее устройство
            db.update("devices", 
                      {k: v for k, v in device_data.items() if k != 'id'}, 
                      {"id": self.id})
        else:
            # Создаем новое устройство
            db.insert("devices", device_data)
        
        return self
    
    def delete(self):
        """Удаляет устройство из базы данных"""
        db.delete("devices", {"id": self.id})