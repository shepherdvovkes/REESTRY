"""
Модуль для управления данными: загрузка, проверка целостности, версионирование
"""

from .database import DatabaseManager
from .integrity import DataIntegrityChecker, IntegrityMonitor
from .download import DataDownloadManager, DataSourceAdapter, APISourceAdapter, FileSourceAdapter, WebSourceAdapter, RSSFeedAdapter
from .datasets import MLDatasetManager
from .change_detector import ChangeDetector
from .scheduler import PeriodicScheduler, PeriodicTask, TaskStatus
from .monitoring import SystemMonitor, AlertHandler, Alert, AlertLevel
from .incremental_pipeline import IncrementalTrainingPipeline

__all__ = [
    'DatabaseManager',
    'DataIntegrityChecker',
    'IntegrityMonitor',
    'DataDownloadManager',
    'DataSourceAdapter',
    'APISourceAdapter',
    'FileSourceAdapter',
    'WebSourceAdapter',
    'RSSFeedAdapter',
    'MLDatasetManager',
    'ChangeDetector',
    'PeriodicScheduler',
    'PeriodicTask',
    'TaskStatus',
    'SystemMonitor',
    'AlertHandler',
    'Alert',
    'AlertLevel',
    'IncrementalTrainingPipeline',
]

