# ⚡ Быстрый старт на VM

## 🚀 За 5 минут

### 1. Подключение к серверу
```bash
ssh ubuntu@158.160.46.251
```

### 2. Установка Docker (если не установлен)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. Клонирование и настройка
```bash
# Клонирование (замените URL на ваш)
git clone https://github.com/your-username/your-repo.git рутуб
cd рутуб

# Установка токена бота
export BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"

# Запуск автоматического развертывания
./deploy_vm.sh
```

### 4. Проверка
```bash
# Статус сервисов
docker-compose -f docker-compose.vm.yml ps

# Проверка API
curl http://localhost:8000/health

# Логи
docker-compose -f docker-compose.vm.yml logs -f
```

## 📱 Получение токена бота

1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Сохраните полученный токен

## 🔧 Управление

```bash
# Остановка
docker-compose -f docker-compose.vm.yml down

# Запуск
docker-compose -f docker-compose.vm.yml up -d

# Рестарт
docker-compose -f docker-compose.vm.yml restart

# Обновление
git pull origin main
docker-compose -f docker-compose.vm.yml build --no-cache
docker-compose -f docker-compose.vm.yml up -d
```

## 🚨 Проблемы?

### Бот не отвечает
```bash
# Проверить токен
docker exec telegram-bot env | grep BOT_TOKEN

# Проверить логи
docker-compose -f docker-compose.vm.yml logs telegram-bot
```

### LLM не работает
```bash
# Проверить статус Ollama
docker exec llm-service ollama list

# Перезагрузить модель
docker exec llm-service ollama pull llama3.2:3b
```

### Нет места на диске
```bash
docker system prune -a
docker volume prune
```

## 🔐 Безопасность

```bash
# Firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8000/tcp  # опционально

# Автообновления
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure unattended-upgrades
```

## ✅ Готово!

После успешного развертывания:
- ✅ Бот доступен в Telegram  
- ✅ LLM сервис работает
- ✅ Автозапуск настроен
- ✅ Логирование активно

**Отправьте `/start` боту для тестирования!** 