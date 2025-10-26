import re
import tldextract

BANNED_PATTERNS = [
    r"ignore (all|the) previous instructions",
    r"disregard (the )?system prompt",
    r"system: .* override",
    r"exfiltrate|leak (data|key|secret)",
]

URL_PATTERN = re.compile(r'https?://\S+')

def contains_injection(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    for pat in BANNED_PATTERNS:
        if re.search(pat, lower):
            return True
    return False

def external_links(text: str) -> list[str]:
    return URL_PATTERN.findall(text or "")

def is_external_domain(url: str, allowlist: set[str] | None = None) -> bool:
    ex = tldextract.extract(url)
    domain = f"{ex.domain}.{ex.suffix}".lower() if ex.suffix else ex.domain.lower()
    if allowlist and domain in allowlist:
        return False
    return True
