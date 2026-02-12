import os

class Config:
    API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'web-secret-key')