# apps/audio_manager/views.py
from django.shortcuts import render, redirect
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count
from django.views.generic import ListView
from django.db.models import Q
from .models import AudioFile
from .forms import AudioUploadForm
#from core.payment.quota import QuotaManager, ServiceType
from django.views.generic import DeleteView
from django.views.generic import DetailView
class AudioUploadView(LoginRequiredMixin, CreateView):
    """音訊上傳視圖"""
    model = AudioFile
    form_class = AudioUploadForm
    template_name = 'audio_manager/upload.html'
    success_url = reverse_lazy('audio_manager:list')
    
    def get_form_kwargs(self):
        """將當前使用者傳入表單"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        # 獲取使用者已上傳的音訊數量，用於顯示配額
        context['user_audio_count'] = AudioFile.objects.filter(
            user=self.request.user
        ).count()
        
        # 暫時硬編碼配額資訊，後續將從使用者設定檔獲取
        context['audio_quota'] = 10  # 假設免費用戶每月可上傳10個檔案
        context['audio_used'] = context['user_audio_count']
        
        return context
    
    def form_valid(self, form):
        """表單驗證成功後的處理"""
        # 檢查使用者配額 (簡化版，不使用QuotaManager)
        user_audio_count = AudioFile.objects.filter(user=self.request.user).count()
        max_audio_count = 10  # 假設免費用戶最多可上傳10個檔案
        
        if self.request.user.profile.subscription_plan == 'free' and user_audio_count >= max_audio_count:
            messages.error(self.request, f'免費帳戶最多只能上傳 {max_audio_count} 個音訊檔案，請升級您的帳戶。')
            return self.form_invalid(form)
        
        # 保存音訊檔案
        self.object = form.save()
        
        # 後續將添加異步處理任務
        # from .tasks import process_audio_file
        # process_audio_file.delay(self.object.id)
        
        messages.success(
            self.request, 
            f'音訊檔案「{self.object.title}」上傳成功，正在處理中，請稍後查看結果。'
        )
        return super().form_valid(form)
class AudioListView(LoginRequiredMixin, ListView):
    """音訊列表視圖"""
    model = AudioFile
    template_name = 'audio_manager/list.html'
    context_object_name = 'audio_files'
    paginate_by = 10
    
    def get_queryset(self):
        """根據查詢參數過濾音訊檔案"""
        queryset = AudioFile.objects.filter(user=self.request.user)
        
        # 搜尋功能
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # 狀態過濾
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(processing_status=status_filter)
        
        # 日期過濾
        date_filter = self.request.GET.get('date')
        if date_filter == 'today':
            from django.utils import timezone
            today = timezone.now().date()
            queryset = queryset.filter(created_at__date=today)
        elif date_filter == 'week':
            from django.utils import timezone
            import datetime
            start_of_week = timezone.now().date() - datetime.timedelta(days=7)
            queryset = queryset.filter(created_at__date__gte=start_of_week)
        elif date_filter == 'month':
            from django.utils import timezone
            import datetime
            start_of_month = timezone.now().date() - datetime.timedelta(days=30)
            queryset = queryset.filter(created_at__date__gte=start_of_month)
        
        # 排序
        sort_by = self.request.GET.get('sort_by', '-created_at')
        valid_sort_fields = ['title', '-title', 'created_at', '-created_at', 
                            'duration', '-duration', 'processing_status', '-processing_status']
        
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-created_at')  # 預設按建立時間降序排列
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 添加當前篩選和排序參數，用於維持分頁時的查詢條件
        context['current_query'] = self.request.GET.copy()
        if 'page' in context['current_query']:
            del context['current_query']['page']
        
        # 添加排序和篩選選項
        context['sort_options'] = [
            {'value': '-created_at', 'label': '最新上傳', 'selected': self.request.GET.get('sort_by') == '-created_at'},
            {'value': 'created_at', 'label': '最舊上傳', 'selected': self.request.GET.get('sort_by') == 'created_at'},
            {'value': 'title', 'label': '標題 A-Z', 'selected': self.request.GET.get('sort_by') == 'title'},
            {'value': '-title', 'label': '標題 Z-A', 'selected': self.request.GET.get('sort_by') == '-title'},
            {'value': 'duration', 'label': '時長 (短到長)', 'selected': self.request.GET.get('sort_by') == 'duration'},
            {'value': '-duration', 'label': '時長 (長到短)', 'selected': self.request.GET.get('sort_by') == '-duration'},
        ]
        
        context['status_options'] = [
            {'value': 'all', 'label': '全部狀態', 'selected': self.request.GET.get('status') == 'all' or not self.request.GET.get('status')},
            {'value': 'pending', 'label': '等待處理', 'selected': self.request.GET.get('status') == 'pending'},
            {'value': 'processing', 'label': '處理中', 'selected': self.request.GET.get('status') == 'processing'},
            {'value': 'completed', 'label': '已完成', 'selected': self.request.GET.get('status') == 'completed'},
            {'value': 'failed', 'label': '處理失敗', 'selected': self.request.GET.get('status') == 'failed'},
        ]
        
        context['date_options'] = [
            {'value': 'all', 'label': '全部時間', 'selected': self.request.GET.get('date') == 'all' or not self.request.GET.get('date')},
            {'value': 'today', 'label': '今天', 'selected': self.request.GET.get('date') == 'today'},
            {'value': 'week', 'label': '過去一週', 'selected': self.request.GET.get('date') == 'week'},
            {'value': 'month', 'label': '過去一個月', 'selected': self.request.GET.get('date') == 'month'},
        ]
        
        # 記住搜尋查詢
        context['search_query'] = self.request.GET.get('q', '')
        
        # 添加統計資訊
        context['total_files'] = AudioFile.objects.filter(user=self.request.user).count()
        context['completed_files'] = AudioFile.objects.filter(user=self.request.user, processing_status='completed').count()
        context['processing_files'] = AudioFile.objects.filter(user=self.request.user, processing_status__in=['pending', 'processing']).count()
        
        return context

class AudioDeleteView(LoginRequiredMixin, DeleteView):
    """音訊刪除視圖"""
    model = AudioFile
    success_url = reverse_lazy('audio_manager:list')
    
    def get_queryset(self):
        """確保只能刪除自己的音訊檔案"""
        return AudioFile.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """自定義刪除邏輯，添加成功訊息"""
        audio = self.get_object()
        title = audio.title
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'音訊「{title}」已成功刪除。')
        return response
    
    # 如需防止直接GET請求刪除，可取消下方註解
    # def get(self, request, *args, **kwargs):
    #     return self.post(request, *args, **kwargs)
class AudioDetailView(LoginRequiredMixin, DetailView):
    """音訊詳情視圖"""
    model = AudioFile
    template_name = 'audio_manager/detail.html'
    context_object_name = 'audio_file'
    
    def get_queryset(self):
        """確保只能查看自己的音訊檔案"""
        return AudioFile.objects.filter(user=self.request.user)

class AudioDetailView(LoginRequiredMixin, DetailView):
    """音訊詳情視圖"""
    model = AudioFile
    template_name = 'audio_manager/detail.html'
    context_object_name = 'audio_file'
    
    def get_queryset(self):
        """確保只能查看自己的音訊檔案"""
        return AudioFile.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        """獲取上下文資料，添加相關資訊"""
        context = super().get_context_data(**kwargs)
        audio_file = self.get_object()
        
        # 未來將添加轉錄相關資訊
        # if hasattr(audio_file, "transcript"):
        #     context["transcript"] = audio_file.transcript
        #     context["segments"] = audio_file.transcript.segments.all().order_by("start_time")
        
        # 未來將添加內容生成相關資訊
        # if hasattr(audio_file, "transcript") and hasattr(audio_file.transcript, "summary"):
        #     context["summary"] = audio_file.transcript.summary
        
        # 添加處理狀態的CSS類別映射
        context['status_classes'] = {
            'pending': 'warning',
            'processing': 'info',
            'completed': 'success',
            'failed': 'danger'
        }
        
        return context