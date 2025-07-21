#!/bin/bash

# 🚀 Скрипт развертывания бота на виртуальной машине
# Использование: ./deploy_vm.sh

set -e  # Останавливаем выполнение при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Логирование
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🚀 Развертывание бота на виртуальной машине"
echo "============================================="

# Проверка переменных окружения
if [ -z "$BOT_TOKEN" ]; then
    log_error "BOT_TOKEN не установлен!"
    echo "Установите токен бота:"
    echo "export BOT_TOKEN='your_bot_token_here'"
    exit 1
fi

log_success "BOT_TOKEN установлен"

# Создание .env файла
log_info "Создание .env файла..."
cat > .env << EOF
BOT_TOKEN=$BOT_TOKEN
LLM_SERVICE_URL=http://llm-service:8000
LOG_LEVEL=INFO
OLLAMA_HOST=0.0.0.0:11434
EOF

log_success ".env файл создан"

# Создание необходимых директорий
log_info "Создание директорий..."
mkdir -p temp models logs
sudo chown -R $USER:$USER temp models logs

# Проверка Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен! Установите Docker сначала."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose не установлен! Установите Docker Compose сначала."
    exit 1
fi

log_success "Docker и Docker Compose найдены"

# Сборка образов
log_info "Сборка Docker образов..."
docker-compose -f docker-compose.vm.yml build

log_success "Образы собраны"

# Запуск LLM сервиса для загрузки модели
log_info "Запуск LLM сервиса для загрузки модели..."
docker-compose -f docker-compose.vm.yml up llm-service -d

# Ожидание готовности сервиса
log_info "Ожидание готовности LLM сервиса..."
sleep 30

# Проверка готовности
max_retries=12
retries=0
while [ $retries -lt $max_retries ]; do
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_success "LLM сервис готов"
        break
    fi
    
    log_info "Ожидание... ($((retries + 1))/$max_retries)"
    sleep 10
    ((retries++))
done

if [ $retries -eq $max_retries ]; then
    log_error "LLM сервис не отвечает"
    docker-compose -f docker-compose.vm.yml logs llm-service
    exit 1
fi

# Загрузка модели
log_info "Загрузка модели llama3.2:3b..."
docker exec llm-service ollama pull llama3.2:3b

# Проверка загрузки модели
docker exec llm-service ollama list

log_success "Модель загружена"

# Запуск всех сервисов
log_info "Запуск всех сервисов..."
docker-compose -f docker-compose.vm.yml up -d

# Проверка статуса
sleep 10
docker-compose -f docker-compose.vm.yml ps

log_success "Развертывание завершено!"

echo ""
echo "📋 Полезные команды:"
echo "  Статус:    docker-compose -f docker-compose.vm.yml ps"
echo "  Логи:      docker-compose -f docker-compose.vm.yml logs -f"
echo "  Остановка: docker-compose -f docker-compose.vm.yml down"
echo "  Рестарт:   docker-compose -f docker-compose.vm.yml restart"
echo ""
echo "🎉 Ваш бот готов к работе!"
echo "Отправьте /start боту в Telegram для тестирования." 