# apps/audio_manager/tasks.py
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from .models import AudioFile, Transcript, TranscriptSegment
import logging
import os
import tempfile
import time
from pathlib import Path
from datetime import timedelta

from core.audio.transcriber import TranscriberFactory
from core.audio.speaker_recognition import BaseSpeakerRecognizer
from core.payment.quota import QuotaManager, ServiceType
from utils.type_definitions import TranscriptionResult

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
        
        # 啟動轉錄任務
        transcribe_audio_file.delay(audio_file_id)
        
        # 更新處理狀態為部分完成（等待轉錄結果）
        audio_file.set_processing_status('processing', '元數據處理完成，啟動轉錄任務')
        audio_file.save()
        
        return {'success': True, 'message': f'成功處理音訊檔案元數據，已啟動轉錄任務'}
        
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_audio_file(self, audio_file_id):
    """
    轉錄音訊檔案並存儲結果
    
    參數:
        audio_file_id: 音訊檔案的 ID
    
    返回:
        包含成功/失敗信息的字典
    """
    logger.info(f"開始轉錄音訊檔案，ID: {audio_file_id}")
    
    try:
        # 獲取音訊檔案記錄
        audio_file = AudioFile.objects.get(id=audio_file_id)
        logger.info(f"成功獲取音訊檔案: {audio_file.title}, 格式: {audio_file.format}, 時長: {audio_file.duration}秒")
        
        # 更新處理狀態
        audio_file.set_processing_status('processing', '開始音訊轉錄')
        
        # 檢查配額
        user_id = audio_file.user_id
        audio_duration = audio_file.duration or 0
        
        quota_check = QuotaManager.check_quota(
            user_id=user_id, 
            service_type=ServiceType.AUDIO_TRANSCRIPTION,
            duration=audio_duration,
            file_size=audio_file.file_size
        )
        
        if not quota_check[0]:
            logger.warning(f"用戶配額不足，ID: {user_id}, 原因: {quota_check[1]}")
            audio_file.set_processing_status('failed', f'處理失敗: {quota_check[1]}')
            audio_file.save()
            return {'success': False, 'message': quota_check[1]}
        
        # 選擇轉錄器（根據用戶配置或系統設定）
        transcriber_type = select_transcriber_type(user_id, audio_duration)
        logger.info(f"選擇轉錄器: {transcriber_type}")
        
        # 建立轉錄器實例
        transcriber = TranscriberFactory.create_transcriber(transcriber_type)
        
        # 初始化轉錄器
        init_result = transcriber.initialize()
        if not init_result["success"]:
            raise Exception(f"轉錄器初始化失敗: {init_result.get('error', '未知錯誤')}")
        
        # 取得檔案路徑
        file_path = audio_file.file.path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"檔案不存在: {file_path}")
        
        # 執行轉錄
        language = 'zh-TW'  # 預設使用繁體中文，可從用戶配置獲取
        logger.info(f"開始轉錄，檔案: {file_path}, 語言: {language}")
        
        transcription_start_time = time.time()
        result = transcriber.transcribe_file(Path(file_path), language=language)
        transcription_time = time.time() - transcription_start_time
        
        logger.info(f"轉錄完成，耗時: {transcription_time:.2f}秒")
        
        if not result["success"]:
            raise Exception(f"轉錄失敗: {result.get('error', '未知錯誤')}")
        
        # 保存轉錄結果到資料庫
        with transaction.atomic():
            transcription_result = result["data"]
            
            # 檢查是否已存在轉錄記錄
            existing_transcript = Transcript.objects.filter(audio_file_id=audio_file_id).first()
            if existing_transcript:
                logger.info(f"找到現有轉錄記錄，更新內容")
                transcript = existing_transcript
                # 刪除現有片段
                transcript.segments.all().delete()
            else:
                logger.info(f"建立新的轉錄記錄")
                transcript = Transcript(
                    audio_file_id=audio_file_id,
                    is_processed=False,
                    processing_method=transcriber_type
                )
            
            # 更新轉錄記錄
            transcript.full_text = transcription_result["text"]
            transcript.language = transcription_result["language"]
            transcript.duration = transcription_result["duration"] or audio_file.duration
            transcript.is_processed = True
            transcript.processed_at = timezone.now()
            transcript.save()
            
            # 保存片段
            segments = transcription_result.get("segments", [])
            for i, segment in enumerate(segments):
                TranscriptSegment.objects.create(
                    transcript=transcript,
                    start_time=segment["start"],
                    end_time=segment["end"],
                    text=segment["text"],
                    speaker_id=segment.get("speaker_id") or f"speaker_{i % 2}",  # 簡單輪換講者
                    speaker_name=None,
                    confidence=segment.get("confidence", 1.0)
                )
            
            logger.info(f"已保存 {len(segments)} 個轉錄片段")
            
            # 記錄配額使用情況
            QuotaManager.log_usage(
                user_id=user_id,
                service_type=ServiceType.AUDIO_TRANSCRIPTION,
                operation="轉錄音訊",
                resource_id=audio_file_id,
                model_name=transcriber_type,
                duration=audio_duration
            )
        
        # 更新音訊檔案處理狀態
        audio_file.set_processing_status('completed', '轉錄完成')
        audio_file.processed_at = timezone.now()
        audio_file.save(update_fields=['processing_status', 'processing_message', 'processed_at'])
        
        # 啟動講者辨識任務（如果需要）
        if getattr(settings, 'ENABLE_SPEAKER_RECOGNITION', True):
            identify_speakers.delay(audio_file_id)
        
        logger.info(f"轉錄任務完成，音訊檔案 ID: {audio_file_id}")
        return {'success': True, 'message': '轉錄成功完成'}
        
    except AudioFile.DoesNotExist:
        logger.error(f"找不到音訊檔案，ID: {audio_file_id}")
        return {'success': False, 'message': f'找不到音訊檔案，ID: {audio_file_id}'}
        
    except Exception as e:
        logger.exception(f"轉錄音訊檔案時發生錯誤，ID: {audio_file_id}: {str(e)}")
        
        # 嘗試更新處理狀態為失敗
        try:
            audio_file = AudioFile.objects.get(id=audio_file_id)
            
            # 檢查是否需要重試
            retries_left = self.max_retries - self.request.retries
            if retries_left > 0:
                audio_file.set_processing_status('processing', f'轉錄失敗，將在 {self.default_retry_delay} 秒後重試 (剩餘 {retries_left} 次)')
                audio_file.save()
                
                # 引發重試
                raise self.retry(exc=e, countdown=self.default_retry_delay)
            else:
                audio_file.set_processing_status('failed', f'轉錄失敗: {str(e)}')
                audio_file.save()
                
        except Exception as inner_e:
            if not isinstance(inner_e, self.retry): 
                logger.exception(f"嘗試更新失敗狀態時發生錯誤: {str(inner_e)}")
            else:
                # 重新引發 retry 異常
                raise
            
        return {'success': False, 'message': f'轉錄失敗: {str(e)}'}


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def identify_speakers(self, audio_file_id):
    """
    對已轉錄的音訊進行講者辨識
    
    參數:
        audio_file_id: 音訊檔案的 ID
    
    返回:
        包含成功/失敗信息的字典
    """
    logger.info(f"開始講者辨識，音訊檔案 ID: {audio_file_id}")
    
    try:
        # 獲取音訊檔案記錄和轉錄記錄
        audio_file = AudioFile.objects.get(id=audio_file_id)
        transcript = Transcript.objects.get(audio_file_id=audio_file_id)
        
        # 檢查轉錄是否已處理
        if not transcript.is_processed:
            logger.warning(f"轉錄尚未完成，無法執行講者辨識，ID: {audio_file_id}")
            return {'success': False, 'message': '轉錄尚未完成，無法執行講者辨識'}
        
        # 取得轉錄片段
        segments = list(transcript.segments.all().order_by('start_time').values())
        if not segments:
            logger.warning(f"找不到轉錄片段，無法執行講者辨識，ID: {audio_file_id}")
            return {'success': False, 'message': '找不到轉錄片段，無法執行講者辨識'}
        
        # 檢查配額
        user_id = audio_file.user_id
        quota_check = QuotaManager.check_quota(
            user_id=user_id, 
            service_type=ServiceType.SPEAKER_IDENTIFICATION,
            duration=audio_file.duration
        )
        
        if not quota_check[0]:
            logger.warning(f"用戶配額不足，ID: {user_id}, 原因: {quota_check[1]}")
            return {'success': False, 'message': quota_check[1]}
        
        # 選擇講者辨識器
        recognizer = get_speaker_recognizer(user_id)
        logger.info(f"選擇講者辨識器: {recognizer.__class__.__name__}")
        
        # 初始化辨識器
        init_result = recognizer.initialize()
        if not init_result["success"]:
            raise Exception(f"講者辨識器初始化失敗: {init_result.get('error', '未知錯誤')}")
        
        # 準備音訊片段
        audio_segments = []
        for segment in segments:
            audio_segments.append({
                "start": segment["start_time"],
                "end": segment["end_time"],
                "text": segment["text"],
                "speaker_id": segment["speaker_id"],
                "confidence": segment["confidence"]
            })
        
        # 執行講者辨識
        file_path = audio_file.file.path
        result = recognizer.identify_speakers(Path(file_path), audio_segments)
        
        if not result["success"]:
            raise Exception(f"講者辨識失敗: {result.get('error', '未知錯誤')}")
        
        # 更新轉錄片段的講者信息
        identified_segments = result["data"]
        with transaction.atomic():
            for segment in identified_segments:
                TranscriptSegment.objects.filter(
                    transcript=transcript,
                    start_time=segment["start"],
                    end_time=segment["end"]
                ).update(speaker_id=segment["speaker_id"])
            
            # 更新轉錄記錄
            transcript.is_speaker_identified = True
            transcript.save(update_fields=['is_speaker_identified'])
        
        # 記錄配額使用情況
        QuotaManager.log_usage(
            user_id=user_id,
            service_type=ServiceType.SPEAKER_IDENTIFICATION,
            operation="講者辨識",
            resource_id=audio_file_id,
            duration=audio_file.duration
        )
        
        logger.info(f"講者辨識任務完成，音訊檔案 ID: {audio_file_id}")
        return {'success': True, 'message': '講者辨識成功完成'}
        
    except (AudioFile.DoesNotExist, Transcript.DoesNotExist) as e:
        logger.error(f"找不到資料庫記錄，ID: {audio_file_id}, 錯誤: {str(e)}")
        return {'success': False, 'message': f'找不到資料庫記錄: {str(e)}'}
        
    except Exception as e:
        logger.exception(f"講者辨識時發生錯誤，ID: {audio_file_id}: {str(e)}")
        
        # 檢查是否需要重試
        retries_left = self.max_retries - self.request.retries
        if retries_left > 0:
            logger.info(f"講者辨識失敗，將在 {self.default_retry_delay} 秒後重試 (剩餘 {retries_left} 次)")
            raise self.retry(exc=e, countdown=self.default_retry_delay)
            
        return {'success': False, 'message': f'講者辨識失敗: {str(e)}'}


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


def select_transcriber_type(user_id, audio_duration):
    """
    根據用戶配置和音訊長度選擇合適的轉錄器類型
    
    參數:
        user_id: 用戶 ID
        audio_duration: 音訊長度（秒）
        
    返回:
        轉錄器類型字符串：'vosk' 或 'whisper'
    """
    from django.conf import settings
    from core.ai.model_selector import ModelSelector
    
    # 使用模型選擇器決定轉錄器
    provider_type = ModelSelector.select_transcription_provider(
        user_id=user_id,
        audio_length=audio_duration
    )
    
    # 將提供者類型轉換為轉錄器類型
    if provider_type == 'vosk':
        return 'vosk'
    elif provider_type == 'whisper':
        return 'whisper'
    else:
        # 預設使用 vosk（離線模型）
        return 'vosk'


def get_speaker_recognizer(user_id):
    """
    根據用戶配置選擇合適的講者辨識器
    
    參數:
        user_id: 用戶 ID
        
    返回:
        BaseSpeakerRecognizer 實例
    """
    from core.audio.speaker_recognition import SimpleSpeakerRecognizer
    
    # 未來可擴展為根據用戶訂閱計劃選擇不同的辨識器
    return SimpleSpeakerRecognizer()