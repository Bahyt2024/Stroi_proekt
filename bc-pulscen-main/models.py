import json
from pydantic import BaseModel, field_validator

class ProductQuery(BaseModel):
    name: str
    code: str
    weight: str
    number: str
    city: str
    monitor: str

    @field_validator('name', 'code', 'weight', 'number', 'city', 'monitor')
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()

def read_cities():
    """Читает файл с городами и их поддоменами"""
    try:
        with open("cities.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def pulscen_get_subdomain(region_name):
    """Получает поддомен для региона"""
    cities = read_cities()
    for entry in cities:
        if entry['region'].lower() == region_name.lower():
            return entry['subdomain']
    return None 