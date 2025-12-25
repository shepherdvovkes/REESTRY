"""
Модуль для управления загрузкой данных из различных источников
"""
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs
import logging
import time
from abc import ABC, abstractmethod
import json
import csv
from io import StringIO
from bs4 import BeautifulSoup

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class DataSourceAdapter(ABC):
    """Базовый класс для адаптеров источников данных"""
    
    def __init__(self, url: str, auth: Optional[Dict] = None):
        """
        Инициализация адаптера
        
        Args:
            url: URL источника
            auth: Параметры аутентификации (если нужны)
        """
        self.url = url
        self.auth = auth
    
    @abstractmethod
    def estimate_total(self) -> int:
        """Оценка общего количества записей"""
        pass
    
    @abstractmethod
    def download_incremental(self, offset: int, limit: int) -> List[Dict]:
        """Инкрементальная загрузка с пагинацией"""
        pass
    
    def supports_incremental(self) -> bool:
        """Поддерживает ли источник инкрементальную загрузку"""
        return True
    
    def fetch_original_data(self) -> List[Dict]:
        """Загрузить все исходные данные для проверки целостности"""
        all_data = []
        offset = 0
        limit = 1000
        
        while True:
            batch = self.download_incremental(offset, limit)
            if not batch:
                break
            all_data.extend(batch)
            offset += len(batch)
            if len(batch) < limit:
                break
        
        return all_data


class APISourceAdapter(DataSourceAdapter):
    """Адаптер для REST API"""
    
    def __init__(self, url: str, auth: Optional[Dict] = None, 
                 pagination_params: Optional[Dict] = None):
        """
        Инициализация API адаптера
        
        Args:
            url: Базовый URL API
            auth: Параметры аутентификации
            pagination_params: Параметры пагинации {'offset': 'offset', 'limit': 'limit'}
        """
        super().__init__(url, auth)
        self.pagination_params = pagination_params or {
            'offset': 'offset',
            'limit': 'limit'
        }
        self.session = requests.Session()
        if auth:
            if 'token' in auth:
                self.session.headers['Authorization'] = f"Bearer {auth['token']}"
            elif 'api_key' in auth:
                self.session.headers['X-API-Key'] = auth['api_key']
    
    def estimate_total(self) -> int:
        """Оценка общего количества записей"""
        try:
            # Пробуем получить первую страницу с метаданными
            params = {self.pagination_params['limit']: 1}
            response = self.session.get(self.url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            # Ищем поле с общим количеством
            if isinstance(data, dict):
                total = data.get('total') or data.get('count') or data.get('total_count')
                if total:
                    return int(total)
            
            # Если не нашли, возвращаем -1 (неизвестно)
            return -1
        except Exception as e:
            logger.warning(f"Could not estimate total for {self.url}: {e}")
            return -1
    
    def download_incremental(self, offset: int, limit: int) -> List[Dict]:
        """Инкрементальная загрузка с пагинацией"""
        try:
            params = {
                self.pagination_params['offset']: offset,
                self.pagination_params['limit']: limit
            }
            
            response = self.session.get(self.url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Обрабатываем разные форматы ответа
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Ищем массив данных
                for key in ['data', 'results', 'items', 'records']:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                # Если не нашли, возвращаем весь объект как одну запись
                return [data]
            
            return []
        except Exception as e:
            logger.error(f"Error downloading from API {self.url}: {e}")
            raise


class FileSourceAdapter(DataSourceAdapter):
    """Адаптер для файлов (CSV, JSON, XML)"""
    
    def __init__(self, url: str, file_type: str = None):
        """
        Инициализация файлового адаптера
        
        Args:
            url: URL файла
            file_type: Тип файла ('csv', 'json', 'xml') - определяется автоматически если не указан
        """
        super().__init__(url)
        self.file_type = file_type or self._detect_file_type(url)
        self._cached_data = None
    
    def _detect_file_type(self, url: str) -> str:
        """Определение типа файла по URL"""
        url_lower = url.lower()
        if url_lower.endswith('.csv'):
            return 'csv'
        elif url_lower.endswith('.json'):
            return 'json'
        elif url_lower.endswith('.xml'):
            return 'xml'
        else:
            # Пробуем определить по Content-Type
            try:
                response = requests.head(url, timeout=10)
                content_type = response.headers.get('Content-Type', '').lower()
                if 'csv' in content_type:
                    return 'csv'
                elif 'json' in content_type:
                    return 'json'
                elif 'xml' in content_type:
                    return 'xml'
            except:
                pass
            return 'json'  # По умолчанию
    
    def _load_file(self):
        """Загрузить и кэшировать файл"""
        if self._cached_data is None:
            response = requests.get(self.url, timeout=60)
            response.raise_for_status()
            
            if self.file_type == 'csv':
                content = response.text
                reader = csv.DictReader(StringIO(content))
                self._cached_data = list(reader)
            elif self.file_type == 'json':
                self._cached_data = response.json()
                if not isinstance(self._cached_data, list):
                    self._cached_data = [self._cached_data]
            else:
                # Для XML нужна дополнительная обработка
                logger.warning(f"XML parsing not fully implemented for {self.url}")
                self._cached_data = []
        
        return self._cached_data
    
    def estimate_total(self) -> int:
        """Оценка общего количества записей"""
        data = self._load_file()
        return len(data)
    
    def download_incremental(self, offset: int, limit: int) -> List[Dict]:
        """Инкрементальная загрузка с пагинацией"""
        data = self._load_file()
        return data[offset:offset + limit]


class WebSourceAdapter(DataSourceAdapter):
    """Адаптер для веб-страниц с пагинацией"""
    
    def __init__(self, url: str, use_playwright: bool = False):
        """
        Инициализация веб-адаптера
        
        Args:
            url: URL страницы
            use_playwright: Использовать Playwright для JS-рендеринга
        """
        super().__init__(url)
        self.use_playwright = use_playwright
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def estimate_total(self) -> int:
        """Оценка общего количества записей"""
        # Для веб-страниц сложно оценить без парсинга
        return -1
    
    def download_incremental(self, offset: int, limit: int) -> List[Dict]:
        """Инкрементальная загрузка с пагинацией"""
        try:
            # Пробуем добавить параметры пагинации к URL
            parsed = urlparse(self.url)
            params = {}
            if parsed.query:
                params = dict(parse_qs(parsed.query))
                params = {k: v[0] if isinstance(v, list) else v for k, v in params.items()}
            
            # Добавляем параметры пагинации
            params['page'] = (offset // limit) + 1
            params['per_page'] = limit
            
            if self.use_playwright:
                # Используем Playwright для JS-страниц
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(self.url, wait_until='networkidle', timeout=30000)
                    html = page.content()
                    browser.close()
            else:
                response = self.session.get(self.url, params=params, timeout=30)
                response.raise_for_status()
                html = response.text
            
            # Парсим HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем таблицы или списки данных
            records = []
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')[1:]  # Пропускаем заголовок
                for row in rows[offset:offset + limit]:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        record = {}
                        for i, cell in enumerate(cells):
                            record[f'column_{i}'] = cell.get_text(strip=True)
                        records.append(record)
            
            return records
        except Exception as e:
            logger.error(f"Error downloading from web {self.url}: {e}")
            raise


class RSSFeedAdapter(DataSourceAdapter):
    """Адаптер для RSS/Atom feeds"""
    
    def __init__(self, url: str, auth: Optional[Dict] = None):
        """
        Инициализация RSS адаптера
        
        Args:
            url: URL RSS/Atom фида
            auth: Параметры аутентификации (если нужны)
        """
        super().__init__(url, auth)
        self._cached_feed = None
        self._feed_etag = None
        self._feed_modified = None
    
    def _parse_feed(self):
        """Парсинг RSS/Atom фида"""
        try:
            import feedparser
            
            # Подготовка заголовков для условных запросов
            headers = {}
            if self._feed_etag:
                headers['If-None-Match'] = self._feed_etag
            if self._feed_modified:
                headers['If-Modified-Since'] = self._feed_modified
            
            # Добавляем аутентификацию если есть
            if self.auth:
                if 'token' in self.auth:
                    headers['Authorization'] = f"Bearer {self.auth['token']}"
                elif 'api_key' in self.auth:
                    headers['X-API-Key'] = self.auth['api_key']
            
            # Парсим фид
            feed = feedparser.parse(self.url, etag=self._feed_etag, modified=self._feed_modified)
            
            # Сохраняем ETag и Last-Modified для следующих запросов
            if hasattr(feed, 'etag'):
                self._feed_etag = feed.etag
            if hasattr(feed, 'modified'):
                self._feed_modified = feed.modified
            
            # Проверяем статус (304 Not Modified)
            if feed.status == 304:
                logger.debug(f"Feed {self.url} not modified since last check")
                return self._cached_feed if self._cached_feed else feed
            
            # Проверяем ошибки
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning for {self.url}: {feed.bozo_exception}")
            
            self._cached_feed = feed
            return feed
            
        except ImportError:
            logger.error("feedparser library not installed. Install it with: pip install feedparser")
            raise
        except Exception as e:
            logger.error(f"Error parsing RSS feed {self.url}: {e}")
            raise
    
    def estimate_total(self) -> int:
        """Оценка общего количества записей в фиде"""
        try:
            feed = self._parse_feed()
            if feed and hasattr(feed, 'entries'):
                return len(feed.entries)
            return -1
        except Exception as e:
            logger.warning(f"Could not estimate total for RSS feed {self.url}: {e}")
            return -1
    
    def download_incremental(self, offset: int, limit: int) -> List[Dict]:
        """
        Инкрементальная загрузка записей из RSS-фида
        
        Args:
            offset: Смещение (номер записи с которой начинать)
            limit: Максимальное количество записей
            
        Returns:
            Список записей из RSS-фида
        """
        try:
            feed = self._parse_feed()
            
            if not feed or not hasattr(feed, 'entries'):
                logger.warning(f"No entries found in RSS feed {self.url}")
                return []
            
            # RSS-фиды обычно отсортированы по дате (новые первыми)
            entries = feed.entries[offset:offset + limit]
            
            records = []
            for entry in entries:
                # Извлекаем дату публикации
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    from datetime import datetime
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'published'):
                    published = entry.published
                
                # Извлекаем дату обновления
                updated = None
                if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    from datetime import datetime
                    updated = datetime(*entry.updated_parsed[:6])
                elif hasattr(entry, 'updated'):
                    updated = entry.updated
                
                # Извлекаем категории/теги
                categories = []
                if hasattr(entry, 'tags'):
                    categories = [tag.get('term', '') for tag in entry.tags]
                elif hasattr(entry, 'category'):
                    categories = [entry.category] if isinstance(entry.category, str) else entry.category
                
                # Извлекаем контент
                content = ''
                if hasattr(entry, 'content'):
                    # Может быть список словарей
                    if isinstance(entry.content, list) and len(entry.content) > 0:
                        content = entry.content[0].get('value', '')
                    elif isinstance(entry.content, str):
                        content = entry.content
                elif hasattr(entry, 'summary'):
                    content = entry.summary
                elif hasattr(entry, 'description'):
                    content = entry.description
                
                # Формируем запись
                record = {
                    'id': entry.get('id') or entry.get('link') or entry.get('guid'),
                    'guid': entry.get('id') or entry.get('guid') or entry.get('link'),
                    'title': entry.get('title', ''),
                    'description': entry.get('description', '') or entry.get('summary', ''),
                    'content': content,
                    'link': entry.get('link', ''),
                    'published': published.isoformat() if isinstance(published, datetime) else str(published) if published else None,
                    'updated': updated.isoformat() if isinstance(updated, datetime) else str(updated) if updated else None,
                    'author': entry.get('author', '') or (entry.get('authors', [{}])[0].get('name', '') if entry.get('authors') else ''),
                    'categories': categories,
                    'source': feed.feed.get('title', '') if hasattr(feed, 'feed') else '',
                    'source_link': feed.feed.get('link', '') if hasattr(feed, 'feed') else '',
                    'rss_metadata': {
                        'feed_title': feed.feed.get('title', '') if hasattr(feed, 'feed') else '',
                        'feed_description': feed.feed.get('description', '') if hasattr(feed, 'feed') else '',
                        'feed_language': feed.feed.get('language', '') if hasattr(feed, 'feed') else '',
                        'feed_version': feed.version if hasattr(feed, 'version') else '',
                    }
                }
                
                records.append(record)
            
            logger.debug(f"Downloaded {len(records)} entries from RSS feed {self.url}")
            return records
            
        except Exception as e:
            logger.error(f"Error downloading from RSS feed {self.url}: {e}")
            raise
    
    def get_feed_info(self) -> Dict:
        """
        Получение информации о фиде
        
        Returns:
            Словарь с информацией о фиде
        """
        try:
            feed = self._parse_feed()
            if not feed or not hasattr(feed, 'feed'):
                return {}
            
            feed_info = feed.feed
            return {
                'title': feed_info.get('title', ''),
                'description': feed_info.get('description', '') or feed_info.get('subtitle', ''),
                'link': feed_info.get('link', ''),
                'language': feed_info.get('language', ''),
                'updated': feed_info.get('updated', ''),
                'version': feed.version if hasattr(feed, 'version') else '',
                'total_entries': len(feed.entries) if hasattr(feed, 'entries') else 0
            }
        except Exception as e:
            logger.error(f"Error getting feed info for {self.url}: {e}")
            return {}


class DataDownloadManager:
    """Менеджер загрузки данных с возобновлением"""
    
    def __init__(self, db: DatabaseManager):
        """
        Инициализация менеджера загрузки
        
        Args:
            db: Менеджер базы данных
        """
        self.db = db
        self.adapters = {
            'api': APISourceAdapter,
            'file': FileSourceAdapter,
            'web': WebSourceAdapter,
            'rss': RSSFeedAdapter
        }
    
    def register_source(self, url: str, source_type: str, 
                      domain: str = None, metadata: Dict = None) -> int:
        """
        Регистрация нового источника
        
        Args:
            url: URL источника
            source_type: Тип источника ('api', 'file', 'web', 'rss')
            domain: Домен источника
            metadata: Дополнительные метаданные
            
        Returns:
            ID созданного источника
        """
        if not domain:
            parsed = urlparse(url)
            domain = parsed.netloc
        
        source_id = self.db.create_source(url, source_type, domain, metadata)
        logger.info(f"Registered source {source_id}: {url} ({source_type})")
        return source_id
    
    def resume_download(self, source_id: int, batch_size: int = 1000):
        """
        Возобновление прерванной загрузки
        
        Args:
            source_id: ID источника
            batch_size: Размер батча для загрузки
        """
        source = self.db.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        logger.info(f"Resuming download for source {source_id}: {source['url']}")
        
        # Создаем адаптер
        adapter_class = self.adapters.get(source['source_type'])
        if not adapter_class:
            raise ValueError(f"Unknown source type: {source['source_type']}")
        
        # Инициализируем адаптер с метаданными
        adapter_kwargs = {}
        if source.get('metadata'):
            if 'auth' in source['metadata']:
                adapter_kwargs['auth'] = source['metadata']['auth']
            if 'pagination_params' in source['metadata']:
                adapter_kwargs['pagination_params'] = source['metadata']['pagination_params']
        
        adapter = adapter_class(source['url'], **adapter_kwargs)
        
        # Обновляем статус
        self.db.update_source_status(source_id, 'downloading')
        
        # Продолжаем с места остановки
        offset = source.get('downloaded_records', 0)
        total_downloaded = offset
        
        try:
            # Оцениваем общее количество (если возможно)
            total_estimate = adapter.estimate_total()
            if total_estimate > 0 and source.get('total_records') != total_estimate:
                # Обновляем оценку общего количества
                self.db.execute_query(
                    "UPDATE data_sources SET total_records = %s WHERE id = %s",
                    (total_estimate, source_id),
                    fetch=False
                )
            
            while True:
                # Загружаем батч
                batch = adapter.download_incremental(offset, batch_size)
                if not batch:
                    break
                
                # Сохраняем батч (это нужно реализовать в зависимости от структуры БД)
                # self.save_batch(source_id, batch)
                
                # Обновляем прогресс
                offset += len(batch)
                total_downloaded += len(batch)
                self.db.update_progress(source_id, total_downloaded)
                
                logger.info(f"Downloaded {total_downloaded} records from source {source_id}")
                
                # Проверяем завершение
                if len(batch) < batch_size:
                    break
                
                # Небольшая задержка для избежания перегрузки
                time.sleep(0.1)
            
            # Обновляем статус на завершено
            self.db.update_source_status(source_id, 'completed', total_downloaded)
            logger.info(f"Download completed for source {source_id}: {total_downloaded} records")
            
        except Exception as e:
            logger.error(f"Error during download for source {source_id}: {e}")
            self.db.update_source_status(source_id, 'failed', error_message=str(e))
            raise
    
    def discover_new_sources(self, seed_urls: List[str] = None):
        """
        Периодическое обнаружение новых источников
        
        Args:
            seed_urls: Начальные URL для поиска (если не указаны, используются из конфига)
        
        Note:
            Это заглушка - реальная реализация требует интеграции с краулером
        """
        logger.info("Discovering new sources...")
        # Интеграция с UkrDeepCrawler для поиска новых источников
        # Здесь можно использовать результаты краулера
        pass

