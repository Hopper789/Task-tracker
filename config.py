import os

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-123'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    SQLALCHEMY_DATABASE_URI = 'postgresql://habit_user:sudo@localhost:5432/habit_tracker'
    DEBUG = True

class TestingConfig(Config):
    """Конфигурация для тестирования"""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                             'postgresql://habit_user:sudo@localhost:5432/habit_tracker'

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}