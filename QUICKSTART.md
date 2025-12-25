# Быстрый старт - Реализация рекомендаций высокого приоритета

## 🚀 Установка за 3 шага

### Шаг 1: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 2: Применение миграций БД

```bash
# Убедитесь, что PostgreSQL запущен и доступен
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

### Шаг 3: Проверка работы

```bash
python3 data_management/example_usage.py
```

## 📋 Основные возможности

### 1. Регистрация и загрузка источника

```python
from data_management import DatabaseManager, DataDownloadManager

db = DatabaseManager(host='localhost', database='reestry', 
                     user='reestry_user', password='reestry_password')
download_manager = DataDownloadManager(db)

# Регистрация
source_id = download_manager.register_source(
    url='https://data.gov.ua/api/dataset/example',
    source_type='api'  # или 'file', 'web'
)

# Загрузка (можно прервать Ctrl+C и возобновить позже)
download_manager.resume_download(source_id)
```

### 2. Проверка целостности

```python
from data_management import DataIntegrityChecker

checker = DataIntegrityChecker(db)
result = checker.verify_downloaded_data(source_id)

print(f"Целостность: {result['integrity_score']:.2%}")
print(f"Отсутствующих: {len(result['missing_records'])}")
print(f"Несовпадающих: {len(result['mismatched_records'])}")
```

### 3. Создание датасета для ML

```python
from data_management import MLDatasetManager

dataset_manager = MLDatasetManager(db)

# Создание версии
version_id = dataset_manager.create_dataset_version(
    name='ukrainian_laws_v1',
    description='Базовый датасет'
)

# Подготовка
result = dataset_manager.prepare_training_dataset(
    version_id=version_id,
    filters={'document_type': 'Кодекс'},
    min_length=1000
)

# Экспорт
dataset_manager.export_for_training(
    version_id=version_id,
    format='jsonl',
    output_file='training_data.jsonl'
)
```

### 4. Инкрементальное обновление

```python
# Получение новых/измененных документов
new_samples = dataset_manager.get_incremental_updates(base_version_id=1)

if len(new_samples) >= 100:
    # Создание инкрементального датасета
    new_version_id = dataset_manager.create_incremental_dataset(
        base_version_id=1,
        new_samples=new_samples
    )
    
    # Экспорт для дообучения
    dataset_manager.export_for_training(
        version_id=new_version_id,
        format='jsonl',
        output_file=f'incremental_{new_version_id}.jsonl'
    )
```

## 🔧 Конфигурация

### Переменные окружения

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=reestry
export POSTGRES_USER=reestry_user
export POSTGRES_PASSWORD=reestry_password
```

### Docker Compose

Если используете docker-compose.yml, переменные уже настроены:
- `POSTGRES_HOST=postgres`
- `POSTGRES_DB=reestry`
- `POSTGRES_USER=reestry_user`
- `POSTGRES_PASSWORD=reestry_password`

## 📚 Дополнительная документация

- **Подробное руководство**: `IMPLEMENTATION_GUIDE.md`
- **Примеры кода**: `data_management/example_usage.py`
- **Документация модуля**: `data_management/README.md`
- **Сводка реализации**: `IMPLEMENTATION_SUMMARY.md`

## ⚠️ Важные замечания

1. **Миграции применяются один раз** - при первом запуске
2. **Возобновление загрузки** - можно прервать (Ctrl+C) и продолжить позже
3. **Проверка целостности** - требует доступа к исходным данным
4. **Инкрементальные датасеты** - создаются только при наличии >= 100 новых образцов

## 🐛 Решение проблем

### Ошибка подключения к БД
```bash
# Проверьте, что PostgreSQL запущен
docker-compose ps postgres

# Или проверьте подключение
psql -h localhost -U reestry_user -d reestry
```

### Миграции не применяются
```bash
# Проверьте логи
python3 database/apply_migrations.py --verbose

# Проверьте права доступа к БД
```

### Импорт модулей не работает
```bash
# Убедитесь, что находитесь в корне проекта
cd /Users/vovkes/REESTRY

# Проверьте установку зависимостей
pip list | grep psycopg2
```

## ✅ Чеклист готовности

- [ ] Зависимости установлены (`pip install -r requirements.txt`)
- [ ] PostgreSQL запущен и доступен
- [ ] Миграции применены (`python3 database/apply_migrations.py`)
- [ ] Примеры работают (`python3 data_management/example_usage.py`)
- [ ] Модули импортируются без ошибок

Готово! 🎉

