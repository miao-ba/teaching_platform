# utils/decorators.py
from functools import wraps
from apps.accounts.services import UsageTrackingService

def track_usage(service_type, operation=None):
    """裝飾器：記錄功能使用情況"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # 只有登入用戶才會記錄
            if request.user.is_authenticated:
                # 如果沒有提供 operation，使用視圖函數名稱
                op = operation or view_func.__name__
                
                # 記錄使用情況
                UsageTrackingService.track_usage(
                    user=request.user,
                    service_type=service_type,
                    operation=op,
                    resource_id=kwargs.get('pk') or kwargs.get('id')
                )
            
            # 正常執行視圖函數
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator