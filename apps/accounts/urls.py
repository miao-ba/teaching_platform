# apps/accounts/urls.py
from django.urls import path
from . import views
from django.http import HttpResponse

app_name = 'accounts'

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.user_logout, name='logout'),
    # 密碼重設路徑
    path('password-reset/', 
         views.CustomPasswordResetView.as_view(), 
         name='password_reset'),
    
    path('password-reset/done/', 
         views.CustomPasswordResetDoneView.as_view(), 
         name='password_reset_done'),
    
    path('password-reset/<uidb64>/<token>/', 
         views.CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    
    path('password-reset/complete/', 
         views.CustomPasswordResetCompleteView.as_view(), 
         name='password_reset_complete'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('usage-statistics/', views.usage_statistics, name='usage_statistics'),
]