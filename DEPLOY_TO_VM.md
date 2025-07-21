# 🚀 Развертывание на виртуальной машине

## 1. Подключение к серверу

```bash
ssh ubuntu@158.160.46.251
```

## 2. Подготовка системы

### Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### Установка Docker
```bash
# Удаляем старые версии (если есть)
sudo apt-get remove docker docker-engine docker.io containerd runc

# Устанавливаем зависимости
sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавляем GPG ключ Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавляем репозиторий Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Устанавливаем Docker
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Перезапускаем сессию для применения изменений
newgrp docker
```

### Установка Docker Compose (отдельно)
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Установка Git и других утилит
```bash
sudo apt install git curl wget htop nano -y
```

## 3. Клонирование проекта

```bash
# Переходим в домашнюю директорию
cd ~

# Клонируем репозиторий (замените на ваш URL)
git clone https://github.com/your-username/your-repo.git рутуб

# Переходим в директорию проекта
cd рутуб
```

## 4. Настройка окружения

### Создание .env файла
```bash
nano .env
```

Добавьте следующие переменные:
```bash
BOT_TOKEN=your_telegram_bot_token_here
LLM_SERVICE_URL=http://llm-service:8000
LOG_LEVEL=INFO
OLLAMA_HOST=0.0.0.0:11434
```

### Создание необходимых директорий
```bash
mkdir -p temp
mkdir -p models
mkdir -p logs
sudo chown -R $USER:$USER temp models logs
```

## 5. Сборка Docker образов

### Сборка образа LLM сервиса
```bash
docker build -t llm-service:latest -f Dockerfile.llm .
```

### Сборка образа Telegram бота
```bash
docker build -t telegram-bot:latest -f Dockerfile.bot .
```

## 6. Настройка Docker Compose для VM

Создайте упрощенный docker-compose.vm.yml:

```bash
nano docker-compose.vm.yml
```

```yaml
version: '3.8'

services:
  llm-service:
    build:
      context: .
      dockerfile: Dockerfile.llm
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

  telegram-bot:
    build:
      context: .
      dockerfile: Dockerfile.bot
    container_name: telegram-bot
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - LLM_SERVICE_URL=http://llm-service:8000
      - LOG_LEVEL=INFO
    volumes:
      - ./temp:/app/temp
    depends_on:
      llm-service:
        condition: service_healthy
    restart: unless-stopped

volumes:
  ollama_data:
    driver: local
```

## 7. Запуск сервисов

### Первый запуск (с загрузкой модели)
```bash
# Загружаем переменные окружения
export $(grep -v '^#' .env | xargs)

# Запускаем только LLM сервис для загрузки модели
docker-compose -f docker-compose.vm.yml up llm-service -d

# Ждем запуска сервиса
sleep 30

# Проверяем статус
docker-compose -f docker-compose.vm.yml logs llm-service

# Заходим в контейнер и загружаем модель
docker exec -it llm-service ollama pull llama3.2:3b

# Проверяем, что модель загружена
docker exec -it llm-service ollama list
```

### Запуск всех сервисов
```bash
# Запускаем все сервисы
docker-compose -f docker-compose.vm.yml up -d

# Проверяем статус
docker-compose -f docker-compose.vm.yml ps
```

## 8. Проверка работы

### Проверка health check
```bash
curl http://localhost:8000/health
```

### Проверка логов
```bash
# Логи LLM сервиса
docker-compose -f docker-compose.vm.yml logs -f llm-service

# Логи бота (в другом терминале)
docker-compose -f docker-compose.vm.yml logs -f telegram-bot
```

### Тестирование бота
1. Отправьте команду `/start` вашему боту в Telegram
2. Попробуйте отправить PDF файл
3. Проверьте, что бот отвечает

## 9. Настройка автозапуска

### Создание systemd сервиса
```bash
sudo nano /etc/systemd/system/rutub-bot.service
```

```ini
[Unit]
Description=Rutub Bot Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/рутуб
ExecStart=/usr/local/bin/docker-compose -f docker-compose.vm.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.vm.yml down
TimeoutStartSec=0
User=ubuntu

[Install]
WantedBy=multi-user.target
```

### Активация сервиса
```bash
sudo systemctl daemon-reload
sudo systemctl enable rutub-bot.service
sudo systemctl start rutub-bot.service

# Проверка статуса
sudo systemctl status rutub-bot.service
```

## 10. Мониторинг и обслуживание

### Полезные команды
```bash
# Статус сервисов
docker-compose -f docker-compose.vm.yml ps

# Логи в реальном времени
docker-compose -f docker-compose.vm.yml logs -f

# Рестарт сервисов
docker-compose -f docker-compose.vm.yml restart

# Остановка сервисов
docker-compose -f docker-compose.vm.yml down

# Обновление образов
docker-compose -f docker-compose.vm.yml pull
docker-compose -f docker-compose.vm.yml up -d
```

### Мониторинг ресурсов
```bash
# Использование Docker
docker stats

# Использование системы
htop

# Место на диске
df -h

# Логи системы
journalctl -u rutub-bot.service -f
```

## 11. Обновление проекта

```bash
# Остановка сервисов
docker-compose -f docker-compose.vm.yml down

# Обновление кода
git pull origin main

# Пересборка образов
docker-compose -f docker-compose.vm.yml build --no-cache

# Запуск обновленных сервисов
docker-compose -f docker-compose.vm.yml up -d
```

## 12. Troubleshooting

### Проблема: Контейнер не запускается
```bash
# Проверяем логи
docker-compose -f docker-compose.vm.yml logs [service-name]

# Проверяем образы
docker images

# Пересобираем с очисткой
docker-compose -f docker-compose.vm.yml build --no-cache
```

### Проблема: Нет места на диске
```bash
# Очистка неиспользуемых образов
docker system prune -a

# Очистка volumes
docker volume prune

# Очистка контейнеров
docker container prune
```

### Проблема: Модель не загружается
```bash
# Проверяем Ollama
docker exec -it llm-service ollama list
docker exec -it llm-service ollama ps

# Повторная загрузка модели
docker exec -it llm-service ollama pull llama3.2:3b
```

## 🔐 Безопасность

### Настройка firewall
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8000/tcp  # для LLM API (опционально)
sudo ufw status
```

### Обновления безопасности
```bash
# Автоматические обновления безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

## 📞 Поддержка

После развертывания ваш бот будет:
- Автоматически запускаться при перезагрузке сервера
- Обрабатывать PDF файлы научных статей
- Предоставлять автоматическое рецензирование
- Логировать все операции

Для мониторинга используйте команды из раздела 10. 