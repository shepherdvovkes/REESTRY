#!/bin/bash
# Скрипт для запуска UI системы управления датасетами и промптами

echo "🚀 Запуск UI системы управления REESTRY..."

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python3."
    exit 1
fi

# Установка зависимостей backend
echo "📦 Установка зависимостей backend..."
cd ui_backend
pip3 install -r requirements.txt --quiet
cd ..

# Запуск backend в фоне
echo "🔧 Запуск backend API на http://localhost:5000..."
cd ui_backend
python3 app.py &
BACKEND_PID=$!
cd ..

# Ожидание запуска backend
sleep 3

# Проверка, что backend запустился
if ! curl -s http://localhost:5000/api/stats > /dev/null; then
    echo "⚠️  Backend не отвечает, но продолжаем..."
fi

# Запуск frontend сервера
echo "🌐 Запуск frontend сервера на http://localhost:8000..."
cd ui_frontend
python3 -m http.server 8000 &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ UI система запущена!"
echo ""
echo "📊 Backend API: http://localhost:5000"
echo "🌐 Frontend UI: http://localhost:8000"
echo ""
echo "Для остановки нажмите Ctrl+C или выполните:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Ожидание сигнала завершения
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait

