# teaching_platform/views.py
from django.shortcuts import render,redirect
from django.http import HttpResponse
from .celery import debug_task
from django.contrib.auth.decorators import login_required

def home(request):
    """網站首頁視圖
    未登入用戶顯示歡迎頁面，已登入用戶重定向到儀表板
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "home.html")

@login_required
def dashboard(request):
    """儀表板首頁視圖
    只有登入用戶可以訪問
    """
    # 獲取用戶統計數據
    context = {
        'audio_count': 0,  # 獲取實際數據
        'audio_duration': 0,  # 獲取實際數據
        'content_count': 0,  # 獲取實際數據
        'quota_remaining': 75,  # 獲取實際數據
        'recent_activities': []  # 從用戶日誌獲取實際數據
    }
    return render(request, "dashboard/home.html", context)

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