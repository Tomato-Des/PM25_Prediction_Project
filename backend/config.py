import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    EPA_API_KEY = os.getenv('EPA_API_KEY', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # Paths
    DATABASE_PATH = os.getenv('DATABASE_PATH', './data/pm25_data.db')
    MODEL_PATH = os.getenv('MODEL_PATH', './models/best_model.keras')
    
    # PM2.5 Monitoring Site
    SITE_NAME = os.getenv('SITE_NAME', '土城')
    
    # EPA API
    EPA_API_URL = 'https://data.moenv.gov.tw/api/v2/aqx_p_193'
    
    # Model Parameters
    SEQUENCE_LENGTH = 720  # 30 days * 24 hours
    PREDICTION_HOURS = 24
    
    # Timezone
    TIMEZONE = os.getenv('TZ', 'Asia/Taipei')
    
    # Port
    PORT = int(os.getenv('PORT', 5000))