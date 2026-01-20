"""Configuration settings for the Flask application."""

import os


class Config:
    """Base configuration."""
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    
    # TrueNAS connection settings
    TRUENAS_HOST = os.environ.get('TRUENAS_HOST', 'localhost')
    TRUENAS_PORT = int(os.environ.get('TRUENAS_PORT', 443))
    TRUENAS_USE_SSL = os.environ.get('TRUENAS_USE_SSL', 'true').lower() == 'true'


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    TRUENAS_HOST = 'test.truenas.local'
    TRUENAS_PORT = 443
    TRUENAS_USE_SSL = True


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
