"""
Пример использования модулей среднего приоритета:
- Инкрементальное обнаружение изменений
- Автоматические периодические проверки
- Мониторинг и алертинг
"""
import logging
from datetime import datetime

from .database import DatabaseManager
from .download import DataDownloadManager
from .integrity import DataIntegrityChecker, IntegrityMonitor
from .datasets import MLDatasetManager
from .change_detector import ChangeDetector
from .scheduler import PeriodicScheduler
from .monitoring import SystemMonitor, AlertHandler, AlertLevel
from .incremental_pipeline import IncrementalTrainingPipeline

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_change_detection():
    """Пример использования детектора изменений"""
    logger.info("=== Пример: Обнаружение изменений ===")
    
    # Инициализация компонентов
    db = DatabaseManager()
    download_manager = DataDownloadManager(db)
    integrity_checker = DataIntegrityChecker(db)
    change_detector = ChangeDetector(db, download_manager, integrity_checker)
    
    # Обнаружение изменений для конкретного источника
    source_id = 1
    changes = change_detector.detect_changes(source_id)
    
    logger.info(f"Обнаружено изменений: {len(changes)}")
    for change in changes[:5]:  # Показываем первые 5
        logger.info(f"  - {change['change_type']}: {change['document_id']}")
    
    # Обнаружение изменений для всех источников
    all_changes = change_detector.detect_changes_all_sources()
    total = sum(len(changes) for changes in all_changes.values())
    logger.info(f"Всего изменений во всех источниках: {total}")
    
    # Получение недавних изменений
    recent = change_detector.get_recent_changes(hours=24)
    logger.info(f"Изменений за последние 24 часа: {len(recent)}")


def example_periodic_scheduler():
    """Пример использования планировщика периодических задач"""
    logger.info("=== Пример: Периодический планировщик ===")
    
    # Инициализация компонентов
    db = DatabaseManager()
    download_manager = DataDownloadManager(db)
    integrity_checker = DataIntegrityChecker(db)
    integrity_monitor = IntegrityMonitor(db, integrity_checker)
    change_detector = ChangeDetector(db, download_manager, integrity_checker)
    dataset_manager = MLDatasetManager(db)
    
    # Создание планировщика
    scheduler = PeriodicScheduler(
        db=db,
        change_detector=change_detector,
        integrity_monitor=integrity_monitor,
        dataset_manager=dataset_manager
    )
    
    # Настройка задач по умолчанию
    scheduler.setup_default_tasks(
        verification_interval_hours=24,      # Проверка целостности раз в сутки
        change_detection_interval_hours=6,   # Обнаружение изменений каждые 6 часов
        incremental_dataset_interval_hours=24  # Инкрементальный датасет раз в сутки
    )
    
    # Запуск планировщика
    scheduler.start()
    logger.info("Планировщик запущен")
    
    # Получение статуса задач
    status = scheduler.get_task_status()
    for task_name, task_info in status.items():
        logger.info(f"Задача {task_name}: {task_info['status']}, "
                   f"следующий запуск: {task_info['next_run']}")
    
    # Немедленное выполнение задачи
    result = scheduler.run_task_now('change_detection')
    logger.info(f"Результат выполнения: {result['status']}")
    
    # Остановка планировщика (в реальном приложении не останавливаем)
    # scheduler.stop()


def example_monitoring():
    """Пример использования мониторинга и алертинга"""
    logger.info("=== Пример: Мониторинг и алертинг ===")
    
    # Создание обработчика алертов
    def alert_callback(alert):
        """Callback для обработки алертов"""
        logger.warning(f"ALERT [{alert.level.value}]: {alert.message}")
        # Здесь можно добавить отправку email, Slack, и т.д.
    
    alert_handler = AlertHandler(callback=alert_callback)
    
    # Инициализация монитора
    db = DatabaseManager()
    monitor = SystemMonitor(db, alert_handler)
    
    # Проверка здоровья источника
    source_id = 1
    health = monitor.check_source_health(source_id)
    logger.info(f"Здоровье источника {source_id}: {health['status']}")
    if health['issues']:
        logger.warning(f"Проблемы: {health['issues']}")
    
    # Проверка здоровья всех источников
    all_health = monitor.check_all_sources_health()
    unhealthy = [h for h in all_health if h['status'] != 'healthy']
    logger.info(f"Неисправных источников: {len(unhealthy)}")
    
    # Проверка оценок целостности
    integrity_issues = monitor.check_integrity_scores(threshold=0.95)
    logger.info(f"Источников с низкой целостностью: {len(integrity_issues)}")
    
    # Проверка системных метрик
    metrics = monitor.check_system_metrics()
    logger.info(f"Метрики системы: {metrics}")
    
    # Запуск всех проверок здоровья
    health_results = monitor.run_health_checks()
    logger.info(f"Результаты проверок здоровья: {health_results}")
    
    # Получение недавних алертов
    recent_alerts = alert_handler.get_recent_alerts(hours=24)
    logger.info(f"Алертов за последние 24 часа: {len(recent_alerts)}")
    
    # Получение неподтвержденных критических алертов
    critical_alerts = alert_handler.get_unacknowledged_alerts(level=AlertLevel.CRITICAL)
    logger.info(f"Неподтвержденных критических алертов: {len(critical_alerts)}")


def example_incremental_pipeline():
    """Пример использования пайплайна инкрементального обучения"""
    logger.info("=== Пример: Инкрементальный пайплайн ===")
    
    # Инициализация компонентов
    db = DatabaseManager()
    download_manager = DataDownloadManager(db)
    integrity_checker = DataIntegrityChecker(db)
    change_detector = ChangeDetector(db, download_manager, integrity_checker)
    dataset_manager = MLDatasetManager(db)
    
    # Создание пайплайна
    pipeline = IncrementalTrainingPipeline(
        db=db,
        dataset_manager=dataset_manager,
        change_detector=change_detector
    )
    
    # Получение статистики для инкрементального обновления
    base_version_id = 1
    stats = pipeline.get_incremental_statistics(base_version_id)
    logger.info(f"Статистика для версии {base_version_id}:")
    logger.info(f"  Всего изменений: {stats['total_changes']}")
    logger.info(f"  Изменений по типам: {stats['changes_by_type']}")
    logger.info(f"  Готово к обновлению: {stats['ready_for_update']}")
    
    # Запуск инкрементального обновления
    if stats['ready_for_update']:
        new_version_id = pipeline.run_incremental_update(
            base_version_id=base_version_id,
            min_new_samples=100
        )
        if new_version_id:
            logger.info(f"Создана новая версия датасета: {new_version_id}")
        else:
            logger.info("Недостаточно изменений для создания новой версии")
    else:
        logger.info("Недостаточно изменений для обновления")


def example_full_integration():
    """Пример полной интеграции всех компонентов"""
    logger.info("=== Пример: Полная интеграция ===")
    
    # Инициализация всех компонентов
    db = DatabaseManager()
    download_manager = DataDownloadManager(db)
    integrity_checker = DataIntegrityChecker(db)
    integrity_monitor = IntegrityMonitor(db, integrity_checker)
    change_detector = ChangeDetector(db, download_manager, integrity_checker)
    dataset_manager = MLDatasetManager(db)
    pipeline = IncrementalTrainingPipeline(db, dataset_manager, change_detector)
    
    # Создание обработчика алертов
    alert_handler = AlertHandler()
    monitor = SystemMonitor(db, alert_handler)
    
    # Создание и настройка планировщика
    scheduler = PeriodicScheduler(
        db=db,
        change_detector=change_detector,
        integrity_monitor=integrity_monitor,
        dataset_manager=dataset_manager
    )
    scheduler.setup_default_tasks()
    
    # Запуск планировщика
    scheduler.start()
    logger.info("Система мониторинга и планирования запущена")
    
    # Пример ручного запуска проверок
    logger.info("Запуск ручных проверок...")
    
    # Проверка здоровья
    health_results = monitor.run_health_checks()
    logger.info(f"Проверка здоровья завершена: {len(health_results['sources_health'])} источников")
    
    # Обнаружение изменений
    changes = change_detector.detect_changes_all_sources()
    total_changes = sum(len(c) for c in changes.values())
    logger.info(f"Обнаружено изменений: {total_changes}")
    
    # Статус задач
    task_status = scheduler.get_task_status()
    logger.info(f"Зарегистрировано задач: {len(task_status)}")
    
    # В реальном приложении планировщик работает постоянно
    # scheduler.stop()


if __name__ == '__main__':
    # Раскомментируйте нужный пример для запуска
    
    # example_change_detection()
    # example_periodic_scheduler()
    # example_monitoring()
    # example_incremental_pipeline()
    # example_full_integration()
    
    logger.info("Примеры готовы к использованию. Раскомментируйте нужный пример.")

