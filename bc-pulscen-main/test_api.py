import requests
import json

# Данные для запроса
data = {
    "name": "Цемент",
    "code": "1111", 
    "weight": "м3",
    "number": "3",  # Изменили с 2 на 3
    "city": "Москва",
    "monitor": "Иванов И.И."
}

# Отправляем запрос
response = requests.post(
    "http://localhost:8000/collect_offers",
    headers={"Content-Type": "application/json"},
    json=data
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}") 