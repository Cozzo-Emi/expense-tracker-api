import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("No se encontró DATABASE_URL en el archivo .env")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Agregamos la configuración de JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')