FROM python:3.9-slim

WORKDIR /app

# Копируем файл бота
COPY bot.py .

# Запускаем бота
CMD ["python", "bot.py"]
