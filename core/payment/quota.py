"""
使用配額管理系統，提供免費和付費服務之間的界限控制。
"""
from typing import Dict, Any, Tuple, Optional
from enum import Enum
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile, UsageLog

User = get_user_model()

class ServiceType(str, Enum):
    """服務類型枚舉"""
    AUDIO_TRANSCRIPTION = "audio_transcription"
    SPEAKER_IDENTIFICATION = "speaker_identification"
    SUMMARY_GENERATION = "summary_generation"
    CONTENT_GENERATION = "content_generation"
    RAG_SEARCH = "rag_search"

class QuotaManager:
    """配額管理類"""
    
    # 不同訂閱計劃的配額定義
    PLAN_QUOTAS = {
        "free": {
            ServiceType.AUDIO_TRANSCRIPTION: {
                "monthly_limit": 5,  # 每月5個檔案
                "max_duration": 60 * 60,  # 最大60分鐘
                "file_size_limit": 100 * 1024 * 1024,  # 100MB
            },
            ServiceType.SPEAKER_IDENTIFICATION: {
                "monthly_limit": 5,  # 每月5個檔案
                "enabled": True,
            },
            ServiceType.SUMMARY_GENERATION: {
                "monthly_limit": 5,  # 每月5個摘要
                "enabled": True,
            },
            ServiceType.CONTENT_GENERATION: {
                "monthly_limit": 2,  # 每月2個筆記
                "enabled": True,
                "allowed_types": ["notes"],  # 只允許筆記
            },
            ServiceType.RAG_SEARCH: {
                "monthly_limit": 10,  # 每月10次搜尋
                "enabled": True,
            },
        },
        "basic": {
            ServiceType.AUDIO_TRANSCRIPTION: {
                "monthly_limit": 20,  # 每月20個檔案
                "max_duration": 180 * 60,  # 最大180分鐘
                "file_size_limit": 500 * 1024 * 1024,  # 500MB
            },
            ServiceType.SPEAKER_IDENTIFICATION: {
                "monthly_limit": 20,  # 每月20個檔案
                "enabled": True,
            },
            ServiceType.SUMMARY_GENERATION: {
                "monthly_limit": 20,  # 每月20個摘要
                "enabled": True,
            },
            ServiceType.CONTENT_GENERATION: {
                "monthly_limit": 20,  # 每月20個內容
                "enabled": True,
                "allowed_types": ["notes", "quiz"],  # 筆記和習題
            },
            ServiceType.RAG_SEARCH: {
                "monthly_limit": 100,  # 每月100次搜尋
                "enabled": True,
            },
        },
        "premium": {
            ServiceType.AUDIO_TRANSCRIPTION: {
                "monthly_limit": -1,  # 無限制
                "max_duration": 480 * 60,  # 最大480分鐘
                "file_size_limit": 2 * 1024 * 1024 * 1024,  # 2GB
            },
            ServiceType.SPEAKER_IDENTIFICATION: {
                "monthly_limit": -1,  # 無限制
                "enabled": True,
            },
            ServiceType.SUMMARY_GENERATION: {
                "monthly_limit": -1,  # 無限制
                "enabled": True,
            },
            ServiceType.CONTENT_GENERATION: {
                "monthly_limit": -1,  # 無限制
                "enabled": True,
                "allowed_types": ["notes", "quiz", "presentation"],  # 所有類型
            },
            ServiceType.RAG_SEARCH: {
                "monthly_limit": -1,  # 無限制
                "enabled": True,
            },
        },
    }
    
    @classmethod
    def check_quota(cls, user_id: int, service_type: ServiceType, **kwargs) -> Tuple[bool, str]:
        """
        檢查使用者是否有足夠的配額使用服務。
        
        參數:
            user_id: 使用者ID
            service_type: 服務類型
            **kwargs: 額外參數，例如:
                - content_type: 內容類型 (筆記、習題等)
                - file_size: 檔案大小 (位元組)
                - duration: 音訊時長 (秒)
        
        返回:
            (是否允許, 訊息)
        """
        try:
            user = User.objects.get(id=user_id)
            profile = UserProfile.objects.get(user=user)
            plan = profile.subscription_plan
            
            # 獲取計劃配額
            plan_quota = cls.PLAN_QUOTAS.get(plan, {}).get(service_type, {})
            
            # 檢查服務是否啟用
            if not plan_quota.get("enabled", False):
                return False, f"您的帳戶類型 ({plan}) 不支援此服務。"
            
            # 檢查內容類型限制
            if service_type == ServiceType.CONTENT_GENERATION:
                content_type = kwargs.get("content_type")
                allowed_types = plan_quota.get("allowed_types", [])
                if content_type not in allowed_types:
                    return False, f"您的帳戶類型 ({plan}) 不支援生成 {content_type} 內容。"
            
            # 檢查檔案大小限制
            if service_type == ServiceType.AUDIO_TRANSCRIPTION and "file_size" in kwargs:
                file_size = kwargs.get("file_size", 0)
                max_size = plan_quota.get("file_size_limit", 0)
                if max_size > 0 and file_size > max_size:
                    max_mb = max_size / (1024 * 1024)
                    return False, f"檔案過大。您的帳戶類型最大支援 {max_mb:.0f}MB 的檔案。"
            
            # 檢查音訊時長限制
            if service_type in [ServiceType.AUDIO_TRANSCRIPTION, ServiceType.SPEAKER_IDENTIFICATION] and "duration" in kwargs:
                duration = kwargs.get("duration", 0)
                max_duration = plan_quota.get("max_duration", 0)
                if max_duration > 0 and duration > max_duration:
                    max_min = max_duration / 60
                    return False, f"音訊時長過長。您的帳戶類型最大支援 {max_min:.0f}分鐘 的音訊。"
            
            # 檢查每月使用量限制
            monthly_limit = plan_quota.get("monthly_limit", 0)
            if monthly_limit > 0:
                # 計算本月使用量
                now = datetime.now()
                month_start = datetime(now.year, now.month, 1)
                month_usage = UsageLog.objects.filter(
                    user=user,
                    service_type=service_type,
                    created_at__gte=month_start
                ).count()
                
                if month_usage >= monthly_limit:
                    return False, f"您已達到本月使用限制 ({monthly_limit} 次)。請下個月再試或升級您的帳戶。"
            
            return True, "允許使用服務"
            
        except User.DoesNotExist:
            return False, "使用者不存在"
        except UserProfile.DoesNotExist:
            return False, "使用者配置檔不存在"
        except Exception as e:
            return False, f"配額檢查錯誤: {str(e)}"
    
    @classmethod
    def log_usage(cls, user_id: int, service_type: ServiceType, **kwargs) -> None:
        """
        記錄服務使用情況
        
        參數:
            user_id: 使用者ID
            service_type: 服務類型
            **kwargs: 額外資訊，例如:
                - operation: 操作描述
                - resource_id: 資源ID
                - tokens_used: 使用的token數量
                - model_name: 模型名稱
                - duration: 音訊時長(秒)
        """
        try:
            user = User.objects.get(id=user_id)
            
            log_data = {
                "user": user,
                "service_type": service_type,
                "operation": kwargs.get("operation", service_type),
                "resource_id": kwargs.get("resource_id"),
                "tokens_used": kwargs.get("tokens_used", 0),
                "model_name": kwargs.get("model_name", ""),
                "audio_duration": kwargs.get("duration"),
            }
            
            UsageLog.objects.create(**log_data)
            
        except Exception as e:
            # 記錄錯誤但不影響主流程
            print(f"使用日誌記錄錯誤: {str(e)}")