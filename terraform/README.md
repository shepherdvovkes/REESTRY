# Terraform конфигурация для развертывания REESTRY

Эта Terraform конфигурация разворачивает Docker контейнеры для системы REESTRY на локальном хосте.

## Компоненты

- **Краулер** (`reestry-crawler`) - интеллектуальный веб-краулер с LLM анализом
- **Обработчик** (`reestry-processor`) - обработка и нормализация данных
- **PostgreSQL** (`reestry-postgres`) - основная база данных
- **Redis** (`reestry-redis`) - кэширование
- **Prometheus** (`reestry-prometheus`) - сбор метрик
- **Grafana** (`reestry-grafana`) - визуализация метрик

## Требования

- Docker и Docker Compose
- Terraform >= 1.0
- ~2GB свободного места на диске

## Установка

1. Убедитесь, что Docker запущен:
```bash
docker ps
```

2. Создайте директории для данных:
```bash
cd terraform
./init-data-dirs.sh
```

Или вручную:
```bash
mkdir -p ../data/{postgres,redis,prometheus,grafana,crawler,processor}
```

3. Инициализируйте Terraform:
```bash
terraform init
```

3. Настройте переменные (опционально):
Создайте файл `terraform.tfvars`:
```hcl
lmstudio_url = "http://192.168.0.60:1234/v1/chat/completions"
postgres_password = "your_secure_password"
grafana_admin_password = "your_grafana_password"
```

4. План развертывания:
```bash
terraform plan
```

5. Развертывание:
```bash
terraform apply
```

Terraform создаст все необходимые контейнеры и сети.

## Использование

### Подключение к базам данных

**PostgreSQL:**
```bash
psql -h localhost -p 5432 -U reestry_user -d reestry
# Пароль: reestry_password (или тот, что указан в переменных)
```

**Redis:**
```bash
redis-cli -h localhost -p 6379
```

### Доступ к веб-интерфейсам

- **Grafana**: http://localhost:3000
  - Пользователь: `admin`
  - Пароль: `admin` (или тот, что указан в переменных)

- **Prometheus**: http://localhost:9090

### Просмотр логов

```bash
# Логи краулера
docker logs reestry-crawler -f

# Логи обработчика
docker logs reestry-processor -f

# Логи PostgreSQL
docker logs reestry-postgres -f

# Логи всех контейнеров
docker-compose logs -f
```

### Управление контейнерами

```bash
# Остановить все контейнеры
terraform destroy

# Перезапустить конкретный контейнер
docker restart reestry-crawler

# Проверить статус контейнеров
docker ps
```

## Структура данных

Данные сохраняются в директории `../data/` относительно terraform директории:

```
data/
├── postgres/      # Данные PostgreSQL
├── redis/         # Данные Redis (AOF файлы)
├── prometheus/    # Метрики Prometheus
├── grafana/       # Конфигурация Grafana
├── crawler/       # Данные краулера
└── processor/     # Данные обработчика
```

## Переменные

Основные переменные можно изменить в `variables.tf` или через `terraform.tfvars`:

- `lmstudio_url` - URL LMStudio API сервера
- `postgres_password` - Пароль PostgreSQL
- `postgres_user` - Пользователь PostgreSQL (по умолчанию: reestry_user)
- `postgres_database` - Имя базы данных (по умолчанию: reestry)
- `grafana_admin_password` - Пароль администратора Grafana

## Мониторинг

После развертывания:

1. Откройте Grafana: http://localhost:3000
2. Войдите с учетными данными администратора
3. Prometheus должен быть автоматически настроен как источник данных
4. Создайте дашборды для мониторинга краулера и обработчика

## Устранение неполадок

### Контейнеры не запускаются

Проверьте логи:
```bash
docker logs reestry-crawler
docker logs reestry-processor
```

### Проблемы с сетью

Убедитесь, что сеть создана:
```bash
docker network ls | grep reestry
```

### Проблемы с правами доступа

Убедитесь, что директории данных созданы с правильными правами:
```bash
mkdir -p ../data/{postgres,redis,prometheus,grafana,crawler,processor}
```

## Удаление

Для полного удаления всех контейнеров и данных:

```bash
terraform destroy
```

**Внимание:** Это удалит все данные в контейнерах. Данные в `data/` директории сохранятся.

Для полного удаления с данными:
```bash
terraform destroy
rm -rf ../data
```

