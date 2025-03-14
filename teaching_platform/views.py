# teaching_platform/views.py
from django.shortcuts import render
from django.http import HttpResponse
from .celery import debug_task

def home(request):
    return render(request, "home.html")

def test_celery(request):
    """執行測試任務並返回確認訊息"""
    task = debug_task.delay()
    return HttpResponse(f"Celery 測試任務已啟動。任務 ID: {task.id}")
def handler404(request, exception=None):
    """自定義 404 錯誤處理器"""
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """自定義 500 錯誤處理器"""
    return render(request, 'errors/500.html', status=500)

def handler403(request, exception=None):
    """自定義 403 錯誤處理器"""
    return render(request, 'errors/permission_denied.html', status=403)