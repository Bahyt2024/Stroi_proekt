#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы браузера с уменьшенным размером окна
"""

import asyncio
from playwright.async_api import async_playwright
import pyautogui
import time
import os

async def test_browser_window():
    """Тестирует запуск браузера с уменьшенным размером окна"""
    print("Тестирование браузера с уменьшенным размером окна...")
    
    try:
        async with async_playwright() as p:
            print("Запуск браузера...")
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--window-size=1600,900',
                    '--window-position=0,0'
                ]
            )
            print("Браузер запущен успешно!")
            
            # Позиционируем окно браузера
            try:
                import subprocess
                subprocess.run(['osascript', '-e', 'tell application "System Events" to set position of first window of application process "Chromium" to {0, 0}'], 
                             capture_output=True, check=False)
                print("Окно браузера позиционировано")
            except Exception as e:
                print(f"Не удалось позиционировать окно: {e}")
            
            context = await browser.new_context(
                viewport={"width": 1600, "height": 900}
            )
            
            page = await context.new_page()
            await page.goto("https://www.google.com")
            print("Открыта страница Google")
            
            # Ждем стабилизации
            await asyncio.sleep(3)
            
            # Делаем скриншот
            print("Создание скриншота...")
            screenshot = pyautogui.screenshot()
            test_path = "test_browser_window.png"
            screenshot.save(test_path)
            
            if os.path.exists(test_path):
                file_size = os.path.getsize(test_path)
                print(f"✅ Скриншот создан: {test_path}")
                print(f"   Размер файла: {file_size} байт")
                
                # Удаляем тестовый файл
                os.remove(test_path)
                print("   Тестовый файл удален")
            else:
                print("❌ Ошибка: файл не создан")
            
            # Закрываем браузер
            await browser.close()
            print("Браузер закрыт")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False
    
    print("✅ Тест завершен успешно!")
    return True

if __name__ == "__main__":
    asyncio.run(test_browser_window()) 