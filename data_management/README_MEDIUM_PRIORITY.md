# Реализация рекомендаций среднего приоритета

Этот документ описывает реализованные модули для рекомендаций среднего приоритета из `recommendations.txt`.

## Реализованные модули

### 1. Инкрементальное обнаружение изменений (`change_detector.py`)

Модуль `ChangeDetector` для автоматического обнаружения изменений в источниках данных.

**Основные возможности:**
- Обнаружение новых записей (created)
- Обнаружение обновленных записей (updated)
- Обнаружение удаленных записей (deleted)
- Сравнение данных по хешам содержимого
- Сохранение истории изменений в БД
- Работа с одним источником или всеми источниками одновременно

**Пример использования:**
```python
from data_management import DatabaseManager, DataDownloadManager, DataIntegrityChecker, ChangeDetector

db = DatabaseManager()
download_manager = DataDownloadManager(db)
integrity_checker = DataIntegrityChecker(db)
change_detector = ChangeDetector(db, download_manager, integrity_checker)

# Обнаружение изменений для конкретного источника
changes = change_detector.detect_changes(source_id=1)

# Обнаружение изменений для всех источников
all_changes = change_detector.detect_changes_all_sources()

# Получение недавних изменений
recent = change_detector.get_recent_changes(hours=24)
```

### 2. Автоматические периодические проверки (`scheduler.py`)

Модуль `PeriodicScheduler` для автоматического выполнения периодических задач.

**Основные возможности:**
- Регистрация периодических задач с настраиваемым интервалом
- Автоматическое выполнение задач в фоновом потоке
- Отслеживание статуса задач (pending, running, completed, failed)
- Статистика выполнения (успешные/неуспешные запуски)
- Встроенные задачи:
  - Проверка целостности всех источников
  - Обнаружение изменений
  - Создание инкрементальных датасетов

**Пример использования:**
```python
from data_management import (
    DatabaseManager, PeriodicScheduler, 
    ChangeDetector, IntegrityMonitor, MLDatasetManager
)

db = DatabaseManager()
# ... инициализация других компонентов ...

scheduler = PeriodicScheduler(
    db=db,
    change_detector=change_detector,
    integrity_monitor=integrity_monitor,
    dataset_manager=dataset_manager
)

# Настройка задач по умолчанию
scheduler.setup_default_tasks(
    verification_interval_hours=24,
    change_detection_interval_hours=6,
    incremental_dataset_interval_hours=24
)

# Запуск планировщика
scheduler.start()

# Получение статуса задач
status = scheduler.get_task_status()

# Немедленное выполнение задачи
result = scheduler.run_task_now('change_detection')
```

### 3. Мониторинг и алертинг (`monitoring.py`)

Модуль `SystemMonitor` и `AlertHandler` для мониторинга системы и генерации алертов.

**Основные возможности:**
- Проверка здоровья источников данных
- Мониторинг оценок целостности данных
- Системные метрики (статусы источников, датасетов, изменений)
- Система алертов с уровнями (INFO, WARNING, ERROR, CRITICAL)
- История алертов
- Подтверждение алертов

**Пример использования:**
```python
from data_management import DatabaseManager, SystemMonitor, AlertHandler, AlertLevel

db = DatabaseManager()

# Создание обработчика алертов
def alert_callback(alert):
    print(f"ALERT [{alert.level.value}]: {alert.message}")

alert_handler = AlertHandler(callback=alert_callback)
monitor = SystemMonitor(db, alert_handler)

# Проверка здоровья источника
health = monitor.check_source_health(source_id=1)

# Проверка всех источников
all_health = monitor.check_all_sources_health()

# Проверка целостности
integrity_issues = monitor.check_integrity_scores(threshold=0.95)

# Системные метрики
metrics = monitor.check_system_metrics()

# Запуск всех проверок
results = monitor.run_health_checks()

# Получение алертов
recent_alerts = alert_handler.get_recent_alerts(hours=24)
critical_alerts = alert_handler.get_unacknowledged_alerts(level=AlertLevel.CRITICAL)
```

### 4. Инкрементальный пайплайн обучения (`incremental_pipeline.py`)

Модуль `IncrementalTrainingPipeline` для автоматизации процесса инкрементального обучения.

**Основные возможности:**
- Автоматическое обнаружение изменений
- Формирование инкрементальных датасетов
- Создание новых версий датасетов на основе изменений
- Статистика изменений
- Интеграция с планировщиком для автоматизации

**Пример использования:**
```python
from data_management import (
    DatabaseManager, MLDatasetManager, ChangeDetector,
    IncrementalTrainingPipeline
)

db = DatabaseManager()
# ... инициализация компонентов ...

pipeline = IncrementalTrainingPipeline(
    db=db,
    dataset_manager=dataset_manager,
    change_detector=change_detector
)

# Получение статистики
stats = pipeline.get_incremental_statistics(base_version_id=1)

# Запуск инкрементального обновления
new_version_id = pipeline.run_incremental_update(
    base_version_id=1,
    min_new_samples=100
)
```

## Интеграция всех компонентов

Полный пример интеграции всех модулей:

```python
from data_management import (
    DatabaseManager, DataDownloadManager, DataIntegrityChecker,
    IntegrityMonitor, ChangeDetector, MLDatasetManager,
    PeriodicScheduler, SystemMonitor, AlertHandler,
    IncrementalTrainingPipeline
)

# Инициализация компонентов
db = DatabaseManager()
download_manager = DataDownloadManager(db)
integrity_checker = DataIntegrityChecker(db)
integrity_monitor = IntegrityMonitor(db, integrity_checker)
change_detector = ChangeDetector(db, download_manager, integrity_checker)
dataset_manager = MLDatasetManager(db)
pipeline = IncrementalTrainingPipeline(db, dataset_manager, change_detector)

# Мониторинг и алертинг
alert_handler = AlertHandler()
monitor = SystemMonitor(db, alert_handler)

# Планировщик
scheduler = PeriodicScheduler(
    db=db,
    change_detector=change_detector,
    integrity_monitor=integrity_monitor,
    dataset_manager=dataset_manager
)
scheduler.setup_default_tasks()
scheduler.start()

# Система готова к работе!
```

## Структура файлов

```
data_management/
├── change_detector.py          # Инкрементальное обнаружение изменений
├── scheduler.py                # Периодический планировщик задач
├── monitoring.py               # Мониторинг и алертинг
├── incremental_pipeline.py      # Пайплайн инкрементального обучения
├── example_medium_priority.py  # Примеры использования
└── README_MEDIUM_PRIORITY.md   # Эта документация
```

## Зависимости

Все модули используют существующие компоненты:
- `DatabaseManager` - для работы с БД
- `DataDownloadManager` - для загрузки данных
- `DataIntegrityChecker` - для проверки целостности
- `MLDatasetManager` - для управления датасетами

## Примечания

1. **Планировщик задач** работает в отдельном потоке и требует явного запуска/остановки
2. **Алерты** могут быть расширены для отправки уведомлений (email, Slack, и т.д.)
3. **Обнаружение изменений** требует доступа к исходным данным через адаптеры
4. Все модули логируют свою работу через стандартный модуль `logging`

## Следующие шаги

Для полной интеграции рекомендуется:
1. Настроить периодические задачи через `PeriodicScheduler`
2. Настроить обработку алертов (email, Slack, и т.д.)
3. Интегрировать с системой развертывания (Docker, systemd, и т.д.)
4. Добавить метрики в систему мониторинга (Prometheus, Grafana)

