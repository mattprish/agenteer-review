#!/bin/bash

# 🚀 Скрипт автоматического обновления бота
# Использование: ./update_deployment.sh [bot-only|llm-only|full-test]

set -e  # Останавливаем выполнение при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
REGISTRY="cr.yandex/crphvdf8t7v4bpqnv3g5"
DOCKER_COMPOSE_FILE="docker-compose.production.yml"
BACKUP_TIMESTAMP=$(date +%Y%m%d-%H%M%S)

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

# Проверка зависимостей
check_dependencies() {
    log_info "Проверка зависимостей..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker не установлен"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose не установлен"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "Git не установлен"
        exit 1
    fi
    
    log_success "Все зависимости установлены"
}

# Создание backup
create_backup() {
    log_info "Создание backup текущих образов..."
    
    # Останавливаем контейнеры
    docker-compose -f $DOCKER_COMPOSE_FILE down
    
    # Создаем backup образов
    if docker image inspect $REGISTRY/telegram-bot:latest &> /dev/null; then
        docker tag $REGISTRY/telegram-bot:latest $REGISTRY/telegram-bot:backup-$BACKUP_TIMESTAMP
        log_success "Backup образа telegram-bot создан"
    fi
    
    if docker image inspect $REGISTRY/llm-service:latest &> /dev/null; then
        docker tag $REGISTRY/llm-service:latest $REGISTRY/llm-service:backup-$BACKUP_TIMESTAMP
        log_success "Backup образа llm-service создан"
    fi
}

# Обновление кода
update_code() {
    log_info "Обновление кода из репозитория..."
    
    # Сохраняем текущую ветку
    CURRENT_BRANCH=$(git branch --show-current)
    
    # Проверяем наличие изменений
    if ! git diff --quiet; then
        log_warning "Обнаружены несохраненные изменения"
        git status
        read -p "Продолжить? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Операция отменена"
            exit 1
        fi
    fi
    
    # Обновляем код
    git fetch origin
    git pull origin $CURRENT_BRANCH
    
    log_success "Код обновлен"
}

# Сборка образов
build_images() {
    local component=$1
    
    case $component in
        "bot-only")
            log_info "Сборка образа telegram-bot..."
            docker build -t $REGISTRY/telegram-bot:latest -f Dockerfile.bot .
            docker push $REGISTRY/telegram-bot:latest
            log_success "Образ telegram-bot собран и загружен"
            ;;
        "llm-only")
            log_info "Сборка образа llm-service..."
            docker build -t $REGISTRY/llm-service:latest -f Dockerfile.llm .
            docker push $REGISTRY/llm-service:latest
            log_success "Образ llm-service собран и загружен"
            ;;
        *)
            log_info "Сборка всех образов..."
            docker build -t $REGISTRY/telegram-bot:latest -f Dockerfile.bot .
            docker build -t $REGISTRY/llm-service:latest -f Dockerfile.llm .
            docker push $REGISTRY/telegram-bot:latest
            docker push $REGISTRY/llm-service:latest
            log_success "Все образы собраны и загружены"
            ;;
    esac
}

# Запуск сервисов
start_services() {
    local component=$1
    
    log_info "Запуск сервисов..."
    
    case $component in
        "bot-only")
            docker-compose -f $DOCKER_COMPOSE_FILE up -d telegram-bot
            ;;
        "llm-only")
            docker-compose -f $DOCKER_COMPOSE_FILE up -d llm-service
            ;;
        *)
            docker-compose -f $DOCKER_COMPOSE_FILE up -d
            ;;
    esac
    
    log_success "Сервисы запущены"
}

# Проверка здоровья сервисов
health_check() {
    log_info "Проверка здоровья сервисов..."
    
    # Ждем запуска
    sleep 10
    
    # Проверяем статус контейнеров
    if ! docker-compose -f $DOCKER_COMPOSE_FILE ps | grep -q "Up"; then
        log_error "Не все контейнеры запущены"
        docker-compose -f $DOCKER_COMPOSE_FILE ps
        return 1
    fi
    
    # Проверяем health check LLM сервиса
    local retries=0
    local max_retries=12  # 2 минуты с интервалом 10 секунд
    
    while [ $retries -lt $max_retries ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log_success "LLM сервис доступен"
            break
        fi
        
        log_info "Ожидание готовности LLM сервиса... ($((retries + 1))/$max_retries)"
        sleep 10
        ((retries++))
    done
    
    if [ $retries -eq $max_retries ]; then
        log_error "LLM сервис не отвечает на health check"
        return 1
    fi
    
    log_success "Все сервисы работают корректно"
    return 0
}

# Запуск тестов
run_tests() {
    log_info "Запуск тестов..."
    
    if [ -f "test_deployment.py" ]; then
        python3 test_deployment.py
        if [ $? -eq 0 ]; then
            log_success "Все тесты пройдены"
        else
            log_error "Тесты не пройдены"
            return 1
        fi
    else
        log_warning "Файл test_deployment.py не найден, пропускаем тесты"
    fi
    
    return 0
}

# Откат к предыдущей версии
rollback() {
    log_warning "Откат к предыдущей версии..."
    
    # Останавливаем текущие контейнеры
    docker-compose -f $DOCKER_COMPOSE_FILE down
    
    # Возвращаем backup образы
    if docker image inspect $REGISTRY/telegram-bot:backup-$BACKUP_TIMESTAMP &> /dev/null; then
        docker tag $REGISTRY/telegram-bot:backup-$BACKUP_TIMESTAMP $REGISTRY/telegram-bot:latest
    fi
    
    if docker image inspect $REGISTRY/llm-service:backup-$BACKUP_TIMESTAMP &> /dev/null; then
        docker tag $REGISTRY/llm-service:backup-$BACKUP_TIMESTAMP $REGISTRY/llm-service:latest
    fi
    
    # Запускаем предыдущую версию
    docker-compose -f $DOCKER_COMPOSE_FILE up -d
    
    log_success "Откат выполнен"
}

# Очистка старых backup'ов
cleanup_backups() {
    log_info "Очистка старых backup'ов..."
    
    # Удаляем backup'ы старше 7 дней
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | \
    grep backup | \
    awk '{print $1}' | \
    while read image; do
        # Извлекаем дату из тега
        date_str=$(echo $image | grep -o '[0-9]\{8\}-[0-9]\{6\}')
        if [ ! -z "$date_str" ]; then
            # Преобразуем в timestamp
            backup_date=$(date -d "${date_str:0:8} ${date_str:9:2}:${date_str:11:2}:${date_str:13:2}" +%s 2>/dev/null || echo 0)
            current_date=$(date +%s)
            
            # Если backup старше 7 дней, удаляем
            if [ $((current_date - backup_date)) -gt 604800 ]; then  # 7 дней в секундах
                log_info "Удаление старого backup: $image"
                docker rmi $image || true
            fi
        fi
    done
    
    log_success "Очистка backup'ов завершена"
}

# Главная функция
main() {
    local mode=${1:-"full"}
    
    echo "🚀 Автоматическое обновление бота"
    echo "Режим: $mode"
    echo "Время: $(date)"
    echo "=================================="
    
    # Проверяем зависимости
    check_dependencies
    
    # Создаем backup
    create_backup
    
    # Обновляем код
    update_code
    
    # Собираем образы
    build_images $mode
    
    # Запускаем сервисы
    start_services $mode
    
    # Проверяем здоровье
    if ! health_check; then
        log_error "Проверка здоровья не пройдена, выполняем откат"
        rollback
        exit 1
    fi
    
    # Запускаем тесты если включен режим full-test
    if [ "$mode" = "full-test" ]; then
        if ! run_tests; then
            log_error "Тесты не пройдены, выполняем откат"
            rollback
            exit 1
        fi
    fi
    
    # Очищаем старые backup'ы
    cleanup_backups
    
    log_success "Обновление завершено успешно!"
    
    echo ""
    echo "📊 Статус сервисов:"
    docker-compose -f $DOCKER_COMPOSE_FILE ps
    
    echo ""
    echo "📋 Полезные команды:"
    echo "  Логи бота: docker-compose -f $DOCKER_COMPOSE_FILE logs -f telegram-bot"
    echo "  Логи LLM:  docker-compose -f $DOCKER_COMPOSE_FILE logs -f llm-service"
    echo "  Статус:    docker-compose -f $DOCKER_COMPOSE_FILE ps"
    echo "  Health:    curl http://localhost:8000/health"
}

# Обработка сигналов
trap 'log_error "Операция прервана"; exit 1' INT TERM

# Запуск
main "$@" 