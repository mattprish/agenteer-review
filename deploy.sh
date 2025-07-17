#!/bin/bash
# Главный скрипт развертывания в Yandex Cloud

set -e

echo "🚀 Starting deployment to Yandex Cloud..."

# Проверяем, что все необходимые команды доступны
command -v yc >/dev/null 2>&1 || { echo "❌ yc CLI not installed"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl not installed"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ docker not installed"; exit 1; }

# Получаем Registry ID
REGISTRY_ID=$(yc container registry get --name my-registry --format json | jq -r .id)
echo "📦 Using registry: $REGISTRY_ID"

# Проверяем статус кластера
echo "🔍 Checking cluster status..."
CLUSTER_STATUS=$(yc managed-kubernetes cluster get --name my-cluster --format json | jq -r .status)
echo "Cluster status: $CLUSTER_STATUS"

if [ "$CLUSTER_STATUS" != "RUNNING" ]; then
    echo "⏳ Cluster is not ready yet. Current status: $CLUSTER_STATUS"
    echo "Please wait for cluster to be in RUNNING state and try again."
    exit 1
fi

# Настраиваем kubectl
echo "🔧 Configuring kubectl..."
yc managed-kubernetes cluster get-credentials --name my-cluster --external

# Проверяем подключение к кластеру
echo "✅ Testing cluster connection..."
kubectl cluster-info

# Создаем node group если не существует
echo "🏗️ Checking node groups..."
NODE_GROUP_COUNT=$(yc managed-kubernetes node-group list --cluster-name my-cluster --format json | jq length)
if [ "$NODE_GROUP_COUNT" -eq 0 ]; then
    echo "Creating node group..."
    yc managed-kubernetes node-group create \
        --name standard-nodes \
        --cluster-name my-cluster \
        --platform-id standard-v3 \
        --cores 2 \
        --memory 8 \
        --disk-size 50 \
        --fixed-size 2 \
        --async
    
    echo "⏳ Node group is being created. Please wait and run this script again."
    exit 0
fi

# Проверяем, что BOT_TOKEN установлен
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN environment variable is not set"
    echo "Please set it with: export BOT_TOKEN=your_bot_token_here"
    exit 1
fi

# Создаем секреты
echo "🔐 Creating secrets..."
./k8s/create-secrets.sh

# Применяем манифесты
echo "📋 Deploying applications..."
kubectl apply -f k8s/llm-deployment.yaml
kubectl apply -f k8s/bot-deployment.yaml

# Настраиваем автомасштабирование
echo "📈 Setting up autoscaling..."
kubectl autoscale deployment telegram-bot --cpu-percent=70 --min=2 --max=10

echo "🎉 Deployment completed!"
echo ""
echo "📊 Checking deployment status:"
kubectl get pods
echo ""
echo "📝 To monitor logs:"
echo "kubectl logs -f deployment/telegram-bot"
echo "kubectl logs -f deployment/llm-service"
echo ""
echo "🔍 To check services:"
echo "kubectl get services" 