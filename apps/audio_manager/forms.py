from django import forms
from .models import AudioFile
from utils.validators import validate_audio_file
from django.utils import timezone
import datetime
from . import models

class AudioUploadForm(forms.ModelForm):
    class Meta:
        model = AudioFile
        fields = ['title', 'description', 'file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入音訊標題'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '請輸入簡要描述（選填）',
                'rows': 3
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'audio/*'
            })
        }
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            validate_audio_file(file)
        return file
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if instance.file:
            instance.format = instance.get_file_extension()
            instance.file_size = instance.file.size
        if commit:
            instance.save()
        return instance

class AudioSearchForm(forms.Form):
    """音訊檔案搜尋和篩選表單"""
    
    # 搜尋關鍵字
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜尋標題或描述...'
        })
    )
    
    # 處理狀態篩選
    STATUS_CHOICES = [
        ('all', '全部狀態'),
        ('pending', '等待處理'),
        ('processing', '處理中'),
        ('completed', '已完成'),
        ('failed', '處理失敗')
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # 日期範圍篩選
    DATE_CHOICES = [
        ('all', '全部時間'),
        ('today', '今天'),
        ('week', '過去一週'),
        ('month', '過去一個月'),
        ('custom', '自訂日期範圍')
    ]
    
    date = forms.ChoiceField(
        choices=DATE_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # 自訂日期範圍
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '開始日期'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '結束日期'
        })
    )
    
    # 時長範圍篩選
    duration_min = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '最短時長 (秒)'
        })
    )
    
    duration_max = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '最長時長 (秒)'
        })
    )
    
    # 排序方式
    SORT_CHOICES = [
        ('-created_at', '最新上傳'),
        ('created_at', '最舊上傳'),
        ('title', '標題 A-Z'),
        ('-title', '標題 Z-A'),
        ('duration', '時長 (短到長)'),
        ('-duration', '時長 (長到短)'),
    ]
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def get_date_range(self):
        """根據選擇的日期選項獲取日期範圍"""
        date_choice = self.cleaned_data.get('date', 'all')
        today = timezone.now().date()
        
        if date_choice == 'today':
            return today, today
        elif date_choice == 'week':
            start_date = today - datetime.timedelta(days=7)
            return start_date, today
        elif date_choice == 'month':
            start_date = today - datetime.timedelta(days=30)
            return start_date, today
        elif date_choice == 'custom':
            start_date = self.cleaned_data.get('start_date')
            end_date = self.cleaned_data.get('end_date')
            if start_date and end_date:
                return start_date, end_date
        
        return None, None
    
    def filter_queryset(self, queryset):
        """根據表單資料篩選 queryset"""
        
        # 關鍵字搜尋
        q = self.cleaned_data.get('q')
        if q:
            queryset = queryset.filter(
                models.Q(title__icontains=q) |
                models.Q(description__icontains=q)
            )
        
        # 處理狀態篩選
        status = self.cleaned_data.get('status')
        if status and status != 'all':
            queryset = queryset.filter(processing_status=status)
        
        # 日期範圍篩選
        start_date, end_date = self.get_date_range()
        if start_date and end_date:
            if start_date == end_date:
                # 如果是同一天，使用 date 篩選
                queryset = queryset.filter(created_at__date=start_date)
            else:
                # 日期範圍篩選
                queryset = queryset.filter(
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date
                )
        
        # 時長範圍篩選
        duration_min = self.cleaned_data.get('duration_min')
        if duration_min is not None:
            queryset = queryset.filter(duration__gte=duration_min)
        
        duration_max = self.cleaned_data.get('duration_max')
        if duration_max is not None:
            queryset = queryset.filter(duration__lte=duration_max)
        
        # 排序
        sort_by = self.cleaned_data.get('sort_by', '-created_at')
        if sort_by:
            queryset = queryset.order_by(sort_by)
        
        return queryset