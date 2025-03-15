# apps/audio_manager/templatetags/audio_tags.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """獲取字典值的模板過濾器"""
    return dictionary.get(key, '')

@register.filter
def format_duration(seconds):
    """將秒數格式化為時:分:秒格式"""
    if not seconds:
        return "00:00:00"
    
    from datetime import timedelta
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

@register.filter
def format_timestamp(seconds):
    """將秒數格式化為分:秒格式"""
    if not seconds:
        return "00:00"
    
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

@register.filter
def status_badge(status):
    """根據狀態返回徽章顏色"""
    colors = {
        'pending': 'warning',
        'processing': 'info',
        'completed': 'success',
        'failed': 'danger'
    }
    return colors.get(status, 'secondary')