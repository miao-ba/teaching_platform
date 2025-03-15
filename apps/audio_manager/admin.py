# apps/audio_manager/admin.py
from django.contrib import admin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render
from django.http import HttpResponseRedirect
from .models import AudioFile, Transcript, TranscriptSegment


@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    """音訊檔案管理介面"""
    
    list_display = ('title', 'user', 'format', 'get_duration_display', 'get_file_size_display', 
                   'processing_status', 'created_at')
    list_filter = ('processing_status', 'format', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('format', 'duration', 'file_size', 'sample_rate', 'channels', 
                      'processing_status', 'processing_message', 'created_at', 'updated_at', 'processed_at')
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('title', 'description', 'user')
        }),
        ('檔案資訊', {
            'fields': ('file', 'format', 'duration', 'file_size', 'sample_rate', 'channels')
        }),
        ('處理狀態', {
            'fields': ('processing_status', 'processing_message', 'processing_method')
        }),
        ('時間資訊', {
            'fields': ('created_at', 'updated_at', 'processed_at')
        }),
    )
    
# 在 apps/audio_manager/admin.py 中添加

class TranscriptSegmentInline(admin.TabularInline):
    model = TranscriptSegment
    extra = 0
    fields = ('start_time', 'end_time', 'text', 'speaker_id', 'speaker_name', 'confidence')
    readonly_fields = ('start_time', 'end_time', 'confidence')

@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'language', 'processing_method', 'word_count', 'is_processed', 'created_at')
    list_filter = ('is_processed', 'processing_method', 'language', 'created_at')
    search_fields = ('audio_file__title', 'full_text')
    readonly_fields = ('word_count', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [TranscriptSegmentInline]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('audio_file', 'language', 'processing_method', 'is_processed')
        }),
        ('轉錄資訊', {
            'fields': ('full_text', 'word_count', 'confidence_score', 'processing_time')
        }),
        ('時間資訊', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(TranscriptSegment)
class TranscriptSegmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_audio_title', 'get_time_range', 'speaker_name', 'text_preview', 'word_count')
    list_filter = ('speaker_id', 'is_manually_edited')
    search_fields = ('text', 'speaker_name', 'transcript__audio_file__title')
    readonly_fields = ('duration', 'word_count')
    
    fieldsets = (
        ('關聯信息', {
            'fields': ('transcript',)
        }),
        ('時間信息', {
            'fields': ('start_time', 'end_time', 'duration')
        }),
        ('講者信息', {
            'fields': ('speaker_id', 'speaker_name')
        }),
        ('文本信息', {
            'fields': ('text', 'word_count', 'confidence', 'is_manually_edited')
        }),
    )
    
    def get_audio_title(self, obj):
        return obj.transcript.audio_file.title
    get_audio_title.short_description = '音訊標題'
    get_audio_title.admin_order_field = 'transcript__audio_file__title'
    
    def get_time_range(self, obj):
        return f"{obj.start_time:.1f} - {obj.end_time:.1f}s"
    get_time_range.short_description = '時間範圍(秒)'
    
    def text_preview(self, obj):
        return f"{obj.text[:50]}{'...' if len(obj.text) > 50 else ''}"
    text_preview.short_description = '文本預覽'
    
    def duration(self, obj):
        return f"{obj.duration:.2f}秒"
    duration.short_description = '持續時間'
    def merge_segments(self, request, queryset):
        """合併選擇的片段"""
        if queryset.count() < 2:
            self.message_user(request, "請選擇至少兩個片段進行合併。", messages.ERROR)
            return
        
        # 檢查是否來自同一個 transcript
        transcripts = set(queryset.values_list('transcript_id', flat=True))
        if len(transcripts) > 1:
            self.message_user(request, "只能合併同一轉錄文本的片段。", messages.ERROR)
            return
    
        # 按開始時間排序
        segments = list(queryset.order_by('start_time'))
        base_segment = segments[0]
        
        try:
            with transaction.atomic():
                # 合併所有其他片段到第一個片段
                for segment in segments[1:]:
                    base_segment.merge_with(segment)
                    segment.delete()
                
                base_segment.save()
                
                # 更新 transcript 的 full_text
                transcript = base_segment.transcript
                all_segments = transcript.segments.order_by('start_time')
                transcript.full_text = ' '.join([s.text for s in all_segments])
                transcript.calculate_word_count()
                transcript.save()
            
            self.message_user(request, f"成功合併 {len(segments)} 個片段。")
        except Exception as e:
            self.message_user(request, f"合併失敗: {str(e)}", messages.ERROR)

    merge_segments.short_description = "合併選擇的片段"
    actions = [merge_segments]

    def assign_speaker(self, request, queryset):
        """為選擇的片段指定講者"""
        from django import forms
        
        # 獲取可用的講者ID
        speaker_ids = set()
        for segment in queryset:
            speakers = TranscriptSegment.objects.filter(
                transcript=segment.transcript
            ).exclude(
                speaker_id__isnull=True
            ).values_list('speaker_id', 'speaker_name').distinct()
            speaker_ids.update(speakers)
        
        # 創建選擇表單
        class SpeakerForm(forms.Form):
            speaker_id = forms.CharField(label="講者ID", max_length=50, required=True)
            speaker_name = forms.CharField(label="講者名稱", max_length=100, required=False)
            _selected_action = forms.CharField(widget=forms.HiddenInput())
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                choices = [('', '-- 選擇講者 --')]
                choices.extend([(sid, f"{sid} ({name})" if name else sid) for sid, name in speaker_ids])
                if choices:
                    self.fields['existing_speaker'] = forms.ChoiceField(
                        label="選擇現有講者",
                        choices=choices,
                        required=False
                    )
        
        # 處理表單提交
        if 'apply' in request.POST:
            form = SpeakerForm(request.POST)
            if form.is_valid():
                speaker_id = form.cleaned_data['speaker_id']
                speaker_name = form.cleaned_data['speaker_name']
                
                count = 0
                for segment in queryset:
                    segment.speaker_id = speaker_id
                    segment.speaker_name = speaker_name
                    segment.save()
                    count += 1
                
                self.message_user(request, f"已將 {count} 個片段指定給講者 {speaker_id} ({speaker_name})")
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = SpeakerForm(initial={'_selected_action': ','.join(str(pk) for pk in queryset.values_list('pk', flat=True))})
        
        # 顯示表單
        return render(
            request,
            'admin/assign_speaker.html',
            {'segments': queryset, 'form': form, 'title': '指定講者'}
        )

    assign_speaker.short_description = "為選擇的片段指定講者"
    actions.append(assign_speaker)
    