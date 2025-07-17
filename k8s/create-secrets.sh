#!/bin/bash
# Скрипт для создания секретов в Kubernetes

# Проверяем, что переменная BOT_TOKEN установлена
if [ -z "$BOT_TOKEN" ]; then
    echo "Error: BOT_TOKEN environment variable is not set"
    echo "Please set it with: export BOT_TOKEN=your_bot_token_here"
    exit 1
fi

# Создаем секрет с токеном бота
kubectl create secret generic bot-secrets \
    --from-literal=token="$BOT_TOKEN" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "Bot secret created successfully!"

# Проверяем секрет
kubectl get secret bot-secrets -o yaml 