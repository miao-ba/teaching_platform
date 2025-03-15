# core/audio/transcriber.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO, List, Union

from utils.type_definitions import TranscriptionResult, ServiceResult, AudioFormat


class BaseTranscriber(ABC):
    """語音轉寫器的基本抽象類別，定義所有轉錄器必須實作的方法"""

    @abstractmethod
    def initialize(self) -> ServiceResult:
        """初始化轉錄器，例如加載模型或設定API連接"""
        pass

    @abstractmethod
    def transcribe_file(self, audio_file: Path, language: Optional[str] = None) -> ServiceResult[TranscriptionResult]:
        """
        轉錄音訊檔案
        
        參數:
            audio_file: 音訊檔案路徑
            language: 音訊語言代碼 (如 'zh-TW', 'en-US')
            
        返回:
            ServiceResult 包含 TranscriptionResult 或錯誤資訊
        """
        pass

    @abstractmethod
    def transcribe_stream(self, audio_stream: BinaryIO, format: AudioFormat, language: Optional[str] = None) -> ServiceResult[TranscriptionResult]:
        """
        轉錄音訊流
        
        參數:
            audio_stream: 音訊資料流
            format: 音訊格式
            language: 音訊語言代碼
            
        返回:
            ServiceResult 包含 TranscriptionResult 或錯誤資訊
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """檢查轉錄服務狀態"""
        pass
    
# 繼續 core/audio/transcriber.py 檔案
import os
import tempfile
import requests
from pathlib import Path
import openai

class WhisperTranscriber(BaseTranscriber):
    """使用OpenAI Whisper API的轉錄器實作"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-1"):
        """
        初始化Whisper轉錄器
        
        參數:
            api_key: OpenAI API金鑰，若為None則從環境變數獲取
            model: Whisper模型名稱
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.initialized = False
    
    def initialize(self) -> ServiceResult:
        """初始化OpenAI API連接"""
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "未提供API金鑰，請設定OPENAI_API_KEY環境變數或在初始化時提供",
                    "status_code": 400
                }
            
            # 設定API金鑰
            openai.api_key = self.api_key
            
            # 簡單測試API連接
            openai.Model.list()
            
            self.initialized = True
            return {
                "success": True,
                "data": f"成功初始化Whisper API ({self.model})",
                "status_code": 200
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"初始化Whisper API失敗: {str(e)}",
                "status_code": 500
            }
    
    def transcribe_file(self, audio_file: Path, language: Optional[str] = None) -> ServiceResult[TranscriptionResult]:
        """使用Whisper API轉錄音訊檔案"""
        try:
            if not self.initialized:
                init_result = self.initialize()
                if not init_result["success"]:
                    return init_result
            
            # 檢查檔案是否存在
            if not audio_file.exists():
                return {
                    "success": False,
                    "error": f"檔案不存在: {str(audio_file)}",
                    "status_code": 404
                }
                
            # 準備API請求參數
            params = {
                "model": self.model,
                "response_format": "verbose_json"
            }
            
            if language:
                params["language"] = language
                
            # 呼叫Whisper API
            with open(audio_file, "rb") as audio:
                response = openai.Audio.transcribe(**params, file=audio)
            
            # 處理回應
            text = response.get("text", "")
            segments = []
            
            # 提取時間戳記片段
            if "segments" in response:
                for segment in response["segments"]:
                    segments.append({
                        "start": segment.get("start", 0),
                        "end": segment.get("end", 0),
                        "text": segment.get("text", ""),
                        "speaker_id": None,  # Whisper不提供講者辨識
                        "confidence": segment.get("confidence", 1.0)
                    })
            
            # 計算音訊時長
            duration = segments[-1]["end"] if segments else 0
            
            transcription_result = {
                "text": text,
                "segments": segments,
                "language": language or response.get("language", ""),
                "duration": duration
            }
            
            return {
                "success": True,
                "data": transcription_result,
                "status_code": 200
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Whisper轉錄失敗: {str(e)}",
                "status_code": 500
            }
    
    def transcribe_stream(self, audio_stream: BinaryIO, format: AudioFormat, language: Optional[str] = None) -> ServiceResult[TranscriptionResult]:
        """使用Whisper API轉錄音訊流"""
        try:
            # Whisper API不直接支援流，故將流保存為臨時檔案
            with tempfile.NamedTemporaryFile(suffix=f'.{format}', delete=False) as temp_file:
                temp_file_path = temp_file.name
                audio_stream.seek(0)
                temp_file.write(audio_stream.read())
            
            # 使用檔案轉錄方法
            result = self.transcribe_file(Path(temp_file_path), language)
            
            # 刪除臨時檔案
            os.unlink(temp_file_path)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Whisper流轉錄失敗: {str(e)}",
                "status_code": 500
            }
    
    def health_check(self) -> bool:
        """檢查Whisper API服務狀態"""
        try:
            if not self.initialized:
                init_result = self.initialize()
                return init_result["success"]
            
            # 簡單檢查API連接
            openai.Model.list()
            return True
        except Exception:
            return False
        
# 繼續 core/audio/transcriber.py 檔案
import wave
import json
from pathlib import Path
import os
import tempfile
from typing import Dict, Any, Optional, BinaryIO, List, Union

from vosk import Model, KaldiRecognizer, SetLogLevel
from pydub import AudioSegment

class VoskTranscriber(BaseTranscriber):
    """使用Vosk進行離線語音辨識的轉錄器實作"""
    
    def __init__(self, model_path: Optional[str] = None, model_name: str = "vosk-model-zh-cn-0.22"):
        """
        初始化Vosk轉錄器
        
        參數:
            model_path: Vosk模型路徑，若為None則使用預設路徑
            model_name: 模型名稱，用於自動下載或從預設目錄尋找模型
        """
        self.model_name = model_name
        self.model_path = model_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "models",
            "vosk",
            model_name
        )
        self.model = None
        self.initialized = False
        SetLogLevel(-1)  # 減少日誌輸出
    
    def initialize(self) -> ServiceResult:
        """初始化Vosk模型"""
        try:
            # 檢查模型是否存在
            if not os.path.exists(self.model_path):
                # 模型不存在，嘗試下載
                self._download_model()
                
            # 確認模型下載成功
            if not os.path.exists(self.model_path):
                return {
                    "success": False,
                    "error": f"無法找到或下載Vosk模型: {self.model_path}",
                    "status_code": 404
                }
            
            # 加載模型
            self.model = Model(self.model_path)
            self.initialized = True
            
            return {
                "success": True,
                "data": f"成功初始化Vosk模型: {self.model_name}",
                "status_code": 200
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"初始化Vosk模型失敗: {str(e)}",
                "status_code": 500
            }
    
    def _download_model(self) -> None:
        """下載Vosk模型"""
        import urllib.request
        import zipfile
        import shutil
        
        # 創建模型目錄（若不存在）
        model_dir = os.path.dirname(self.model_path)
        os.makedirs(model_dir, exist_ok=True)
        
        # 下載模型
        model_url = f"https://alphacephei.com/vosk/models/{self.model_name}.zip"
        temp_zip = os.path.join(tempfile.gettempdir(), f"{self.model_name}.zip")
        
        try:
            print(f"正在下載Vosk模型: {self.model_name}...")
            urllib.request.urlretrieve(model_url, temp_zip)
            
            # 解壓模型
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                # 解壓到臨時目錄
                extract_dir = tempfile.mkdtemp()
                zip_ref.extractall(extract_dir)
                
                # 模型通常在一個子目錄中，獲取解壓後的目錄
                extracted_model_dir = os.path.join(extract_dir, self.model_name)
                
                # 將模型移動到最終位置
                if os.path.exists(extracted_model_dir):
                    shutil.move(extracted_model_dir, self.model_path)
                else:
                    # 若子目錄名稱不同，嘗試找到解壓的目錄
                    subdirs = [d for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
                    if subdirs:
                        shutil.move(os.path.join(extract_dir, subdirs[0]), self.model_path)
            
            print(f"Vosk模型下載完成: {self.model_path}")
        except Exception as e:
            print(f"下載Vosk模型失敗: {str(e)}")
        finally:
            # 清理臨時檔案
            if os.path.exists(temp_zip):
                os.unlink(temp_zip)
    
    def transcribe_file(self, audio_file: Path, language: Optional[str] = None) -> ServiceResult[TranscriptionResult]:
        """使用Vosk轉錄音訊檔案"""
        try:
            if not self.initialized:
                init_result = self.initialize()
                if not init_result["success"]:
                    return init_result
            
            # 確保音訊為WAV格式
            temp_wav = None
            wav_file_path = str(audio_file)
            
            if not str(audio_file).lower().endswith('.wav'):
                # 使用pydub轉換格式
                audio = AudioSegment.from_file(str(audio_file))
                temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                wav_file_path = temp_wav.name
                audio.export(wav_file_path, format='wav')
                
            # 打開WAV檔案
            with wave.open(wav_file_path, "rb") as wf:
                # 檢查音訊格式
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                    # 若非單聲道16-bit PCM，需要轉換
                    audio = AudioSegment.from_file(wav_file_path)
                    audio = audio.set_channels(1)  # 轉換為單聲道
                    audio = audio.set_sample_width(2)  # 設定為16-bit
                    
                    if temp_wav:
                        temp_wav.close()
                    
                    temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                    wav_file_path = temp_wav.name
                    audio.export(wav_file_path, format='wav', parameters=["-acodec", "pcm_s16le"])
                    
                    # 重新打開轉換後的檔案
                    wf.close()
                    wf = wave.open(wav_file_path, "rb")
                
                # 創建識別器
                sample_rate = wf.getframerate()
                rec = KaldiRecognizer(self.model, sample_rate)
                rec.SetWords(True)  # 啟用詞級時間戳記
                
                # 存儲結果
                result_text = ""
                segments = []
                
                # 處理音訊
                chunk_size = 4000  # 每次處理4000幀
                last_end_time = 0
                
                while True:
                    data = wf.readframes(chunk_size)
                    if len(data) == 0:
                        break
                    
                    if rec.AcceptWaveform(data):
                        result_json = json.loads(rec.Result())
                        
                        # 提取文本
                        segment_text = result_json.get("text", "").strip()
                        if segment_text:
                            result_text += segment_text + " "
                            
                            # 提取詞級時間戳記
                            if "result" in result_json and result_json["result"]:
                                words = result_json["result"]
                                start_time = words[0].get("start", last_end_time)
                                end_time = words[-1].get("end", start_time + 1.0)
                                
                                # 更新最後的結束時間
                                last_end_time = end_time
                                
                                # 添加片段
                                segments.append({
                                    "start": start_time,
                                    "end": end_time,
                                    "text": segment_text,
                                    "speaker_id": None,  # Vosk不提供講者辨識
                                    "confidence": 1.0  # Vosk不提供置信度
                                })
                
                # 處理最後的部分結果
                final_result = json.loads(rec.FinalResult())
                final_text = final_result.get("text", "").strip()
                
                if final_text:
                    result_text += final_text
                    
                    # 提取最後部分的詞級時間戳記
                    if "result" in final_result and final_result["result"]:
                        words = final_result["result"]
                        start_time = words[0].get("start", last_end_time)
                        end_time = words[-1].get("end", start_time + 1.0)
                        
                        # 添加最後片段
                        segments.append({
                            "start": start_time,
                            "end": end_time,
                            "text": final_text,
                            "speaker_id": None,
                            "confidence": 1.0
                        })
                
                # 計算音訊持續時間
                duration = float(wf.getnframes()) / sample_rate
                
                # 清理臨時檔案
                if temp_wav:
                    temp_wav.close()
                    os.unlink(wav_file_path)
                
                # 創建轉錄結果
                transcription_result = {
                    "text": result_text.strip(),
                    "segments": segments,
                    "language": language or "zh-TW",  # 預設使用繁體中文
                    "duration": duration
                }
                
                return {
                    "success": True,
                    "data": transcription_result,
                    "status_code": 200
                }
                
        except Exception as e:
            # 清理臨時檔案
            if temp_wav and os.path.exists(temp_wav.name):
                temp_wav.close()
                os.unlink(temp_wav.name)
                
            return {
                "success": False,
                "error": f"Vosk轉錄失敗: {str(e)}",
                "status_code": 500
            }
    
    def transcribe_stream(self, audio_stream: BinaryIO, format: AudioFormat, language: Optional[str] = None) -> ServiceResult[TranscriptionResult]:
        """使用Vosk轉錄音訊流"""
        try:
            # Vosk需要WAV格式，故將流保存為臨時檔案
            with tempfile.NamedTemporaryFile(suffix=f'.{format}', delete=False) as temp_file:
                temp_file_path = temp_file.name
                audio_stream.seek(0)
                temp_file.write(audio_stream.read())
            
            # 使用檔案轉錄方法
            result = self.transcribe_file(Path(temp_file_path), language)
            
            # 刪除臨時檔案
            os.unlink(temp_file_path)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Vosk流轉錄失敗: {str(e)}",
                "status_code": 500
            }
    
    def health_check(self) -> bool:
        """檢查Vosk服務狀態"""
        try:
            if not self.initialized:
                init_result = self.initialize()
                return init_result["success"]
                
            # 檢查模型是否已加載
            return self.model is not None
        except Exception:
            return False
        
# 繼續 core/audio/transcriber.py 檔案
class TranscriberFactory:
    """轉錄器工廠類別，用於創建不同的轉錄器實例"""
    
    @staticmethod
    def create_transcriber(transcriber_type: str, **kwargs) -> BaseTranscriber:
        """
        創建指定類型的轉錄器
        
        參數:
            transcriber_type: 轉錄器類型 ('whisper' 或 'vosk')
            **kwargs: 轉錄器的其他參數
            
        返回:
            BaseTranscriber 的實例
        """
        if transcriber_type.lower() == 'whisper':
            return WhisperTranscriber(**kwargs)
        elif transcriber_type.lower() == 'vosk':
            return VoskTranscriber(**kwargs)
        else:
            raise ValueError(f"不支援的轉錄器類型: {transcriber_type}")