import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_jwt_secret")
    
    # PostgreSQL 連線參數
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "medpulse_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

    # ⚡ Redis 連線參數
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    DB_REDIS = int(os.getenv("DB_REDIS", 0))

    # Flask-Mail / SMTP 郵件伺服器設定
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'your_gmail_address@gmail.com') 
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'your_16_digit_app_password') 
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_USERNAME', 'your_gmail_address@gmail.com')