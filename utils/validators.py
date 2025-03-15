# utils/validators.py
from django.core.exceptions import ValidationError
import os

def validate_audio_file(file):
    """驗證上傳的檔案是否為支援的音訊格式"""
    # 檢查檔案大小（限制為100MB）
    max_size = 100 * 1024 * 1024  # 100MB
    if file.size > max_size:
        raise ValidationError('檔案大小不能超過100MB')
    
    # 檢查檔案副檔名
    file_ext = os.path.splitext(file.name)[1].lower()
    allowed_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.flac']
    
    if file_ext not in allowed_extensions:
        raise ValidationError(f'不支援的檔案格式。支援的格式有: {", ".join(allowed_extensions)}')
    
    # 嘗試使用 magic 進行更深入的檢查（可選）
    try:
        import magic
        file_content = file.read(1024)
        file.seek(0)
        mime = magic.from_buffer(file_content, mime=True)
        
        allowed_mimes = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 
                          'audio/x-m4a', 'audio/flac', 'audio/x-flac']
        
        if mime not in allowed_mimes:
            raise ValidationError('檔案內容不是有效的音訊格式')
    except (ImportError, NameError):
        # 如果 python-magic 未安裝或出錯，僅依靠檔案副檔名檢查
        pass