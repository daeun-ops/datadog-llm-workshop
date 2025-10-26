from __future__ import annotations
import os
from typing import List
try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None

_MODEL_NAME = os.getenv("NLI_MODEL", "cross-encoder/nli-deberta-v3-base")
_ce = None

def _ensure_ce():
    global _ce
    if _ce is None and CrossEncoder:
        try:
            _ce = CrossEncoder(_MODEL_NAME)
        except Exception:
            _ce = None
    return _ce

def support_score(answer: str, contexts: List[str]) -> float:
    """Return 0~1 support score; uses NLI if available else lexical heuristic."""
    if not answer or not contexts:
        return 0.0
    ce = _ensure_ce()
    if ce:
        pairs = [(ctx, answer) for ctx in contexts]
        scores = ce.predict(pairs)
        return float(max(scores)) if hasattr(scores, "__len__") else float(scores)
    import re
    aw = set(re.findall(r"\w+", answer.lower()))
    best = 0.0
    for ctx in contexts:
        cw = set(re.findall(r"\w+", ctx.lower()))
        inter = len(aw & cw)
        best = max(best, inter / max(1, len(aw)))
    return best
