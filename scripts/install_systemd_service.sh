#!/bin/bash

# 🔧 Скрипт установки systemd сервиса для автозапуска бота
# Использование: sudo ./install_systemd_service.sh

set -e

# Проверка прав
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo ./install_systemd_service.sh"
    exit 1
fi

# Получение текущей директории и пользователя
CURRENT_DIR="$(pwd)"
CURRENT_USER="${SUDO_USER:-$USER}"

echo "🔧 Установка systemd сервиса для автозапуска бота"
echo "================================================="
echo "Директория проекта: $CURRENT_DIR"
echo "Пользователь: $CURRENT_USER"

# Создание systemd unit файла
cat > /etc/systemd/system/rutub-bot.service << EOF
[Unit]
Description=Rutub Bot Service - Automatic Scientific Article Review Bot
Documentation=https://github.com/your-username/your-repo
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$CURRENT_DIR
ExecStartPre=/usr/local/bin/docker-compose -f docker-compose.vm.yml down
ExecStart=/usr/local/bin/docker-compose -f docker-compose.vm.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.vm.yml down
ExecReload=/usr/local/bin/docker-compose -f docker-compose.vm.yml restart
TimeoutStartSec=300
TimeoutStopSec=60
User=$CURRENT_USER
Group=docker

# Настройки безопасности
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$CURRENT_DIR $CURRENT_DIR/temp $CURRENT_DIR/logs
NoNewPrivileges=yes

# Ограничения ресурсов
MemoryMax=4G
CPUQuota=80%

# Перезапуск при сбоях
Restart=on-failure
RestartSec=30
StartLimitInterval=300
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Файл сервиса создан: /etc/systemd/system/rutub-bot.service"

# Перезагрузка systemd
systemctl daemon-reload
echo "✅ systemd конфигурация перезагружена"

# Включение автозапуска
systemctl enable rutub-bot.service
echo "✅ Автозапуск включен"

# Запуск сервиса
systemctl start rutub-bot.service
echo "✅ Сервис запущен"

# Проверка статуса
sleep 5
systemctl status rutub-bot.service --no-pager

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Полезные команды:"
echo "  Статус сервиса:    sudo systemctl status rutub-bot"
echo "  Запуск:            sudo systemctl start rutub-bot"
echo "  Остановка:         sudo systemctl stop rutub-bot"
echo "  Рестарт:           sudo systemctl restart rutub-bot"
echo "  Отключить автозапуск: sudo systemctl disable rutub-bot"
echo "  Логи сервиса:      journalctl -u rutub-bot -f"
echo "  Логи контейнеров:  docker-compose -f docker-compose.vm.yml logs -f"
echo ""
echo "🔄 Бот теперь автоматически запускается при загрузке системы!" 