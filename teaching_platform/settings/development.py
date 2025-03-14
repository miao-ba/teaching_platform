# teaching_platform/settings/development.py
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# 開發環境特定的設定
INSTALLED_APPS += [
    'django_extensions',  # 開發輔助工具
]

# 電子郵件設定
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 日誌設定
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}