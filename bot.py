import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import requests
import time
import random

# === НАСТРОЙКИ ===
VK_TOKEN = "vk1.a.zlTzO6lNzOBYHaY-QCZIyaIb455Z0Gy3WXuRVLGR_SgsL7KwaSSTFVar-g_loULT7K6GPcBnKkrlr3sdLSK9OZ5WFJxoqrI3CzUhzu9aTdQCQbsIYpLPZ1KM8Qe_CNbpv-M1_cIQdFGf5j22oT-ZLXONIXdxq0g23S0FnJLVJ7YLD_UaEv1F3Xi4TTA9L0tfOSwLyhcOF0pUJGBbFhgmbgЫ"  # Токен сообщества
REPO_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt"

# Хранилище состояний диалога (user_id -> ожидание ответа)
user_states = {}

# === ФУНКЦИЯ ПОЛУЧЕНИЯ ВСЕХ ССЫЛОК ИЗ РЕПОЗИТОРИЯ ===
def get_all_configs():
    try:
        response = requests.get(REPO_URL, timeout=10)
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            # Фильтруем только vless ссылки
            configs = [line.strip() for line in lines if line.strip().startswith('vless://')]
            return configs
        else:
            print(f"Ошибка загрузки: {response.status_code}")
            return []
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

# === ФОРМАТИРОВАНИЕ ССЫЛОК ДЛЯ ОТПРАВКИ ===
def format_configs_message(configs):
    """Форматирует список ссылок в одно сообщение"""
    if not configs:
        return "❌ Не удалось загрузить конфиги. Попробуйте позже."
    
    # Ограничиваем количество ссылок в одном сообщении (ВК лимит ~4000 символов)
    message = "📁 *WHITE VPN — ВСЕ ДОСТУПНЫЕ КОНФИГИ:*\n\n"
    message += "🔽 Скопируйте любую ссылку и вставьте в Happ:\n\n"
    
    for i, config in enumerate(configs, 1):
        message += f"{i}. `{config}`\n\n"
    
    message += "\n✨ *Инструкция:*\n"
    message += "1. Скопируйте ссылку\n"
    message += "2. Вставьте в приложение Happ\n"
    message += "3. Наслаждайтесь свободным интернетом!\n\n"
    message += "🌐 *WHITE VPN — ваш надёжный выбор*"
    
    return message

# === ОТПРАВКА ДЛИННЫХ СООБЩЕНИЙ (с разбивкой) ===
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
                current_part = line
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
            time.sleep(0.3)  # Небольшая пауза между частями

# === ОСНОВНОЙ БОТ ===
def main():
    print("🟢 Бот WHITE VPN запущен...")
    print("Ожидание сообщений...")
    
    # Авторизация
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)
    
    # Кеш для конфигов
    cached_configs = []
    last_update = 0
    
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            message_text = event.text.lower().strip()
            print(f"📩 Сообщение от {user_id}: {message_text}")
            
            # Обновляем кеш конфигов раз в 10 минут
            if time.time() - last_update > 600 or not cached_configs:
                cached_configs = get_all_configs()
                last_update = time.time()
                print(f"📥 Загружено {len(cached_configs)} конфигов")
            
            # Проверяем состояние пользователя
            if user_id in user_states:
                state = user_states[user_id]
                
                # Пользователь ответил на вопрос про сайт
                if state == "waiting_for_site_answer":
                    if message_text in ["да", "+", "yes", "lf", "y", "даа", "ага", "ок"]:
                        # Сайт открывается - всё хорошо
                        vk.messages.send(
                            user_id=user_id,
                            message="✅ Отлично! Рады, что всё работает.\n\n" +
                                   "Если понадобится помощь — просто напишите любое сообщение 😊\n\n" +
                                   "🌐 *WHITE VPN — всегда с вами!*",
                            random_id=random.randint(1, 2**31)
                        )
                        del user_states[user_id]
                        
                    elif message_text in ["нет", "-", "no", "ytn", "n", "неа", "не открывается"]:
                        # Сайт не открывается - скидываем все ссылки
                        vk.messages.send(
                            user_id=user_id,
                            message="😔 Понял, сайт не открывается.\n\n" +
                                   "🔽 *Отправляю все доступные конфиги прямо в чат:*\n" +
                                   "Скопируйте любую ссылку и вставьте в Happ.\n" +
                                   "⏳ Подождите пару секунд, ссылки загружаются...",
                            random_id=random.randint(1, 2**31)
                        )
                        
                        time.sleep(1)
                        
                        if cached_configs:
                            configs_message = format_configs_message(cached_configs)
                            send_long_message(vk, user_id, configs_message)
                        else:
                            vk.messages.send(
                                user_id=user_id,
                                message="❌ Ошибка: не удалось загрузить конфиги. Попробуйте позже.",
                                random_id=random.randint(1, 2**31)
                            )
                        
                        del user_states[user_id]
                    else:
                        # Непонятный ответ
                        vk.messages.send(
                            user_id=user_id,
                            message="❓ Пожалуйста, ответьте «да» или «нет».\n\n" +
                                   "Открывается ли сайт https://redis0n.github.io/?",
                            random_id=random.randint(1, 2**31)
                        )
                    continue
            
            # НОВЫЙ ПОЛЬЗОВАТЕЛЬ (или обычное сообщение)
            # Сначала отправляем ссылку на сайт
            vk.messages.send(
                user_id=user_id,
                message="🌐 *WHITE VPN — Добро пожаловать!* 🌐\n\n" +
                       "🔗 *Попробуйте зайти на сайт:*\n" +
                       "👉 https://redis0n.github.io/\n\n" +
                       "❓ *Открывается ли сайт?*\n" +
                       "Напишите «да» или «нет»",
                random_id=random.randint(1, 2**31)
            )
            
            # Устанавливаем состояние ожидания ответа
            user_states[user_id] = "waiting_for_site_answer"
            print(f"⏳ Ожидаем ответ от {user_id}")

if __name__ == "__main__":
    main()