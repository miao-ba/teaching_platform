# apps/audio_manager/urls.py
from django.urls import path
from . import views

app_name = 'audio_manager'

urlpatterns = [
    path('upload/', views.AudioUploadView.as_view(), name='upload'),
    path('', views.AudioListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.AudioDeleteView.as_view(), name='delete'),
    path('<int:pk>/', views.AudioDetailView.as_view(), name='detail'),
    path('status/<int:pk>/', views.audio_status, name='status'),
    path('transcript/<int:transcript_id>/download/', views.download_transcript, name='download_transcript'),
    path('transcript/<int:transcript_id>/download-srt/', views.download_srt, name='download_srt'),
    path('transcript/<int:transcript_id>/download-vtt/', views.download_vtt, name='download_vtt'),
]