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
import socket
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Список доступных ссылок для режима "конфиг"
CONFIG_URLS = [
    "https://translated.turbopages.org/proxy_u/ru-en.ru.518e6b1b-6a0c8606-38125922-74722d776562/https/gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/WHITE-CIDR-RU-checked.txt?ref_type=heads",
    "https://translated.turbopages.org/proxy_u/en-ru.ru.c53b472c-6a0ca721-11675f27-74722d776562/https/raw.githubusercontent.com/lm705/vair/refs/heads/main/vless_alive.txt",
    "https://translated.turbopages.org/proxy_u/en-ru.ru.c26e2dac-6a0ca8ae-663daea7-74722d776562/https/raw.githubusercontent.com/Maskkost93/kizyak-vpn-4.0/refs/heads/main/kizyakbeta6.txt",
    "https://translated.turbopages.org/proxy_u/en-ru.ru.4457a266-6a0ca8f8-0450916b-74722d776562/https/raw.githubusercontent.com/Maskkost93/kizyak-vpn-4.0/refs/heads/main/kizyaktestru.txt"
]

# JSON ссылка (обрабатывается отдельно)
JSON_URL = "https://translated.turbopages.org/proxy_u/en-ru.ru.a0d5284c-6a0ca798-0ee9aa88-74722d776562/https/raw.githubusercontent.com/tiagorrg/vless-checker/refs/heads/main/docs/keys.json"

# Ссылка для тестирования быстрых конфигов
FAST_CONFIG_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt"

user_states = {}
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

# === ФУНКЦИИ ДЛЯ РЕЖИМОВ ===

# Режим 1: Конфиг
def get_config_from_url(url):
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None

def send_long_message(vk, user_id, text, max_length=4000):
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
            vk.messages.send(
                user_id=user_id,
                message=f"📄 Часть {i}/{len(parts)}\n\n{part}",
                random_id=random.randint(1, 2**31)
            )
            time.sleep(0.5)

def handle_config_mode(vk, user_id, url_index=None):
    if url_index is None:
        # Показываем список доступных ссылок
        message = "📁 Доступные источники конфигов:\n\n"
        for i, url in enumerate(CONFIG_URLS, 1):
            message += f"{i}. Источник {i}\n"
        message += f"5. JSON источник (специальная обработка)\n\n"
        message += "Напишите номер источника (1-5) или отправьте свою ссылку"
        vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=random.randint(1, 2**31)
        )
        user_states[user_id] = "waiting_for_config_source"
        return
    
    if url_index == 5:
        # Обработка JSON
        content = get_config_from_url(JSON_URL)
        if content:
            try:
                import json
                data = json.loads(content)
                vless_urls = []
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'vless' in item:
                            vless_urls.append(item['vless'])
                        elif isinstance(item, str) and item.startswith('vless://'):
                            vless_urls.append(item)
                
                if vless_urls:
                    message = "📋 Найденные VLESS ссылки из JSON:\n\n"
                    for i, url in enumerate(vless_urls[:50], 1):
                        message += f"{i}. {url}\n\n"
                    
                    if len(vless_urls) > 50:
                        message += f"... и ещё {len(vless_urls) - 50} ссылок\n\n"
                    
                    send_long_message(vk, user_id, message)
                else:
                    vk.messages.send(
                        user_id=user_id,
                        message="❌ Не удалось найти VLESS ссылки в JSON",
                        random_id=random.randint(1, 2**31)
                    )
            except Exception as e:
                vk.messages.send(
                    user_id=user_id,
                    message=f"❌ Ошибка обработки JSON: {e}",
                    random_id=random.randint(1, 2**31)
                )
        else:
            vk.messages.send(
                user_id=user_id,
                message="❌ Не удалось загрузить JSON источник",
                random_id=random.randint(1, 2**31)
            )
    elif 1 <= url_index <= len(CONFIG_URLS):
        url = CONFIG_URLS[url_index - 1]
        vk.messages.send(
            user_id=user_id,
            message=url,
            random_id=random.randint(1, 2**31)
        )
        time.sleep(0.5)
        vk.messages.send(
            user_id=user_id,
            message="📱 Инструкция:\n\n1️⃣ Скопируйте ссылку выше\n2️⃣ Вставьте её в приложение Happ\n3️⃣ Приложение само загрузит все конфиги\n\n🚀 WHITE VPN - свобода в один клик!",
            random_id=random.randint(1, 2**31)
        )
    else:
        vk.messages.send(
            user_id=user_id,
            message="❌ Неверный номер. Попробуйте ещё раз",
            random_id=random.randint(1, 2**31)
        )

# Режим 2: Просмотр страниц через turbopages
def generate_turbopages_url(original_url, template_key="583c48c2-6a0ca2e3-ee125e71-74722d776562"):
    base = f"https://translated.turbopages.org/proxy_u/en-ru.ru.{template_key}/https/"
    clean_url = original_url.replace("https://", "").replace("http://", "")
    return base + clean_url

def handle_proxy_mode(vk, user_id):
    vk.messages.send(
        user_id=user_id,
        message="🌐 Режим просмотра страниц\n\nВведите ссылку на сайт, который нужно открыть (например, google.com или https://example.com)",
        random_id=random.randint(1, 2**31)
    )
    user_states[user_id] = "waiting_for_proxy_url"

# Режим 3: Самые быстрые конфиги
def parse_host_port(key):
    try:
        without_scheme = key[len("vless://"):]
        at_idx = without_scheme.rfind("@")
        after_at = without_scheme[at_idx + 1:]
        host_port = after_at.split("?")[0].split("#")[0]
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            return host.strip("[]"), int(port)
    except:
        pass
    return None, None

def test_key(key):
    host, port = parse_host_port(key)
    if not host:
        return {"key": key, "host": "?", "port": "?", "status": "invalid", "latency_ms": None}
    
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        elapsed = round((time.time() - start) * 1000, 1)
        
        if result == 0:
            return {"key": key, "host": host, "port": port, "status": "ok", "latency_ms": elapsed}
        else:
            return {"key": key, "host": host, "port": port, "status": "closed", "latency_ms": None}
    except:
        return {"key": key, "host": host, "port": port, "status": "error", "latency_ms": None}

def handle_fast_mode(vk, user_id):
    vk.messages.send(
        user_id=user_id,
        message="⚡ Тестирую самые быстрые конфиги...\n\n⏳ Пожалуйста, подождите 10-20 секунд",
        random_id=random.randint(1, 2**31)
    )
    
    try:
        response = requests.get(FAST_CONFIG_URL, timeout=15)
        if response.status_code != 200:
            vk.messages.send(
                user_id=user_id,
                message="❌ Не удалось загрузить конфиги для тестирования",
                random_id=random.randint(1, 2**31)
            )
            return
        
        lines = response.text.strip().splitlines()
        keys = [line.strip() for line in lines if line.strip().startswith("vless://")]
        
        if not keys:
            vk.messages.send(
                user_id=user_id,
                message="❌ Не найдено VLESS ключей",
                random_id=random.randint(1, 2**31)
            )
            return
        
        vk.messages.send(
            user_id=user_id,
            message=f"📥 Найдено {len(keys)} ключей. Начинаю тестирование...",
            random_id=random.randint(1, 2**31)
        )
        
        results = []
        MAX_WORKERS = 15
        MAX_LATENCY_MS = 2000
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(test_key, key): key for key in keys[:50]}
            done = 0
            for future in as_completed(futures):
                r = future.result()
                done += 1
                results.append(r)
        
        working = sorted(
            [r for r in results if r["status"] == "ok" and r["latency_ms"] <= MAX_LATENCY_MS],
            key=lambda x: x["latency_ms"]
        )
        
        if working:
            message = f"⚡ Найдено {len(working)} рабочих конфигов\n\n"
            message += f"🏆 ТОП-5 самых быстрых:\n\n"
            for i, r in enumerate(working[:5], 1):
                message += f"{i}. {r['host']}:{r['port']} — {r['latency_ms']} мс\n\n"
            
            message += f"🚀 Лучший конфиг:\n\n{working[0]['key']}"
            send_long_message(vk, user_id, message)
        else:
            vk.messages.send(
                user_id=user_id,
                message="😕 Рабочих конфигов не найдено. Попробуйте позже",
                random_id=random.randint(1, 2**31)
            )
            
    except Exception as e:
        vk.messages.send(
            user_id=user_id,
            message=f"❌ Ошибка: {e}",
            random_id=random.randint(1, 2**31)
        )

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
                    
                    message_id = getattr(event, 'message_id', None)
                    if message_id and message_id in processed_messages:
                        print(f"⚠️ Пропущен дубль сообщения {message_id}")
                        continue
                    
                    if message_id:
                        processed_messages.append(message_id)
                    
                    user_id = event.user_id
                    message_text = event.text.lower().strip()
                    print(f"📩 От {user_id}: {message_text[:50]}")
                    
                    # Обработка состояний
                    if user_id in user_states:
                        state = user_states[user_id]
                        
                        if state == "waiting_for_mode":
                            if message_text == "1":
                                handle_config_mode(vk, user_id)
                            elif message_text == "2":
                                handle_fast_mode(vk, user_id)
                            elif message_text == "3":
                                handle_proxy_mode(vk, user_id)
                            else:
                                vk.messages.send(
                                    user_id=user_id,
                                    message="❌ Неверный выбор. Напишите 1, 2 или 3",
                                    random_id=random.randint(1, 2**31)
                                )
                            continue
                        
                        elif state == "waiting_for_config_source":
                            if message_text.isdigit():
                                handle_config_mode(vk, user_id, int(message_text))
                            elif message_text.startswith("http"):
                                # Пользователь отправил свою ссылку
                                vk.messages.send(
                                    user_id=user_id,
                                    message=message_text,
                                    random_id=random.randint(1, 2**31)
                                )
                                time.sleep(0.5)
                                vk.messages.send(
                                    user_id=user_id,
                                    message="📱 Инструкция:\n\n1️⃣ Скопируйте ссылку выше\n2️⃣ Вставьте её в приложение Happ\n\n🚀 WHITE VPN - свобода в один клик!",
                                    random_id=random.randint(1, 2**31)
                                )
                            else:
                                vk.messages.send(
                                    user_id=user_id,
                                    message="❌ Отправьте номер источника (1-5) или ссылку",
                                    random_id=random.randint(1, 2**31)
                                )
                            del user_states[user_id]
                            continue
                        
                        elif state == "waiting_for_proxy_url":
                            if message_text.startswith("http") or "." in message_text:
                                proxy_url = generate_turbopages_url(message_text)
                                vk.messages.send(
                                    user_id=user_id,
                                    message=f"🌐 Ваша прокси-ссылка:\n\n{proxy_url}\n\n💡 Скопируйте и вставьте в браузер",
                                    random_id=random.randint(1, 2**31)
                                )
                            else:
                                vk.messages.send(
                                    user_id=user_id,
                                    message="❌ Введите корректную ссылку (например, google.com или https://example.com)",
                                    random_id=random.randint(1, 2**31)
                                )
                            del user_states[user_id]
                            continue
                    
                    # Начало диалога - показываем режимы
                    vk.messages.send(
                        user_id=user_id,
                        message="🌐 WHITE VPN - Добро пожаловать!\n\nВыберите режим работы:\n\n1️⃣ Конфиг - получить ссылку с конфигами\n\n2️⃣ Самые быстрые конфиги - тестирование и выдача лучшего\n\n3️⃣ Просмотр страниц - обход блокировок через turbopages\n\nНапишите номер режима (1, 2 или 3)",
                        random_id=random.randint(1, 2**31)
                    )
                    user_states[user_id] = "waiting_for_mode"
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
