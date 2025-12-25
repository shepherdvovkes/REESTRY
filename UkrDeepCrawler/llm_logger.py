"""
Модуль для логирования вызовов LLM в базу данных
"""
import requests
import json
import sqlite3
import os
import time
from typing import Dict, Optional
from datetime import datetime

class LLMLogger:
    """Логгер для записи вызовов LLM в базу данных"""
    
    def __init__(self, db_path: str = None):
        """
        Инициализация логгера
        
        Args:
            db_path: Путь к базе данных (по умолчанию llm_history.db в корне проекта)
        """
        if db_path is None:
            # Путь к базе данных в корне проекта
            # Получаем корень проекта (на уровень выше UkrDeepCrawler)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)  # Поднимаемся на уровень выше
            db_path = os.path.join(project_root, 'llm_history.db')
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица истории LLM вызовов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS llm_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER,
                algorithm_step TEXT,
                input_data TEXT,
                output_data TEXT,
                model TEXT,
                temperature REAL,
                tokens_used INTEGER,
                response_time_ms INTEGER,
                success BOOLEAN,
                error_message TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_llm_call(self,
                    algorithm_step: str,
                    input_data: Dict,
                    output_data: Dict,
                    model: str,
                    temperature: float,
                    response_time_ms: int,
                    success: bool = True,
                    error_message: Optional[str] = None,
                    prompt_id: Optional[int] = None,
                    tokens_used: Optional[int] = None,
                    metadata: Optional[Dict] = None) -> int:
        """
        Записать вызов LLM в историю
        
        Args:
            algorithm_step: Шаг алгоритма, где произошел вызов
            input_data: Входные данные (промпт, параметры)
            output_data: Выходные данные (ответ LLM)
            model: Название модели
            temperature: Температура генерации
            response_time_ms: Время ответа в миллисекундах
            success: Успешность вызова
            error_message: Сообщение об ошибке (если есть)
            prompt_id: ID промпта из базы (если есть)
            tokens_used: Количество использованных токенов
            metadata: Дополнительные метаданные
            
        Returns:
            ID созданной записи
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO llm_history 
                (prompt_id, algorithm_step, input_data, output_data, 
                 model, temperature, tokens_used, response_time_ms, 
                 success, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                prompt_id,
                algorithm_step,
                json.dumps(input_data, ensure_ascii=False),
                json.dumps(output_data, ensure_ascii=False),
                model,
                temperature,
                tokens_used,
                response_time_ms,
                success,
                error_message,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            history_id = cursor.lastrowid
            conn.commit()
            return history_id
        except Exception as e:
            conn.rollback()
            print(f"⚠️  Error logging LLM call: {e}")
            return -1
        finally:
            conn.close()

