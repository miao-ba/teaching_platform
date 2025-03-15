# apps/audio_manager/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import AudioFile
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

@shared_task
def process_audio_file(audio_file_id):
    """
    處理上傳的音訊檔案：
    1. 獲取音訊元數據（時長、採樣率等）
    2. 進行轉錄（如果啟用）
    3. 進行講者辨識（如果啟用）
    """
    from django.conf import settings
    
    try:
        # 獲取音訊檔案記錄
        audio_file = AudioFile.objects.get(id=audio_file_id)
        
        # 更新處理狀態
        audio_file.set_processing_status('processing', '開始處理音訊檔案')
        
        # 處理音訊元數據
        process_audio_metadata(audio_file)
        
        # TODO: 在這裡添加轉錄處理
        # TODO: 在這裡添加講者辨識處理
        
        # 更新處理狀態為完成
        audio_file.set_processing_status('completed', '處理完成')
        
        # 設置處理完成時間
        audio_file.processed_at = timezone.now()
        audio_file.save(update_fields=['processed_at'])
        
        return {'success': True, 'message': f'成功處理音訊檔案 {audio_file.title}'}
        
    except AudioFile.DoesNotExist:
        logger.error(f"找不到音訊檔案，ID: {audio_file_id}")
        return {'success': False, 'message': f'找不到音訊檔案，ID: {audio_file_id}'}
        
    except Exception as e:
        logger.exception(f"處理音訊檔案時發生錯誤，ID: {audio_file_id}")
        
        # 更新處理狀態為失敗
        try:
            audio_file = AudioFile.objects.get(id=audio_file_id)
            audio_file.set_processing_status('failed', f'處理失敗: {str(e)}')
        except:
            pass
            
        return {'success': False, 'message': f'處理失敗: {str(e)}'}

def process_audio_metadata(audio_file):
    """
    處理音訊元數據：獲取時長、採樣率、聲道數等
    """
    from mutagen import File
    import contextlib
    import wave
    import subprocess
    
    file_path = audio_file.file.path
    format_lower = audio_file.format.lower() if audio_file.format else ''
    
    try:
        # 使用 mutagen 獲取音訊元數據
        audio_meta = File(file_path)
        
        if audio_meta:
            # 取得音訊時長
            if hasattr(audio_meta, 'info') and hasattr(audio_meta.info, 'length'):
                audio_file.duration = audio_meta.info.length
            
            # 取得採樣率和聲道數（如果可用）
            if hasattr(audio_meta, 'info'):
                if hasattr(audio_meta.info, 'sample_rate'):
                    audio_file.sample_rate = audio_meta.info.sample_rate
                if hasattr(audio_meta.info, 'channels'):
                    audio_file.channels = audio_meta.info.channels
        
        # 對於 WAV 檔案，也可以使用 wave 模組來獲取更精確的資訊
        if format_lower == 'wav':
            with contextlib.closing(wave.open(file_path, 'r')) as wav_file:
                audio_file.duration = wav_file.getnframes() / wav_file.getframerate()
                audio_file.sample_rate = wav_file.getframerate()
                audio_file.channels = wav_file.getnchannels()
        
        # 如果上述方法未能獲取時長，可以嘗試使用 ffmpeg（如果已安裝）
        if audio_file.duration is None:
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 
                     'default=noprint_wrappers=1:nokey=1', file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                if result.stdout.strip():
                    audio_file.duration = float(result.stdout.strip())
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
        
        # 更新檔案大小
        audio_file.file_size = os.path.getsize(file_path)
        
        # 儲存更新的元數據
        audio_file.save(update_fields=['duration', 'sample_rate', 'channels', 'file_size'])
        
        return True
        
    except Exception as e:
        logger.exception(f"處理音訊元數據時發生錯誤: {e}")
        return False