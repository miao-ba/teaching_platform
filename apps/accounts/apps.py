from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'  # 修改為正確的應用路徑
    verbose_name = '使用者管理'  # 中文顯示名稱