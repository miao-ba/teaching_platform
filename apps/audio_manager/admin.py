# apps/audio_manager/admin.py
from django.contrib import admin
from .models import AudioFile

@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    """音訊檔案管理介面"""
    
    list_display = ('title', 'user', 'format', 'get_duration_display', 'get_file_size_display', 
                   'processing_status', 'created_at')
    list_filter = ('processing_status', 'format', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('format', 'duration', 'file_size', 'sample_rate', 'channels', 
                      'processing_status', 'processing_message', 'created_at', 'updated_at', 'processed_at')
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('title', 'description', 'user')
        }),
        ('檔案資訊', {
            'fields': ('file', 'format', 'duration', 'file_size', 'sample_rate', 'channels')
        }),
        ('處理狀態', {
            'fields': ('processing_status', 'processing_message', 'processing_method')
        }),
        ('時間資訊', {
            'fields': ('created_at', 'updated_at', 'processed_at')
        }),
    )