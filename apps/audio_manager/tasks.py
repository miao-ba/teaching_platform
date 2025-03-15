# apps/audio_manager/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import AudioFile
import logging
import os
import tempfile
import time
from pathlib import Path

# 設置日誌記錄器
logger = logging.getLogger(__name__)

@shared_task
def process_audio_file(audio_file_id):
    """
    處理上傳的音訊檔案：獲取元數據並更新資料庫記錄
    """
    logger.info(f"開始處理音訊檔案，ID: {audio_file_id}")
    
    try:
        # 獲取音訊檔案記錄
        audio_file = AudioFile.objects.get(id=audio_file_id)
        logger.info(f"成功獲取音訊檔案: {audio_file.title}")
        
        # 更新處理狀態
        audio_file.set_processing_status('processing', '開始處理音訊檔案')
        
        # 取得檔案路徑並確認存在
        file_path = audio_file.file.path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"檔案不存在: {file_path}")
        
        # 確保檔案可以被讀取（權限檢查）
        try:
            with open(file_path, 'rb') as f:
                # 只讀取一小部分以確認權限
                f.read(1024)
        except PermissionError:
            logger.error(f"無法讀取檔案，權限不足: {file_path}")
            # 為了確保播放器能工作，設定基本元數據
            audio_file.duration = 60  # 預設為 60 秒
            audio_file.format = os.path.splitext(file_path)[1].lstrip('.')
            audio_file.file_size = os.path.getsize(file_path) if os.access(file_path, os.R_OK) else 0
            audio_file.set_processing_status('failed', '處理失敗: 無法讀取音訊檔案，權限不足')
            audio_file.save()
            return {'success': False, 'message': '權限錯誤: 無法讀取音訊檔案'}
        
        # 處理音訊元數據（多種方法嘗試）
        metadata_result = process_audio_metadata(audio_file)
        
        # 如果音訊元數據處理失敗，仍然要確保設定基本值
        if not metadata_result and not audio_file.duration:
            audio_file.duration = 60  # 預設為 60 秒
            audio_file.save(update_fields=['duration'])
            logger.warning(f"無法獲取音訊時長，設定預設值: 60秒")
        
        # 更新處理狀態為完成
        audio_file.set_processing_status('completed', '處理完成')
        audio_file.processed_at = timezone.now()
        audio_file.save(update_fields=['processed_at'])
        
        return {'success': True, 'message': f'成功處理音訊檔案 {audio_file.title}'}
        
    except AudioFile.DoesNotExist:
        logger.error(f"找不到音訊檔案，ID: {audio_file_id}")
        return {'success': False, 'message': f'找不到音訊檔案，ID: {audio_file_id}'}
        
    except Exception as e:
        logger.exception(f"處理音訊檔案時發生錯誤，ID: {audio_file_id}: {str(e)}")
        
        # 嘗試更新處理狀態為失敗
        try:
            audio_file = AudioFile.objects.get(id=audio_file_id)
            audio_file.set_processing_status('failed', f'處理失敗: {str(e)}')
            
            # 確保有預設的時長
            if not audio_file.duration:
                audio_file.duration = 60
                audio_file.save(update_fields=['duration'])
                
        except Exception as inner_e:
            logger.exception(f"嘗試更新失敗狀態時發生錯誤: {str(inner_e)}")
            
        return {'success': False, 'message': f'處理失敗: {str(e)}'}
def process_audio_metadata(audio_file):
    """
    處理音訊元數據：獲取時長、採樣率、聲道數等
    使用多種方法嘗試獲取元數據，確保可以獲取時長等重要信息
    
    針對 Windows 環境進行了優化，避免文件鎖定問題。
    """
    logger.info(f"開始處理音訊元數據: {audio_file.file.name}")
    
    # 獲取檔案路徑
    file_path = audio_file.file.path
    if not os.path.exists(file_path):
        logger.error(f"音訊檔案不存在: {file_path}")
        return False
    
    # 使用 pathlib 處理路徑，避免 Windows 上的路徑問題
    file_path = Path(file_path).resolve()
    logger.info(f"音訊檔案絕對路徑: {file_path}")
    
    # 首先獲取檔案大小（這通常不會有權限問題）
    try:
        file_size = file_path.stat().st_size
        logger.info(f"檔案大小: {file_size} 位元組")
        
        # 使用 ORM 更新而非直接修改物件
        AudioFile.objects.filter(id=audio_file.id).update(file_size=file_size)
    except Exception as e:
        logger.error(f"獲取檔案大小失敗: {e}")
    
    # 從檔案名稱獲取格式
    format_lower = audio_file.format.lower() if audio_file.format else ''
    if not format_lower:
        format_lower = file_path.suffix.lstrip('.').lower()
        logger.info(f"從檔案名稱獲取格式: {format_lower}")
        
        # 使用 ORM 更新格式
        AudioFile.objects.filter(id=audio_file.id).update(format=format_lower)
    
    # 建立一個臨時檔案副本，避免文件鎖定問題
    duration = None
    sample_rate = None
    channels = None
    
    try:
        # 嘗試使用 pydub 獲取音訊資訊（它對 Windows 相對友好）
        # 複製到臨時文件避免鎖定問題
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_lower}') as temp_file:
            temp_path = Path(temp_file.name)
            
            # 使用二進制模式複製文件
            with open(file_path, 'rb') as src_file:
                temp_file.write(src_file.read())
        
        # 使用 pydub 處理臨時文件
        try:
            from pydub import AudioSegment
            logger.info(f"使用 pydub 嘗試讀取臨時檔案: {temp_path}")
            
            # 根據不同格式讀取音訊
            if format_lower == 'mp3':
                audio = AudioSegment.from_mp3(temp_path)
            elif format_lower == 'wav':
                audio = AudioSegment.from_wav(temp_path)
            elif format_lower == 'ogg':
                audio = AudioSegment.from_ogg(temp_path)
            elif format_lower in ['m4a', 'mp4']:
                audio = AudioSegment.from_file(temp_path, format='mp4')
            elif format_lower == 'flac':
                audio = AudioSegment.from_file(temp_path, format='flac')
            else:
                # 嘗試自動檢測格式
                audio = AudioSegment.from_file(temp_path)
            
            # 獲取音訊資訊
            duration = len(audio) / 1000  # 毫秒轉秒
            sample_rate = audio.frame_rate
            channels = audio.channels
            
            logger.info(f"使用 pydub 獲取資訊: 時長={duration}秒, 採樣率={sample_rate}Hz, 聲道數={channels}")
        except Exception as e:
            logger.warning(f"使用 pydub 獲取音訊資訊失敗: {e}")
            
            # 如果 pydub 失敗，嘗試使用 mutagen
            try:
                import mutagen
                logger.info(f"使用 mutagen 嘗試讀取臨時檔案")
                
                audio_meta = mutagen.File(temp_path)
                if audio_meta and hasattr(audio_meta, 'info'):
                    if hasattr(audio_meta.info, 'length'):
                        duration = audio_meta.info.length
                    if hasattr(audio_meta.info, 'sample_rate'):
                        sample_rate = audio_meta.info.sample_rate
                    if hasattr(audio_meta.info, 'channels'):
                        channels = audio_meta.info.channels
                        
                    logger.info(f"使用 mutagen 獲取資訊: 時長={duration}秒, 採樣率={sample_rate}Hz, 聲道數={channels}")
            except Exception as e:
                logger.warning(f"使用 mutagen 獲取音訊資訊失敗: {e}")
        
        # 刪除臨時檔案
        try:
            temp_path.unlink()
        except Exception as e:
            logger.warning(f"刪除臨時檔案失敗: {e}")
    except Exception as e:
        logger.error(f"創建臨時檔案副本失敗: {e}")
    
    # 如果所有方法都失敗，設定預設值
    if duration is None:
        duration = 60  # 預設 60 秒
        logger.warning(f"未能獲取音訊時長，使用預設值 {duration} 秒")
    
    if sample_rate is None:
        sample_rate = 44100  # 預設 44.1kHz
        logger.warning(f"未能獲取採樣率，使用預設值 {sample_rate} Hz")
    
    if channels is None:
        channels = 2  # 預設立體聲
        logger.warning(f"未能獲取聲道數，使用預設值 {channels} 聲道")
    
    # 使用 ORM 更新而非直接修改物件屬性，避免多進程問題
    try:
        AudioFile.objects.filter(id=audio_file.id).update(
            duration=duration,
            sample_rate=sample_rate,
            channels=channels
        )
        logger.info(f"成功更新音訊元數據: ID={audio_file.id}, 時長={duration}秒, 採樣率={sample_rate}Hz, 聲道數={channels}")
        return True
    except Exception as e:
        logger.exception(f"更新音訊元數據時發生錯誤: {e}")
        return False