"""
Teaching Platform 專案初始化。
"""
# 導入 Celery 配置
from .celery import app as celery_app

__all__ = ('celery_app',)