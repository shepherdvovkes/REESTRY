# Развертывание REESTRY с Terraform

Быстрый старт для развертывания всей системы REESTRY с помощью Terraform на локальном хосте.

## Быстрый старт

```bash
# 1. Перейдите в директорию terraform
cd terraform

# 2. Создайте директории для данных
./init-data-dirs.sh

# 3. Настройте переменные (опционально)
cp terraform.tfvars.example terraform.tfvars
# Отредактируйте terraform.tfvars

# 4. Инициализируйте Terraform
terraform init

# 5. Просмотрите план развертывания
terraform plan

# 6. Разверните систему
terraform apply

# 7. Проверьте статус контейнеров
make status
# или
docker ps --filter "name=reestry-"
```

## Альтернатива: Docker Compose

Если предпочитаете использовать Docker Compose напрямую (без Terraform):

```bash
# 1. Создайте файл .env
cp .env.example .env
# Отредактируйте .env

# 2. Создайте директории для данных
mkdir -p data/{postgres,redis,prometheus,grafana,crawler,processor}

# 3. Запустите все сервисы
docker-compose up -d

# 4. Проверьте логи
docker-compose logs -f

# 5. Остановите все сервисы
docker-compose down
```

## Компоненты системы

После развертывания будут доступны следующие сервисы:

| Сервис | Порт | Описание |
|--------|------|----------|
| PostgreSQL | 5432 | Основная база данных |
| Redis | 6379 | Кэширование |
| Краулер | - | Контейнер с краулером |
| Обработчик | - | Контейнер с обработчиком документов |
| Prometheus | 9090 | Сбор метрик |
| Grafana | 3000 | Визуализация метрик |

## Доступ к сервисам

### Grafana
- URL: http://localhost:3000
- Пользователь: `admin`
- Пароль: указан в `terraform.tfvars` (по умолчанию: `admin`)

### Prometheus
- URL: http://localhost:9090

### PostgreSQL
```bash
psql -h localhost -p 5432 -U reestry_user -d reestry
```

### Redis
```bash
redis-cli -h localhost -p 6379
```

## Полезные команды

### С помощью Makefile (в директории terraform)

```bash
make init          # Инициализация Terraform
make plan          # Просмотр плана
make apply         # Развертывание
make destroy       # Удаление всех контейнеров
make status        # Статус контейнеров
make logs          # Логи краулера
make logs-processor # Логи обработчика
```

### Прямые команды Docker

```bash
# Просмотр логов конкретного контейнера
docker logs reestry-crawler -f
docker logs reestry-processor -f

# Перезапуск контейнера
docker restart reestry-crawler

# Вход в контейнер
docker exec -it reestry-crawler bash

# Просмотр использования ресурсов
docker stats reestry-*
```

### Terraform команды

```bash
# Просмотр outputs (URL, учетные данные)
terraform output

# Просмотр состояния
terraform show

# Обновление после изменений
terraform apply -auto-approve
```

## Структура данных

Все данные сохраняются в директории `data/`:

```
data/
├── postgres/      # PostgreSQL данные
├── redis/         # Redis данные (AOF)
├── prometheus/    # Метрики Prometheus
├── grafana/       # Конфигурация и данные Grafana
├── crawler/       # Данные краулера
└── processor/     # Данные обработчика
```

**Важно:** При удалении директории `data/` все данные будут потеряны!

## Настройка переменных

Основные переменные в `terraform/variables.tf`:

- `lmstudio_url` - URL для LMStudio API (для краулера)
- `postgres_password` - Пароль PostgreSQL
- `postgres_user` - Пользователь PostgreSQL
- `postgres_database` - Имя базы данных
- `grafana_admin_password` - Пароль администратора Grafana

Настройка через файл `terraform.tfvars`:

```hcl
lmstudio_url = "http://192.168.0.60:1234/v1/chat/completions"
postgres_password = "your_secure_password"
grafana_admin_password = "your_grafana_password"
```

## Мониторинг

После развертывания:

1. Откройте Grafana: http://localhost:3000
2. Войдите с учетными данными
3. Prometheus уже настроен как источник данных
4. Создайте дашборды для мониторинга:
   - Статистика краулера (обработанные страницы, ошибки)
   - Статистика обработчика (документы, время обработки)
   - Использование ресурсов БД
   - Использование Redis кэша

## Устранение неполадок

### Контейнеры не запускаются

1. Проверьте логи:
```bash
docker logs reestry-crawler
docker logs reestry-processor
```

2. Проверьте, что директории данных созданы:
```bash
ls -la data/
```

3. Проверьте, что порты не заняты:
```bash
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :9090  # Prometheus
lsof -i :3000  # Grafana
```

### Проблемы с сетью Docker

```bash
# Проверьте, что сеть создана
docker network ls | grep reestry

# Пересоздайте сеть
docker network rm reestry-network
terraform apply
```

### Проблемы с правами доступа (Linux)

```bash
# Установите правильные права для PostgreSQL
sudo chown -R 999:999 data/postgres
sudo chmod -R 755 data/postgres
```

### Очистка и пересоздание

```bash
# Удалить все контейнеры
terraform destroy

# Удалить все данные (ВНИМАНИЕ: необратимо!)
rm -rf ../data

# Пересоздать
./init-data-dirs.sh
terraform apply
```

## Остановка системы

```bash
# Остановить все контейнеры (данные сохранятся)
terraform destroy

# Или с Docker Compose
docker-compose down

# Полное удаление с данными
terraform destroy
rm -rf ../data
```

## Дополнительная информация

- Подробная документация Terraform: [terraform/README.md](terraform/README.md)
- Документация краулера: [UkrDeepCrawler/README.md](UkrDeepCrawler/README.md)
- Docker Compose: [docker-compose.yml](docker-compose.yml)

