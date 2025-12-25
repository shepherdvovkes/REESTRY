#!/bin/bash
# Скрипт для создания директорий данных перед развертыванием

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DATA_DIR="$SCRIPT_DIR/../data"

echo "Создание директорий для данных..."

mkdir -p "$DATA_DIR"/{postgres,redis,prometheus,grafana,crawler,processor}

# Установка правильных прав доступа
chmod -R 755 "$DATA_DIR"

# PostgreSQL требует права для пользователя postgres (UID 999 в контейнере)
# На macOS это может не работать, но попробуем
if [[ "$OSTYPE" != "darwin"* ]]; then
    chown -R 999:999 "$DATA_DIR/postgres" 2>/dev/null || true
fi

echo "✅ Директории созданы в: $DATA_DIR"
echo ""
echo "Структура:"
ls -la "$DATA_DIR"

