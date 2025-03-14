# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile,UsageLog

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = '使用者配置檔'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_subscription_plan')
    
    def get_subscription_plan(self, obj):
        return obj.profile.get_subscription_plan_display()
    
    get_subscription_plan.short_description = '訂閱計劃'

# 重新註冊 User 模型
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# 註冊 UserProfile 模型
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_plan', 'created_at', 'updated_at')
    list_filter = ('subscription_plan', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    """使用日誌管理介面"""
    list_display = ('user', 'service_type', 'operation', 'tokens_used', 'audio_duration', 'created_at')
    list_filter = ('service_type', 'created_at', 'user')
    search_fields = ('user__username', 'operation', 'model_name')
    date_hierarchy = 'created_at'