# apps/audio_manager/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import os
from datetime import timedelta

class AudioFile(models.Model):
    """音訊檔案模型，用於儲存和管理使用者上傳的課堂錄音"""
    
    PROCESSING_STATUS_CHOICES = [
        ('pending', '等待處理'),
        ('processing', '處理中'),
        ('completed', '已完成'),
        ('failed', '處理失敗'),
    ]
    
    # 基本資訊
    title = models.CharField(
        max_length=255, 
        verbose_name=_('標題'),
        help_text=_('音訊檔案的標題或名稱')
    )
    description = models.TextField(
        blank=True, 
        verbose_name=_('描述'),
        help_text=_('音訊檔案的簡要描述（選填）')
    )
    
    # 檔案資訊
    file = models.FileField(
        upload_to='audio_files/%Y/%m/',
        verbose_name=_('音訊檔案'),
        help_text=_('支援的格式：MP3, WAV, OGG, M4A, FLAC')
    )
    format = models.CharField(
        max_length=10, 
        blank=True, 
        verbose_name=_('檔案格式')
    )
    duration = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name=_('時長（秒）')
    )
    file_size = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name=_('檔案大小（位元組）')
    )
    sample_rate = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name=_('採樣率 (Hz)')
    )
    channels = models.PositiveSmallIntegerField(
        null=True, 
        blank=True, 
        verbose_name=_('聲道數')
    )
    
    # 處理狀態
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending',
        verbose_name=_('處理狀態')
    )
    processing_message = models.TextField(
        blank=True, 
        verbose_name=_('處理訊息')
    )
    processing_method = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name=_('處理方法'),
        help_text=_('使用的轉錄引擎或模型')
    )
    
    # 關聯
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='audio_files',
        verbose_name=_('使用者')
    )
    
    # 時間記錄
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_('建立時間')
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('更新時間')
    )
    processed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name=_('處理完成時間')
    )
    
    class Meta:
        verbose_name = _('音訊檔案')
        verbose_name_plural = _('音訊檔案')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_duration_display(self):
        """顯示格式化的持續時間"""
        if not self.duration:
            return "00:00:00"
        
        td = timedelta(seconds=self.duration)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_file_size_display(self):
        """顯示人類可讀的檔案大小"""
        if not self.file_size:
            return "未知"
        
        # 轉換為 KB, MB, GB 等
        units = ['B', 'KB', 'MB', 'GB']
        size = float(self.file_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
    
    def get_file_extension(self):
        """獲取檔案副檔名"""
        _, ext = os.path.splitext(self.file.name)
        return ext.lstrip('.').lower()
    
    def update_metadata(self, duration=None, sample_rate=None, channels=None, format=None, file_size=None):
        """更新音訊檔案的元數據"""
        if duration is not None:
            self.duration = duration
        if sample_rate is not None:
            self.sample_rate = sample_rate
        if channels is not None:
            self.channels = channels
        if format is not None:
            self.format = format
        if file_size is not None:
            self.file_size = file_size
        
        self.save(update_fields=['duration', 'sample_rate', 'channels', 'format', 'file_size', 'updated_at'])
    
    def set_processing_status(self, status, message=""):
        """更新處理狀態和相關訊息"""
        self.processing_status = status
        if message:
            self.processing_message = message
        
        # 如果處理完成，設定處理時間
        if status == 'completed':
            from django.utils import timezone
            self.processed_at = timezone.now()
        
        self.save(update_fields=['processing_status', 'processing_message', 'processed_at', 'updated_at'])