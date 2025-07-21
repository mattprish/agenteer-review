FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY config/requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY src/ ./src/
COPY docker/.env* ./

# Создаем необходимые директории
RUN mkdir -p /app/temp /app/models /app/logs

# Устанавливаем права
RUN chmod +x src/app.py

# Экспортируем порт
EXPOSE 8000

# Устанавливаем PYTHONPATH для корректной работы импортов
ENV PYTHONPATH=/app/src

# Запускаем приложение
CMD ["python", "src/app.py"] 