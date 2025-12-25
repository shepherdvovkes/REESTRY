"""
Модуль для инкрементального обнаружения изменений в источниках данных
"""
import hashlib
import json
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .database import DatabaseManager
from .download import DataDownloadManager, DataSourceAdapter
from .integrity import DataIntegrityChecker

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Обнаружение изменений в документах и источниках данных"""
    
    def __init__(self, db: DatabaseManager, download_manager: DataDownloadManager,
                 integrity_checker: DataIntegrityChecker):
        """
        Инициализация детектора изменений
        
        Args:
            db: Менеджер базы данных
            download_manager: Менеджер загрузки данных
            integrity_checker: Проверяющий целостность данных
        """
        self.db = db
        self.download_manager = download_manager
        self.integrity_checker = integrity_checker
    
    def _calculate_hash(self, data: Dict) -> str:
        """Вычисление хеша данных"""
        normalized = self.integrity_checker._normalize_for_hash(data)
        content_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    def _has_changes(self, old: Dict, new: Dict) -> bool:
        """Проверка наличия изменений"""
        old_hash = self._calculate_hash(old)
        new_hash = self._calculate_hash(new)
        return old_hash != new_hash
    
    def _get_field_changes(self, old: Dict, new: Dict) -> Dict[str, Dict]:
        """Получение изменений по полям"""
        changes = {}
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            
            if old_val != new_val:
                changes[key] = {
                    'old': old_val,
                    'new': new_val
                }
        
        return changes
    
    def _fetch_current_data(self, source: Dict) -> List[Dict]:
        """Загрузка текущих данных из источника"""
        try:
            # Создаем адаптер для источника
            adapter_class = self.download_manager.adapters.get(source['source_type'])
            if not adapter_class:
                logger.warning(f"Unknown source type: {source['source_type']}")
                return []
            
            # Инициализируем адаптер
            adapter_kwargs = {}
            if source.get('metadata'):
                if 'auth' in source['metadata']:
                    adapter_kwargs['auth'] = source['metadata']['auth']
                if 'pagination_params' in source['metadata']:
                    adapter_kwargs['pagination_params'] = source['metadata']['pagination_params']
            
            adapter = adapter_class(source['url'], **adapter_kwargs)
            
            # Загружаем все данные
            return adapter.fetch_original_data()
        except Exception as e:
            logger.error(f"Error fetching current data for source {source['id']}: {e}")
            return []
    
    def _get_saved_data(self, source_id: int) -> List[Dict]:
        """Получение сохраненных данных для источника"""
        try:
            return self.db.get_downloaded_records(source_id)
        except Exception as e:
            logger.error(f"Error getting saved data for source {source_id}: {e}")
            return []
    
    def detect_changes(self, source_id: int) -> List[Dict]:
        """
        Обнаружение изменений в источниках
        
        Args:
            source_id: ID источника для проверки
            
        Returns:
            Список обнаруженных изменений
        """
        source = self.db.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        logger.info(f"Detecting changes for source {source_id}: {source['url']}")
        
        # Для RSS-источников используем оптимизированный метод
        if source.get('source_type') == 'rss':
            return self._detect_rss_changes(source_id, source)
        
        # Загружаем текущие данные из источника
        current_data = self._fetch_current_data(source)
        
        if not current_data:
            logger.warning(f"No current data fetched for source {source_id}")
            return []
        
        # Загружаем сохраненные данные
        saved_data = self._get_saved_data(source_id)
        
        # Сравниваем и находим изменения
        changes = []
        
        # Индексируем сохраненные данные
        saved_by_id = {}
        for record in saved_data:
            record_id = record.get('id') or record.get('_id') or record.get('document_id') or record.get('guid')
            if record_id:
                saved_by_id[record_id] = record
        
        # Проверяем текущие данные
        current_ids = set()
        for current_record in current_data:
            # Для RSS используем guid, для других - id
            record_id = (current_record.get('guid') or 
                        current_record.get('id') or 
                        current_record.get('_id') or 
                        current_record.get('document_id'))
            
            if not record_id:
                # Если нет ID, используем хеш содержимого
                record_id = self._calculate_hash(current_record)
            
            current_ids.add(record_id)
            
            if record_id not in saved_by_id:
                # Новая запись
                new_hash = self._calculate_hash(current_record)
                changes.append({
                    'document_id': str(record_id),
                    'change_type': 'created',
                    'new_data': current_record,
                    'new_content_hash': new_hash,
                    'old_content_hash': None,
                    'metadata': {
                        'source_id': source_id,
                        'source_url': source['url'],
                        'detected_at': datetime.utcnow().isoformat()
                    }
                })
            else:
                # Проверяем на изменения
                saved_record = saved_by_id[record_id]
                if self._has_changes(current_record, saved_record):
                    field_changes = self._get_field_changes(saved_record, current_record)
                    old_hash = self._calculate_hash(saved_record)
                    new_hash = self._calculate_hash(current_record)
                    
                    changes.append({
                        'document_id': str(record_id),
                        'change_type': 'updated',
                        'old_data': saved_record,
                        'new_data': current_record,
                        'old_content_hash': old_hash,
                        'new_content_hash': new_hash,
                        'changes': field_changes,
                        'metadata': {
                            'source_id': source_id,
                            'source_url': source['url'],
                            'detected_at': datetime.utcnow().isoformat(),
                            'changed_fields': list(field_changes.keys())
                        }
                    })
        
        # Проверяем удаленные записи
        for saved_id, saved_record in saved_by_id.items():
            if saved_id not in current_ids:
                old_hash = self._calculate_hash(saved_record)
                changes.append({
                    'document_id': str(saved_id),
                    'change_type': 'deleted',
                    'old_data': saved_record,
                    'new_data': None,
                    'old_content_hash': old_hash,
                    'new_content_hash': None,
                    'metadata': {
                        'source_id': source_id,
                        'source_url': source['url'],
                        'detected_at': datetime.utcnow().isoformat()
                    }
                })
        
        # Сохраняем изменения в БД
        if changes:
            try:
                self.db.save_changes(changes)
                logger.info(f"Detected {len(changes)} changes for source {source_id}: "
                          f"{sum(1 for c in changes if c['change_type'] == 'created')} created, "
                          f"{sum(1 for c in changes if c['change_type'] == 'updated')} updated, "
                          f"{sum(1 for c in changes if c['change_type'] == 'deleted')} deleted")
            except Exception as e:
                logger.error(f"Error saving changes: {e}")
        
        return changes
    
    def detect_changes_all_sources(self) -> Dict[int, List[Dict]]:
        """
        Обнаружение изменений во всех активных источниках
        
        Returns:
            Словарь {source_id: [changes]}
        """
        sources = self.db.get_all_active_sources()
        all_changes = {}
        
        logger.info(f"Detecting changes for {len(sources)} sources")
        
        for source in sources:
            try:
                changes = self.detect_changes(source['id'])
                all_changes[source['id']] = changes
            except Exception as e:
                logger.error(f"Error detecting changes in source {source['id']}: {e}")
                all_changes[source['id']] = []
        
        total_changes = sum(len(changes) for changes in all_changes.values())
        logger.info(f"Total changes detected: {total_changes} across {len(sources)} sources")
        
        return all_changes
    
    def _detect_rss_changes(self, source_id: int, source: Dict) -> List[Dict]:
        """
        Оптимизированное обнаружение изменений для RSS-источников
        
        Args:
            source_id: ID источника
            source: Информация об источнике
            
        Returns:
            Список обнаруженных изменений
        """
        logger.info(f"Using optimized RSS change detection for source {source_id}")
        
        try:
            # Создаем RSS адаптер
            from .download import RSSFeedAdapter
            adapter = RSSFeedAdapter(source['url'])
            
            # Загружаем текущие записи из RSS
            current_data = adapter.download_incremental(0, 1000)  # RSS обычно содержит последние записи
            
            if not current_data:
                return []
            
            # Загружаем сохраненные данные
            saved_data = self._get_saved_data(source_id)
            
            # Для RSS используем guid для идентификации
            saved_by_guid = {}
            for record in saved_data:
                guid = record.get('guid') or record.get('id')
                if guid:
                    saved_by_guid[guid] = record
            
            changes = []
            current_guids = set()
            
            # Проверяем текущие записи
            for current_record in current_data:
                guid = current_record.get('guid') or current_record.get('id')
                if not guid:
                    continue
                
                current_guids.add(guid)
                
                if guid not in saved_by_guid:
                    # Новая запись
                    changes.append({
                        'document_id': str(guid),
                        'change_type': 'created',
                        'new_data': current_record,
                        'new_content_hash': self._calculate_hash(current_record),
                        'old_content_hash': None,
                        'metadata': {
                            'source_id': source_id,
                            'source_url': source['url'],
                            'detected_at': datetime.utcnow().isoformat(),
                            'published': current_record.get('published'),
                            'rss_source': True
                        }
                    })
                else:
                    # Проверяем на обновления (по дате или содержимому)
                    saved_record = saved_by_guid[guid]
                    current_published = current_record.get('published')
                    saved_published = saved_record.get('published')
                    
                    # Если дата публикации изменилась или содержимое изменилось
                    if (current_published != saved_published or 
                        self._has_changes(current_record, saved_record)):
                        
                        field_changes = self._get_field_changes(saved_record, current_record)
                        old_hash = self._calculate_hash(saved_record)
                        new_hash = self._calculate_hash(current_record)
                        
                        changes.append({
                            'document_id': str(guid),
                            'change_type': 'updated',
                            'old_data': saved_record,
                            'new_data': current_record,
                            'old_content_hash': old_hash,
                            'new_content_hash': new_hash,
                            'changes': field_changes,
                            'metadata': {
                                'source_id': source_id,
                                'source_url': source['url'],
                                'detected_at': datetime.utcnow().isoformat(),
                                'changed_fields': list(field_changes.keys()),
                                'published_changed': current_published != saved_published,
                                'rss_source': True
                            }
                        })
            
            # Проверяем удаленные записи (только если они были недавно опубликованы)
            # RSS обычно не содержит информацию об удаленных записях
            # Но мы можем пометить записи как "не найдены в последнем фиде"
            # Это менее критично для RSS, так как RSS обычно содержит только последние записи
            
            # Сохраняем изменения
            if changes:
                try:
                    self.db.save_changes(changes)
                    logger.info(f"Detected {len(changes)} RSS changes for source {source_id}: "
                              f"{sum(1 for c in changes if c['change_type'] == 'created')} created, "
                              f"{sum(1 for c in changes if c['change_type'] == 'updated')} updated")
                except Exception as e:
                    logger.error(f"Error saving RSS changes: {e}")
            
            return changes
            
        except Exception as e:
            logger.error(f"Error in RSS change detection for source {source_id}: {e}")
            # Fallback на обычный метод
            return self.detect_changes(source_id)
    
    def get_recent_changes(self, source_id: Optional[int] = None, 
                          hours: int = 24) -> List[Dict]:
        """
        Получение недавних изменений
        
        Args:
            source_id: ID источника (если None, для всех источников)
            hours: Количество часов назад
            
        Returns:
            Список изменений
        """
        # Используем параметризованный запрос для безопасности
        query = """
            SELECT * FROM document_changes 
            WHERE changed_at > NOW() - INTERVAL '%s hours'
        """ % hours
        
        params = []
        
        if source_id:
            # Фильтруем по source_id из metadata
            query = """
                SELECT * FROM document_changes 
                WHERE changed_at > NOW() - INTERVAL '%s hours'
                AND metadata->>'source_id' = %s
            """ % hours
            params.append(str(source_id))
        
        query += " ORDER BY changed_at DESC"
        
        return self.db.execute_query(query, tuple(params) if params else None)

