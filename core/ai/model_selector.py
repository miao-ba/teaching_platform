"""
模型選擇器，根據使用者偏好和可用資源選擇適合的 AI 模型。
"""
from typing import Dict, Any, List, Optional
from enum import Enum
from django.conf import settings
from apps.accounts.models import UserProfile

class ModelProviderType(str, Enum):
    """模型提供者類型"""
    GEMINI = "gemini"
    OLLAMA = "ollama"
    OPENAI = "openai"
    WHISPER = "whisper"
    VOSK = "vosk"
    PYANNOTE = "pyannote"
    SIMPLE_SPEAKER = "simple_speaker"

class ModelSelector:
    """模型選擇器類別"""
    
    # 預設模型配置
    DEFAULT_MODELS = {
        "llm": ModelProviderType.GEMINI,
        "transcription": ModelProviderType.WHISPER,
        "speaker_recognition": ModelProviderType.SIMPLE_SPEAKER,
    }
    
    # 免費替代方案配置
    FREE_MODELS = {
        "llm": ModelProviderType.OLLAMA,
        "transcription": ModelProviderType.VOSK,
        "speaker_recognition": ModelProviderType.SIMPLE_SPEAKER,
    }
    
    # 進階方案配置
    PREMIUM_MODELS = {
        "llm": ModelProviderType.GEMINI,
        "transcription": ModelProviderType.WHISPER,
        "speaker_recognition": ModelProviderType.PYANNOTE,
    }
    
    @classmethod
    def select_llm_provider(cls, user_id: Optional[int] = None, **kwargs) -> ModelProviderType:
        """選擇 LLM 提供者"""
        # 檢查用戶偏好
        if user_id:
            try:
                profile = UserProfile.objects.get(user_id=user_id)
                # 讀取用戶偏好設定
                user_preference = profile.monthly_quota.get("preferred_llm")
                if user_preference:
                    return ModelProviderType(user_preference)
                
                # 根據訂閱計劃選擇
                if profile.subscription_plan == "free":
                    # 如果 Gemini 配額還有剩餘，則使用 Gemini
                    gemini_usage = profile.used_quota.get("gemini_calls", 0)
                    gemini_limit = 20  # 免費版每月 20 次 Gemini 調用
                    
                    if gemini_usage < gemini_limit:
                        return ModelProviderType.GEMINI
                    else:
                        return cls.FREE_MODELS["llm"]
                    
                elif profile.subscription_plan in ["basic", "premium"]:
                    return cls.PREMIUM_MODELS["llm"]
                    
            except UserProfile.DoesNotExist:
                pass
        
        # 檢查環境設定
        env_preference = getattr(settings, "DEFAULT_LLM_PROVIDER", None)
        if env_preference:
            try:
                return ModelProviderType(env_preference)
            except ValueError:
                pass
        
        # 檢查特定需求
        if kwargs.get("local_only", False):
            return ModelProviderType.OLLAMA
            
        # 預設值
        return cls.DEFAULT_MODELS["llm"]
    
    @classmethod
    def select_transcription_provider(cls, user_id: Optional[int] = None, **kwargs) -> ModelProviderType:
        """選擇轉錄提供者"""
        audio_length = kwargs.get("audio_length", 0)
        
        # 檢查用戶偏好
        if user_id:
            try:
                profile = UserProfile.objects.get(user_id=user_id)
                # 讀取用戶偏好設定
                user_preference = profile.monthly_quota.get("preferred_transcription")
                if user_preference:
                    return ModelProviderType(user_preference)
                
                # 根據訂閱計劃選擇
                if profile.subscription_plan == "free":
                    # 對於長音訊使用本地方案
                    if audio_length > 10 * 60:  # 超過10分鐘
                        return ModelProviderType.VOSK
                    
                    # 檢查 Whisper 配額
                    whisper_seconds = profile.used_quota.get("whisper_seconds", 0)
                    whisper_limit = 30 * 60  # 免費版每月 30 分鐘
                    
                    if whisper_seconds + audio_length <= whisper_limit:
                        return ModelProviderType.WHISPER
                    else:
                        return ModelProviderType.VOSK
                
                elif profile.subscription_plan in ["basic", "premium"]:
                    return cls.PREMIUM_MODELS["transcription"]
                    
            except UserProfile.DoesNotExist:
                pass
        
        # 檢查環境設定
        env_preference = getattr(settings, "DEFAULT_TRANSCRIBER", None)
        if env_preference:
            try:
                return ModelProviderType(env_preference)
            except ValueError:
                pass
        
        # 檢查特定需求
        if kwargs.get("offline", False) or kwargs.get("local_only", False):
            return ModelProviderType.VOSK
            
        # 預設值
        return cls.DEFAULT_MODELS["transcription"]
    
    @classmethod
    def select_speaker_recognition_provider(cls, user_id: Optional[int] = None, **kwargs) -> ModelProviderType:
        """選擇講者辨識提供者"""
        # 檢查用戶偏好
        if user_id:
            try:
                profile = UserProfile.objects.get(user_id=user_id)
                # 讀取用戶偏好設定
                user_preference = profile.monthly_quota.get("preferred_speaker_recognition")
                if user_preference:
                    return ModelProviderType(user_preference)
                
                # 根據訂閱計劃選擇
                if profile.subscription_plan == "premium":
                    return cls.PREMIUM_MODELS["speaker_recognition"]
                    
            except UserProfile.DoesNotExist:
                pass
        
        # 檢查環境設定
        env_preference = getattr(settings, "DEFAULT_SPEAKER_RECOGNIZER", None)
        if env_preference:
            try:
                return ModelProviderType(env_preference)
            except ValueError:
                pass
        
        # 大部分情況使用簡化版講者辨識
        return cls.DEFAULT_MODELS["speaker_recognition"]