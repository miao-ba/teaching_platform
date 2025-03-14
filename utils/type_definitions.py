"""
定義專案中使用的自定義類型。
"""
from typing import Dict, Any, List, Optional, TypedDict, Union,Literal

# 服務結果類型
class ServiceResult(TypedDict, total=False):
    """服務操作結果的標準格式"""
    success: bool
    data: Any
    error: Optional[str]
    status_code: int

# 音訊片段類型
class AudioSegment(TypedDict, total=False):
    """音訊片段的標準格式"""
    start: float
    end: float
    text: str
    speaker_id: Optional[str]
    confidence: Optional[float]

# 轉錄結果類型
class TranscriptionResult(TypedDict, total=False):
    """轉錄結果的標準格式"""
    text: str
    segments: List[AudioSegment]
    language: str
    duration: float

# LLM 參數類型
class LLMParameters(TypedDict, total=False):
    """LLM 參數的標準格式"""
    temperature: float
    top_p: float
    top_k: int
    max_tokens: int
    stop_sequences: List[str]
    max_retries: int

# 支援的音訊格式
AudioFormat = Literal['mp3', 'wav', 'ogg', 'm4a', 'flac']