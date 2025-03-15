from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import AudioFile, Transcript, TranscriptSegment
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class TranscriptModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        # 創建測試音訊檔案
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp3')
        self.audio_file = AudioFile.objects.create(
            title='測試音訊',
            file=SimpleUploadedFile(
                name='test_audio.mp3',
                content=temp_file.read(),
                content_type='audio/mpeg'
            ),
            user=self.user
        )
        temp_file.close()
        
        # 創建轉錄文本
        self.transcript = Transcript.objects.create(
            audio_file=self.audio_file,
            full_text="這是一個測試用的轉錄文本內容。",
            language="zh-tw",
            processing_method="whisper"
        )
        
        # 創建轉錄片段
        self.segment1 = TranscriptSegment.objects.create(
            transcript=self.transcript,
            start_time=0.0,
            end_time=2.5,
            text="這是一個",
            speaker_id="speaker_0",
            speaker_name="講者1",
            confidence=0.95
        )
        
        self.segment2 = TranscriptSegment.objects.create(
            transcript=self.transcript,
            start_time=2.5,
            end_time=5.0,
            text="測試用的轉錄文本內容。",
            speaker_id="speaker_0",
            speaker_name="講者1",
            confidence=0.92
        )
    
    def test_transcript_creation(self):
        self.assertEqual(self.transcript.audio_file, self.audio_file)
        self.assertEqual(self.transcript.language, "zh-tw")
        self.assertEqual(self.transcript.processing_method, "whisper")
        
    def test_word_count_calculation(self):
        self.transcript.calculate_word_count()
        self.transcript.save()
        self.assertEqual(self.transcript.word_count, 12)
        
    def test_get_segments(self):
        segments = self.transcript.get_segments()
        self.assertEqual(segments.count(), 2)
        self.assertEqual(segments.first(), self.segment1)
        
    def test_get_text_by_speaker(self):
        speaker_text = self.transcript.get_text_by_speaker("speaker_0")
        self.assertIn("這是一個", speaker_text)
        self.assertIn("測試用的轉錄文本內容", speaker_text)
        
    def test_segment_duration(self):
        self.assertEqual(self.segment1.duration, 2.5)
        
    def test_segment_formatted_timestamp(self):
        expected = "00:00.000 --> 00:02.500"
        self.assertEqual(self.segment1.get_formatted_timestamp(), expected)
# 在 apps/audio_manager/tests.py 中添加

class TranscriptSegmentTest(TestCase):
    def setUp(self):
        # 創建測試用戶和音訊檔案
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        # 創建測試音訊檔案
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp3')
        self.audio_file = AudioFile.objects.create(
            title='測試音訊',
            file=SimpleUploadedFile(
                name='test_audio.mp3',
                content=temp_file.read(),
                content_type='audio/mpeg'
            ),
            user=self.user
        )
        temp_file.close()
        
        # 創建轉錄文本
        self.transcript = Transcript.objects.create(
            audio_file=self.audio_file,
            full_text="這是一個測試用的轉錄文本內容。",
            language="zh-tw",
            processing_method="whisper"
        )
        
        # 創建轉錄片段
        self.segments_data = [
            {
                'start_time': 0.0,
                'end_time': 2.5,
                'text': "這是",
                'speaker_id': "speaker_0",
                'speaker_name': "講者1",
                'confidence': 0.95
            },
            {
                'start_time': 2.5,
                'end_time': 4.0,
                'text': "一個測試用的",
                'speaker_id': "speaker_1",
                'speaker_name': "講者2",
                'confidence': 0.92
            },
            {
                'start_time': 4.0,
                'end_time': 5.5,
                'text': "轉錄文本內容。",
                'speaker_id': "speaker_0",
                'speaker_name': "講者1",
                'confidence': 0.90
            }
        ]
        
        self.segments = TranscriptSegment.bulk_create_from_segments(
            self.transcript, self.segments_data
        )
    
    def test_segment_creation(self):
        self.assertEqual(TranscriptSegment.objects.count(), 3)
        
        segment = TranscriptSegment.objects.first()
        self.assertEqual(segment.start_time, 0.0)
        self.assertEqual(segment.end_time, 2.5)
        self.assertEqual(segment.text, "這是")
        self.assertEqual(segment.speaker_id, "speaker_0")
    
    def test_duration_property(self):
        segment = TranscriptSegment.objects.get(start_time=2.5)
        self.assertEqual(segment.duration, 1.5)
    
    def test_formatted_timestamp(self):
        segment = TranscriptSegment.objects.get(start_time=0.0)
        self.assertEqual(segment.get_formatted_timestamp(False), "00:00.000 --> 00:02.500")
        self.assertEqual(segment.get_formatted_timestamp(True), "00:00:00,000 --> 00:00:02,500")
    
    def test_srt_format(self):
        segment = TranscriptSegment.objects.get(start_time=0.0)
        expected = "1\n00:00:00,000 --> 00:00:02,500\n這是\n"
        self.assertEqual(segment.to_srt_format(1), expected)
    
    def test_export_to_srt(self):
        srt_content = TranscriptSegment.export_to_srt(self.transcript.id)
        self.assertIn("00:00:00,000 --> 00:00:02,500", srt_content)
        self.assertIn("00:00:02,500 --> 00:00:04,000", srt_content)
        self.assertIn("00:00:04,000 --> 00:00:05,500", srt_content)
    
    def test_export_by_speaker(self):
        speaker_texts = TranscriptSegment.export_by_speaker(self.transcript.id)
        
        self.assertIn("speaker_0", speaker_texts)
        self.assertIn("speaker_1", speaker_texts)
        
        self.assertIn("這是", speaker_texts["speaker_0"]["text"])
        self.assertIn("轉錄文本內容", speaker_texts["speaker_0"]["text"])
        self.assertIn("一個測試用的", speaker_texts["speaker_1"]["text"])
        
        self.assertEqual(speaker_texts["speaker_0"]["total_time"], 4.0)  # 0-2.5 + 4.0-5.5
        self.assertEqual(speaker_texts["speaker_1"]["total_time"], 1.5)  # 2.5-4.0
    
    def test_merge_segments(self):
        segment1 = TranscriptSegment.objects.get(start_time=0.0)
        segment2 = TranscriptSegment.objects.get(start_time=2.5)
        
        merged = segment1.merge_with(segment2)
        merged.save()
        
        # 驗證合併結果
        self.assertEqual(merged.start_time, 0.0)
        self.assertEqual(merged.end_time, 4.0)
        self.assertEqual(merged.text, "這是 一個測試用的")
        self.assertIsNone(merged.speaker_id)  # 因為不同講者合併
        self.assertEqual(merged.speaker_name, "多位講者")
        self.assertTrue(merged.is_manually_edited)
        
        # 確認第二個片段已被刪除
        self.assertEqual(TranscriptSegment.objects.count(), 2)
    
    def test_split_segment(self):
        segment = TranscriptSegment.objects.get(start_time=2.5)  # "一個測試用的"
        
        left, right = segment.split_at(3.0)
        right.save()  # left (原始片段) 會在 split_at 中保存
        
        # 驗證分割結果
        self.assertEqual(left.start_time, 2.5)
        self.assertEqual(left.end_time, 3.0)
        # 文字分割不會很精確，但應該大致相當於原文的前 1/3
        self.assertLess(len(left.text), len("一個測試用的"))
        
        self.assertEqual(right.start_time, 3.0)
        self.assertEqual(right.end_time, 4.0)
        self.assertGreater(len(right.text), 0)
        
        # 確認片段數增加了 1
        self.assertEqual(TranscriptSegment.objects.count(), 4)