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
REPO_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt"

user_states = {}

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

# === ПОЛУЧЕНИЕ ССЫЛОК ===
def get_all_configs():
    try:
        response = requests.get(REPO_URL, timeout=15)
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            configs = [line.strip() for line in lines if line.strip().startswith('vless://')]
            print(f"📥 Загружено {len(configs)} конфигов")
            return configs
        return []
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

# === ФОРМАТИРОВАНИЕ ССЫЛОК (ТОЛЬКО ССЫЛКИ, БЕЗ НУМЕРАЦИИ) ===
def format_configs_message(configs):
    """Возвращает только ссылки, каждая с новой строки, без лишнего текста"""
    if not configs:
        return ""
    
    # Просто ссылки друг под другом, без нумерации и без кавычек
    return "\n".join(configs)

# === ОТПРАВКА ДЛИННЫХ СООБЩЕНИЙ (РАЗБИВКА ПО 100 ССЫЛОК) ===
def send_configs(vk, user_id, configs):
    """Отправляет ссылки частями, чистыми сообщениями без лишнего текста"""
    if not configs:
        return
    
    # Отправляем по 100 ссылок за раз (ВК лимит ~4000 символов)
    chunk_size = 100
    for i in range(0, len(configs), chunk_size):
        chunk = configs[i:i+chunk_size]
        message = "\n".join(chunk)
        vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=random.randint(1, 2**31)
        )
        time.sleep(0.3)  # Пауза между сообщениями

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
    
    cached_configs = []
    last_update = 0
    
    print("🎯 Бот готов к работе!")
    
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    user_id = event.user_id
                    message_text = event.text.lower().strip()
                    print(f"📩 От {user_id}: {message_text[:50]}")
                    
                    # Обновляем кеш конфигов раз в 10 минут
                    if time.time() - last_update > 600 or not cached_configs:
                        cached_configs = get_all_configs()
                        last_update = time.time()
                    
                    # Проверяем состояние пользователя
                    if user_id in user_states and user_states[user_id] == "waiting_for_site_answer":
                        
                        if message_text in ["да", "+", "yes", "lf", "y", "даа", "ага", "ок", "окей"]:
                            vk.messages.send(
                                user_id=user_id,
                                message="✅ Отлично! Рады, что всё работает.\n\nЕсли понадобится помощь — просто напишите любое сообщение 😊\n\n🌐 *WHITE VPN — всегда с вами!*",
                                random_id=random.randint(1, 2**31)
                            )
                            del user_states[user_id]
                            
                        elif message_text in ["нет", "-", "no", "ytn", "n", "неа", "не открывается", "нет("]:
                            # Сначала отправляем только ссылки, без лишнего текста
                            if cached_configs:
                                send_configs(vk, user_id, cached_configs)
                                time.sleep(0.5)
                                
                                # Только после ссылок отправляем инструкцию
                                vk.messages.send(
                                    user_id=user_id,
                                    message="📱 *Как использовать:*\n\n1️⃣ Скопируйте любую ссылку выше\n2️⃣ Скачайте Happ: https://disk.yandex.ru/d/LffqUWBFbfs2Yw\n3️⃣ Вставьте ссылку в приложение\n\n🚀 *WHITE VPN — ваш надёжный выбор!*",
                                    random_id=random.randint(1, 2**31)
                                )
                            else:
                                vk.messages.send(
                                    user_id=user_id,
                                    message="❌ Ошибка: не удалось загрузить конфиги. Попробуйте позже.",
                                    random_id=random.randint(1, 2**31)
                                )
                            
                            del user_states[user_id]
                        else:
                            vk.messages.send(
                                user_id=user_id,
                                message="❓ Пожалуйста, ответьте «да» или «нет».\n\nОткрывается ли сайт https://redis0n.github.io/?",
                                random_id=random.randint(1, 2**31)
                            )
                        continue
                    
                    # Новый пользователь — отправляем приветствие
                    vk.messages.send(
                        user_id=user_id,
                        message="🌐 *WHITE VPN — Добро пожаловать!* 🌐\n\n🔗 *Попробуйте зайти на сайт:*\n👉 https://redis0n.github.io/\n\n❓ *Открывается ли сайт?*\nНапишите «да» или «нет»",
                        random_id=random.randint(1, 2**31)
                    )
                    user_states[user_id] = "waiting_for_site_answer"
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
