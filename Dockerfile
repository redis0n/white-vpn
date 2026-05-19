FROM python:3.9-slim

WORKDIR /app

# Устанавливаем зависимости
RUN pip install vk-api requests openai

# Копируем бота
COPY bot.py .

# Запускаем бота
CMD ["python", "bot.py"]
