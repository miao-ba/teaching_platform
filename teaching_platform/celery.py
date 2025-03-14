"""
Celery 配置檔案。
"""
import os
from celery import Celery

# 設定 Django 設定模組
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_platform.settings')

# 建立 Celery 應用
app = Celery('teaching_platform')

# 使用 Django 設定中以 'CELERY_' 開頭的設定
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自動從所有已註冊的 Django 應用程式中發現任務
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """測試任務，用於確認 Celery 是否正常運行"""
    print(f'Request: {self.request!r}')