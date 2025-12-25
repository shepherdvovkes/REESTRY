"""
Модуль для проверки целостности данных
"""
import hashlib
import json
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class DataIntegrityChecker:
    """Система проверки целостности данных"""
    
    def __init__(self, db: DatabaseManager):
        """
        Инициализация проверяющего целостность
        
        Args:
            db: Менеджер базы данных
        """
        self.db = db
    
    def calculate_content_hash(self, data: Dict) -> str:
        """
        Вычисление хеша содержимого записи
        
        Args:
            data: Словарь с данными записи
            
        Returns:
            SHA256 хеш в hex формате
        """
        normalized = self._normalize_for_hash(data)
        content_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    def _normalize_for_hash(self, data: Dict) -> Dict:
        """
        Нормализация данных для хеширования (убираем метаданные)
        
        Args:
            data: Исходные данные
            
        Returns:
            Нормализованные данные без метаданных
        """
        # Убираем поля, которые могут меняться при загрузке
        exclude_fields = {
            'downloaded_at', 'updated_at', 'created_at', 
            'id', 'internal_id', '_id', 'source_id'
        }
        return {k: v for k, v in data.items() if k not in exclude_fields}
    
    def store_source_fingerprint(self, source_id: int, source_url: str, records: List[Dict]):
        """
        Сохранение отпечатка исходных данных
        
        Args:
            source_id: ID источника
            source_url: URL источника
            records: Список записей для сохранения отпечатков
        """
        fingerprints = []
        for record in records:
            fp = {
                'source_id': source_id,
                'record_id': record.get('id') or record.get('_id') or str(hash(str(record))),
                'content_hash': self.calculate_content_hash(record),
                'original_hash': self.calculate_content_hash(record),
                'verification_status': 'pending',
                'timestamp': datetime.utcnow()
            }
            fingerprints.append(fp)
        
        try:
            self.db.save_fingerprints(fingerprints)
            logger.info(f"Stored {len(fingerprints)} fingerprints for source {source_id}")
        except Exception as e:
            logger.error(f"Error storing fingerprints: {e}")
            raise
    
    def verify_downloaded_data(self, source_id: int, 
                              original_records: List[Dict] = None) -> Dict:
        """
        Проверка соответствия загруженных данных исходным
        
        Args:
            source_id: ID источника
            original_records: Исходные данные (если не указаны, будут загружены)
            
        Returns:
            Словарь с результатами сравнения
        """
        source = self.db.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        # Получаем загруженные данные
        downloaded_records = self.db.get_downloaded_records(source_id)
        
        # Если исходные данные не предоставлены, нужно их загрузить
        # Это зависит от типа источника
        if original_records is None:
            logger.warning(f"Original records not provided for source {source_id}, "
                         "verification may be incomplete")
            original_records = []
        
        # Сравнение
        comparison = {
            'source_id': source_id,
            'source_url': source['url'],
            'total_original': len(original_records),
            'total_downloaded': len(downloaded_records),
            'missing_records': [],
            'mismatched_records': [],
            'extra_records': [],
            'integrity_score': 0.0,
            'verified_at': datetime.utcnow().isoformat()
        }
        
        # Создаем индексы для быстрого поиска
        original_by_id = {}
        for r in original_records:
            record_id = r.get('id') or r.get('_id') or self.calculate_content_hash(r)
            original_by_id[record_id] = r
        
        downloaded_by_id = {}
        for r in downloaded_records:
            record_id = r.get('id') or r.get('_id') or self.calculate_content_hash(r)
            downloaded_by_id[record_id] = r
        
        # Проверяем каждую исходную запись
        for orig_id, orig_record in original_by_id.items():
            if orig_id not in downloaded_by_id:
                comparison['missing_records'].append(orig_id)
            else:
                # Сравниваем хеши
                orig_hash = self.calculate_content_hash(orig_record)
                down_hash = self.calculate_content_hash(downloaded_by_id[orig_id])
                
                if orig_hash != down_hash:
                    differences = self._find_differences(orig_record, downloaded_by_id[orig_id])
                    comparison['mismatched_records'].append({
                        'id': orig_id,
                        'original_hash': orig_hash,
                        'downloaded_hash': down_hash,
                        'differences': differences
                    })
        
        # Находим лишние записи
        for down_id in downloaded_by_id:
            if down_id not in original_by_id:
                comparison['extra_records'].append(down_id)
        
        # Вычисляем score целостности
        if comparison['total_original'] > 0:
            matched = (comparison['total_original'] - 
                      len(comparison['missing_records']) - 
                      len(comparison['mismatched_records']))
            comparison['integrity_score'] = matched / comparison['total_original']
        elif comparison['total_downloaded'] > 0:
            # Если нет исходных данных, считаем что все загружено
            comparison['integrity_score'] = 1.0
        
        return comparison
    
    def _find_differences(self, original: Dict, downloaded: Dict) -> List[str]:
        """
        Находит различия между записями
        
        Args:
            original: Исходная запись
            downloaded: Загруженная запись
            
        Returns:
            Список строк с описанием различий
        """
        differences = []
        all_keys = set(original.keys()) | set(downloaded.keys())
        
        for key in all_keys:
            orig_val = original.get(key)
            down_val = downloaded.get(key)
            
            if orig_val != down_val:
                # Обрезаем длинные значения для читаемости
                orig_str = str(orig_val)[:100] if orig_val else 'None'
                down_str = str(down_val)[:100] if down_val else 'None'
                differences.append(f"{key}: '{orig_str}' != '{down_str}'")
        
        return differences


class IntegrityMonitor:
    """Мониторинг целостности данных"""
    
    def __init__(self, db: DatabaseManager, checker: DataIntegrityChecker):
        """
        Инициализация монитора
        
        Args:
            db: Менеджер базы данных
            checker: Проверяющий целостность
        """
        self.db = db
        self.checker = checker
    
    def verify_all_sources(self) -> List[Dict]:
        """
        Проверка всех источников
        
        Returns:
            Список результатов проверки
        """
        sources = self.db.get_all_active_sources()
        results = []
        
        logger.info(f"Starting verification for {len(sources)} sources")
        
        for source in sources:
            try:
                # Для полной проверки нужны исходные данные
                # Здесь предполагаем, что они будут загружены адаптером
                result = self.checker.verify_downloaded_data(
                    source['id'],
                    original_records=None  # Будет загружено адаптером
                )
                
                results.append({
                    'source_id': source['id'],
                    'source_url': source['url'],
                    'integrity_score': result['integrity_score'],
                    'status': 'ok' if result['integrity_score'] >= 0.99 else 'warning',
                    'missing_count': len(result['missing_records']),
                    'mismatched_count': len(result['mismatched_records']),
                    'extra_count': len(result['extra_records'])
                })
                
                # Обновляем статус источника на основе результата
                if result['integrity_score'] < 0.95:
                    self.db.update_source_status(
                        source['id'],
                        'failed',
                        error_message=f"Low integrity score: {result['integrity_score']:.2%}"
                    )
                
            except Exception as e:
                logger.error(f"Error verifying source {source['id']}: {e}")
                results.append({
                    'source_id': source['id'],
                    'status': 'error',
                    'error': str(e)
                })
        
        logger.info(f"Verification completed: {len(results)} sources checked")
        return results
    
    def schedule_verification(self, source_id: int, interval_hours: int = 24):
        """
        Планирование периодической проверки
        
        Args:
            source_id: ID источника
            interval_hours: Интервал проверки в часах
            
        Note:
            Для реализации периодических проверок используйте Celery Beat или cron
        """
        # Это заглушка - реальная реализация требует планировщика задач
        logger.info(f"Scheduled verification for source {source_id} "
                   f"every {interval_hours} hours")

