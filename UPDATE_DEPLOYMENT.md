# 🚀 Обновление бота на виртуальной машине

## 📋 Пошаговая инструкция обновления

### 1. Подготовка к обновлению

```bash
# Подключаемся к виртуальной машине
ssh username@your-vm-ip

# Переходим в директорию проекта
cd /path/to/your/project

# Сохраняем текущую версию для возможного отката
docker-compose -f docker-compose.production.yml down
docker tag cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:backup-$(date +%Y%m%d-%H%M%S)
docker tag cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:latest cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:backup-$(date +%Y%m%d-%H%M%S)
```

### 2. Обновление кода

```bash
# Получаем изменения из репозитория
git fetch origin
git pull origin main

# Или если вы работаете с форком
git pull origin your-branch-name
```

### 3. Пересборка и деплой

#### Вариант A: Обновление обоих сервисов

```bash
# Собираем новые образы
docker build -t cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest -f Dockerfile.bot .
docker build -t cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:latest -f Dockerfile.llm .

# Пушим в реестр
docker push cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest
docker push cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:latest

# Запускаем обновленные сервисы
docker-compose -f docker-compose.production.yml up -d
```

#### Вариант B: Обновление только бота (например, при добавлении нового агента)

```bash
# Собираем только образ бота
docker build -t cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest -f Dockerfile.bot .
docker push cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest

# Обновляем только сервис бота
docker-compose -f docker-compose.production.yml up -d telegram-bot
```

#### Вариант C: Обновление только LLM сервиса

```bash
# Собираем только образ LLM
docker build -t cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:latest -f Dockerfile.llm .
docker push cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:latest

# Обновляем только LLM сервис
docker-compose -f docker-compose.production.yml up -d llm-service
```

### 4. Проверка обновления

```bash
# Проверяем статус контейнеров
docker-compose -f docker-compose.production.yml ps

# Проверяем логи
docker-compose -f docker-compose.production.yml logs -f telegram-bot
docker-compose -f docker-compose.production.yml logs -f llm-service

# Проверяем health check
curl http://localhost:8000/health
```

### 5. Тестирование после обновления

```bash
# Запускаем быстрые тесты
python test_deployment.py

# Отправляем тестовое сообщение боту
# (см. раздел тестирования ниже)
```

## 🔄 Сценарии обновления

### Сценарий 1: Добавили нового агента

```bash
# Пример: добавили CitationAgent в core/agents/

# 1. Обновляем код
git pull origin main

# 2. Пересобираем только бот (LLM сервис не изменился)
docker build -t cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest -f Dockerfile.bot .
docker push cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest

# 3. Обновляем только бот
docker-compose -f docker-compose.production.yml up -d telegram-bot

# 4. Проверяем работу нового агента
python test_new_agent.py
```

### Сценарий 2: Изменили зависимости

```bash
# Если изменился requirements.txt

# 1. Обновляем код
git pull origin main

# 2. Пересобираем оба образа (зависимости могли измениться в обоих)
docker build -t cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest -f Dockerfile.bot .
docker build -t cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:latest -f Dockerfile.llm .

# 3. Пушим образы
docker push cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest
docker push cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:latest

# 4. Полное обновление
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

### Сценарий 3: Экстренный откат

```bash
# Если что-то пошло не так, откатываемся к предыдущей версии

# 1. Останавливаем текущие контейнеры
docker-compose -f docker-compose.production.yml down

# 2. Возвращаем предыдущие образы
docker tag cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:backup-YYYYMMDD-HHMMSS cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest
docker tag cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:backup-YYYYMMDD-HHMMSS cr.yandex/crphvdf8t7v4bpqnv3g5/llm-service:latest

# 3. Запускаем предыдущую версию
docker-compose -f docker-compose.production.yml up -d

# 4. Возвращаем код в репозитории
git reset --hard HEAD~1  # или нужный коммит
```

## 🛠️ Автоматизация обновления

Для упрощения процесса создан скрипт автоматического обновления:

```bash
# Запуск автоматического обновления
./update_deployment.sh

# Обновление только бота
./update_deployment.sh bot-only

# Обновление только LLM
./update_deployment.sh llm-only

# Полное обновление с тестами
./update_deployment.sh full-test
```

## 📊 Мониторинг после обновления

### Проверка метрик

```bash
# Использование ресурсов
docker stats

# Логи в реальном времени
docker-compose -f docker-compose.production.yml logs -f

# Проверка доступности
curl -f http://localhost:8000/health || echo "LLM service unavailable"
```

### Алерты

Настройте уведомления для критических событий:
- Падение контейнера
- Высокое использование CPU/памяти
- Ошибки в логах
- Недоступность health check

## 🚨 Troubleshooting

### Проблема: Контейнер не запускается

```bash
# Проверяем логи
docker-compose -f docker-compose.production.yml logs telegram-bot
docker-compose -f docker-compose.production.yml logs llm-service

# Проверяем образы
docker images | grep telegram-bot
docker images | grep llm-service

# Пересобираем с очисткой кеша
docker build --no-cache -t cr.yandex/crphvdf8t7v4bpqnv3g5/telegram-bot:latest -f Dockerfile.bot .
```

### Проблема: LLM сервис недоступен

```bash
# Проверяем порты
netstat -tulpn | grep :8000
netstat -tulpn | grep :11434

# Проверяем Ollama
docker exec -it llm-service ollama list
docker exec -it llm-service ollama ps
```

### Проблема: Бот не отвечает

```bash
# Проверяем переменные окружения
docker exec -it telegram-bot env | grep BOT_TOKEN
docker exec -it telegram-bot env | grep LLM_SERVICE_URL

# Проверяем подключение к LLM
docker exec -it telegram-bot curl http://llm-service:8000/health
```

## 🔐 Безопасность

### Обязательные проверки перед обновлением

1. **Backup данных**: Сохраните текущие образы и данные
2. **Тестирование**: Запустите тесты перед продакшеном
3. **Мониторинг**: Следите за метриками после обновления
4. **Rollback план**: Подготовьте план отката

### Чек-лист безопасности

- [ ] BOT_TOKEN не попал в логи
- [ ] Временные файлы очищаются
- [ ] Контейнеры работают с минимальными правами
- [ ] Health checks настроены
- [ ] Backup создан
- [ ] Тесты пройдены

## 📞 Поддержка

В случае проблем:
1. Проверьте логи: `docker-compose logs`
2. Запустите тесты: `python test_deployment.py`
3. Проверьте health checks: `curl http://localhost:8000/health`
4. При критических проблемах сделайте откат к предыдущей версии 