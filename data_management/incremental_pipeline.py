"""
Модуль для инкрементального обучения - интеграция всех компонентов
"""
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .database import DatabaseManager
from .change_detector import ChangeDetector
from .datasets import MLDatasetManager
from .integrity import DataIntegrityChecker

logger = logging.getLogger(__name__)


class IncrementalTrainingPipeline:
    """Пайплайн для инкрементального обучения"""
    
    def __init__(self, 
                 db: DatabaseManager,
                 dataset_manager: MLDatasetManager,
                 change_detector: ChangeDetector):
        """
        Инициализация пайплайна
        
        Args:
            db: Менеджер базы данных
            dataset_manager: Менеджер датасетов
            change_detector: Детектор изменений
        """
        self.db = db
        self.dataset_manager = dataset_manager
        self.change_detector = change_detector
    
    def run_incremental_update(self, 
                              base_version_id: int,
                              min_new_samples: int = 100) -> Optional[int]:
        """
        Запуск инкрементального обновления датасета
        
        Args:
            base_version_id: ID базовой версии датасета
            min_new_samples: Минимальное количество новых образцов для создания датасета
            
        Returns:
            ID новой версии датасета или None если недостаточно изменений
        """
        logger.info(f"Starting incremental update from base version {base_version_id}")
        
        # Проверяем существование базовой версии
        base_version = self.db.get_dataset_version(base_version_id)
        if not base_version:
            raise ValueError(f"Base version {base_version_id} not found")
        
        # 1. Обнаруживаем изменения во всех источниках
        logger.info("Detecting changes in all sources...")
        all_changes = self.change_detector.detect_changes_all_sources()
        
        total_changes = sum(len(changes) for changes in all_changes.values())
        logger.info(f"Total changes detected: {total_changes}")
        
        if total_changes < min_new_samples:
            logger.info(f"Not enough changes ({total_changes} < {min_new_samples})")
            return None
        
        # 2. Формируем инкрементальный датасет
        logger.info("Formatting new samples for training...")
        new_samples = []
        
        for source_id, changes in all_changes.items():
            for change in changes:
                if change['change_type'] in ['created', 'updated']:
                    try:
                        sample = self.dataset_manager._format_for_training(change['new_data'])
                        sample['change_type'] = change['change_type']
                        sample['source_id'] = source_id
                        new_samples.append(sample)
                    except Exception as e:
                        logger.warning(f"Error formatting sample from change: {e}")
                        continue
        
        if len(new_samples) < min_new_samples:
            logger.info(f"Not enough formatted samples ({len(new_samples)} < {min_new_samples})")
            return None
        
        logger.info(f"Formatted {len(new_samples)} new samples")
        
        # 3. Создаем новую версию датасета
        logger.info("Creating incremental dataset version...")
        new_version_id = self.dataset_manager.create_incremental_dataset(
            base_version_id,
            new_samples
        )
        
        logger.info(f"Created incremental dataset version {new_version_id} "
                   f"with {len(new_samples)} samples")
        
        return new_version_id
    
    def get_incremental_statistics(self, base_version_id: int) -> Dict:
        """
        Получение статистики для инкрементального обновления
        
        Args:
            base_version_id: ID базовой версии
            
        Returns:
            Словарь со статистикой
        """
        base_version = self.db.get_dataset_version(base_version_id)
        if not base_version:
            raise ValueError(f"Base version {base_version_id} not found")
        
        # Получаем изменения
        all_changes = self.change_detector.detect_changes_all_sources()
        total_changes = sum(len(changes) for changes in all_changes.values())
        
        # Подсчитываем по типам
        changes_by_type = {}
        for changes in all_changes.values():
            for change in changes:
                change_type = change['change_type']
                changes_by_type[change_type] = changes_by_type.get(change_type, 0) + 1
        
        # Получаем последние изменения
        recent_changes = self.change_detector.get_recent_changes(hours=24)
        
        return {
            'base_version_id': base_version_id,
            'base_version_name': base_version['name'],
            'total_changes': total_changes,
            'changes_by_type': changes_by_type,
            'changes_by_source': {
                str(source_id): len(changes) 
                for source_id, changes in all_changes.items()
            },
            'recent_changes_24h': len(recent_changes),
            'ready_for_update': total_changes >= 100
        }
    
    def schedule_incremental_updates(self, interval_hours: int = 24):
        """
        Планирование периодических обновлений
        
        Args:
            interval_hours: Интервал обновлений в часах
            
        Note:
            Для реализации используйте PeriodicScheduler
        """
        logger.info(f"Scheduled incremental updates every {interval_hours} hours")
        # Реальная реализация требует интеграции с PeriodicScheduler
        # Это заглушка для документации

