# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from .models import UserProfile
class UserRegistrationForm(UserCreationForm):
    """使用者註冊表單，擴展了 Django 的 UserCreationForm。"""
    
    email = forms.EmailField(
        max_length=254,
        required=True,
        help_text='必填。請輸入有效的電子郵件地址。',
        label='電子郵件'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': '使用者名稱',
        }
    
    def clean_email(self):
        """驗證電子郵件是否已被使用"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('此電子郵件已被註冊，請使用其他電子郵件。')
        return email
    
    def __init__(self, *args, **kwargs):
        """自定義表單初始化，添加CSS類別"""
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs['class'] = 'form-control'

class UserLoginForm(AuthenticationForm):
    """使用者登入表單，擴展了 Django 的 AuthenticationForm"""
    
    def __init__(self, *args, **kwargs):
        """自定義表單初始化，添加 CSS 類別並修改標籤"""
        super().__init__(*args, **kwargs)
        self.fields['username'].label = '使用者名稱'
        self.fields['password'].label = '密碼'
        
        # 為所有欄位添加 Bootstrap 表單類別
        for field_name in self.fields:
            self.fields[field_name].widget.attrs['class'] = 'form-control'
            self.fields[field_name].widget.attrs['placeholder'] = self.fields[field_name].label

class CustomPasswordResetForm(PasswordResetForm):
    """自訂密碼重設表單，優化使用者體驗"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = '電子郵件'
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '請輸入您註冊時使用的電子郵件'
        })

class CustomSetPasswordForm(SetPasswordForm):
    """自訂密碼設定表單，用於重設密碼流程"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = '新密碼'
        self.fields['new_password2'].label = '確認新密碼'
        
        # 為所有欄位添加 Bootstrap 表單類別
        for field_name in self.fields:
            self.fields[field_name].widget.attrs['class'] = 'form-control'
            
class UserProfileForm(forms.ModelForm):
    """使用者配置檔編輯表單"""
    
    class Meta:
        model = UserProfile
        fields = ['subscription_plan']
        widgets = {
            'subscription_plan': forms.Select(attrs={'class': 'form-select'}),
        }
        
class UserForm(forms.ModelForm):
    """使用者資料編輯表單"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': '名字',
            'last_name': '姓氏',
            'email': '電子郵件',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        
    def clean_email(self):
        """驗證電子郵件是否已被使用"""
        email = self.cleaned_data.get('email')
        username = self.instance.username
        
        if User.objects.filter(email=email).exclude(username=username).exists():
            raise forms.ValidationError('此電子郵件已被其他帳號使用。')
        return email