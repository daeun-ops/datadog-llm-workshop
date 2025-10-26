import re

EMAIL_RE = re.compile(r'([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})')
PHONE_RE = re.compile(r'(\+?\d[\d\-\s]{7,}\d)')

def mask_pii(text: str) -> str:
    if not text:
        return text
    text = EMAIL_RE.sub(lambda m: m.group(1)[0] + "***@" + m.group(2), text)
    text = PHONE_RE.sub(lambda m: m.group(1)[:3] + "****", text)
    return text
