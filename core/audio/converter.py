"""
音訊格式轉換功能模組。
提供各種音訊格式轉換、採樣率調整和通道數轉換的功能。
"""
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Union, BinaryIO
import logging

from pydub import AudioSegment
import librosa
import soundfile as sf
import numpy as np

from utils.type_definitions import AudioFormat, ServiceResult

logger = logging.getLogger(__name__)

class AudioConverter:
    """音訊格式轉換器類別，提供音訊格式轉換和參數調整功能"""
    
    SUPPORTED_FORMATS = ['mp3', 'wav', 'ogg', 'm4a', 'flac']
    
    @staticmethod
    def convert_format(
        input_file: Union[str, Path, BinaryIO],
        output_format: AudioFormat,
        output_path: Optional[Union[str, Path]] = None,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None
    ) -> ServiceResult:
        """
        將音訊檔案轉換為指定格式，並可選擇性地調整採樣率和通道數。
        
        參數:
            input_file: 輸入音訊檔案路徑或檔案對象
            output_format: 目標音訊格式（mp3, wav, ogg, m4a, flac）
            output_path: 輸出檔案路徑（若未指定則使用臨時檔案）
            sample_rate: 目標採樣率（Hz）
            channels: 目標通道數（1為單聲道，2為立體聲）
            
        返回:
            包含結果的字典:
                success: 是否成功
                data: 成功時返回輸出檔案路徑
                error: 錯誤時返回錯誤訊息
        """
        try:
            # 檢查格式是否支援
            if output_format not in AudioConverter.SUPPORTED_FORMATS:
                return {
                    "success": False,
                    "error": f"不支援的輸出格式: {output_format}。支援的格式有: {', '.join(AudioConverter.SUPPORTED_FORMATS)}",
                    "status_code": 400
                }
            
            # 確定輸出路徑
            if output_path is None:
                # 創建臨時檔案
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{output_format}')
                output_path = temp_file.name
                temp_file.close()
            else:
                output_path = str(output_path)
            
            # 處理輸入文件
            if isinstance(input_file, (str, Path)):
                # 如果是檔案路徑
                audio_data = AudioConverter._load_audio(str(input_file), sample_rate, channels)
            else:
                # 如果是檔案對象
                with tempfile.NamedTemporaryFile(delete=False) as temp_input:
                    input_file.seek(0)
                    temp_input.write(input_file.read())
                    temp_input_path = temp_input.name
                
                audio_data = AudioConverter._load_audio(temp_input_path, sample_rate, channels)
                os.unlink(temp_input_path)
            
            if audio_data is None:
                return {
                    "success": False,
                    "error": "無法讀取音訊檔案",
                    "status_code": 400
                }
            
            # 保存為目標格式
            audio_array, curr_sample_rate, curr_channels = audio_data
            AudioConverter._save_audio(audio_array, output_path, output_format, curr_sample_rate, curr_channels)
            
            return {
                "success": True,
                "data": output_path,
                "status_code": 200
            }
            
        except Exception as e:
            logger.exception(f"音訊格式轉換失敗: {str(e)}")
            return {
                "success": False,
                "error": f"音訊格式轉換失敗: {str(e)}",
                "status_code": 500
            }
    
    @staticmethod
    def get_audio_info(file_path: Union[str, Path]) -> ServiceResult:
        """
        獲取音訊檔案的相關資訊。
        
        參數:
            file_path: 音訊檔案路徑
            
        返回:
            包含音訊資訊的字典:
                format: 檔案格式
                sample_rate: 採樣率（Hz）
                channels: 通道數
                duration: 音訊長度（秒）
                bit_depth: 位元深度
        """
        try:
            file_path = str(file_path)
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            
            # 使用 pydub 獲取基本資訊
            if file_ext == 'mp3':
                audio = AudioSegment.from_mp3(file_path)
            elif file_ext == 'wav':
                audio = AudioSegment.from_wav(file_path)
            elif file_ext == 'ogg':
                audio = AudioSegment.from_ogg(file_path)
            elif file_ext in ['m4a', 'mp4']:
                audio = AudioSegment.from_file(file_path, format='mp4')
            elif file_ext == 'flac':
                audio = AudioSegment.from_file(file_path, format='flac')
            else:
                audio = AudioSegment.from_file(file_path)
            
            # 獲取音訊資訊
            info = {
                "format": file_ext,
                "sample_rate": audio.frame_rate,
                "channels": audio.channels,
                "duration": len(audio) / 1000.0,  # 毫秒轉換為秒
                "bit_depth": audio.sample_width * 8
            }
            
            return {
                "success": True,
                "data": info,
                "status_code": 200
            }
            
        except Exception as e:
            logger.exception(f"獲取音訊資訊失敗: {str(e)}")
            return {
                "success": False,
                "error": f"獲取音訊資訊失敗: {str(e)}",
                "status_code": 500
            }
    
    @staticmethod
    def adjust_audio(
        input_file: Union[str, Path],
        output_path: Union[str, Path],
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        normalize: bool = False,
        trim_silence: bool = False
    ) -> ServiceResult:
        """
        調整音訊參數，如採樣率、通道數等，並可選擇性地進行音量標準化和靜音修剪。
        
        參數:
            input_file: 輸入音訊檔案路徑
            output_path: 輸出檔案路徑
            sample_rate: 目標採樣率（Hz）
            channels: 目標通道數（1為單聲道，2為立體聲）
            normalize: 是否標準化音量
            trim_silence: 是否修剪頭尾靜音部分
            
        返回:
            包含結果的字典
        """
        try:
            # 讀取音訊檔案
            audio_data = AudioConverter._load_audio(str(input_file), sample_rate, channels)
            if audio_data is None:
                return {
                    "success": False,
                    "error": "無法讀取音訊檔案",
                    "status_code": 400
                }
            
            audio_array, curr_sample_rate, curr_channels = audio_data
            
            # 標準化音量
            if normalize:
                audio_array = AudioConverter._normalize_audio(audio_array)
            
            # 修剪靜音
            if trim_silence:
                audio_array, _ = librosa.effects.trim(audio_array, top_db=30)
            
            # 獲取輸出格式
            output_format = os.path.splitext(str(output_path))[1].lower().lstrip('.')
            if output_format not in AudioConverter.SUPPORTED_FORMATS:
                return {
                    "success": False,
                    "error": f"不支援的輸出格式: {output_format}",
                    "status_code": 400
                }
            
            # 保存調整後的音訊
            AudioConverter._save_audio(audio_array, str(output_path), output_format, curr_sample_rate, curr_channels)
            
            return {
                "success": True,
                "data": str(output_path),
                "status_code": 200
            }
            
        except Exception as e:
            logger.exception(f"音訊調整失敗: {str(e)}")
            return {
                "success": False,
                "error": f"音訊調整失敗: {str(e)}",
                "status_code": 500
            }
    
    @staticmethod
    def _load_audio(
        file_path: str,
        target_sample_rate: Optional[int] = None,
        target_channels: Optional[int] = None
    ) -> Optional[Tuple[np.ndarray, int, int]]:
        """
        讀取音訊檔案並調整採樣率和聲道數。
        
        返回:
            音訊數據、採樣率、聲道數的元組
        """
        try:
            # 使用 librosa 讀取音訊
            audio_array, sample_rate = librosa.load(file_path, sr=target_sample_rate, mono=False)
            
            # 檢查聲道數並調整
            if audio_array.ndim == 1:
                # 單聲道
                channels = 1
                if target_channels == 2:
                    # 轉換為立體聲（複製通道）
                    audio_array = np.stack([audio_array, audio_array])
                    channels = 2
            else:
                # 立體聲或多聲道
                channels = audio_array.shape[0]
                if target_channels == 1:
                    # 轉換為單聲道（平均所有通道）
                    audio_array = np.mean(audio_array, axis=0)
                    channels = 1
                elif target_channels is not None and target_channels != channels:
                    # 如果有更多通道，取前 target_channels 個通道
                    # 如果通道不足，複製最後一個通道
                    if target_channels > channels:
                        additional_channels = target_channels - channels
                        last_channel = audio_array[-1:, :]
                        audio_array = np.concatenate([audio_array, np.tile(last_channel, (additional_channels, 1))])
                    else:
                        audio_array = audio_array[:target_channels, :]
                    channels = target_channels
            
            return audio_array, sample_rate, channels
            
        except Exception as e:
            logger.exception(f"讀取音訊檔案失敗: {str(e)}")
            return None
    
    @staticmethod
    def _save_audio(
        audio_array: np.ndarray,
        output_path: str,
        output_format: str,
        sample_rate: int,
        channels: int
    ) -> bool:
        """
        保存音訊數據為指定格式的檔案。
        
        返回:
            是否成功
        """
        try:
            # 確保音訊數組格式正確
            if channels == 1 and audio_array.ndim > 1:
                audio_array = np.mean(audio_array, axis=0)
            elif channels > 1 and audio_array.ndim == 1:
                audio_array = np.stack([audio_array] * channels)
            
            # 根據格式使用不同的保存方法
            if output_format == 'mp3':
                # 對於 MP3，使用 pydub
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                # 先保存為 WAV
                sf.write(temp_path, audio_array.T if channels > 1 else audio_array, sample_rate, 'PCM_16')
                
                # 轉換為 MP3
                audio = AudioSegment.from_wav(temp_path)
                audio.export(output_path, format='mp3')
                
                # 刪除臨時檔案
                os.unlink(temp_path)
            else:
                # 對於其他格式，使用 soundfile
                format_map = {
                    'wav': 'WAV',
                    'ogg': 'OGG',
                    'flac': 'FLAC'
                }
                sf_format = format_map.get(output_format, 'WAV')
                
                # 保存音訊
                sf.write(
                    output_path,
                    audio_array.T if channels > 1 else audio_array,
                    sample_rate,
                    format=sf_format
                )
            
            return True
            
        except Exception as e:
            logger.exception(f"保存音訊檔案失敗: {str(e)}")
            return False
    
    @staticmethod
    def _normalize_audio(audio_array: np.ndarray) -> np.ndarray:
        """
        標準化音訊音量。
        
        返回:
            標準化後的音訊數組
        """
        # 確保音訊不是靜音
        if np.max(np.abs(audio_array)) > 0:
            return audio_array / np.max(np.abs(audio_array))
        return audio_array