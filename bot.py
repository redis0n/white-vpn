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
from collections import deque

# === АВТОУСТАНОВКА БИБЛИОТЕК ===
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_dependencies():
    required_packages = ["vk-api", "requests"]
    for package in required_packages:
        try:
            importlib.import_module(package.replace("-", "_"))
            print(f"✅ {package} уже установлен")
        except ImportError:
            print(f"📦 Устанавливаю {package}...")
            install_package(package)
            print(f"✅ {package} установлен")

check_and_install_dependencies()

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

# === НАСТРОЙКИ ===
VK_TOKEN = "vk1.a.zlTzO6lNzOBYHaY-QCZIyaIb455Z0Gy3WXuRVLGR_SgsL7KwaSSTFVar-g_loULT7K6GPcBnKkrlr3sdLSK9OZ5WFJxoqrI3CzUhzu9aTdQCQbsIYpLPZ1KM8Qe_CNbpv-M1_cIQdFGf5j22oT-ZLXONIXdxq0g23S0FnJLVJ7YLD_UaEv1F3Xi4TTA9L0tfOSwLyhcOF0pUJGBbFhgmbg"

# ССЫЛКА НА ФАЙЛ С КОНФИГАМИ (GitLab)
CONFIGS_URL = "https://translated.turbopages.org/proxy_u/ru-en.ru.518e6b1b-6a0c8606-38125922-74722d776562/https/gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/WHITE-CIDR-RU-checked.txt?ref_type=heads"

# НОВАЯ ССЫЛКА НА HAPP
HAPP_URL = "https://disk.yandex.ru/d/rSVad4tmlR_dGg"

user_states = {}

# === КЕШ ДЛЯ ПРЕДОТВРАЩЕНИЯ ДУБЛЕЙ ===
# Храним последние 100 обработанных ID сообщений
processed_messages = deque(maxlen=100)

# === ВЕБ-СЕРВЕР ДЛЯ KEEP-ALIVE ===
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/ping' or self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌐 Веб-сервер запущен на порту {port}")
    server.serve_forever()

def keep_alive():
    time.sleep(30)
    while True:
        try:
            service_url = os.getenv("RENDER_EXTERNAL_URL", "https://white-vpn.onrender.com")
            requests.get(f"{service_url}/ping", timeout=5)
            print("🏓 Keep-alive пинг")
            time.sleep(600)
        except:
            time.sleep(600)

# === ПРОВЕРКА ДОСТУПНОСТИ ССЫЛКИ ===
def check_configs_url():
    try:
        response = requests.get(CONFIGS_URL, timeout=10)
        return response.status_code == 200
    except:
        return False

# === ОСНОВНОЙ БОТ ===
def main():
    print("🟢 Запуск WHITE VPN бота...")
    
    threading.Thread(target=run_web_server, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    
    try:
        vk_session = vk_api.VkApi(token=VK_TOKEN)
        vk = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)
        print("✅ ВК подключен успешно!")
    except Exception as e:
        print(f"❌ Ошибка подключения к ВК: {e}")
        return
    
    print("🎯 Бот готов к работе!")
    
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    
                    # === ПРОВЕРКА НА ДУБЛЬ ===
                    message_id = getattr(event, 'message_id', None)
                    if message_id and message_id in processed_messages:
                        print(f"⚠️ Пропущен дубль сообщения {message_id}")
                        continue
                    
                    # Запоминаем ID обработанного сообщения
                    if message_id:
                        processed_messages.append(message_id)
                    
                    user_id = event.user_id
                    message_text = event.text.lower().strip()
                    print(f"📩 От {user_id}: {message_text[:50]} (ID: {message_id})")
                    
                    # Проверяем состояние пользователя
                    if user_id in user_states and user_states[user_id] == "waiting_for_site_answer":
                        
                        if message_text in ["да", "+", "yes", "lf", "y", "даа", "ага", "ок", "окей"]:
                            vk.messages.send(
                                user_id=user_id,
                                message="✅ Отлично! Рады, что всё работает.\n\nЕсли понадобится помощь — просто напишите любое сообщение 😊\n\n🌐 WHITE VPN — всегда с вами!",
                                random_id=random.randint(1, 2**31)
                            )
                            del user_states[user_id]
                            
                        elif message_text in ["нет", "-", "no", "ytn", "n", "неа", "не открывается", "нет("]:
                            url_available = check_configs_url()
                            
                            if url_available:
                                # Отправляем ссылку на файл с конфигами
                                vk.messages.send(
                                    user_id=user_id,
                                    message=CONFIGS_URL,
                                    random_id=random.randint(1, 2**31)
                                )
                                time.sleep(0.5)
                                
                                # Инструкция по использованию
                                vk.messages.send(
                                    user_id=user_id,
                                    message="📱 ИНСТРУКЦИЯ:\n\n"
                                           "➖➖➖➖➖➖➖➖➖➖\n\n"
                                           "1️⃣ Скопируйте ссылку выше\n\n"
                                           "2️⃣ Вставьте её в приложение HAPP\n\n"
                                           "3️⃣ Приложение само загрузит все конфиги\n\n"
                                           "4️⃣ Выберите любой и подключитесь\n\n"
                                           "➖➖➖➖➖➖➖➖➖➖\n\n"
                                           "📲 Скачать HAPP:\n"
                                           f"{HAPP_URL}\n\n"
                                           "➖➖➖➖➖➖➖➖➖➖\n\n"
                                           "🚀 WHITE VPN — свобода в один клик!",
                                    random_id=random.randint(1, 2**31)
                                )
                            else:
                                vk.messages.send(
                                    user_id=user_id,
                                    message="❌ Ошибка: источник конфигов временно недоступен. Попробуйте позже.",
                                    random_id=random.randint(1, 2**31)
                                )
                            
                            del user_states[user_id]
                        else:
                            vk.messages.send(
                                user_id=user_id,
                                message="❓ Пожалуйста, ответьте ДА или НЕТ.\n\nОткрывается ли сайт:\nhttps://redis0n.github.io/",
                                random_id=random.randint(1, 2**31)
                            )
                        continue
                    
                    # Новый пользователь
                    vk.messages.send(
                        user_id=user_id,
                        message="🌐 WHITE VPN — ДОБРО ПОЖАЛОВАТЬ! 🌐\n\n"
                               "➖➖➖➖➖➖➖➖➖➖\n\n"
                               "🔗 ПРОВЕРЬТЕ ДОСТУП К САЙТУ:\n"
                               "https://redis0n.github.io/\n\n"
                               "➖➖➖➖➖➖➖➖➖➖\n\n"
                               "❓ САЙТ ОТКРЫВАЕТСЯ?\n"
                               "Напишите ДА или НЕТ",
                        random_id=random.randint(1, 2**31)
                    )
                    user_states[user_id] = "waiting_for_site_answer"
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
