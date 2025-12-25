"""
Менеджер базы данных для работы с источниками данных и датасетами
"""
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import ThreadedConnectionPool
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер для работы с PostgreSQL"""
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 5432,
                 database: str = 'reestry',
                 user: str = 'reestry_user',
                 password: str = 'reestry_password',
                 min_conn: int = 1,
                 max_conn: int = 10):
        """
        Инициализация менеджера БД
        
        Args:
            host: Хост PostgreSQL
            port: Порт PostgreSQL
            database: Имя базы данных
            user: Пользователь
            password: Пароль
            min_conn: Минимальное количество соединений в пуле
            max_conn: Максимальное количество соединений в пуле
        """
        self.db_config = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        
        try:
            self.pool = ThreadedConnectionPool(
                min_conn, max_conn,
                **self.db_config
            )
            logger.info(f"Database connection pool created: {min_conn}-{max_conn} connections")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    def get_connection(self):
        """Получить соединение из пула"""
        return self.pool.getconn()
    
    def return_connection(self, conn):
        """Вернуть соединение в пул"""
        self.pool.putconn(conn)
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        """Выполнить запрос"""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Query execution error: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    # Методы для работы с источниками данных
    def create_source(self, url: str, source_type: str, domain: str = None, metadata: Dict = None) -> int:
        """Создать новый источник данных"""
        query = """
            INSERT INTO data_sources (url, source_type, domain, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute_query(query, (url, source_type, domain, Json(metadata or {})))
        return result[0]['id']
    
    def get_source(self, source_id: int) -> Optional[Dict]:
        """Получить источник по ID"""
        query = "SELECT * FROM data_sources WHERE id = %s"
        result = self.execute_query(query, (source_id,))
        return result[0] if result else None
    
    def get_all_active_sources(self) -> List[Dict]:
        """Получить все активные источники"""
        query = """
            SELECT * FROM data_sources 
            WHERE status IN ('pending', 'downloading', 'partial')
            ORDER BY created_at DESC
        """
        return self.execute_query(query)
    
    def update_source_status(self, source_id: int, status: str, 
                           downloaded_records: int = None,
                           error_message: str = None):
        """Обновить статус источника"""
        updates = [f"status = %s", "updated_at = NOW()"]
        params = [status]
        
        if downloaded_records is not None:
            updates.append("downloaded_records = %s")
            params.append(downloaded_records)
            updates.append("last_successful_download = NOW()")
        
        if error_message:
            updates.append("error_message = %s")
            params.append(error_message)
            updates.append("retry_count = retry_count + 1")
        
        params.append(source_id)
        
        query = f"""
            UPDATE data_sources 
            SET {', '.join(updates)}
            WHERE id = %s
        """
        self.execute_query(query, tuple(params), fetch=False)
    
    def update_progress(self, source_id: int, downloaded_records: int):
        """Обновить прогресс загрузки"""
        query = """
            UPDATE data_sources 
            SET downloaded_records = %s,
                last_successful_download = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """
        self.execute_query(query, (downloaded_records, source_id), fetch=False)
    
    # Методы для работы с целостностью данных
    def save_fingerprints(self, fingerprints: List[Dict]):
        """Сохранить отпечатки данных"""
        query = """
            INSERT INTO data_integrity 
            (source_id, record_id, content_hash, original_hash, verification_status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                for fp in fingerprints:
                    cursor.execute(query, (
                        fp['source_id'],
                        fp['record_id'],
                        fp['content_hash'],
                        fp.get('original_hash'),
                        fp.get('verification_status', 'pending')
                    ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving fingerprints: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def get_downloaded_records(self, source_id: int) -> List[Dict]:
        """Получить загруженные записи для источника"""
        # Предполагаем, что данные хранятся в отдельной таблице raw_data
        # Это нужно будет адаптировать под вашу структуру
        query = """
            SELECT * FROM raw_data 
            WHERE source_id = %s
        """
        return self.execute_query(query, (source_id,))
    
    # Методы для работы с датасетами
    def create_dataset_version(self, name: str, description: str = "", 
                             base_version_id: int = None,
                             metadata: Dict = None) -> int:
        """Создать новую версию датасета"""
        query = """
            INSERT INTO dataset_versions 
            (name, description, base_version_id, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute_query(query, (
            name, description, base_version_id, Json(metadata or {})
        ))
        return result[0]['id']
    
    def get_dataset_version(self, version_id: int) -> Optional[Dict]:
        """Получить версию датасета"""
        query = "SELECT * FROM dataset_versions WHERE id = %s"
        result = self.execute_query(query, (version_id,))
        return result[0] if result else None
    
    def save_dataset(self, version_id: int, dataset: Dict):
        """Сохранить датасет"""
        # Сохраняем образцы
        query = """
            INSERT INTO dataset_samples (version_id, document_id, sample_data, sample_hash)
            VALUES (%s, %s, %s, %s)
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                for sample in dataset.get('samples', []):
                    cursor.execute(query, (
                        version_id,
                        sample.get('id'),
                        Json(sample),
                        sample.get('sample_hash')
                    ))
            
            # Обновляем метаданные версии
            update_query = """
                UPDATE dataset_versions 
                SET total_samples = %s,
                    metadata = %s,
                    status = 'ready',
                    updated_at = NOW()
                WHERE id = %s
            """
            cursor.execute(update_query, (
                len(dataset.get('samples', [])),
                Json(dataset.get('metadata', {})),
                version_id
            ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving dataset: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def get_documents_for_training(self, filters: Dict = None, min_length: int = 1000) -> List[Dict]:
        """Получить документы для обучения"""
        # Адаптируйте под вашу структуру таблицы documents
        query = """
            SELECT * FROM documents 
            WHERE LENGTH(content) >= %s
        """
        params = [min_length]
        
        if filters:
            if filters.get('document_type'):
                query += " AND document_type = %s"
                params.append(filters['document_type'])
        
        query += " ORDER BY document_type, title"
        return self.execute_query(query, tuple(params))
    
    def get_documents_modified_since(self, since_date: datetime) -> List[Dict]:
        """Получить документы, измененные после указанной даты"""
        query = """
            SELECT * FROM documents 
            WHERE updated_at > %s OR created_at > %s
            ORDER BY updated_at DESC
        """
        return self.execute_query(query, (since_date, since_date))
    
    def save_changes(self, changes: List[Dict]):
        """Сохранить изменения документов"""
        query = """
            INSERT INTO document_changes 
            (document_id, change_type, old_content_hash, new_content_hash, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                for change in changes:
                    cursor.execute(query, (
                        change['document_id'],
                        change['change_type'],
                        change.get('old_content_hash'),
                        change.get('new_content_hash'),
                        Json(change.get('metadata', {}))
                    ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving changes: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def close(self):
        """Закрыть пул соединений"""
        if hasattr(self, 'pool'):
            self.pool.closeall()
            logger.info("Database connection pool closed")

