#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы pyautogui
"""

import pyautogui
import time
import os

def test_pyautogui():
    """Тестирует функциональность pyautogui"""
    print("Тестирование pyautogui...")
    
    try:
        # Получаем размер экрана
        screen_width, screen_height = pyautogui.size()
        print(f"Размер экрана: {screen_width}x{screen_height}")
        
        # Получаем текущую позицию мыши
        mouse_x, mouse_y = pyautogui.position()
        print(f"Позиция мыши: {mouse_x}, {mouse_y}")
        
        # Делаем тестовый скриншот
        print("Создание тестового скриншота...")
        screenshot = pyautogui.screenshot()
        
        # Сохраняем скриншот
        test_path = "test_screenshot.png"
        screenshot.save(test_path)
        
        if os.path.exists(test_path):
            file_size = os.path.getsize(test_path)
            print(f"✅ Скриншот создан успешно: {test_path}")
            print(f"   Размер файла: {file_size} байт")
            
            # Удаляем тестовый файл
            os.remove(test_path)
            print("   Тестовый файл удален")
        else:
            print("❌ Ошибка: файл не создан")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании pyautogui: {e}")
        return False
    
    print("✅ Тест pyautogui завершен успешно!")
    return True

if __name__ == "__main__":
    test_pyautogui() 