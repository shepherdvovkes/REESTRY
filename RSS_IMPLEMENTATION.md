# Реализация поддержки RSS-источников

## Что было реализовано

### 1. RSSFeedAdapter (`data_management/download.py`)

Создан специальный адаптер для обработки RSS/Atom фидов:

**Основные возможности:**
- ✅ Парсинг RSS/Atom фидов с помощью библиотеки `feedparser`
- ✅ Поддержка условных запросов (ETag, Last-Modified) для эффективных обновлений
- ✅ Извлечение всех метаданных: title, description, link, published, updated, author, categories
- ✅ Инкрементальная загрузка записей
- ✅ Метод `get_feed_info()` для получения информации о фиде

**Особенности:**
- Использует кэширование фида для избежания повторных запросов
- Поддерживает аутентификацию (Bearer token, API key)
- Обрабатывает ошибки парсинга gracefully
- Извлекает контент из различных полей (content, summary, description)

### 2. Обновление краулера (`UkrDeepCrawler/crawler.py`)

**Добавлено:**
- ✅ Метод `extract_rss_links()` для поиска RSS-ссылок в HTML
- ✅ Поиск через `<link rel="alternate" type="application/rss+xml">`
- ✅ Поиск ссылок с текстом "RSS", "Feed", "Подписка"
- ✅ Поиск URL с паттернами `/feed`, `/rss`, `/atom`, `.rss`
- ✅ Обновлен промпт LLM для поиска RSS-источников
- ✅ Добавлена статистика RSS-фидов
- ✅ RSS-ссылки автоматически извлекаются на каждой странице

**Приоритеты:**
- RSS-фиды получают приоритет 2-3 (высокий)
- Автоматически добавляются в очередь обхода

### 3. Интеграция в систему загрузки

**Обновлено:**
- ✅ `DataDownloadManager` поддерживает тип источника `rss`
- ✅ RSS-источники регистрируются и обрабатываются автоматически
- ✅ Интеграция с системой возобновления загрузки

### 4. Оптимизация ChangeDetector для RSS

**Добавлено:**
- ✅ Метод `_detect_rss_changes()` для оптимизированного обнаружения изменений
- ✅ Использование `guid` для идентификации записей (вместо хеша)
- ✅ Сравнение по дате публикации для эффективности
- ✅ Специальная обработка метаданных RSS

**Преимущества:**
- Более быстрое обнаружение изменений
- Использование встроенных идентификаторов RSS (guid)
- Эффективное сравнение по датам

### 5. Обновление зависимостей

**Добавлено:**
- ✅ `feedparser>=6.0.10` в `requirements.txt`

## Использование

### Регистрация RSS-источника

```python
from data_management import DatabaseManager, DataDownloadManager

db = DatabaseManager()
download_manager = DataDownloadManager(db)

# Регистрация RSS-источника
source_id = download_manager.register_source(
    url="https://data.gov.ua/feed",
    source_type='rss',
    metadata={
        'feed_type': 'rss',
        'update_frequency': 'hourly'
    }
)

# Загрузка данных
download_manager.resume_download(source_id, batch_size=50)
```

### Прямое использование RSSFeedAdapter

```python
from data_management import RSSFeedAdapter

adapter = RSSFeedAdapter("https://data.gov.ua/feed")

# Информация о фиде
feed_info = adapter.get_feed_info()

# Загрузка записей
entries = adapter.download_incremental(0, 10)
```

### Обнаружение изменений в RSS

```python
from data_management import (
    DatabaseManager, DataDownloadManager,
    DataIntegrityChecker, ChangeDetector
)

db = DatabaseManager()
download_manager = DataDownloadManager(db)
integrity_checker = DataIntegrityChecker(db)
change_detector = ChangeDetector(db, download_manager, integrity_checker)

# Обнаружение изменений (автоматически использует оптимизированный метод для RSS)
changes = change_detector.detect_changes(source_id)
```

## Автоматическое обнаружение RSS краулером

Краулер теперь автоматически находит RSS-источники:

1. **Через HTML-разметку:**
   ```html
   <link rel="alternate" type="application/rss+xml" href="/feed">
   ```

2. **Через ссылки с текстом:**
   - "RSS", "Feed", "Подписка", "Підписка"

3. **Через паттерны URL:**
   - `/feed`, `/rss`, `/atom`, `.rss`, `.xml`

4. **Через LLM-анализ:**
   - LLM ищет RSS-источники в промпте

## Преимущества реализации

### 1. Эффективность
- ✅ Использование ETag и Last-Modified для условных запросов
- ✅ RSS-фиды обычно содержат только последние записи
- ✅ Не нужно загружать весь фид для проверки обновлений

### 2. Структурированность
- ✅ Все метаданные извлекаются и сохраняются
- ✅ Использование guid для уникальной идентификации
- ✅ Даты публикации для сортировки и фильтрации

### 3. Автоматизация
- ✅ Автоматическое обнаружение RSS-источников
- ✅ Интеграция с системой периодических проверок
- ✅ Оптимизированное обнаружение изменений

### 4. Надежность
- ✅ Обработка ошибок парсинга
- ✅ Поддержка различных форматов RSS/Atom
- ✅ Fallback на обычный метод при ошибках

## Примеры RSS-источников в украинских порталах

Типичные места для поиска RSS:

1. **Порталы открытых данных:**
   - `https://data.gov.ua/feed`
   - `https://opendatabot.ua/rss`

2. **Министерства и ведомства:**
   - `https://minjust.gov.ua/rss`
   - `https://nazk.gov.ua/feed`

3. **Реестры:**
   - `https://usr.minjust.gov.ua/feed/changes`
   - `https://registry.gov.ua/rss/updates`

4. **Новостные порталы:**
   - `https://portal.gov.ua/rss/news`
   - `https://gov.ua/feed`

## Интеграция с планировщиком

RSS-источники идеально подходят для периодических проверок:

```python
from data_management import PeriodicScheduler

scheduler = PeriodicScheduler(...)
scheduler.setup_default_tasks(
    change_detection_interval_hours=1  # RSS можно проверять чаще
)
```

Рекомендуемые интервалы для RSS:
- **Активные источники:** каждые 1-3 часа
- **Обычные источники:** каждые 6-12 часов
- **Редко обновляемые:** каждые 24 часа

## Следующие шаги

### Рекомендуемые улучшения:

1. **Кэширование фидов:**
   - Сохранение ETag и Last-Modified в БД
   - Избежание повторных запросов к неизмененным фидам

2. **Мониторинг RSS:**
   - Отслеживание доступности фидов
   - Алерты при изменении структуры фида

3. **Обработка полных фидов:**
   - Поддержка архивных RSS-фидов
   - Загрузка исторических данных

4. **Валидация RSS:**
   - Проверка валидности RSS-структуры
   - Валидация метаданных

## Заключение

Реализована полная поддержка RSS-источников в системе:

✅ **Обнаружение:** Краулер автоматически находит RSS-источники  
✅ **Обработка:** RSSFeedAdapter правильно парсит и извлекает данные  
✅ **Обновления:** Оптимизированное обнаружение изменений  
✅ **Интеграция:** Полная интеграция с существующей системой  

RSS-источники теперь являются полноценной частью системы для отслеживания обновлений данных в украинских государственных порталах.

