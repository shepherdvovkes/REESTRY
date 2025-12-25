# Архитектура обработки данных

Архитектура системы обработки данных из источников, найденных UkrDeepCrawler, с использованием LLM (openai/gpt-oss-20b через LMStudio API).

## Общая схема

```
┌─────────────────┐
│  UkrDeepCrawler │  Находит источники данных
│   (результаты)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│           Data Processing Pipeline                       │
│                                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐        │
│  │ Загрузка │───▶│  LLM     │───▶│ Валидация │        │
│  │  данных  │    │ Анализ   │    │           │        │
│  └──────────┘    └──────────┘    └──────────┘        │
│       │                │                 │              │
│       └────────────────┴─────────────────┘              │
│                          │                               │
│                          ▼                               │
│                  ┌──────────────┐                       │
│                  │ Нормализация │                       │
│                  │   и очистка  │                       │
│                  └──────┬───────┘                       │
│                         │                               │
│                         ▼                               │
│                  ┌──────────────┐                       │
│                  │ Определение  │                       │
│                  │   схемы БД   │                       │
│                  └──────┬───────┘                       │
│                         │                               │
│                         ▼                               │
│                  ┌──────────────┐                       │
│                  │  Сохранение  │                       │
│                  │     в БД     │                       │
│                  └──────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

## Компоненты системы

### 1. Data Loader (Загрузчик данных)

**Назначение:** Загрузка данных из различных источников (API, файлы, веб-страницы).

**Типы источников:**

- **REST API** - прямые HTTP запросы к API endpoints
- **GraphQL API** - запросы через GraphQL
- **Файлы** - CSV, JSON, XML, Excel
- **Веб-страницы** - парсинг HTML таблиц и форм
- **Потоковые данные** - обработка streaming API

**Реализация:**

```python
class DataLoader:
    def load_from_api(self, url, params=None):
        """Загрузка через REST API"""
        pass
    
    def load_from_file(self, file_path):
        """Загрузка из файла"""
        pass
    
    def load_from_web(self, url, use_js=False):
        """Загрузка через веб-скрапинг"""
        pass
```

### 2. LLM Analyzer (LLM-анализатор)

**Назначение:** Использование LLM для анализа и структурирования данных.

**Модель:** `openai/gpt-oss-20b` через LMStudio API (`http://192.168.0.60:1234/v1/chat/completions`)

**Функции LLM:**

1. **Определение структуры данных**
   - Анализ формата (CSV, JSON, HTML таблица, текст)
   - Извлечение схемы полей
   - Определение типов данных

2. **Извлечение структурированных данных**
   - Парсинг неструктурированного контента
   - Извлечение сущностей из текста
   - Преобразование в JSON

3. **Валидация данных**
   - Проверка корректности форматов
   - Валидация обязательных полей
   - Проверка бизнес-правил

4. **Исправление ошибок**
   - Исправление опечаток
   - Нормализация форматов
   - Восстановление повреждённых данных

5. **Определение стратегии хранения**
   - Выбор оптимальной СУБД
   - Генерация схемы таблиц
   - Определение индексов

**Промпты для LLM:**

```python
# Пример промпта для анализа структуры
ANALYZE_STRUCTURE_PROMPT = """Проанализируй следующие данные и определи:
1. Тип данных (CSV, JSON, HTML таблица, текст, API response)
2. Структуру полей (названия, типы, обязательность)
3. Оптимальный метод парсинга
4. Потенциальные проблемы

Данные:
{data}

Верни JSON:
{{
    "data_type": "...",
    "schema": {{
        "fields": [
            {{"name": "...", "type": "...", "required": true/false}}
        ]
    }},
    "parsing_method": "...",
    "issues": ["..."]
}}"""

# Пример промпта для извлечения данных
EXTRACT_DATA_PROMPT = """Извлеки структурированные данные из следующего контента.
Верни валидный JSON массив объектов.

Схема полей: {schema}

Контент:
{content}

Важно: сохрани все данные, даже если формат не идеален."""

# Пример промпта для валидации
VALIDATE_DATA_PROMPT = """Валидируй и исправь следующие данные согласно схеме:
{schema}

Данные:
{data}

Исправь:
- Опечатки в названиях полей
- Неправильные форматы дат (используй DD.MM.YYYY для украинских дат)
- Некорректные типы данных
- Отсутствующие обязательные поля (заполни null если невозможно определить)
- ИНН/ЕДРПОУ (10 цифр)
- Email/URL формат

Верни исправленный JSON."""
```

### 3. Data Validator (Валидатор данных)

**Назначение:** Проверка качества и корректности данных.

**Уровни валидации:**

1. **Структурная валидация**
   - Проверка наличия обязательных полей
   - Проверка типов данных
   - Проверка форматов (даты, ИНН, email)

2. **Бизнес-валидация**
   - Проверка логических связей
   - Валидация диапазонов значений
   - Проверка уникальности

3. **LLM-валидация**
   - Семантическая проверка
   - Обнаружение аномалий
   - Контекстная валидация

**Реализация:**

```python
class DataValidator:
    def validate_structure(self, data, schema):
        """Структурная валидация"""
        pass
    
    def validate_business_rules(self, data):
        """Бизнес-валидация"""
        pass
    
    def llm_validate(self, data, schema):
        """LLM валидация через LMStudio"""
        pass
```

### 4. Data Normalizer (Нормализатор данных)

**Назначение:** Приведение данных к единому формату.

**Операции нормализации:**

- Унификация форматов дат
- Нормализация текста (удаление лишних пробелов, приведение к регистру)
- Стандартизация названий полей
- Преобразование единиц измерения
- Кодировка (UTF-8)

**LLM-нормализация:**

```python
NORMALIZE_PROMPT = """Нормализуй следующие данные для украинских реестров:

1. Даты: формат DD.MM.YYYY
2. Текст: удали лишние пробелы, приведи к нормальному виду
3. Названия полей: стандартизируй (например: "ІПН" → "inn", "ЄДРПОУ" → "edrpou")
4. Кодировка: убедись что все в UTF-8

Данные:
{data}

Верни нормализованный JSON."""
```

### 5. Schema Detector (Детектор схемы БД)

**Назначение:** Определение оптимальной структуры БД для хранения данных.

**Функции:**

1. **Анализ характеристик данных**
   - Объём данных
   - Типы связей между сущностями
   - Частота обновлений
   - Паттерны запросов

2. **Выбор СУБД**
   - PostgreSQL - для реляционных данных
   - MongoDB - для гибкой схемы
   - Elasticsearch - для текстового поиска
   - Комбинация - для сложных случаев

3. **Генерация схемы**
   - SQL DDL для PostgreSQL
   - Индексы для оптимизации
   - Ограничения и валидации

**LLM-промпт:**

```python
DETERMINE_SCHEMA_PROMPT = """Определи оптимальную СУБД и схему для следующих данных:

Схема полей: {schema}
Объём данных: ~{volume} записей
Характеристики: {characteristics}

Выбери:
1. PostgreSQL - для реляционных данных, сложных связей
2. MongoDB - для гибкой схемы, документно-ориентированных данных
3. Elasticsearch - для текстового поиска, аналитики
4. Комбинация - если нужны разные подходы

Верни JSON:
{{
    "db_type": "postgresql/mongodb/elasticsearch/hybrid",
    "schema": {{
        "tables": [...],
        "indexes": [...],
        "relationships": [...]
    }},
    "reasoning": "..."
}}"""
```

### 6. Data Storage (Хранилище данных)

**Назначение:** Сохранение обработанных данных в БД.

**Стратегии хранения:**

- **Сырые данные** - оригинальные данные до обработки
- **Обработанные данные** - нормализованные и валидированные
- **Метаданные** - информация об источнике, времени обработки

**Реализация:**

```python
class DataStorage:
    def save_raw_data(self, source_url, raw_content, metadata):
        """Сохранение сырых данных"""
        pass
    
    def save_processed_data(self, data, schema, db_type):
        """Сохранение обработанных данных"""
        pass
    
    def update_metadata(self, source_url, metadata):
        """Обновление метаданных"""
        pass
```

## Поток обработки данных

### Этап 1: Загрузка

```python
# 1. Получение списка источников из crawler
sources = crawler.relevant_urls

# 2. Загрузка данных из каждого источника
for source in sources:
    loader = DataLoader()
    raw_data = loader.load(source['url'], source['type'])
```

### Этап 2: LLM-анализ

```python
# 3. LLM анализирует структуру
llm_analyzer = LLMAnalyzer(lmstudio_url)
analysis = llm_analyzer.analyze_structure(raw_data)

# 4. LLM извлекает структурированные данные
structured_data = llm_analyzer.extract_data(raw_data, analysis['schema'])
```

### Этап 3: Валидация и исправление

```python
# 5. Валидация данных
validator = DataValidator()
validation_result = validator.validate(structured_data, analysis['schema'])

# 6. LLM исправляет ошибки если есть
if validation_result['has_errors']:
    fixed_data = llm_analyzer.fix_errors(
        structured_data, 
        validation_result['errors'],
        analysis['schema']
    )
else:
    fixed_data = structured_data
```

### Этап 4: Нормализация

```python
# 7. Нормализация данных
normalizer = DataNormalizer()
normalized_data = normalizer.normalize(fixed_data, analysis['schema'])
```

### Этап 5: Определение схемы БД

```python
# 8. LLM определяет оптимальную БД и схему
db_strategy = llm_analyzer.determine_database_strategy(
    normalized_data,
    analysis['schema'],
    source_metadata
)
```

### Этап 6: Сохранение

```python
# 9. Сохранение в БД
storage = DataStorage()
storage.save_raw_data(source['url'], raw_data, source_metadata)
storage.save_processed_data(
    normalized_data,
    db_strategy['schema'],
    db_strategy['db_type']
)
```

## Интеграция с LMStudio

### Конфигурация

```python
LMSTUDIO_CONFIG = {
    "url": "http://192.168.0.60:1234/v1/chat/completions",
    "model": "openai/gpt-oss-20b",
    "temperature": 0.2,  # Низкая для точности
    "max_tokens": -1,
    "timeout": 120
}
```

### Кэширование LLM-запросов

Для оптимизации использования LLM рекомендуется кэшировать результаты:

```python
# Кэш для одинаковых запросов
cache_key = hash(content + prompt_template)
if cache.exists(cache_key):
    return cache.get(cache_key)
else:
    result = llm.call(prompt)
    cache.set(cache_key, result, ttl=7*24*3600)  # 7 дней
    return result
```

## Обработка ошибок

### Стратегии обработки ошибок

1. **Retry с экспоненциальной задержкой**
   - При временных ошибках LLM API
   - При сетевых проблемах

2. **Fallback методы**
   - Если LLM не может обработать → базовый парсинг
   - Если валидация не прошла → пометить для ручной проверки

3. **Логирование**
   - Все ошибки сохраняются в лог
   - Проблемные источники помечаются для повторной обработки

## Мониторинг и метрики

### Отслеживаемые метрики

- Количество обработанных источников
- Успешность обработки (%)
- Время обработки на источник
- Количество LLM-запросов
- Использование кэша (%)
- Ошибки валидации
- Объём сохранённых данных

### Дашборд

```python
metrics = {
    "sources_processed": 150,
    "success_rate": 0.95,
    "avg_processing_time": 12.5,  # секунд
    "llm_requests": 450,
    "cache_hit_rate": 0.65,
    "validation_errors": 8,
    "data_volume_mb": 1250
}
```

## Пример полного workflow

```python
from data_processor import DataProcessor
from crawler import LLMCrawler

# 1. Crawler находит источники
crawler = LLMCrawler()
crawler.crawl(seed_urls=[...])
sources = crawler.relevant_urls

# 2. Обработка данных
processor = DataProcessor(
    lmstudio_url="http://192.168.0.60:1234/v1/chat/completions",
    cache_backend="redis",
    storage_backend="postgresql"
)

# 3. Обработка каждого источника
for source in sources:
    try:
        result = processor.process_source(source)
        print(f"✅ Processed: {source['url']}")
    except Exception as e:
        print(f"❌ Error processing {source['url']}: {e}")
        # Логируем для последующей обработки
        processor.log_error(source, e)

# 4. Статистика
stats = processor.get_statistics()
print(f"Processed: {stats['success']}/{stats['total']}")
```

## Оптимизации

### 1. Параллельная обработка

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(processor.process_source, source) 
               for source in sources]
    results = [f.result() for f in futures]
```

### 2. Batch-обработка

```python
# Обработка нескольких источников одним LLM-запросом
batch = sources[:10]
batch_result = llm_analyzer.analyze_batch(batch)
```

### 3. Инкрементальная обработка

```python
# Обработка только новых/изменённых источников
if source['last_updated'] > last_processed_time:
    processor.process_source(source)
```

## Заключение

Данная архитектура обеспечивает:

- ✅ Автоматическую обработку различных форматов данных
- ✅ Интеллектуальную валидацию и исправление ошибок через LLM
- ✅ Гибкое определение схемы БД
- ✅ Масштабируемость и отказоустойчивость
- ✅ Эффективное использование LLM через кэширование

