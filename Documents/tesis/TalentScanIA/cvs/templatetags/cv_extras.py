import re

from django import template

register = template.Library()


@register.filter
def chips(value, limit=8):
    if not value:
        return []

    if isinstance(value, (list, tuple)):
        raw_items = value
    else:
        raw_items = re.split(r"[,;\n|]+", str(value))

    cleaned = []
    seen = set()

    for item in raw_items:
        text = str(item or "").strip(" \t\r\n-•")
        key = text.lower()

        if not text or key == "no informado" or key in seen:
            continue

        cleaned.append(text)
        seen.add(key)

        if len(cleaned) >= int(limit):
            break

    return cleaned


@register.filter
def remaining_chips_count(value, limit=8):
    if not value:
        return 0

    if isinstance(value, (list, tuple)):
        raw_items = value
    else:
        raw_items = re.split(r"[,;\n|]+", str(value))

    total = len([
        item
        for item in raw_items
        if str(item or "").strip(" \t\r\n-•")
    ])

    return max(total - int(limit), 0)
