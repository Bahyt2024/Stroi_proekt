# Используем официальный Python образ
FROM python:3.11-slim-bookworm

# Устанавливаем системные зависимости для Playwright и Tesseract
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    xvfb \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы требований
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Playwright и браузеры автоматически
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

# Копируем исходный код приложения
COPY . .

# Создаем необходимые директории
RUN mkdir -p output json

# Открываем порт
EXPOSE 8000

# Запускаем виртуальный дисплей для pyautogui и uvicorn с proxy-headers для туннелей
CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x24 & python -m uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --timeout-keep-alive 300"]