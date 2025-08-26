#!/usr/bin/env python3
"""
Тестовый файл для проверки скриншот системы
"""

import pyautogui
import time
from datetime import datetime
import os

def test_screenshot():
    """Тестирует создание скриншота"""
    try:
        print("🧪 Тестирую скриншот систему...")
        
        # Создаем папку для скриншотов
        screenshots_dir = "system_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        # Делаем тестовый скриншот
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{screenshots_dir}/test_screenshot_{timestamp}.png"
        
        print(f"📸 Создаю тестовый скриншот: {filename}")
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        
        print(f"✅ Тестовый скриншот создан: {filename}")
        print(f"📊 Размер: {screenshot.size}")
        print(f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Тест скриншот системы")
    print("=" * 30)
    
    success = test_screenshot()
    
    if success:
        print("\n🎯 Тест прошел успешно!")
    else:
        print("\n❌ Тест не прошел") 