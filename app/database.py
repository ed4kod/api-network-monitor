import os
import sqlite3
from contextlib import contextmanager
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Получение пути к базе данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///devices.db")
DB_PATH = DATABASE_URL.replace("sqlite:///", "")

class Database:
    _instance = None
    
    def __new__(cls, db_path=DB_PATH):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance.connection = None
            cls._instance._init_db()
        return cls._instance
    
    def __init__(self, db_path=DB_PATH):
        # Инициализация уже произошла в __new__
        pass
    
    def _init_db(self):
        """Инициализация базы данных и создание таблиц"""
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                ip TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                is_online INTEGER,
                last_check TEXT
            )
            """)
    
    @contextmanager
    def _get_connection(self):
        """Контекстный менеджер для соединения с базой данных"""
        # Используем существующее соединение или создаем новое
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Возвращать результаты как словари
        
        try:
            yield self.connection
        except Exception as e:
            # В случае ошибки закрываем соединение и создаем новое при следующем запросе
            if self.connection:
                self.connection.close()
                self.connection = None
            raise e
    
    def execute(self, query, params=None):
        """Выполнение SQL запроса (не возвращает курсор вне контекста)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            # Возвращаем число затронутых строк для справки
            return cursor.rowcount
    
    def fetch_all(self, query, params=None):
        """Получение всех результатов запроса"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            # Преобразуем результаты в список словарей для безопасного использования вне контекста
            result = [dict(row) for row in rows]
            return result
    
    def fetch_one(self, query, params=None):
        """Получение одного результата запроса"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            # Преобразуем результат в словарь для безопасного использования вне контекста
            if row:
                return dict(row)
            return None
    
    def insert(self, table, data):
        """Вставка данных в таблицу"""
        placeholders = ", ".join(["?"] * len(data))
        columns = ", ".join(data.keys())
        values = tuple(data.values())
        
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
    
    def update(self, table, data, condition):
        """Обновление данных в таблице"""
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        where_clause = " AND ".join([f"{key} = ?" for key in condition.keys()])
        
        values = tuple(list(data.values()) + list(condition.values()))
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            
    def close(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def delete(self, table, condition):
        """Удаление данных из таблицы"""
        where_clause = " AND ".join([f"{key} = ?" for key in condition.keys()])
        values = tuple(condition.values())
        
        query = f"DELETE FROM {table} WHERE {where_clause}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()

# Создание экземпляра базы данных для использования в приложении
db = Database()