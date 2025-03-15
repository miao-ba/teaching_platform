# teaching_platform/settings/base.py
import os
from pathlib import Path

# 建立 BASE_DIR，指向專案根目錄
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 安全設定
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-change-this-in-production")

# 應用程式定義
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',  # 靜態檔案處理
    
    # 自定義應用
    'apps.accounts.apps.AccountsConfig',  # 使用完整路徑
    'apps.audio_manager.apps.AudioManagerConfig',
]

# 中間件設定
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # 靜態檔案處理
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'teaching_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'teaching_platform.wsgi.application'

# 資料庫設定 (由環境特定設定檔覆寫)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'teaching_platform'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '0000'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# 密碼驗證設定
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 國際化設定
LANGUAGE_CODE = 'zh-Hant'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# 靜態檔案設定
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static' / 'collected'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 媒體檔案設定
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 預設主鍵欄位類型
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery 設定
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'home'  # 可以修改為儀表板或其他適合的頁面

# 電子郵件設定 (開發環境)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 電子郵件內容設定
DEFAULT_FROM_EMAIL = '教學語音處理平台 <noreply@teaching-platform.example.com>'
EMAIL_SUBJECT_PREFIX = '[教學語音處理平台] '