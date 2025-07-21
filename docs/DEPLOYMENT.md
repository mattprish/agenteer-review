# 🚀 Деплоймент

## Docker (локально)

```bash
# 1. Настройка
cd docker
cp .env.example .env
# Отредактируйте BOT_TOKEN в .env

# 2. Запуск
docker-compose up -d

# 3. Проверка
docker-compose logs -f
curl http://localhost:8000/health
```

## Продакшен

```bash
# 1. Подготовка сервера
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# 2. Деплой
git clone <repo-url>
cd agenteer-review
export BOT_TOKEN="your_token"
./scripts/deploy.sh
```

## Управление

```bash
# Перезапуск
cd docker && docker-compose restart

# Логи
cd docker && docker-compose logs -f app

# Остановка
cd docker && docker-compose down

# Обновление
git pull && docker-compose build --no-cache && docker-compose up -d
```

## Мониторинг

```bash
# Статус
docker-compose ps

# Ресурсы
docker stats

# Проверка API
curl http://localhost:8000/health
``` 