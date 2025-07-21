#!/bin/bash

# Скрипт для запуска всех тестов
echo "🧪 Запуск всех тестов в виртуальном окружении"
echo "============================================="

# Активируем виртуальное окружение
source venv/bin/activate

echo "📋 Запуск test_local.py..."
python3 test_local.py
if [ $? -ne 0 ]; then
    echo "❌ test_local.py failed"
    exit 1
fi

echo ""
echo "🆕 Запуск test_new_agent.py..."
python3 test_new_agent.py
if [ $? -ne 0 ]; then
    echo "❌ test_new_agent.py failed"
    exit 1
fi

echo ""
echo "🚀 Запуск test_deployment.py --quick..."
python3 test_deployment.py --quick
if [ $? -ne 0 ]; then
    echo "❌ test_deployment.py failed"
    exit 1
fi

echo ""
echo "🎉 Все тесты прошли успешно!" 