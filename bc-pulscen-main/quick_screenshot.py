#!/usr/bin/env python3
"""
Быстрый скрипт для создания скриншота системы
"""

import os
import time
import webbrowser
import pyautogui
from datetime import datetime

def quick_screenshot():
    """Быстро создает скриншот системы"""
    
    # URL сайта
    url = "http://localhost:8000"
    
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Запуск скриншота")
    
    try:
        # Открываем сайт в браузере
        print(f"🌐 Открываю {url}")
        webbrowser.open(url)
        
        # Ждем загрузки
        print("⏳ Ждем загрузки...")
        time.sleep(4)
        
        # Создаем папку для скриншотов
        screenshots_dir = "system_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        # Делаем скриншот
        print("📸 Делаем скриншот...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{screenshots_dir}/quick_screenshot_{timestamp}.png"
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        
        print(f"✅ Скриншот сохранен: {filename}")
        print(f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}")
        print(f"📊 Размер: {screenshot.size}")
        
        return filename
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Быстрый скриншот системы")
    print("=" * 30)
    
    result = quick_screenshot()
    
    if result:
        print(f"\n🎯 Готово! Файл: {result}")
    else:
        print("\n❌ Не удалось создать скриншот") 