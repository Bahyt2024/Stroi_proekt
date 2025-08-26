import os
import time
import webbrowser
import pyautogui
from datetime import datetime
import subprocess
import sys

def open_browser_and_screenshot():
    """
    Открывает сайт в браузере и делает скриншот всей системы
    """
    try:
        # URL сайта (замените на нужный)
        url = "http://localhost:8000"
        
        print(f"🕐 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Открываю сайт: {url}")
        
        # Открываем сайт в браузере по умолчанию
        webbrowser.open(url)
        
        # Ждем 3 секунды, чтобы сайт загрузился
        print("⏳ Ждем загрузки сайта...")
        time.sleep(3)
        
        # Делаем скриншот всей системы
        print("📸 Делаем скриншот всей системы...")
        
        # Создаем папку для скриншотов, если её нет
        screenshots_dir = "system_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        # Генерируем имя файла с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"{screenshots_dir}/system_screenshot_{timestamp}.png"
        
        # Делаем скриншот всей системы
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_filename)
        
        print(f"✅ Скриншот сохранен: {screenshot_filename}")
        print(f"🕐 Время создания скриншота: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Показываем информацию о скриншоте
        print(f"📊 Размер скриншота: {screenshot.size}")
        
        return screenshot_filename
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def open_browser_with_custom_browser(browser_name="chrome"):
    """
    Открывает сайт в указанном браузере и делает скриншот
    """
    try:
        url = "http://localhost:8000"
        
        print(f"🕐 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Открываю сайт в {browser_name}: {url}")
        
        # Команды для разных браузеров
        browser_commands = {
            "chrome": ["google-chrome", "--new-window"],
            "firefox": ["firefox", "--new-window"],
            "safari": ["open", "-a", "Safari"],
            "edge": ["msedge", "--new-window"]
        }
        
        if browser_name in browser_commands:
            cmd = browser_commands[browser_name] + [url]
            subprocess.Popen(cmd)
        else:
            # Если браузер не найден, используем браузер по умолчанию
            webbrowser.open(url)
        
        # Ждем загрузки
        print("⏳ Ждем загрузки сайта...")
        time.sleep(5)
        
        # Делаем скриншот
        print("📸 Делаем скриншот всей системы...")
        
        screenshots_dir = "system_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"{screenshots_dir}/system_screenshot_{browser_name}_{timestamp}.png"
        
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_filename)
        
        print(f"✅ Скриншот сохранен: {screenshot_filename}")
        print(f"🕐 Время создания скриншота: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return screenshot_filename
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def take_multiple_screenshots(interval=5, count=3):
    """
    Делает несколько скриншотов с интервалом
    """
    try:
        url = "http://localhost:8000"
        
        print(f"🕐 Начинаем серию скриншотов: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Открываем сайт: {url}")
        
        # Открываем сайт
        webbrowser.open(url)
        time.sleep(3)
        
        screenshots_dir = "system_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        screenshots_taken = []
        
        for i in range(count):
            print(f"📸 Скриншот {i+1}/{count}...")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"{screenshots_dir}/system_screenshot_series_{timestamp}.png"
            
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_filename)
            
            screenshots_taken.append(screenshot_filename)
            print(f"✅ Скриншот {i+1} сохранен: {screenshot_filename}")
            print(f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}")
            
            if i < count - 1:
                print(f"⏳ Ждем {interval} секунд...")
                time.sleep(interval)
        
        print(f"🎉 Все {count} скриншотов созданы!")
        return screenshots_taken
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

if __name__ == "__main__":
    print("🚀 Запуск системы скриншотов")
    print("=" * 50)
    
    # Проверяем, запущен ли сервер
    try:
        import requests
        response = requests.get("http://localhost:8000", timeout=5)
        if response.status_code == 200:
            print("✅ Сервер запущен и доступен")
        else:
            print("⚠️ Сервер отвечает, но с ошибкой")
    except:
        print("❌ Сервер не запущен. Запустите сначала main.py")
        print("💡 Команда: python main.py")
        sys.exit(1)
    
    print("\nВыберите режим:")
    print("1. Простой скриншот (браузер по умолчанию)")
    print("2. Скриншот в Chrome")
    print("3. Скриншот в Firefox")
    print("4. Серия скриншотов")
    
    try:
        choice = input("\nВведите номер (1-4) или Enter для режима 1: ").strip()
        
        if choice == "2":
            open_browser_with_custom_browser("chrome")
        elif choice == "3":
            open_browser_with_custom_browser("firefox")
        elif choice == "4":
            count = input("Количество скриншотов (по умолчанию 3): ").strip()
            count = int(count) if count.isdigit() else 3
            interval = input("Интервал в секундах (по умолчанию 5): ").strip()
            interval = int(interval) if interval.isdigit() else 5
            take_multiple_screenshots(interval, count)
        else:
            open_browser_and_screenshot()
            
    except KeyboardInterrupt:
        print("\n👋 Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
    
    print("\n🎯 Готово! Проверьте папку 'system_screenshots'") 