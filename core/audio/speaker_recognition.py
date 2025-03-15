"""
講者辨識模組，提供音訊中不同講者的自動識別功能。
支援簡易版基於聚類的方法，作為輕量且離線的講者分離解決方案。
"""
from abc import ABC, abstractmethod
from pathlib import Path
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import librosa
from sklearn.cluster import AgglomerativeClustering

from utils.type_definitions import AudioSegment, ServiceResult

class BaseSpeakerRecognizer(ABC):
    """講者辨識的基本抽象類別，定義所有講者辨識器必須實作的方法"""

    @abstractmethod
    def initialize(self) -> ServiceResult:
        """初始化講者辨識器，例如加載模型或設定連接"""
        pass

    @abstractmethod
    def identify_speakers(self, audio_file: Path, segments: Optional[List[AudioSegment]] = None) -> ServiceResult[List[AudioSegment]]:
        """
        識別講者
        
        參數:
            audio_file: 音訊檔案路徑
            segments: 轉錄片段列表，每個片段包含 start, end, text 等資訊
            
        返回:
            ServiceResult 包含更新後的片段列表，添加了講者資訊
        """
        pass

    @abstractmethod
    def get_speaker_count(self, audio_file: Path) -> ServiceResult[int]:
        """
        獲取講者數量估計值
        
        參數:
            audio_file: 音訊檔案路徑
            
        返回:
            ServiceResult 包含估計的講者數量
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """檢查講者辨識服務狀態"""
        pass


class SimpleSpeakerRecognizer(BaseSpeakerRecognizer):
    """使用基本音訊特徵和聚類進行講者辨識的簡易實現"""
    
    def __init__(self):
        """初始化簡易講者辨識器"""
        self.initialized = False
    
    def initialize(self) -> ServiceResult:
        """初始化講者辨識器"""
        try:
            # 此簡易實現不需要加載模型，僅檢查依賴項
            import librosa
            import numpy as np
            from sklearn.cluster import AgglomerativeClustering
            
            self.initialized = True
            
            return {
                "success": True,
                "data": "成功初始化簡易講者辨識器",
                "status_code": 200
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"初始化講者辨識器失敗: {str(e)}",
                "status_code": 500
            }
    
    def identify_speakers(self, audio_file: Path, segments: Optional[List[AudioSegment]] = None) -> ServiceResult[List[AudioSegment]]:
        """識別講者"""
        try:
            if not self.initialized:
                init_result = self.initialize()
                if not init_result["success"]:
                    return init_result
            
            if not segments or len(segments) <= 1:
                return {
                    "success": False,
                    "error": "需要至少兩個音訊片段才能進行講者辨識",
                    "status_code": 400
                }
            
            # 讀取音訊檔案
            y, sr = librosa.load(str(audio_file), sr=None)
            
            # 提取音訊片段並計算特徵
            segment_features = []
            valid_segments = []
            
            for segment in segments:
                start_sample = int(segment["start"] * sr)
                end_sample = int(segment["end"] * sr)
                
                if end_sample <= start_sample or start_sample >= len(y) or end_sample <= 0:
                    continue
                
                # 確保範圍有效
                start_sample = max(0, start_sample)
                end_sample = min(len(y), end_sample)
                
                # 提取片段
                segment_audio = y[start_sample:end_sample]
                
                # 確保片段夠長
                if len(segment_audio) < sr * 0.5:  # 至少 0.5 秒
                    continue
                
                # 提取 MFCC 特徵
                try:
                    mfcc = librosa.feature.mfcc(y=segment_audio, sr=sr, n_mfcc=13)
                    mfcc_mean = np.mean(mfcc, axis=1)
                    segment_features.append(mfcc_mean)
                    valid_segments.append(segment)
                except Exception:
                    continue
            
            if len(valid_segments) <= 1:
                return {
                    "success": False,
                    "error": "有效片段不足，無法進行講者辨識",
                    "status_code": 400
                }
            
            # 估計講者數量
            estimated_speakers = self._estimate_speaker_count(len(valid_segments))
            
            # 執行聚類
            features_array = np.array(segment_features)
            clustering = AgglomerativeClustering(
                n_clusters=estimated_speakers,
                affinity="euclidean",
                linkage="ward"
            )
            labels = clustering.fit_predict(features_array)
            
            # 將聚類結果應用到片段
            result_segments = []
            for i, segment in enumerate(valid_segments):
                segment_with_speaker = segment.copy()
                segment_with_speaker["speaker_id"] = f"speaker_{labels[i]}"
                result_segments.append(segment_with_speaker)
            
            # 處理未能提取特徵的片段
            processed_indices = [segments.index(s) for s in valid_segments]
            for i, segment in enumerate(segments):
                if i not in processed_indices:
                    # 嘗試根據鄰近片段分配講者
                    nearest_speaker = self._find_nearest_speaker(segment, result_segments)
                    segment_with_speaker = segment.copy()
                    segment_with_speaker["speaker_id"] = nearest_speaker
                    result_segments.append(segment_with_speaker)
            
            # 排序結果
            result_segments.sort(key=lambda x: x["start"])
            
            return {
                "success": True,
                "data": result_segments,
                "status_code": 200
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"講者辨識失敗: {str(e)}",
                "status_code": 500
            }
    
    def get_speaker_count(self, audio_file: Path) -> ServiceResult[int]:
        """獲取講者數量估計值"""
        try:
            # 簡單估計：讀取前 30 秒音訊，提取特徵，嘗試聚類
            y, sr = librosa.load(str(audio_file), sr=None, duration=30)
            
            # 將音訊切分為 3 秒片段
            segment_length = 3 * sr
            segments = []
            
            for i in range(0, len(y), segment_length):
                segment = y[i:i+segment_length]
                if len(segment) >= sr:  # 至少 1 秒
                    mfcc = librosa.feature.mfcc(y=segment, sr=sr, n_mfcc=13)
                    mfcc_mean = np.mean(mfcc, axis=1)
                    segments.append(mfcc_mean)
            
            if len(segments) < 3:
                estimated_speakers = 1
            else:
                # 使用高斯混合模型估計聚類數量
                from sklearn.mixture import GaussianMixture
                
                features_array = np.array(segments)
                bic_scores = []
                
                # 嘗試 1-5 個講者
                for n_components in range(1, min(6, len(segments))):
                    gmm = GaussianMixture(n_components=n_components)
                    gmm.fit(features_array)
                    bic_scores.append(gmm.bic(features_array))
                
                # 選擇 BIC 最低的聚類數量
                estimated_speakers = np.argmin(bic_scores) + 1
            
            return {
                "success": True,
                "data": estimated_speakers,
                "status_code": 200
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"講者數量估計失敗: {str(e)}",
                "status_code": 500
            }
    
    def _estimate_speaker_count(self, segment_count: int) -> int:
        """根據片段數量估計講者數量"""
        # 簡單規則：
        # - 10 個以下片段，假設 2 個講者
        # - 10-30 個片段，假設 3 個講者
        # - 30 個以上片段，假設 4 個講者
        # - 但講者數量不超過片段數量的 1/3
        
        if segment_count < 10:
            return min(2, segment_count)
        elif segment_count < 30:
            return min(3, segment_count // 3)
        else:
            return min(4, segment_count // 4)
    
    def _find_nearest_speaker(self, segment: AudioSegment, labeled_segments: List[AudioSegment]) -> str:
        """根據時間找到最近的講者"""
        segment_mid = (segment["start"] + segment["end"]) / 2
        nearest_distance = float("inf")
        nearest_speaker = "speaker_0"  # 預設
        
        for labeled in labeled_segments:
            labeled_mid = (labeled["start"] + labeled["end"]) / 2
            distance = abs(segment_mid - labeled_mid)
            
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_speaker = labeled["speaker_id"]
        
        return nearest_speaker
    
    def health_check(self) -> bool:
        """檢查講者辨識服務狀態"""
        try:
            if not self.initialized:
                init_result = self.initialize()
                return init_result["success"]
            return True
        except Exception:
            return False