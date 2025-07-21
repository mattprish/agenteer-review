#!/bin/bash
# Скрипт развертывания бота на виртуальной машине

set -e

echo "🚀 Развертывание бота на виртуальной машине"
echo "============================================="

# Проверяем BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не установлен"
    echo "Установите токен: export BOT_TOKEN=ваш_токен"
    exit 1
fi

echo "[SUCCESS] BOT_TOKEN установлен"

# Создаем .env файл
echo "[INFO] Создание .env файла..."
cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
LOG_LEVEL=INFO
OLLAMA_HOST=0.0.0.0:11434
EOF
echo "[SUCCESS] .env файл создан"

# Создаем необходимые директории
echo "[INFO] Создание директорий..."
mkdir -p temp logs models
echo "[SUCCESS] Директории созданы"

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

echo "[SUCCESS] Docker и Docker Compose найдены"

# Останавливаем существующие контейнеры если есть
echo "[INFO] Остановка существующих контейнеров..."
docker-compose -f docker-compose.production.yml down --remove-orphans || true

# Очищаем старые образы
echo "[INFO] Очистка старых образов..."
docker system prune -f || true

# Собираем образы локально для ВМ
echo "[INFO] Сборка Docker образов..."

# Собираем LLM сервис
echo "Building llm-service"
docker build -t agenteer-review_llm-service:latest -f Dockerfile.llm .

# Собираем Telegram бот
echo "Building telegram-bot"  
docker build -t agenteer-review_telegram-bot:latest -f Dockerfile.bot .

echo "[SUCCESS] Образы собраны"

# Создаем docker-compose файл для ВМ
echo "[INFO] Создание конфигурации для ВМ..."
cat > docker-compose.vm.yml << 'EOF'
version: '3.8'

services:
  llm-service:
    image: agenteer-review_llm-service:latest
    container_name: llm-service
    ports:
      - "8000:8000"
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    volumes:
      - ollama_data:/root/.ollama
      - ./temp:/app/temp
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"] 
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  telegram-bot:
    image: agenteer-review_telegram-bot:latest
    container_name: telegram-bot
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - LLM_SERVICE_URL=http://llm-service:8000
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./temp:/app/temp
    depends_on:
      llm-service:
        condition: service_healthy
    restart: unless-stopped

volumes:
  ollama_data:
    driver: local
EOF

echo "[SUCCESS] Конфигурация создана"

# Запускаем LLM сервис для загрузки модели
echo "[INFO] Запуск LLM сервиса для загрузки модели..."
docker-compose -f docker-compose.vm.yml up -d llm-service

echo "[INFO] Ожидание запуска LLM сервиса..."
sleep 30

# Проверяем, что сервис запустился
echo "[INFO] Проверка здоровья LLM сервиса..."
for i in {1..10}; do
    if curl -f http://localhost:8000/health &>/dev/null; then
        echo "[SUCCESS] LLM сервис готов"
        break
    fi
    echo "Попытка $i/10: ждем готовности сервиса..."
    sleep 10
done

# Запускаем Telegram бота
echo "[INFO] Запуск Telegram бота..."
docker-compose -f docker-compose.vm.yml up -d telegram-bot

echo "[SUCCESS] Деплой завершен!"
echo ""
echo "📊 Статус сервисов:"
docker-compose -f docker-compose.vm.yml ps
echo ""
echo "📝 Просмотр логов:"
echo "docker-compose -f docker-compose.vm.yml logs -f llm-service"
echo "docker-compose -f docker-compose.vm.yml logs -f telegram-bot"
echo ""
echo "🛑 Остановка сервисов:"
echo "docker-compose -f docker-compose.vm.yml down"
echo ""
echo "🔄 Перезапуск:"
echo "docker-compose -f docker-compose.vm.yml restart"