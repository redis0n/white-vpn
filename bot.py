#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import importlib
import os
import time
import random
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# === АВТОУСТАНОВКА БИБЛИОТЕК ===
def install_package(package):
    """Устанавливает Python пакет"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_dependencies():
    """Проверяет и устанавливает необходимые библиотеки"""
    required_packages = [
        "vk-api",
        "requests"
    ]
    
    for package in required_packages:
        try:
            importlib.import_module(package.replace("-", "_"))
            print(f"✅ {package} уже установлен")
        except ImportError:
            print(f"📦 Устанавливаю {package}...")
            install_package(package)
            print(f"✅ {package} установлен")

# Устанавливаем зависимости перед импортом
check_and_install_dependencies()

# Теперь импортируем библиотеки
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

# === НАСТРОЙКИ ===
VK_TOKEN = os.getenv("VK_TOKEN", "vk1.a.zlTzO6lNzOBYHaY-QCZIyaIb455Z0Gy3WXuRVLGR_SgsL7KwaSSTFVar-g_loULT7K6GPcBnKkrlr3sdLSK9OZ5WFJxoqrI3CzUhzu9aTdQCQbsIYpLPZ1KM8Qe_CNbpv-M1_cIQdFGf5j22oT-ZLXONIXdxq0g23S0FnJLVJ7YLD_UaEv1F3Xi4TTA9L0tfOSwLyhcOF0pUJGBbFhgmbg")  # Можно через переменную окружения
REPO_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt"

# Хранилище состояний диалога
user_states = {}

# === ВЕБ-СЕРВЕР ДЛЯ KEEP-ALIVE (Render.com) ===
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/ping' or self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Отключаем логирование веб-сервера

def run_web_server():
    """Запускает простой веб-сервер для health check"""
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌐 Веб-сервер запущен на порту {port}")
    server.serve_forever()

def keep_alive():
    """Пингует себя каждые 10 минут, чтобы сервис не засыпал"""
    time.sleep(30)  # Даём время на запуск основного бота
    while True:
        try:
            service_url = os.getenv("RENDER_EXTERNAL_URL", "https://white-vpn.onrender.com")
            response = requests.get(f"{service_url}/ping", timeout=5)
            print(f"🏓 Keep-alive пинг: {response.status_code}")
            time.sleep(600)  # 10 минут
        except Exception as e:
            print(f"⚠️ Keep-alive ошибка: {e}")
            time.sleep(600)

# === ФУНКЦИЯ ПОЛУЧЕНИЯ ВСЕХ ССЫЛОК ИЗ РЕПОЗИТОРИЯ ===
def get_all_configs():
    try:
        response = requests.get(REPO_URL, timeout=15)
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            configs = [line.strip() for line in lines if line.strip().startswith('vless://')]
            print(f"📥 Загружено {len(configs)} конфигов")
            return configs
        else:
            print(f"❌ Ошибка загрузки: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

# === ФОРМАТИРОВАНИЕ ССЫЛОК ===
def format_configs_message(configs):
    """Форматирует список ссылок в одно сообщение"""
    if not configs:
        return "❌ Не удалось загрузить конфиги. Попробуйте позже."
    
    message = "📁 *WHITE VPN — ВСЕ ДОСТУПНЫЕ КОНФИГИ:*\n\n"
    message += "🔽 Скопируйте любую ссылку и вставьте в Happ:\n\n"
    
    # Ограничиваем количество ссылок (ВК лимит ~4000 символов)
    max_configs = min(len(configs), 50)
    
    for i, config in enumerate(configs[:max_configs], 1):
        message += f"{i}. `{config}`\n\n"
    
    if len(configs) > max_configs:
        message += f"... и ещё {len(configs) - max_configs} конфигов\n\n"
    
    message += "\n✨ *Инструкция:*\n"
    message += "1. Скопируйте ссылку\n"
    message += "2. Вставьте в приложение Happ\n"
    message += "3. Наслаждайтесь свободным интернетом!\n\n"
    message += "🌐 *WHITE VPN — ваш надёжный выбор*"
    
    return message

# === ОТПРАВКА ДЛИННЫХ СООБЩЕНИЙ ===
def send_long_message(vk, user_id, text, max_length=4000):
    """Разбивает длинное сообщение на части и отправляет"""
    if len(text) <= max_length:
        vk.messages.send(
            user_id=user_id,
            message=text,
            random_id=random.randint(1, 2**31)
        )
    else:
        parts = []
        current_part = ""
        
        for line in text.split('\n'):
            if len(current_part) + len(line) + 1 > max_length:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part)
        
        for i, part in enumerate(parts, 1):
            header = f"📄 *Часть {i}/{len(parts)}*\n\n"
            final_part = header + part
            vk.messages.send(
                user_id=user_id,
                message=final_part,
                random_id=random.randint(1, 2**31)
            )
            time.sleep(0.5)

# === ОСНОВНОЙ БОТ ===
def main():
    print("🟢 Запуск WHITE VPN бота...")
    print("🤖 Версия: 2.0")
    print("📡 Режим: VK Long Poll + Web Keep-Alive")
    
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # Запускаем keep-alive в отдельном потоке
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    # Проверяем токен
    if VK_TOKEN == "ВАШ_ТОКЕН_ГРУППЫ":
        print("⚠️ ВНИМАНИЕ: Используется токен по умолчанию!")
        print("📌 Для продакшена установите переменную окружения VK_TOKEN")
    
    # Авторизация ВК
    try:
        vk_session = vk_api.VkApi(token=VK_TOKEN)
        vk = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)
        print("✅ ВК подключен успешно!")
    except Exception as e:
        print(f"❌ Ошибка подключения к ВК: {e}")
        print("💡 Проверьте токен доступа группы")
        return
    
    # Кеш для конфигов
    cached_configs = []
    last_update = 0
    
    print("🎯 Бот готов к работе!")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    user_id = event.user_id
                    message_text = event.text.lower().strip()
                    print(f"📩 [{time.strftime('%H:%M:%S')}] От {user_id}: {message_text[:50]}")
                    
                    # Обновляем кеш конфигов раз в 10 минут
                    if time.time() - last_update > 600 or not cached_configs:
                        cached_configs = get_all_configs()
                        last_update = time.time()
                    
                    # Проверяем состояние пользователя
                    if user_id in user_states and user_states[user_id] == "waiting_for_site_answer":
                        
                        if message_text in ["да", "+", "yes", "lf", "y", "даа", "ага", "ок", "окей"]:
                            vk.messages.send(
                                user_id=user_id,
                                message="✅ Отлично! Рады, что всё работает.\n\n" +
                                       "Если понадобится помощь — просто напишите любое сообщение 😊\n\n" +
                                       "🌐 *WHITE VPN — всегда с вами!*",
                                random_id=random.randint(1, 2**31)
                            )
                            del user_states[user_id]
                            
                        elif message_text in ["нет", "-", "no", "ytn", "n", "неа", "не открывается", "нет("]:
                            vk.messages.send(
                                user_id=user_id,
                                message="😔 Понял, сайт не открывается.\n\n" +
                                       "🔽 *Отправляю все доступные конфиги прямо в чат:*\n\n" +
                                       "⏳ Подождите пару секунд, ссылки загружаются...",
                                random_id=random.randint(1, 2**31)
                            )
                            
                            time.sleep(1.5)
                            
                            if cached_configs:
                                configs_message = format_configs_message(cached_configs)
                                send_long_message(vk, user_id, configs_message)
                                
                                # Отправляем инструкцию по установке Happ
                                time.sleep(0.5)
                                vk.messages.send(
                                    user_id=user_id,
                                    message="📱 *Как использовать:*\n\n" +
                                           "1️⃣ Скопируйте любую ссылку выше\n" +
                                           "2️⃣ Скачайте Happ: https://disk.yandex.ru/d/LffqUWBFbfs2Yw\n" +
                                           "3️⃣ Вставьте ссылку в приложение\n\n" +
                                           "🚀 *WHITE VPN — ваш надёжный выбор!*",
                                    random_id=random.randint(1, 2**31)
                                )
                            else:
                                vk.messages.send(
                                    user_id=user_id,
                                    message="❌ Ошибка: не удалось загрузить конфиги. Попробуйте позже.\n\n" +
                                           "🔄 Напишите любое сообщение снова, чтобы повторить попытку.",
                                    random_id=random.randint(1, 2**31)
                                )
                            
                            del user_states[user_id]
                        else:
                            vk.messages.send(
                                user_id=user_id,
                                message="❓ Пожалуйста, ответьте «да» или «нет».\n\n" +
                                       "Открывается ли сайт https://redis0n.github.io/?",
                                random_id=random.randint(1, 2**31)
                            )
                        continue
                    
                    # Новый пользователь
                    vk.messages.send(
                        user_id=user_id,
                        message="🌐 *WHITE VPN — Добро пожаловать!* 🌐\n\n" +
                               "🔗 *Попробуйте зайти на сайт:*\n" +
                               "👉 https://redis0n.github.io/\n\n" +
                               "❓ *Открывается ли сайт?*\n" +
                               "Напишите «да» или «нет»",
                        random_id=random.randint(1, 2**31)
                    )
                    
                    user_states[user_id] = "waiting_for_site_answer"
                    print(f"⏳ Ожидаем ответ от {user_id}")
        
        except Exception as e:
            print(f"❌ Ошибка в основном цикле: {e}")
            print("🔄 Переподключение через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    main()
