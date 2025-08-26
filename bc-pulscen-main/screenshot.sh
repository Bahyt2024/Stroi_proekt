#!/bin/bash

# Скрипт для запуска системы скриншотов
# Автор: AI Assistant
# Дата: $(date +%Y-%m-%d)

echo "🚀 Система скриншотов для сайта"
echo "=================================="

# Проверяем, запущен ли Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python3."
    exit 1
fi

# Проверяем, запущен ли сервер
echo "🔍 Проверяем доступность сервера..."
if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo "✅ Сервер запущен и доступен"
else
    echo "❌ Сервер не запущен"
    echo "💡 Запустите сначала: python3 main.py"
    echo ""
    read -p "Хотите запустить сервер сейчас? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Запускаю сервер..."
        python3 main.py &
        SERVER_PID=$!
        echo "⏳ Ждем запуска сервера..."
        sleep 5
        
        # Проверяем снова
        if curl -s http://localhost:8000 > /dev/null 2>&1; then
            echo "✅ Сервер успешно запущен (PID: $SERVER_PID)"
        else
            echo "❌ Не удалось запустить сервер"
            exit 1
        fi
    else
        exit 1
    fi
fi

echo ""
echo "Выберите режим:"
echo "1. Быстрый скриншот"
echo "2. Полный скрипт с выбором"
echo "3. Серия скриншотов (каждые 30 секунд)"
echo "4. Выход"

read -p "Введите номер (1-4): " choice

case $choice in
    1)
        echo "📸 Запускаю быстрый скриншот..."
        python3 quick_screenshot.py
        ;;
    2)
        echo "🎯 Запускаю полный скрипт..."
        python3 screenshot_system.py
        ;;
    3)
        echo "🔄 Запускаю серию скриншотов..."
        read -p "Количество скриншотов (по умолчанию 5): " count
        count=${count:-5}
        read -p "Интервал в секундах (по умолчанию 30): " interval
        interval=${interval:-30}
        
        echo "📸 Создаю $count скриншотов с интервалом $interval секунд..."
        for i in $(seq 1 $count); do
            echo "📸 Скриншот $i/$count..."
            python3 quick_screenshot.py > /dev/null 2>&1
            if [ $i -lt $count ]; then
                echo "⏳ Ждем $interval секунд..."
                sleep $interval
            fi
        done
        echo "🎉 Все скриншоты созданы!"
        ;;
    4)
        echo "👋 До свидания!"
        exit 0
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac

echo ""
echo "🎯 Готово! Проверьте папку 'system_screenshots'"

# Если мы запускали сервер, спрашиваем, нужно ли его остановить
if [ ! -z "$SERVER_PID" ]; then
    echo ""
    read -p "Остановить сервер? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🛑 Останавливаю сервер..."
        kill $SERVER_PID
        echo "✅ Сервер остановлен"
    fi
fi 