"""
Модуль для мониторинга и алертинга
"""
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Уровни алертов"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Алерт"""
    
    def __init__(self, level: AlertLevel, message: str, source: str,
                 metadata: Optional[Dict] = None):
        """
        Инициализация алерта
        
        Args:
            level: Уровень алерта
            message: Сообщение
            source: Источник алерта
            metadata: Дополнительные метаданные
        """
        self.level = level
        self.message = message
        self.source = source
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.acknowledged = False
    
    def to_dict(self) -> Dict:
        """Преобразование в словарь"""
        return {
            'level': self.level.value,
            'message': self.message,
            'source': self.source,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged
        }


class AlertHandler:
    """Обработчик алертов"""
    
    def __init__(self, callback: Optional[Callable[[Alert], None]] = None):
        """
        Инициализация обработчика
        
        Args:
            callback: Функция для обработки алертов
        """
        self.callback = callback
        self.alerts: List[Alert] = []
        self.max_alerts = 1000  # Максимальное количество хранимых алертов
    
    def handle(self, alert: Alert):
        """
        Обработка алерта
        
        Args:
            alert: Алерт для обработки
        """
        self.alerts.append(alert)
        
        # Ограничиваем количество алертов
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Логируем алерт
        log_level = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }.get(alert.level, logger.info)
        
        log_level(f"[{alert.level.value.upper()}] {alert.source}: {alert.message}")
        
        # Вызываем callback если есть
        if self.callback:
            try:
                self.callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def get_recent_alerts(self, hours: int = 24, 
                         level: Optional[AlertLevel] = None) -> List[Alert]:
        """
        Получение недавних алертов
        
        Args:
            hours: Количество часов назад
            level: Фильтр по уровню (если указан)
            
        Returns:
            Список алертов
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        alerts = [a for a in self.alerts if a.timestamp >= cutoff]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_unacknowledged_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """
        Получение неподтвержденных алертов
        
        Args:
            level: Фильтр по уровню (если указан)
            
        Returns:
            Список неподтвержденных алертов
        """
        alerts = [a for a in self.alerts if not a.acknowledged]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def acknowledge_alert(self, index: int):
        """Подтверждение алерта"""
        if 0 <= index < len(self.alerts):
            self.alerts[index].acknowledged = True


class SystemMonitor:
    """Мониторинг системы"""
    
    def __init__(self, db: DatabaseManager, alert_handler: AlertHandler):
        """
        Инициализация монитора
        
        Args:
            db: Менеджер базы данных
            alert_handler: Обработчик алертов
        """
        self.db = db
        self.alert_handler = alert_handler
    
    def check_source_health(self, source_id: int) -> Dict:
        """
        Проверка здоровья источника
        
        Args:
            source_id: ID источника
            
        Returns:
            Словарь с результатами проверки
        """
        source = self.db.get_source(source_id)
        if not source:
            return {'status': 'error', 'message': 'Source not found'}
        
        issues = []
        status = 'healthy'
        
        # Проверка статуса источника
        if source['status'] == 'failed':
            issues.append('Source status is failed')
            status = 'unhealthy'
            self.alert_handler.handle(Alert(
                AlertLevel.ERROR,
                f"Source {source_id} has failed status",
                'source_health_check',
                {'source_id': source_id, 'source_url': source['url']}
            ))
        
        # Проверка количества ошибок
        if source.get('retry_count', 0) > 5:
            issues.append(f"High retry count: {source['retry_count']}")
            status = 'warning'
            self.alert_handler.handle(Alert(
                AlertLevel.WARNING,
                f"Source {source_id} has high retry count: {source['retry_count']}",
                'source_health_check',
                {'source_id': source_id, 'retry_count': source['retry_count']}
            ))
        
        # Проверка времени последней успешной загрузки
        if source.get('last_successful_download'):
            last_download = source['last_successful_download']
            if isinstance(last_download, str):
                last_download = datetime.fromisoformat(last_download.replace('Z', '+00:00'))
            
            hours_since = (datetime.utcnow() - last_download.replace(tzinfo=None)).total_seconds() / 3600
            
            if hours_since > 48:
                issues.append(f"Last successful download was {hours_since:.1f} hours ago")
                status = 'warning' if status == 'healthy' else status
                self.alert_handler.handle(Alert(
                    AlertLevel.WARNING,
                    f"Source {source_id} hasn't been updated in {hours_since:.1f} hours",
                    'source_health_check',
                    {'source_id': source_id, 'hours_since': hours_since}
                ))
        
        # Проверка прогресса загрузки
        if source.get('total_records') and source.get('downloaded_records'):
            progress = source['downloaded_records'] / source['total_records']
            if progress < 0.9 and source['status'] == 'completed':
                issues.append(f"Download incomplete: {progress:.1%}")
                status = 'warning'
        
        return {
            'source_id': source_id,
            'status': status,
            'issues': issues,
            'checked_at': datetime.utcnow().isoformat()
        }
    
    def check_all_sources_health(self) -> List[Dict]:
        """
        Проверка здоровья всех источников
        
        Returns:
            Список результатов проверки
        """
        sources = self.db.get_all_active_sources()
        results = []
        
        for source in sources:
            try:
                result = self.check_source_health(source['id'])
                results.append(result)
            except Exception as e:
                logger.error(f"Error checking health for source {source['id']}: {e}")
                results.append({
                    'source_id': source['id'],
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    def check_integrity_scores(self, threshold: float = 0.95) -> List[Dict]:
        """
        Проверка оценок целостности
        
        Args:
            threshold: Порог для алерта
            
        Returns:
            Список источников с низкой целостностью
        """
        # Получаем последние проверки целостности из БД
        query = """
            SELECT DISTINCT ON (source_id) 
                source_id, 
                verification_status,
                last_verified
            FROM data_integrity
            WHERE last_verified IS NOT NULL
            ORDER BY source_id, last_verified DESC
        """
        
        results = self.db.execute_query(query)
        low_integrity_sources = []
        
        # Для каждого источника вычисляем score целостности
        for row in results:
            source_id = row['source_id']
            
            # Подсчитываем статусы верификации
            status_query = """
                SELECT verification_status, COUNT(*) as count
                FROM data_integrity
                WHERE source_id = %s AND last_verified IS NOT NULL
                GROUP BY verification_status
            """
            status_counts = self.db.execute_query(status_query, (source_id,))
            
            total = sum(s['count'] for s in status_counts)
            if total == 0:
                continue
            
            verified = sum(s['count'] for s in status_counts if s['verification_status'] == 'verified')
            integrity_score = verified / total if total > 0 else 0
            
            if integrity_score < threshold:
                source = self.db.get_source(source_id)
                low_integrity_sources.append({
                    'source_id': source_id,
                    'source_url': source['url'] if source else 'unknown',
                    'integrity_score': integrity_score,
                    'verified': verified,
                    'total': total
                })
                
                self.alert_handler.handle(Alert(
                    AlertLevel.WARNING,
                    f"Source {source_id} has low integrity score: {integrity_score:.2%}",
                    'integrity_check',
                    {
                        'source_id': source_id,
                        'integrity_score': integrity_score,
                        'threshold': threshold
                    }
                ))
        
        return low_integrity_sources
    
    def check_system_metrics(self) -> Dict:
        """
        Проверка системных метрик
        
        Returns:
            Словарь с метриками системы
        """
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'sources': {},
            'datasets': {},
            'changes': {}
        }
        
        # Метрики источников
        sources_query = """
            SELECT status, COUNT(*) as count
            FROM data_sources
            GROUP BY status
        """
        sources_stats = self.db.execute_query(sources_query)
        metrics['sources'] = {s['status']: s['count'] for s in sources_stats}
        
        # Метрики датасетов
        datasets_query = """
            SELECT status, COUNT(*) as count
            FROM dataset_versions
            GROUP BY status
        """
        datasets_stats = self.db.execute_query(datasets_query)
        metrics['datasets'] = {d['status']: d['count'] for d in datasets_stats}
        
        # Метрики изменений (за последние 24 часа)
        changes_query = """
            SELECT change_type, COUNT(*) as count
            FROM document_changes
            WHERE changed_at > NOW() - INTERVAL '24 hours'
            GROUP BY change_type
        """
        changes_stats = self.db.execute_query(changes_query)
        metrics['changes'] = {c['change_type']: c['count'] for c in changes_stats}
        
        # Проверяем критические метрики
        failed_sources = metrics['sources'].get('failed', 0)
        if failed_sources > 0:
            self.alert_handler.handle(Alert(
                AlertLevel.WARNING,
                f"{failed_sources} sources have failed status",
                'system_metrics',
                {'failed_sources': failed_sources}
            ))
        
        return metrics
    
    def run_health_checks(self) -> Dict:
        """
        Запуск всех проверок здоровья
        
        Returns:
            Словарь с результатами всех проверок
        """
        logger.info("Running health checks")
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'sources_health': self.check_all_sources_health(),
            'integrity_issues': self.check_integrity_scores(),
            'system_metrics': self.check_system_metrics()
        }
        
        # Подсчитываем общее состояние
        unhealthy_sources = sum(1 for s in results['sources_health'] 
                              if s['status'] != 'healthy')
        
        if unhealthy_sources > 0:
            self.alert_handler.handle(Alert(
                AlertLevel.WARNING,
                f"{unhealthy_sources} sources are unhealthy",
                'health_checks',
                {'unhealthy_count': unhealthy_sources}
            ))
        
        return results

