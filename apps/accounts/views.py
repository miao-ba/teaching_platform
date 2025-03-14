# apps/accounts/views.py
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegistrationForm
from .forms import UserLoginForm
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from .forms import CustomPasswordResetForm, CustomSetPasswordForm
from .models import UserProfile
from .forms import UserForm, UserProfileForm
from .services import UsageTrackingService

class UserRegistrationView(CreateView):
    """使用者註冊視圖"""
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        """表單驗證成功時的處理"""
        user = form.save()
        login(self.request, user)
        messages.success(self.request, '註冊成功！歡迎加入教學語音處理平台。')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, '註冊失敗，請檢查表單內容並修正錯誤。')
        return super().form_invalid(form)
class UserLoginView(LoginView):
    """使用者登入視圖"""
    form_class = UserLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """登入成功後的跳轉 URL"""
        return reverse_lazy('home')  # 可以修改為儀表板或其他適合的頁面
    
    def form_valid(self, form):
        """登入成功的處理"""
        messages.success(self.request, f'歡迎回來，{form.get_user().username}！')
        return super().form_valid(form)
        
    def form_invalid(self, form):
        """登入失敗的處理"""
        messages.error(self.request, '登入失敗，請確認使用者名稱和密碼是否正確。')
        return super().form_invalid(form)
@login_required
def user_logout(request):
    """使用者登出視圖"""
    username = request.user.username
    logout(request)
    messages.success(request, f'{username}，您已成功登出系統。')
    return redirect('home')
class CustomPasswordResetView(PasswordResetView):
    """密碼重設請求視圖"""
    template_name = 'accounts/password_reset.html'
    form_class = CustomPasswordResetForm
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    """密碼重設請求完成視圖"""
    template_name = 'accounts/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """密碼重設確認視圖"""
    template_name = 'accounts/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('accounts:password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """密碼重設完成視圖"""
    template_name = 'accounts/password_reset_complete.html'
class ProfileView(LoginRequiredMixin, UpdateView):
    """使用者配置檔視圖"""
    template_name = 'accounts/profile.html'
    model = UserProfile
    form_class = UserProfileForm
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self, queryset=None):
        """獲取要編輯的物件"""
        return self.request.user.profile
    
    def get_context_data(self, **kwargs):
        """獲取上下文資料"""
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['user_form'] = UserForm(self.request.POST, instance=self.request.user)
        else:
            context['user_form'] = UserForm(instance=self.request.user)
            
        # 添加使用配額資訊
        profile = self.request.user.profile
        context['monthly_quota'] = profile.monthly_quota
        context['used_quota'] = profile.used_quota
        
        # 計算配額使用百分比
        quota_percentages = {}
        for service, limit in profile.monthly_quota.items():
            used = profile.used_quota.get(service, 0)
            if limit <= 0:  # 無限制
                percentage = 0
            else:
                percentage = min(100, int((used / limit) * 100))
            quota_percentages[service] = percentage
        
        context['quota_percentages'] = quota_percentages
        return context
    
    def form_valid(self, form):
        """表單驗證成功的處理"""
        context = self.get_context_data()
        user_form = context['user_form']
        
        if user_form.is_valid():
            user_form.save()
            form.save()
            messages.success(self.request, '個人資料已成功更新！')
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))
        
@login_required
def usage_statistics(request):
    """顯示使用者的使用統計頁面"""
    # 獲取天數參數，預設為 30 天
    days = int(request.GET.get('days', 30))
    
    # 獲取使用摘要
    usage_summary = UsageTrackingService.get_usage_summary(request.user, days)
    
    # 獲取每日使用情況
    daily_usage = UsageTrackingService.get_daily_usage(request.user, days=days)
    
    context = {
        'usage_summary': usage_summary,
        'daily_usage': daily_usage,
        'days': days
    }
    
    return render(request, 'accounts/usage_statistics.html', context)