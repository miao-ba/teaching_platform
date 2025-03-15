# apps/audio_manager/urls.py
from django.urls import path
from . import views

app_name = 'audio_manager'

urlpatterns = [
    path('upload/', views.AudioUploadView.as_view(), name='upload'),
    path('', views.AudioListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.AudioDeleteView.as_view(), name='delete'),
    # 預留音訊詳情頁面的URL，我們將在下一節實現
    path('<int:pk>/', views.AudioDetailView.as_view(), name='detail'),
]