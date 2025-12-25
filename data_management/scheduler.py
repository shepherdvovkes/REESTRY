"""
Модуль для автоматических периодических проверок и задач
"""
import time
import threading
from typing import Dict, List, Callable, Optional
from datetime import datetime, timedelta
import logging
from enum import Enum

from .database import DatabaseManager
from .change_detector import ChangeDetector
from .integrity import IntegrityMonitor
from .datasets import MLDatasetManager

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Статусы задач"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PeriodicTask:
    """Периодическая задача"""
    
    def __init__(self, name: str, func: Callable, interval_seconds: int,
                 enabled: bool = True, last_run: Optional[datetime] = None):
        """
        Инициализация периодической задачи
        
        Args:
            name: Имя задачи
            func: Функция для выполнения
            interval_seconds: Интервал выполнения в секундах
            enabled: Включена ли задача
            last_run: Время последнего выполнения
        """
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.last_run = last_run
        self.status = TaskStatus.PENDING
        self.error_count = 0
        self.success_count = 0
    
    def should_run(self) -> bool:
        """Проверка, нужно ли выполнять задачу"""
        if not self.enabled:
            return False
        
        if self.last_run is None:
            return True
        
        next_run = self.last_run + timedelta(seconds=self.interval_seconds)
        return datetime.utcnow() >= next_run
    
    def run(self) -> Dict:
        """Выполнение задачи"""
        if not self.should_run():
            return {
                'status': 'skipped',
                'message': 'Task not due yet'
            }
        
        self.status = TaskStatus.RUNNING
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Running task: {self.name}")
            result = self.func()
            
            self.last_run = datetime.utcnow()
            self.status = TaskStatus.COMPLETED
            self.success_count += 1
            duration = (self.last_run - start_time).total_seconds()
            
            logger.info(f"Task {self.name} completed in {duration:.2f}s")
            
            return {
                'status': 'completed',
                'duration_seconds': duration,
                'result': result
            }
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error_count += 1
            self.last_run = datetime.utcnow()
            duration = (self.last_run - start_time).total_seconds()
            
            logger.error(f"Task {self.name} failed after {duration:.2f}s: {e}")
            
            return {
                'status': 'failed',
                'duration_seconds': duration,
                'error': str(e)
            }


class PeriodicScheduler:
    """Планировщик периодических задач"""
    
    def __init__(self, db: DatabaseManager,
                 change_detector: Optional[ChangeDetector] = None,
                 integrity_monitor: Optional[IntegrityMonitor] = None,
                 dataset_manager: Optional[MLDatasetManager] = None):
        """
        Инициализация планировщика
        
        Args:
            db: Менеджер базы данных
            change_detector: Детектор изменений
            integrity_monitor: Монитор целостности
            dataset_manager: Менеджер датасетов
        """
        self.db = db
        self.change_detector = change_detector
        self.integrity_monitor = integrity_monitor
        self.dataset_manager = dataset_manager
        
        self.tasks: Dict[str, PeriodicTask] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
    
    def register_task(self, name: str, func: Callable, interval_seconds: int,
                     enabled: bool = True):
        """
        Регистрация периодической задачи
        
        Args:
            name: Имя задачи
            func: Функция для выполнения
            interval_seconds: Интервал выполнения в секундах
            enabled: Включена ли задача
        """
        task = PeriodicTask(name, func, interval_seconds, enabled)
        self.tasks[name] = task
        logger.info(f"Registered task: {name} (interval: {interval_seconds}s)")
    
    def unregister_task(self, name: str):
        """Удаление задачи"""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Unregistered task: {name}")
    
    def enable_task(self, name: str):
        """Включение задачи"""
        if name in self.tasks:
            self.tasks[name].enabled = True
            logger.info(f"Enabled task: {name}")
    
    def disable_task(self, name: str):
        """Отключение задачи"""
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"Disabled task: {name}")
    
    def _run_verification_task(self) -> Dict:
        """Задача проверки целостности всех источников"""
        if not self.integrity_monitor:
            return {'error': 'IntegrityMonitor not initialized'}
        
        results = self.integrity_monitor.verify_all_sources()
        return {
            'sources_checked': len(results),
            'results': results
        }
    
    def _run_change_detection_task(self) -> Dict:
        """Задача обнаружения изменений"""
        if not self.change_detector:
            return {'error': 'ChangeDetector not initialized'}
        
        all_changes = self.change_detector.detect_changes_all_sources()
        total_changes = sum(len(changes) for changes in all_changes.values())
        
        return {
            'sources_checked': len(all_changes),
            'total_changes': total_changes,
            'changes_by_source': {
                str(source_id): len(changes) 
                for source_id, changes in all_changes.items()
            }
        }
    
    def _run_incremental_dataset_task(self) -> Dict:
        """Задача создания инкрементального датасета"""
        if not self.dataset_manager or not self.change_detector:
            return {'error': 'DatasetManager or ChangeDetector not initialized'}
        
        # Получаем последнюю версию датасета
        query = """
            SELECT id FROM dataset_versions 
            WHERE status = 'ready'
            ORDER BY created_at DESC 
            LIMIT 1
        """
        result = self.db.execute_query(query)
        
        if not result:
            return {'message': 'No base dataset version found'}
        
        base_version_id = result[0]['id']
        
        # Обнаруживаем изменения
        all_changes = self.change_detector.detect_changes_all_sources()
        total_changes = sum(len(changes) for changes in all_changes.values())
        
        if total_changes < 100:  # Минимум изменений для создания датасета
            return {
                'message': f'Not enough changes ({total_changes} < 100)',
                'total_changes': total_changes
            }
        
        # Формируем инкрементальный датасет
        new_samples = []
        for source_id, changes in all_changes.items():
            for change in changes:
                if change['change_type'] in ['created', 'updated']:
                    sample = self.dataset_manager._format_for_training(change['new_data'])
                    sample['change_type'] = change['change_type']
                    new_samples.append(sample)
        
        if new_samples:
            new_version_id = self.dataset_manager.create_incremental_dataset(
                base_version_id,
                new_samples
            )
            return {
                'new_version_id': new_version_id,
                'samples_count': len(new_samples)
            }
        
        return {'message': 'No new samples to add'}
    
    def setup_default_tasks(self, 
                           verification_interval_hours: int = 24,
                           change_detection_interval_hours: int = 6,
                           incremental_dataset_interval_hours: int = 24):
        """
        Настройка задач по умолчанию
        
        Args:
            verification_interval_hours: Интервал проверки целостности (часы)
            change_detection_interval_hours: Интервал обнаружения изменений (часы)
            incremental_dataset_interval_hours: Интервал создания инкрементального датасета (часы)
        """
        if self.integrity_monitor:
            self.register_task(
                'integrity_verification',
                self._run_verification_task,
                verification_interval_hours * 3600
            )
        
        if self.change_detector:
            self.register_task(
                'change_detection',
                self._run_change_detection_task,
                change_detection_interval_hours * 3600
            )
        
        if self.dataset_manager and self.change_detector:
            self.register_task(
                'incremental_dataset',
                self._run_incremental_dataset_task,
                incremental_dataset_interval_hours * 3600
            )
    
    def _scheduler_loop(self):
        """Основной цикл планировщика"""
        logger.info("Scheduler started")
        
        while not self.stop_event.is_set():
            try:
                # Проверяем все задачи
                for task_name, task in self.tasks.items():
                    if task.should_run():
                        try:
                            result = task.run()
                            logger.debug(f"Task {task_name} result: {result['status']}")
                        except Exception as e:
                            logger.error(f"Error running task {task_name}: {e}")
                
                # Ждем перед следующей проверкой (каждую минуту)
                self.stop_event.wait(60)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
        
        logger.info("Scheduler stopped")
    
    def start(self):
        """Запуск планировщика в отдельном потоке"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        logger.info("Scheduler thread started")
    
    def stop(self):
        """Остановка планировщика"""
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("Scheduler stopped")
    
    def get_task_status(self) -> Dict[str, Dict]:
        """Получение статуса всех задач"""
        status = {}
        for name, task in self.tasks.items():
            status[name] = {
                'enabled': task.enabled,
                'status': task.status.value,
                'interval_seconds': task.interval_seconds,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'success_count': task.success_count,
                'error_count': task.error_count,
                'next_run': (
                    (task.last_run + timedelta(seconds=task.interval_seconds)).isoformat()
                    if task.last_run else None
                )
            }
        return status
    
    def run_task_now(self, task_name: str) -> Dict:
        """Немедленное выполнение задачи"""
        if task_name not in self.tasks:
            return {'error': f'Task {task_name} not found'}
        
        task = self.tasks[task_name]
        return task.run()

