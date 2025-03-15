# apps/audio_manager/forms.py
from django import forms
from .models import AudioFile
from utils.validators import validate_audio_file

class AudioUploadForm(forms.ModelForm):
    """音訊上傳表單"""
    
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
        self.user = kwargs.pop('user', None)  # 從kwargs中獲取使用者
        super().__init__(*args, **kwargs)
    
    def clean_file(self):
        """驗證上傳的音訊檔案"""
        file = self.cleaned_data.get('file')
        if file:
            validate_audio_file(file)  # 使用前面定義的驗證函數
        return file
    
    def save(self, commit=True):
        """保存表單資料，自動設定使用者為當前使用者"""
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
            
        # 從檔案名稱獲取格式
        if instance.file:
            instance.format = instance.get_file_extension()
            instance.file_size = instance.file.size
            
        if commit:
            instance.save()
        return instance