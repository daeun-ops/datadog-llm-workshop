from __future__ import annotations

import os
import re

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}\b")
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_APIKEY = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16,})\b")
_CREDITCARD = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

REDACT_OUTPUT = os.getenv("WORKSHOP_REDACT_OUTPUT", "1") == "1"


def redact_text(text: str) -> str:
    if not text:
        return text
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _PHONE.sub("[REDACTED_PHONE]", text)
    text = _IP.sub("[REDACTED_IP]", text)
    text = _APIKEY.sub("[REDACTED_KEY]", text)
    text = _CREDITCARD.sub("[REDACTED_CARD]", text)
    return text


def redact_output(text: str) -> str:
    return redact_text(text) if REDACT_OUTPUT else text
