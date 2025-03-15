# apps/audio_manager/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import os
from datetime import timedelta

class AudioFile(models.Model):
    """音訊檔案模型，用於儲存和管理使用者上傳的課堂錄音"""
    
    PROCESSING_STATUS_CHOICES = [
        ('pending', '等待處理'),
        ('processing', '處理中'),
        ('completed', '已完成'),
        ('failed', '處理失敗'),
    ]
    
    # 基本資訊
    title = models.CharField(
        max_length=255, 
        verbose_name=_('標題'),
        help_text=_('音訊檔案的標題或名稱')
    )
    description = models.TextField(
        blank=True, 
        verbose_name=_('描述'),
        help_text=_('音訊檔案的簡要描述（選填）')
    )
    
    # 檔案資訊
    file = models.FileField(
        upload_to='audio_files/%Y/%m/',
        verbose_name=_('音訊檔案'),
        help_text=_('支援的格式：MP3, WAV, OGG, M4A, FLAC')
    )
    format = models.CharField(
        max_length=10, 
        blank=True, 
        verbose_name=_('檔案格式')
    )
    duration = models.FloatField(
        null=True, 
        blank=True, 
        verbose_name=_('時長（秒）')
    )
    file_size = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name=_('檔案大小（位元組）')
    )
    sample_rate = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name=_('採樣率 (Hz)')
    )
    channels = models.PositiveSmallIntegerField(
        null=True, 
        blank=True, 
        verbose_name=_('聲道數')
    )
    
    # 處理狀態
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending',
        verbose_name=_('處理狀態')
    )
    processing_message = models.TextField(
        blank=True, 
        verbose_name=_('處理訊息')
    )
    processing_method = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name=_('處理方法'),
        help_text=_('使用的轉錄引擎或模型')
    )
    
    # 關聯
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='audio_files',
        verbose_name=_('使用者')
    )
    
    # 時間記錄
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_('建立時間')
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('更新時間')
    )
    processed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name=_('處理完成時間')
    )
    
    class Meta:
        verbose_name = _('音訊檔案')
        verbose_name_plural = _('音訊檔案')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_duration_display(self):
        """顯示格式化的持續時間"""
        if not self.duration:
            return "00:00:00"
        
        td = timedelta(seconds=self.duration)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_file_size_display(self):
        """顯示人類可讀的檔案大小"""
        if not self.file_size:
            return "未知"
        
        # 轉換為 KB, MB, GB 等
        units = ['B', 'KB', 'MB', 'GB']
        size = float(self.file_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
    
    def get_file_extension(self):
        """獲取檔案副檔名"""
        _, ext = os.path.splitext(self.file.name)
        return ext.lstrip('.').lower()
    
    def update_metadata(self, duration=None, sample_rate=None, channels=None, format=None, file_size=None):
        """更新音訊檔案的元數據"""
        if duration is not None:
            self.duration = duration
        if sample_rate is not None:
            self.sample_rate = sample_rate
        if channels is not None:
            self.channels = channels
        if format is not None:
            self.format = format
        if file_size is not None:
            self.file_size = file_size
        
        self.save(update_fields=['duration', 'sample_rate', 'channels', 'format', 'file_size', 'updated_at'])
    
    def set_processing_status(self, status, message=""):
        """更新處理狀態和相關訊息"""
        self.processing_status = status
        if message:
            self.processing_message = message
        
        # 如果處理完成，設定處理時間
        if status == 'completed':
            from django.utils import timezone
            self.processed_at = timezone.now()
        
        self.save(update_fields=['processing_status', 'processing_message', 'processed_at', 'updated_at'])

class Transcript(models.Model):
    """音訊轉錄文本模型"""
    
    PROCESSING_METHODS = [
        ('whisper', 'OpenAI Whisper'),
        ('vosk', 'Vosk 本地引擎'),
        ('manual', '手動轉錄'),
    ]
    
    audio_file = models.OneToOneField(
        AudioFile, 
        on_delete=models.CASCADE, 
        related_name='transcript',
        verbose_name=_('音訊檔案')
    )
    full_text = models.TextField(
        verbose_name=_('完整文本'),
        help_text=_('完整的轉錄文本內容')
    )
    language = models.CharField(
        max_length=20,
        verbose_name=_('辨識語言'),
        default='zh-tw',
        help_text=_('轉錄辨識的語言')
    )
    processing_method = models.CharField(
        max_length=50,
        choices=PROCESSING_METHODS,
        default='whisper',
        verbose_name=_('處理方法'),
        help_text=_('使用的轉錄引擎或模型')
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('信心分數'),
        help_text=_('轉錄文本的整體信心分數 (0-1)')
    )
    is_processed = models.BooleanField(
        default=False,
        verbose_name=_('處理完成'),
        help_text=_('是否已完成處理（包括講者辨識等）')
    )
    word_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('字數'),
        help_text=_('轉錄文本的總字數')
    )
    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('處理時間(秒)'),
        help_text=_('轉錄處理所花費的時間(秒)')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('建立時間')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新時間')
    )
    
    class Meta:
        verbose_name = _('轉錄文本')
        verbose_name_plural = _('轉錄文本')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.audio_file.title} 的轉錄文本"
    
    def calculate_word_count(self):
        """計算轉錄文本字數"""
        if not self.full_text:
            return 0
        
        # 針對中文特別處理，移除標點符號和空白再計算字數
        import re
        text = re.sub(r'[^\w\s]', '', self.full_text)
        text = re.sub(r'\s+', '', text)
        self.word_count = len(text)
        return self.word_count
    
    def get_segments(self):
        """獲取所有文本片段，依時間排序"""
        return self.segments.all().order_by('start_time')
    
    def get_text_by_speaker(self, speaker_id=None):
        """獲取特定講者的所有文本"""
        segments = self.segments.filter(speaker_id=speaker_id) if speaker_id else self.segments.all()
        return '\n'.join([segment.text for segment in segments])
    
    def save(self, *args, **kwargs):
        # 保存前計算字數
        if self.full_text and not self.word_count:
            self.calculate_word_count()
        super().save(*args, **kwargs)
        
class TranscriptSegment(models.Model):
    """轉錄文本片段模型，用於存儲分段轉錄文本和講者信息"""
    
    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.CASCADE,
        related_name='segments',
        verbose_name=_('轉錄文本')
    )
    start_time = models.FloatField(
        verbose_name=_('開始時間(秒)'),
        help_text=_('片段開始時間(秒)')
    )
    end_time = models.FloatField(
        verbose_name=_('結束時間(秒)'),
        help_text=_('片段結束時間(秒)')
    )
    text = models.TextField(
        verbose_name=_('文本內容'),
        help_text=_('該時間段的轉錄文本')
    )
    speaker_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('講者ID'),
        help_text=_('講者識別ID')
    )
    speaker_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('講者名稱'),
        help_text=_('講者顯示名稱')
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('信心分數'),
        help_text=_('該片段的信心分數 (0-1)')
    )
    word_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('字數'),
        help_text=_('片段文本的字數')
    )
    is_manually_edited = models.BooleanField(
        default=False,
        verbose_name=_('手動編輯'),
        help_text=_('是否被手動編輯過')
    )
    
    class Meta:
        verbose_name = _('轉錄片段')
        verbose_name_plural = _('轉錄片段')
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['transcript', 'speaker_id']),
            models.Index(fields=['start_time', 'end_time']),
        ]
    
    def __str__(self):
        return f"{self.start_time:.1f}-{self.end_time:.1f}s: {self.text[:30]}{'...' if len(self.text) > 30 else ''}"
    
    @property
    def duration(self):
        """片段持續時間(秒)"""
        return self.end_time - self.start_time
    
    def get_formatted_timestamp(self, srt_format=True):
        """
        獲取格式化的時間戳記
        
        Args:
            srt_format (bool): 如為True則返回SRT格式 (00:00:00,000)，否則返回一般格式 (00:00.000)
        """
        if srt_format:
            start = self.format_time_srt(self.start_time)
            end = self.format_time_srt(self.end_time)
        else:
            start = self.format_time(self.start_time)
            end = self.format_time(self.end_time)
        return f"{start} --> {end}"
    
    @staticmethod
    def format_time(seconds):
        """將秒數格式化為 MM:SS.ms 格式"""
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"
    
    @staticmethod
    def format_time_srt(seconds):
        """將秒數格式化為 SRT 格式 (HH:MM:SS,ms)"""
        hours = int(seconds // 3600)
        seconds %= 3600
        minutes = int(seconds // 60)
        seconds %= 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def to_srt_format(self, index):
        """
        將片段轉換為 SRT 格式
        
        Args:
            index (int): SRT 片段索引
        
        Returns:
            str: SRT 格式的文本
        """
        timestamp = self.get_formatted_timestamp(srt_format=True)
        return f"{index}\n{timestamp}\n{self.text}\n"
    
    def to_vtt_format(self, include_speaker=True):
        """
        將片段轉換為 WebVTT 格式
        
        Args:
            include_speaker (bool): 是否包含講者信息
        
        Returns:
            str: WebVTT 格式的文本
        """
        timestamp = self.get_formatted_timestamp(srt_format=False)
        speaker_info = f"<v {self.speaker_name or self.speaker_id}>" if include_speaker and self.speaker_id else ""
        return f"{timestamp}\n{speaker_info}{self.text}\n"
    
    def to_dict(self):
        """將片段轉換為字典格式"""
        return {
            'id': self.id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'text': self.text,
            'duration': self.duration,
            'speaker_id': self.speaker_id,
            'speaker_name': self.speaker_name,
            'confidence': self.confidence,
            'word_count': self.word_count,
            'is_manually_edited': self.is_manually_edited
        }
    
    def update_word_count(self):
        """更新片段字數"""
        # 針對中文特別處理，移除標點符號和空白再計算字數
        import re
        text = re.sub(r'[^\w\s]', '', self.text)
        text = re.sub(r'\s+', '', text)
        self.word_count = len(text)
        return self.word_count
    
    def merge_with(self, other_segment):
        """
        與另一個片段合併
        
        Args:
            other_segment (TranscriptSegment): 要合併的另一個片段
        
        Returns:
            TranscriptSegment: 合併後的片段（自身）
        """
        if self.transcript_id != other_segment.transcript_id:
            raise ValueError("無法合併不同轉錄文本的片段")
        
        # 更新時間範圍
        self.start_time = min(self.start_time, other_segment.start_time)
        self.end_time = max(self.end_time, other_segment.end_time)
        
        # 合併文本
        if self.start_time == other_segment.start_time:
            # 如果開始時間相同，依結束時間排序
            segments = sorted([self, other_segment], key=lambda s: s.end_time)
        else:
            # 依開始時間排序
            segments = sorted([self, other_segment], key=lambda s: s.start_time)
        
        self.text = " ".join([s.text for s in segments])
        
        # 如果講者不同，更新講者信息
        if self.speaker_id != other_segment.speaker_id:
            self.speaker_id = None
            self.speaker_name = "多位講者"
        
        # 更新字數
        self.update_word_count()
        self.is_manually_edited = True
        
        return self
    
    def split_at(self, split_time):
        """
        在指定時間點分割片段
        
        Args:
            split_time (float): 分割時間點
        
        Returns:
            tuple: (左側片段, 右側片段)
        """
        if split_time <= self.start_time or split_time >= self.end_time:
            raise ValueError(f"分割時間 {split_time} 必須在片段時間範圍內 ({self.start_time}, {self.end_time})")
        
        # 計算分割點在文本中的相對位置
        position_ratio = (split_time - self.start_time) / self.duration
        # 簡單地按照時間比例分割文本（實際應用可能需要更精確的方法）
        text_position = max(1, int(len(self.text) * position_ratio))
        
        # 創建右側新片段
        right_segment = TranscriptSegment(
            transcript=self.transcript,
            start_time=split_time,
            end_time=self.end_time,
            text=self.text[text_position:],
            speaker_id=self.speaker_id,
            speaker_name=self.speaker_name,
            confidence=self.confidence,
            is_manually_edited=True
        )
        
        # 更新左側片段（自身）
        self.end_time = split_time
        self.text = self.text[:text_position]
        self.is_manually_edited = True
        
        # 更新字數
        self.update_word_count()
        right_segment.update_word_count()
        
        return self, right_segment
    
    def save(self, *args, **kwargs):
        # 保存前更新字數
        if self.text and not self.word_count:
            self.update_word_count()
        super().save(*args, **kwargs)
    @classmethod
    def bulk_create_from_segments(cls, transcript, segments_data):
        """
        從片段數據批量創建轉錄片段
        
        Args:
            transcript (Transcript): 轉錄對象
            segments_data (list): 片段數據列表，每個元素應包含:
                - start_time: 開始時間
                - end_time: 結束時間
                - text: 文本內容
                - speaker_id: (可選) 講者ID
                - confidence: (可選) 信心分數
        
        Returns:
            list: 創建的 TranscriptSegment 對象列表
        """
        transcript_segments = []
        
        for segment_data in segments_data:
            segment = cls(
                transcript=transcript,
                start_time=segment_data['start_time'],
                end_time=segment_data['end_time'],
                text=segment_data['text'],
                speaker_id=segment_data.get('speaker_id'),
                speaker_name=segment_data.get('speaker_name'),
                confidence=segment_data.get('confidence')
            )
            segment.update_word_count()
            transcript_segments.append(segment)
        
        # 批量創建片段
        created_segments = cls.objects.bulk_create(transcript_segments)
        
        # 更新轉錄文本的全文
        if created_segments:
            all_text = ' '.join(segment.text for segment in transcript_segments)
            transcript.full_text = all_text
            transcript.calculate_word_count()
            transcript.save()
        
        return created_segments

    @classmethod
    def export_to_srt(cls, transcript_id):
        """
        將轉錄片段導出為 SRT 格式
        
        Args:
            transcript_id: 轉錄 ID
        
        Returns:
            str: SRT 格式的完整文本
        """
        segments = cls.objects.filter(transcript_id=transcript_id).order_by('start_time')
        srt_content = []
        
        for i, segment in enumerate(segments, 1):
            srt_content.append(segment.to_srt_format(i))
        
        return "\n".join(srt_content)

    @classmethod
    def export_to_vtt(cls, transcript_id, include_speaker=True):
        """
        將轉錄片段導出為 WebVTT 格式
        
        Args:
            transcript_id: 轉錄 ID
            include_speaker: 是否包含講者信息
        
        Returns:
            str: WebVTT 格式的完整文本
        """
        segments = cls.objects.filter(transcript_id=transcript_id).order_by('start_time')
        vtt_content = ["WEBVTT\n"]
        
        for segment in segments:
            vtt_content.append(segment.to_vtt_format(include_speaker))
        
        return "\n".join(vtt_content)

    @classmethod
    def export_by_speaker(cls, transcript_id):
        """
        按講者導出轉錄文本
        
        Args:
            transcript_id: 轉錄 ID
        
        Returns:
            dict: 以講者ID為鍵，內容為該講者的全部文本
        """
        segments = cls.objects.filter(transcript_id=transcript_id).order_by('start_time')
        speaker_texts = {}
        
        for segment in segments:
            speaker_id = segment.speaker_id or "unknown"
            if speaker_id not in speaker_texts:
                speaker_texts[speaker_id] = {
                    'speaker_name': segment.speaker_name or speaker_id,
                    'text': [],
                    'total_time': 0
                }
            
            speaker_texts[speaker_id]['text'].append(segment.text)
            speaker_texts[speaker_id]['total_time'] += segment.duration
        
        # 合併每個講者的文本
        for speaker_id in speaker_texts:
            speaker_texts[speaker_id]['text'] = ' '.join(speaker_texts[speaker_id]['text'])
        
        return speaker_texts