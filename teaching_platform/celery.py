# teaching_platform/celery.py
"""
Celery 配置檔案，針對 Windows 環境進行優化。
"""
import os
from celery import Celery
import platform

# 設定 Django 設定模組
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_platform.settings')

# 建立 Celery 應用
app = Celery('teaching_platform')

# 使用 Django 設定中以 'CELERY_' 開頭的設定
app.config_from_object('django.conf:settings', namespace='CELERY')

# Windows 專用設定
if platform.system() == 'Windows':
    # 設定任務執行池
    app.conf.task_pool = 'solo'  # 使用單進程池，避免 Windows 上的多進程問題
    
    # 設定序列化器
    app.conf.task_serializer = 'json'
    app.conf.result_serializer = 'json'
    app.conf.accept_content = ['json']
    
    # 禁用預取，避免記憶體和檔案鎖問題
    app.conf.worker_prefetch_multiplier = 1
    
    # 設定並發數為 1
    app.conf.worker_concurrency = 1
    
    # 任務確認設定
    app.conf.task_acks_late = True
    
    # 設定結果後端為文件系統或數據庫（避免使用 Redis 作為結果後端）
    # app.conf.result_backend = 'db+sqlite:///celery-results.sqlite'

# 自動從所有已註冊的 Django 應用程式中發現任務
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """測試任務，用於確認 Celery 是否正常運行"""
    print(f'Request: {self.request!r}')