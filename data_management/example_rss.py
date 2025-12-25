"""
Пример использования RSS-источников в системе
"""
import logging
from datetime import datetime

from .database import DatabaseManager
from .download import DataDownloadManager, RSSFeedAdapter
from .change_detector import ChangeDetector
from .integrity import DataIntegrityChecker

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_rss_adapter():
    """Пример использования RSSFeedAdapter напрямую"""
    logger.info("=== Пример: Использование RSSFeedAdapter ===")
    
    # Пример RSS-фида (замените на реальный)
    rss_url = "https://data.gov.ua/feed"  # Пример URL
    
    try:
        adapter = RSSFeedAdapter(rss_url)
        
        # Получение информации о фиде
        feed_info = adapter.get_feed_info()
        logger.info(f"Feed info: {feed_info}")
        
        # Оценка количества записей
        total = adapter.estimate_total()
        logger.info(f"Total entries: {total}")
        
        # Загрузка первых 10 записей
        entries = adapter.download_incremental(0, 10)
        logger.info(f"Downloaded {len(entries)} entries")
        
        # Показываем первую запись
        if entries:
            first_entry = entries[0]
            logger.info(f"First entry:")
            logger.info(f"  Title: {first_entry.get('title')}")
            logger.info(f"  Published: {first_entry.get('published')}")
            logger.info(f"  Link: {first_entry.get('link')}")
            logger.info(f"  Categories: {first_entry.get('categories')}")
    
    except Exception as e:
        logger.error(f"Error: {e}")


def example_register_rss_source():
    """Пример регистрации RSS-источника в системе"""
    logger.info("=== Пример: Регистрация RSS-источника ===")
    
    db = DatabaseManager()
    download_manager = DataDownloadManager(db)
    
    # Регистрация RSS-источника
    rss_url = "https://data.gov.ua/feed"
    source_id = download_manager.register_source(
        url=rss_url,
        source_type='rss',
        metadata={
            'feed_type': 'rss',
            'update_frequency': 'hourly',
            'description': 'RSS feed for data.gov.ua updates'
        }
    )
    
    logger.info(f"Registered RSS source with ID: {source_id}")
    
    # Загрузка данных из RSS
    try:
        download_manager.resume_download(source_id, batch_size=50)
        logger.info("RSS feed downloaded successfully")
    except Exception as e:
        logger.error(f"Error downloading RSS feed: {e}")


def example_rss_change_detection():
    """Пример обнаружения изменений в RSS-источнике"""
    logger.info("=== Пример: Обнаружение изменений в RSS ===")
    
    db = DatabaseManager()
    download_manager = DataDownloadManager(db)
    integrity_checker = DataIntegrityChecker(db)
    change_detector = ChangeDetector(db, download_manager, integrity_checker)
    
    # Предполагаем, что источник уже зарегистрирован
    source_id = 1  # Замените на реальный ID
    
    # Обнаружение изменений
    changes = change_detector.detect_changes(source_id)
    
    logger.info(f"Detected {len(changes)} changes")
    
    for change in changes[:5]:  # Показываем первые 5
        logger.info(f"  - {change['change_type']}: {change['document_id']}")
        if change.get('metadata', {}).get('published'):
            logger.info(f"    Published: {change['metadata']['published']}")


def example_rss_incremental_update():
    """Пример инкрементального обновления RSS-источника"""
    logger.info("=== Пример: Инкрементальное обновление RSS ===")
    
    db = DatabaseManager()
    download_manager = DataDownloadManager(db)
    
    # Регистрация RSS-источника
    rss_url = "https://data.gov.ua/feed"
    source_id = download_manager.register_source(
        url=rss_url,
        source_type='rss'
    )
    
    # Первая загрузка
    logger.info("First download...")
    download_manager.resume_download(source_id, batch_size=50)
    
    # Получаем информацию об источнике
    source = db.get_source(source_id)
    logger.info(f"Downloaded {source.get('downloaded_records', 0)} records")
    
    # Через некоторое время (например, через час) - инкрементальное обновление
    # RSSFeedAdapter автоматически использует ETag и Last-Modified для эффективных обновлений
    logger.info("Incremental update...")
    
    # Создаем адаптер
    adapter = RSSFeedAdapter(rss_url)
    
    # Загружаем только новые записи (RSS обычно содержит последние записи)
    new_entries = adapter.download_incremental(0, 100)
    
    logger.info(f"Found {len(new_entries)} entries in feed")
    
    # Проверяем, какие из них новые (по guid)
    # Это можно сделать через ChangeDetector


def example_rss_feed_info():
    """Пример получения информации о RSS-фиде"""
    logger.info("=== Пример: Информация о RSS-фиде ===")
    
    rss_url = "https://data.gov.ua/feed"
    
    try:
        adapter = RSSFeedAdapter(rss_url)
        feed_info = adapter.get_feed_info()
        
        logger.info("RSS Feed Information:")
        logger.info(f"  Title: {feed_info.get('title')}")
        logger.info(f"  Description: {feed_info.get('description', '')[:100]}...")
        logger.info(f"  Link: {feed_info.get('link')}")
        logger.info(f"  Language: {feed_info.get('language')}")
        logger.info(f"  Version: {feed_info.get('version')}")
        logger.info(f"  Total entries: {feed_info.get('total_entries')}")
        logger.info(f"  Last updated: {feed_info.get('updated')}")
    
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == '__main__':
    # Раскомментируйте нужный пример для запуска
    
    # example_rss_adapter()
    # example_register_rss_source()
    # example_rss_change_detection()
    # example_rss_incremental_update()
    # example_rss_feed_info()
    
    logger.info("RSS examples ready. Uncomment the example you want to run.")

