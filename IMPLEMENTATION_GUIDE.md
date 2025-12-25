# Руководство по реализации рекомендаций высокого приоритета

## ✅ Реализованные компоненты

### 1. Система проверки целостности данных

**Файлы:**
- `data_management/integrity.py` - `DataIntegrityChecker` и `IntegrityMonitor`
- `database/migrations/001_create_data_sources_tables.sql` - таблицы для целостности

**Возможности:**
- ✅ Вычисление SHA256 хешей для каждой записи
- ✅ Сравнение загруженных данных с исходными
- ✅ Обнаружение отсутствующих, несовпадающих и лишних записей
- ✅ Расчет score целостности (0.0 - 1.0)
- ✅ Автоматический мониторинг всех источников

**Использование:**
```python
from data_management import DatabaseManager, DataIntegrityChecker

db = DatabaseManager(...)
checker = DataIntegrityChecker(db)

# Проверка конкретного источника
result = checker.verify_downloaded_data(source_id=1)
print(f"Целостность: {result['integrity_score']:.2%}")
```

### 2. Версионирование датасетов

**Файлы:**
- `data_management/datasets.py` - `MLDatasetManager`
- Таблицы: `dataset_versions`, `dataset_samples`

**Возможности:**
- ✅ Создание версий датасетов с метаданными
- ✅ Подготовка данных для обучения с фильтрами
- ✅ Инкрементальные обновления датасетов
- ✅ Экспорт в разных форматах (JSONL, text, HuggingFace)
- ✅ Дедупликация образцов по хешу

**Использование:**
```python
from data_management import MLDatasetManager

dataset_manager = MLDatasetManager(db)

# Создание базовой версии
version_id = dataset_manager.create_dataset_version(
    name='ukrainian_laws_v1',
    description='Базовый датасет'
)

# Подготовка датасета
result = dataset_manager.prepare_training_dataset(
    version_id=version_id,
    filters={'document_type': 'Кодекс'},
    min_length=1000
)

# Инкрементальное обновление
new_samples = dataset_manager.get_incremental_updates(version_id)
if len(new_samples) >= 100:
    new_version_id = dataset_manager.create_incremental_dataset(
        base_version_id=version_id,
        new_samples=new_samples
    )
```

### 3. Механизм возобновления загрузки

**Файлы:**
- `data_management/download.py` - `DataDownloadManager` и адаптеры
- Таблица: `data_sources` с полями `status`, `downloaded_records`

**Возможности:**
- ✅ Регистрация источников разных типов (API, File, Web)
- ✅ Инкрементальная загрузка с пагинацией
- ✅ Автоматическое возобновление с места остановки
- ✅ Отслеживание прогресса в БД
- ✅ Обработка ошибок и retry логика

**Адаптеры:**
- `APISourceAdapter` - для REST API с пагинацией
- `FileSourceAdapter` - для CSV, JSON, XML файлов
- `WebSourceAdapter` - для веб-страниц с парсингом HTML

**Использование:**
```python
from data_management import DataDownloadManager

download_manager = DataDownloadManager(db)

# Регистрация источника
source_id = download_manager.register_source(
    url='https://api.example.com/data',
    source_type='api',
    metadata={'auth': {'api_key': 'key'}}
)

# Загрузка (можно прервать и возобновить)
download_manager.resume_download(source_id, batch_size=1000)
```

## Установка и настройка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Применение миграций БД

```bash
# Используя переменные окружения
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=reestry
export POSTGRES_USER=reestry_user
export POSTGRES_PASSWORD=reestry_password

python3 database/apply_migrations.py
```

Или с параметрами:
```bash
python3 database/apply_migrations.py \
    --host localhost \
    --port 5432 \
    --database reestry \
    --user reestry_user \
    --password reestry_password
```

### 3. Проверка работы

```bash
python3 data_management/example_usage.py
```

## Структура базы данных

После применения миграций создаются следующие таблицы:

### data_sources
Отслеживание источников данных:
- `status` - статус загрузки (pending, downloading, completed, failed, partial)
- `downloaded_records` - количество загруженных записей
- `total_records` - общее количество записей (если известно)
- `last_successful_download` - время последней успешной загрузки

### data_integrity
Проверка целостности:
- `content_hash` - SHA256 хеш содержимого записи
- `original_hash` - хеш из исходного источника
- `verification_status` - статус проверки (verified, mismatch, missing)

### dataset_versions
Версии датасетов:
- `name` - имя версии
- `base_version_id` - ссылка на базовую версию (для инкрементальных)
- `status` - статус (preparing, ready, training, archived)
- `total_samples` - количество образцов

### dataset_samples
Образцы датасетов:
- `sample_data` - JSONB с форматированными данными для обучения
- `sample_hash` - хеш для дедупликации

### document_changes
Отслеживание изменений:
- `change_type` - тип изменения (created, updated, deleted)
- `old_content_hash` / `new_content_hash` - хеши для сравнения

## Интеграция с существующими компонентами

### С UkrDeepCrawler

Краулер может автоматически регистрировать найденные источники:

```python
from data_management import DataDownloadManager
from UkrDeepCrawler.crawler import LLMCrawler

crawler = LLMCrawler()
crawler.crawl(seed_urls=[...])

download_manager = DataDownloadManager(db)

# Регистрация найденных источников
for relevant_url in crawler.relevant_urls:
    source_id = download_manager.register_source(
        url=relevant_url['url'],
        source_type=relevant_url['type']
    )
```

### С download_documents.py

Можно интегрировать с существующим загрузчиком документов:

```python
# После загрузки документа
from data_management import DataIntegrityChecker

checker = DataIntegrityChecker(db)
checker.store_source_fingerprint(
    source_id=source_id,
    source_url=url,
    records=[document_data]
)
```

## Следующие шаги

### Средний приоритет (рекомендуется реализовать далее):

1. **Автоматическое обнаружение изменений**
   - Периодический запуск `ChangeDetector`
   - Интеграция с Celery Beat или cron

2. **Планировщик задач**
   - Автоматические проверки целостности
   - Автоматическое создание инкрементальных датасетов

3. **Мониторинг и алертинг**
   - Интеграция с Prometheus/Grafana
   - Уведомления при проблемах с целостностью

### Низкий приоритет:

1. Оптимизация производительности
2. Расширенная аналитика
3. UI для управления датасетами

## Примеры использования

См. полные примеры в `data_management/example_usage.py`:
- Регистрация и загрузка источника
- Проверка целостности
- Мониторинг всех источников
- Создание датасета
- Инкрементальные обновления

## Поддержка

При возникновении проблем:
1. Проверьте логи в консоли
2. Убедитесь, что миграции применены
3. Проверьте подключение к БД
4. См. примеры в `example_usage.py`

