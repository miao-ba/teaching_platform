# apps/accounts/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
    
    def test_profile_created_automatically(self):
        """測試使用者建立時是否自動創建配置檔"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, UserProfile)
    
    def test_profile_default_values(self):
        """測試配置檔的預設值"""
        profile = self.user.profile
        self.assertEqual(profile.subscription_plan, 'free')
        self.assertTrue('audio_transcription' in profile.monthly_quota)
        self.assertEqual(profile.used_quota, {})
    
    def test_get_available_quota(self):
        """測試獲取可用配額功能"""
        profile = self.user.profile
        
        # 設定測試資料
        profile.monthly_quota = {'test_service': 10}
        profile.used_quota = {'test_service': 3}
        profile.save()
        
        # 驗證計算
        self.assertEqual(profile.get_available_quota('test_service'), 7)
        self.assertEqual(profile.get_available_quota('nonexistent_service'), 0)