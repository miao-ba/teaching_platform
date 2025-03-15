"""
SRT 字幕檔案生成模組。

此模組提供將轉錄片段轉換為標準 SRT 格式的功能，
支援多種輸入來源和輸出選項。
"""
from typing import List, Dict, Any, Union, Optional, TextIO
from datetime import timedelta
import re
import io

class SRTGenerator:
    """SRT 字幕生成器，將轉錄片段轉換為 SubRip Text 格式"""
    
    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """
        將秒數轉換為 SRT 時間戳格式 (HH:MM:SS,mmm)
        
        參數:
            seconds: 時間點（秒）
            
        返回:
            格式化的時間戳字符串
        """
        # 處理負數時間（避免錯誤）
        seconds = max(0, seconds)
        
        # 轉換為時分秒毫秒
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        seconds_whole, seconds_frac = divmod(seconds, 1)
        milliseconds = int(seconds_frac * 1000)
        
        # 格式化為 SRT 時間戳
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds_whole):02d},{milliseconds:03d}"
    
    @staticmethod
    def generate_from_segments(segments: List[Dict[str, Any]], include_speaker: bool = True) -> str:
        """
        從轉錄片段生成 SRT 字幕內容
        
        參數:
            segments: 轉錄片段列表，每個片段包含 start, end, text 和可選的 speaker_id/speaker_name
            include_speaker: 是否在字幕中包含講者信息
            
        返回:
            SRT 格式的字幕內容
        """
        if not segments:
            return ""
        
        # 按開始時間排序片段
        sorted_segments = sorted(segments, key=lambda s: s.get('start', 0))
        
        srt_lines = []
        for i, segment in enumerate(sorted_segments, 1):
            # 獲取必要數據
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            text = segment.get('text', '').strip()
            
            # 跳過空文本片段
            if not text:
                continue
            
            # 獲取講者信息
            speaker_name = None
            if include_speaker:
                # 優先使用講者名稱，如果沒有則使用講者ID
                speaker_name = segment.get('speaker_name')
                if not speaker_name and 'speaker_id' in segment and segment['speaker_id']:
                    speaker_name = f"講者 {segment['speaker_id']}"
            
            # 序號
            srt_lines.append(str(i))
            
            # 時間戳
            timestamp = (
                f"{SRTGenerator.format_timestamp(start_time)} --> "
                f"{SRTGenerator.format_timestamp(end_time)}"
            )
            srt_lines.append(timestamp)
            
            # 文本（加上講者信息）
            if speaker_name:
                srt_lines.append(f"[{speaker_name}] {text}")
            else:
                srt_lines.append(text)
            
            # 空行（分隔不同字幕）
            srt_lines.append("")
        
        return "\n".join(srt_lines)
    
    @staticmethod
    def generate_from_transcript(transcript, include_speaker: bool = True) -> str:
        """
        從 Transcript 數據庫模型生成 SRT 字幕內容
        
        參數:
            transcript: Transcript 模型實例
            include_speaker: 是否在字幕中包含講者信息
            
        返回:
            SRT 格式的字幕內容
        """
        # 從 Transcript 獲取所有片段
        segments = []
        
        try:
            # 獲取片段並轉換為字典格式
            for segment in transcript.segments.all().order_by('start_time'):
                segments.append({
                    'start': segment.start_time,
                    'end': segment.end_time,
                    'text': segment.text,
                    'speaker_id': segment.speaker_id,
                    'speaker_name': segment.speaker_name
                })
                
        except (AttributeError, TypeError) as e:
            # 處理傳入的可能不是 Transcript 實例的情況
            return f"# 無法生成 SRT: {str(e)}"
        
        return SRTGenerator.generate_from_segments(segments, include_speaker)
    
    @staticmethod
    def write_to_file(segments: List[Dict[str, Any]], file_path: str, include_speaker: bool = True) -> bool:
        """
        將 SRT 字幕內容寫入檔案
        
        參數:
            segments: 轉錄片段列表
            file_path: 輸出檔案路徑
            include_speaker: 是否在字幕中包含講者信息
            
        返回:
            操作是否成功
        """
        try:
            srt_content = SRTGenerator.generate_from_segments(segments, include_speaker)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
                
            return True
        except Exception as e:
            print(f"SRT 寫入失敗: {str(e)}")
            return False
    
    @staticmethod
    def get_file_object(segments: List[Dict[str, Any]], include_speaker: bool = True) -> io.StringIO:
        """
        取得包含 SRT 內容的檔案物件，用於 HTTP 響應
        
        參數:
            segments: 轉錄片段列表
            include_speaker: 是否在字幕中包含講者信息
            
        返回:
            包含 SRT 內容的 StringIO 物件
        """
        srt_content = SRTGenerator.generate_from_segments(segments, include_speaker)
        return io.StringIO(srt_content)
    
    @staticmethod
    def merge_short_segments(segments: List[Dict[str, Any]], min_duration: float = 1.0, 
                             max_gap: float = 0.3) -> List[Dict[str, Any]]:
        """
        合併短片段，提高字幕可讀性
        
        參數:
            segments: 轉錄片段列表
            min_duration: 最短片段時長（秒）
            max_gap: 合併的最大間隔（秒）
            
        返回:
            合併後的片段列表
        """
        if not segments:
            return []
        
        # 按開始時間排序
        sorted_segments = sorted(segments, key=lambda s: s.get('start', 0))
        
        merged_segments = []
        current = None
        
        for segment in sorted_segments:
            # 如果還沒有當前片段，直接使用這個片段
            if current is None:
                current = segment.copy()
                continue
            
            # 計算與前一個片段的間隔
            gap = segment.get('start', 0) - current.get('end', 0)
            
            # 決定是否合併
            same_speaker = segment.get('speaker_id') == current.get('speaker_id')
            short_duration = (current.get('end', 0) - current.get('start', 0)) < min_duration
            small_gap = gap <= max_gap
            
            if same_speaker and (short_duration or small_gap):
                # 合併片段
                current['end'] = segment.get('end', 0)
                current['text'] += " " + segment.get('text', '')
            else:
                # 添加當前片段並開始新片段
                merged_segments.append(current)
                current = segment.copy()
        
        # 添加最後一個片段
        if current:
            merged_segments.append(current)
        
        return merged_segments


class VTTGenerator:
    """WebVTT 字幕生成器，將轉錄片段轉換為 Web Video Text Tracks 格式"""
    
    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """
        將秒數轉換為 VTT 時間戳格式 (HH:MM:SS.mmm)
        
        參數:
            seconds: 時間點（秒）
            
        返回:
            格式化的時間戳字符串
        """
        # 處理負數時間（避免錯誤）
        seconds = max(0, seconds)
        
        # 轉換為時分秒毫秒
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        seconds_whole, seconds_frac = divmod(seconds, 1)
        milliseconds = int(seconds_frac * 1000)
        
        # 格式化為 VTT 時間戳（注意 VTT 使用點而非逗號分隔毫秒）
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds_whole):02d}.{milliseconds:03d}"
    
    @staticmethod
    def generate_from_segments(segments: List[Dict[str, Any]], include_speaker: bool = True) -> str:
        """從轉錄片段生成 WebVTT 字幕內容"""
        if not segments:
            return "WEBVTT\n\n"
        
        # VTT 文件頭
        vtt_lines = ["WEBVTT", ""]
        
        # 按開始時間排序片段
        sorted_segments = sorted(segments, key=lambda s: s.get('start', 0))
        
        for i, segment in enumerate(sorted_segments, 1):
            # 獲取必要數據
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            text = segment.get('text', '').strip()
            
            # 跳過空文本片段
            if not text:
                continue
            
            # 獲取講者信息
            speaker_name = None
            if include_speaker:
                speaker_name = segment.get('speaker_name')
                if not speaker_name and 'speaker_id' in segment and segment['speaker_id']:
                    speaker_name = f"講者 {segment['speaker_id']}"
            
            # 可選的序號（VTT 中序號非必須）
            vtt_lines.append(str(i))
            
            # 時間戳
            timestamp = (
                f"{VTTGenerator.format_timestamp(start_time)} --> "
                f"{VTTGenerator.format_timestamp(end_time)}"
            )
            vtt_lines.append(timestamp)
            
            # 文本（加上講者信息）
            if speaker_name:
                vtt_lines.append(f"<v {speaker_name}>{text}</v>")
            else:
                vtt_lines.append(text)
            
            # 空行（分隔不同字幕）
            vtt_lines.append("")
        
        return "\n".join(vtt_lines)


def convert_srt_to_vtt(srt_content: str) -> str:
    """
    將 SRT 格式轉換為 WebVTT 格式
    
    參數:
        srt_content: SRT 格式的字幕內容
        
    返回:
        WebVTT 格式的字幕內容
    """
    # 添加 WEBVTT 頭
    vtt_content = "WEBVTT\n\n"
    
    # 移除 BOM
    if srt_content.startswith('\ufeff'):
        srt_content = srt_content[1:]
    
    # 替換時間戳格式（逗號換成點）
    vtt_content += re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})', r'\1.\2', srt_content)
    
    return vtt_content