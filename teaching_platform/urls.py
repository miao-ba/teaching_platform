from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path,include
from .views import home, test_celery,dashboard
from django.views.generic import TemplateView
from django.views.defaults import page_not_found, server_error, permission_denied

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('accounts/', include('apps.accounts.urls')),  # 添加這一行
    path('audio/', include('apps.audio_manager.urls')),
    path('test-celery/', test_celery, name='test_celery'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path('404/', lambda request: page_not_found(request, exception=None)),
        path('500/', server_error),
        path('403/', lambda request: permission_denied(request, exception=None)),
    ]
handler404 = 'teaching_platform.views.handler404'
handler500 = 'teaching_platform.views.handler500'
handler403 = 'teaching_platform.views.handler403'