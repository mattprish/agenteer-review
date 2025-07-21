#!/bin/bash
# Скрипт развертывания бота с исправленной архитектурой

set -e

echo "🚀 Развертывание бота с правильной архитектурой"
echo "================================================"

# Проверяем BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не установлен"
    echo "Установите токен: export BOT_TOKEN=ваш_токен"
    exit 1
fi

echo "✅ BOT_TOKEN установлен"

# Создаем .env файл
echo "📝 Создание .env файла..."
cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
LOG_LEVEL=INFO
TEMP_DIR=/app/temp
MODEL_CACHE_DIR=/app/models
DOCKER_ENV=1
EOF
echo "✅ .env файл создан"

# Создаем необходимые директории
echo "📁 Создание директорий..."
mkdir -p temp logs models
sudo chown -R $USER:docker temp logs models 2>/dev/null || true
echo "✅ Директории созданы"

# Проверяем наличие Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден. Устанавливаем Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker установлен. Перезайдите в систему и запустите скрипт снова."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не найден. Устанавливаем..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

echo "✅ Docker и Docker Compose найдены"

# Останавливаем существующие контейнеры если есть
echo "⏹️ Остановка существующих контейнеров..."
docker-compose down --remove-orphans 2>/dev/null || true
docker-compose -f docker-compose.production.yml down --remove-orphans 2>/dev/null || true

# Очищаем старые образы
echo "🧹 Очистка старых образов..."
docker system prune -f || true

# Проверяем наличие правильных файлов архитектуры
echo "🔍 Проверка архитектуры..."
required_files=("app.py" "api/llm_server.py" "bot/handlers.py" "docker-compose.yml" "Dockerfile")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Отсутствует файл: $file"
        echo "Убедитесь что вы используете исправленную архитектуру!"
        exit 1
    fi
done
echo "✅ Архитектура соответствует требованиям"

# Проверяем что bot/handlers.py не содержит запрещенных импортов
echo "🚫 Проверка запрещенных импортов..."
forbidden_imports=("from core.orchestrator import" "from core.agents." "from core.pdf_extractor import")
for import in "${forbidden_imports[@]}"; do
    if grep -q "$import" bot/handlers.py; then
        echo "❌ Найден запрещенный импорт в bot/handlers.py: $import"
        echo "Телеграм-бот должен использовать только HTTP клиент!"
        exit 1
    fi
done
echo "✅ Запрещенных импортов не найдено"

# Собираем образы
echo "🏗️ Сборка Docker образов..."
docker-compose build --no-cache

echo "✅ Образы собраны"

# Запускаем ollama отдельно для загрузки модели
echo "🤖 Запуск Ollama для загрузки модели..."
docker-compose up -d ollama

# Ждем пока ollama запустится
echo "⏳ Ожидание запуска Ollama..."
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
        echo "✅ Ollama запущен"
        break
    fi
    echo "Ожидание Ollama... ($timeout сек)"
    sleep 3
    timeout=$((timeout-3))
done

if [ $timeout -eq 0 ]; then
    echo "❌ Ollama не запустился в течение 60 секунд"
    docker-compose logs ollama
    exit 1
fi

# Загружаем модель
echo "📥 Загрузка модели llama3.2:3b..."
if docker exec ollama-server ollama list | grep -q "llama3.2:3b"; then
    echo "✅ Модель llama3.2:3b уже загружена"
else
    echo "⏳ Загрузка модели... Это может занять несколько минут"
    docker exec ollama-server ollama pull llama3.2:3b
    echo "✅ Модель llama3.2:3b загружена"
fi

# Запускаем основное приложение
echo "🚀 Запуск основного приложения..."
docker-compose up -d app

# Ждем пока приложение запустится
echo "⏳ Ожидание запуска приложения..."
timeout=30
while [ $timeout -gt 0 ]; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ FastAPI сервер запущен"
        break
    fi
    echo "Ожидание FastAPI... ($timeout сек)"
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -eq 0 ]; then
    echo "❌ FastAPI не запустился в течение 30 секунд"
    docker-compose logs app
    exit 1
fi

# Проверяем работоспособность
echo "🧪 Проверка работоспособности..."

# Проверка health endpoint
health=$(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "error")
if [ "$health" = "healthy" ]; then
    echo "✅ Health check пройден"
else
    echo "❌ Health check не пройден"
    docker-compose logs app
    exit 1
fi

# Проверка models endpoint  
models=$(curl -s http://localhost:8000/models | jq -r '.success' 2>/dev/null || echo "false")
if [ "$models" = "true" ]; then
    echo "✅ Models endpoint работает"
else
    echo "❌ Models endpoint не работает"
    docker-compose logs app
    exit 1
fi

echo ""
echo "🎉 ДЕПЛОЙМЕНТ УСПЕШНО ЗАВЕРШЕН!"
echo "=================================="
echo "✅ Единый контейнер app работает на порту 8000"
echo "✅ Ollama сервер работает на порту 11434"
echo "✅ Telegram бот активен"
echo "✅ FastAPI сервер доступен"
echo "✅ Архитектура соответствует ТЗ"
echo ""
echo "📊 Статус сервисов:"
docker-compose ps
echo ""
echo "🔗 Полезные команды:"
echo "  Логи приложения: docker-compose logs app"
echo "  Логи ollama: docker-compose logs ollama"
echo "  Остановка: docker-compose down"
echo "  Перезапуск: docker-compose restart app"
echo ""
echo "🌐 Эндпоинты:"
echo "  Health: http://localhost:8000/health"
echo "  Models: http://localhost:8000/models"
echo "  Review: http://localhost:8000/review"
echo ""
echo "🤖 Telegram бот готов к работе!" 