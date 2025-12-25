# UI Backend для управления датасетами и промптами

Backend API для веб-интерфейса управления датасетами, промптами и историей LLM обработки.

## Установка

```bash
cd ui_backend
pip install -r requirements.txt
```

## Запуск

```bash
python app.py
```

Сервер запустится на `http://localhost:5000`

## API Endpoints

### Промпты

- `GET /api/prompts` - Получить все промпты
- `GET /api/prompts/<id>` - Получить промпт по ID
- `POST /api/prompts` - Создать новый промпт
- `PUT /api/prompts/<id>` - Обновить промпт
- `DELETE /api/prompts/<id>` - Удалить промпт

### История LLM обработки

- `GET /api/llm-history` - Получить историю (параметры: `limit`, `algorithm_step`, `prompt_id`)
- `GET /api/llm-history/<id>` - Получить запись истории по ID
- `POST /api/llm-history` - Записать вызов LLM в историю

### Датасеты

- `GET /api/datasets` - Получить все датасеты
- `GET /api/datasets/<id>` - Получить датасет по ID
- `POST /api/datasets` - Создать новый датасет

### Статистика и алгоритм

- `GET /api/stats` - Общая статистика
- `GET /api/algorithm-steps` - Получить все шаги алгоритма с LLM обработкой

## База данных

Используется SQLite база данных `llm_history.db` в корне проекта.

Таблицы:
- `prompts` - Промпты для LLM
- `llm_history` - История вызовов LLM
- `datasets` - Датасеты
- `dataset_processing_history` - Связь датасетов с историей обработки

