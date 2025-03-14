from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """獲取字典值的模板過濾器"""
    return dictionary.get(key, 0)