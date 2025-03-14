# apps/accounts/models.py
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """使用者配置檔"""
    
    SUBSCRIPTION_CHOICES = [
        ("free", "免費版"),
        ("basic", "基礎版"),
        ("premium", "進階版"),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="profile"
    )
    subscription_plan = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_CHOICES,
        default="free",
        verbose_name="訂閱計劃"
    )
    monthly_quota = models.JSONField(
        default=dict,
        help_text="每月使用配額",
        verbose_name="月度配額"
    )
    used_quota = models.JSONField(
        default=dict,
        help_text="已使用配額",
        verbose_name="已用配額"
    )
    api_key = models.CharField(
        max_length=100, 
        blank=True,
        help_text="API 金鑰",
        verbose_name="API金鑰"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "使用者配置檔"
        verbose_name_plural = "使用者配置檔"
        
    def __str__(self):
        return f"{self.user.username} 的配置檔"
    
    def get_available_quota(self, service_type):
        """獲取特定服務的可用配額"""
        monthly = self.monthly_quota.get(service_type, 0)
        used = self.used_quota.get(service_type, 0)
        
        if monthly < 0:  # 負值表示無限制
            return float('inf')
        
        return max(0, monthly - used)
    
    def reset_monthly_quota(self):
        """重置已使用配額（每月自動執行）"""
        self.used_quota = {}
        self.save()
    def update_usage_quota(self, service_type, amount=1):
        """更新指定服務類型的使用配額"""
        if service_type not in self.used_quota:
            self.used_quota[service_type] = 0
        
        self.used_quota[service_type] += amount
        self.save()
        
        # 檢查是否超出配額
        if service_type in self.monthly_quota:
            limit = self.monthly_quota[service_type]
            # 負值表示無限制
            if limit >= 0 and self.used_quota[service_type] >= limit:
                return False
        
        return True


# 使用信號確保在使用者創建時同時創建配置檔
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """當使用者被創建時，自動創建對應的配置檔"""
    if created:
        # 設定預設配額
        default_quotas = {
            "free": {
                "audio_transcription": 5,
                "speaker_identification": 5,
                "summary_generation": 5,
                "content_generation": 2,
                "rag_search": 10
            }
        }
        
        UserProfile.objects.create(
            user=instance,
            subscription_plan="free",
            monthly_quota=default_quotas["free"],
            used_quota={}
        )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """當使用者被保存時，同時保存對應的配置檔"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
class UsageLog(models.Model):
    """使用日誌模型，記錄使用者對系統資源的使用情況"""
    
    SERVICE_TYPES = [
        ('audio_transcription', '音訊轉錄'),
        ('speaker_identification', '講者辨識'),
        ('summary_generation', '摘要生成'),
        ('content_generation', '內容生成'),
        ('rag_search', '知識檢索')
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="usage_logs",
        verbose_name="使用者"
    )
    service_type = models.CharField(
        max_length=50,
        choices=SERVICE_TYPES,
        verbose_name="服務類型"
    )
    operation = models.CharField(
        max_length=100,
        verbose_name="操作描述"
    )
    resource_id = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="資源 ID"
    )
    tokens_used = models.IntegerField(
        default=0,
        verbose_name="使用 Token 數量"
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="模型名稱"
    )
    audio_duration = models.FloatField(
        null=True, 
        blank=True,
        verbose_name="音訊時長(秒)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="建立時間"
    )
    
    class Meta:
        verbose_name = "使用日誌"
        verbose_name_plural = "使用日誌"
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"{self.user.username} - {self.get_service_type_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    @classmethod
    def log_usage(cls, user, service_type, operation, **kwargs):
        """記錄使用情況的便捷方法"""
        return cls.objects.create(
            user=user,
            service_type=service_type,
            operation=operation,
            resource_id=kwargs.get('resource_id'),
            tokens_used=kwargs.get('tokens_used', 0),
            model_name=kwargs.get('model_name', ''),
            audio_duration=kwargs.get('audio_duration')
        )
    
    @classmethod
    def get_user_usage(cls, user, service_type=None, days=30):
        """取得使用者在指定時間範圍內的使用情況"""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        
        # 基本查詢：按使用者和時間過濾
        query = cls.objects.filter(user=user, created_at__gte=start_date)
        
        # 如果指定了服務類型，進一步過濾
        if service_type:
            query = query.filter(service_type=service_type)
            
        return query