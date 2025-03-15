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
from .forms import AudioUploadForm,AudioSearchForm
#from core.payment.quota import QuotaManager, ServiceType
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.http import JsonResponse
from django.utils import timezone
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
        
        # 啟動異步處理任務
        from .tasks import process_audio_file
        process_audio_file.delay(self.object.id)
        
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
        queryset = AudioFile.objects.filter(user=self.request.user)
        
        # 初始化搜尋表單
        form = AudioSearchForm(self.request.GET or None)
        if form.is_valid():
            queryset = form.filter_queryset(queryset)
        else:
            # 預設排序：最新上傳
            queryset = queryset.order_by('-created_at')
        
        self.form = form  # 儲存表單實例以供在 get_context_data 中使用
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = getattr(self, 'form', AudioSearchForm())
        context['current_query'] = self.request.GET.copy()
        
        if 'page' in context['current_query']:
            del context['current_query']['page']
            
        # 計算統計數據
        context['total_files'] = AudioFile.objects.filter(user=self.request.user).count()
        context['completed_files'] = AudioFile.objects.filter(
            user=self.request.user, 
            processing_status='completed'
        ).count()
        context['processing_files'] = AudioFile.objects.filter(
            user=self.request.user, 
            processing_status__in=['pending', 'processing']
        ).count()
        
        # 為模板準備下拉選單選項
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
            {'value': 'custom', 'label': '自訂日期範圍', 'selected': self.request.GET.get('date') == 'custom'},
        ]
        
        context['sort_options'] = [
            {'value': '-created_at', 'label': '最新上傳', 'selected': self.request.GET.get('sort_by') == '-created_at' or not self.request.GET.get('sort_by')},
            {'value': 'created_at', 'label': '最舊上傳', 'selected': self.request.GET.get('sort_by') == 'created_at'},
            {'value': 'title', 'label': '標題 A-Z', 'selected': self.request.GET.get('sort_by') == 'title'},
            {'value': '-title', 'label': '標題 Z-A', 'selected': self.request.GET.get('sort_by') == '-title'},
            {'value': 'duration', 'label': '時長 (短到長)', 'selected': self.request.GET.get('sort_by') == 'duration'},
            {'value': '-duration', 'label': '時長 (長到短)', 'selected': self.request.GET.get('sort_by') == '-duration'},
        ]
        
        context['search_query'] = self.request.GET.get('q', '')
        context['show_custom_date'] = self.request.GET.get('date') == 'custom'
        
        return context

class AudioDeleteView(LoginRequiredMixin, DeleteView):
    """音訊刪除視圖"""
    model = AudioFile
    success_url = reverse_lazy('audio_manager:list')
    
    def get_queryset(self):
        """確保只能刪除自己的音訊檔案"""
        return AudioFile.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """刪除音訊檔案並返回成功訊息"""
        try:
            audio = self.get_object()
            title = audio.title
            
            # 執行刪除操作
            result = super().delete(request, *args, **kwargs)
            
            # 添加成功訊息
            messages.success(request, f'音訊「{title}」已成功刪除。')
            return result
            
        except Exception as e:
            # 記錄錯誤並返回錯誤訊息
            messages.error(request, f'刪除失敗：{str(e)}')
            return redirect('audio_manager:list')
    
    # 對於直接的 GET 請求，重定向到列表頁面
    def get(self, request, *args, **kwargs):
        return redirect('audio_manager:list')

class AudioDetailView(LoginRequiredMixin, DetailView):
    model = AudioFile
    template_name = 'audio_manager/detail.html'
    context_object_name = 'audio_file'
    def get_queryset(self):
        return AudioFile.objects.filter(user=self.request.user)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        audio_file = self.get_object()
        context['status_classes'] = {
            'pending': 'warning',
            'processing': 'info',
            'completed': 'success',
            'failed': 'danger'
        }
        return context
def audio_status(request, pk):
    """AJAX 端點，返回音訊檔案的處理狀態"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': '請先登入'}, status=401)
    
    try:
        audio_file = AudioFile.objects.get(pk=pk, user=request.user)
        data = {
            'id': audio_file.id,
            'status': audio_file.processing_status,
            'status_display': audio_file.get_processing_status_display(),
            'message': audio_file.processing_message,
            'last_updated': timezone.localtime(audio_file.updated_at).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 添加完成時間（如果已完成）
        if audio_file.processed_at:
            data['processed_at'] = timezone.localtime(audio_file.processed_at).strftime('%Y-%m-%d %H:%M:%S')
            processing_time = (audio_file.processed_at - audio_file.created_at).total_seconds()
            data['processing_time'] = round(processing_time, 2)
        
        # 添加時長資訊（如果可用）
        if audio_file.duration:
            data['duration'] = audio_file.duration
            data['duration_display'] = audio_file.get_duration_display()
        
        return JsonResponse(data)
    except AudioFile.DoesNotExist:
        return JsonResponse({'error': '找不到指定的音訊檔案'}, status=404)

# 在現有的 views.py 文件中添加下列內容

from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from .models import Transcript, AudioFile
from core.audio.srt import SRTGenerator, VTTGenerator

@login_required
@require_GET
def download_transcript(request, transcript_id):
    """下載純文本格式的轉錄內容"""
    # 獲取轉錄記錄，確保只能下載自己的轉錄
    transcript = get_object_or_404(Transcript, id=transcript_id, audio_file__user=request.user)
    
    # 獲取檔案名稱
    filename = f"{transcript.audio_file.title}_transcript.txt"
    safe_filename = filename.replace(' ', '_').encode('utf-8', 'ignore').decode('utf-8')
    
    # 創建響應
    response = HttpResponse(transcript.full_text, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response

@login_required
@require_GET
def download_srt(request, transcript_id):
    """下載 SRT 格式的字幕檔案"""
    # 獲取轉錄記錄
    transcript = get_object_or_404(Transcript, id=transcript_id, audio_file__user=request.user)
    
    # 獲取片段
    segments = []
    for segment in transcript.segments.all().order_by('start_time'):
        segments.append({
            'start': segment.start_time,
            'end': segment.end_time,
            'text': segment.text,
            'speaker_id': segment.speaker_id,
            'speaker_name': segment.speaker_name
        })
    
    # 生成 SRT 內容
    include_speaker = request.GET.get('include_speaker', '1') == '1'
    merge_short = request.GET.get('merge_short', '1') == '1'
    
    if merge_short:
        segments = SRTGenerator.merge_short_segments(segments)
    
    srt_content = SRTGenerator.generate_from_segments(segments, include_speaker)
    
    # 獲取檔案名稱
    filename = f"{transcript.audio_file.title}_subtitle.srt"
    safe_filename = filename.replace(' ', '_').encode('utf-8', 'ignore').decode('utf-8')
    
    # 創建響應
    response = HttpResponse(srt_content, content_type='text/srt; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response

@login_required
@require_GET
def download_vtt(request, transcript_id):
    """下載 WebVTT 格式的字幕檔案"""
    # 獲取轉錄記錄
    transcript = get_object_or_404(Transcript, id=transcript_id, audio_file__user=request.user)
    
    # 獲取片段
    segments = []
    for segment in transcript.segments.all().order_by('start_time'):
        segments.append({
            'start': segment.start_time,
            'end': segment.end_time,
            'text': segment.text,
            'speaker_id': segment.speaker_id,
            'speaker_name': segment.speaker_name
        })
    
    # 生成 VTT 內容
    include_speaker = request.GET.get('include_speaker', '1') == '1'
    merge_short = request.GET.get('merge_short', '1') == '1'
    
    if merge_short:
        segments = SRTGenerator.merge_short_segments(segments)
    
    vtt_content = VTTGenerator.generate_from_segments(segments, include_speaker)
    
    # 獲取檔案名稱
    filename = f"{transcript.audio_file.title}_subtitle.vtt"
    safe_filename = filename.replace(' ', '_').encode('utf-8', 'ignore').decode('utf-8')
    
    # 創建響應
    response = HttpResponse(vtt_content, content_type='text/vtt; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response