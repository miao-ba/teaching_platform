from django.apps import AppConfig

class AudioManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audio_manager'  # 正確的完整路徑
    verbose_name = '音訊管理'
    label = 'audio_manager'  # 添加這一行，指定簡短標籤