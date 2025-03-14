# teaching_platform/settings/__init__.py
import os

# 預設使用開發環境設定
if os.environ.get("DJANGO_ENVIRONMENT") == "production":
    from .production import *
else:
    from .development import *