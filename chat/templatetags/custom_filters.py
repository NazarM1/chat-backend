from django import template

register = template.Library()

@register.filter
def has_attr(obj, attr_name):
    return hasattr(obj, attr_name)

@register.filter
def my_custom_filter(value):
    return value.upper()