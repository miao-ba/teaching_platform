# apps/accounts/services.py
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from .models import UsageLog

class UsageTrackingService:
    """使用追蹤服務類，提供使用統計與分析功能"""
    
    @staticmethod
    def track_usage(user, service_type, operation, **kwargs):
        """記錄使用情況並更新使用者配額"""
        # 記錄使用日誌
        usage_log = UsageLog.log_usage(user, service_type, operation, **kwargs)
        
        # 根據服務類型決定要增加的量
        amount = 1
        if service_type == 'audio_transcription' and kwargs.get('audio_duration'):
            # 對於音訊轉錄，使用時長作為量
            amount = kwargs.get('audio_duration') / 60  # 轉換為分鐘
        elif kwargs.get('tokens_used'):
            # 如果提供了 tokens_used，使用它
            amount = kwargs.get('tokens_used')
            
        # 更新使用者配額
        profile = user.profile
        quota_status = profile.update_usage_quota(service_type, amount)
        
        return usage_log, quota_status
    
    @staticmethod
    def get_usage_summary(user, days=30):
        """獲取使用者的使用摘要"""
        start_date = timezone.now() - timedelta(days=days)
        
        # 按服務類型分組的使用次數
        service_counts = UsageLog.objects.filter(
            user=user, 
            created_at__gte=start_date
        ).values('service_type').annotate(
            count=Count('id')
        ).order_by('service_type')
        
        # 按服務類型分組的 Token 使用量
        token_usage = UsageLog.objects.filter(
            user=user, 
            created_at__gte=start_date
        ).values('service_type').annotate(
            total_tokens=Sum('tokens_used')
        ).order_by('service_type')
        
        # 按服務類型分組的音訊時長
        audio_duration = UsageLog.objects.filter(
            user=user, 
            created_at__gte=start_date,
            audio_duration__isnull=False
        ).values('service_type').annotate(
            total_duration=Sum('audio_duration')
        ).order_by('service_type')
        
        # 最近的使用記錄
        recent_logs = UsageLog.objects.filter(
            user=user
        ).order_by('-created_at')[:10]
        
        return {
            'service_counts': service_counts,
            'token_usage': token_usage,
            'audio_duration': audio_duration,
            'recent_logs': recent_logs
        }
    
    @staticmethod
    def get_daily_usage(user, service_type=None, days=30):
        """獲取使用者的每日使用情況"""
        from django.db.models.functions import TruncDate
        
        start_date = timezone.now() - timedelta(days=days)
        
        # 基本查詢
        query = UsageLog.objects.filter(user=user, created_at__gte=start_date)
        
        # 如果指定了服務類型，進一步過濾
        if service_type:
            query = query.filter(service_type=service_type)
            
        # 按日期分組統計
        daily_counts = query.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return daily_counts