from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from workshop_app.redaction import redact_output, redact_text


@dataclass
class LLMResult:
    content: str
    model: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    latency_ms: int


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20] + "\n...[TRUNCATED]"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
def chat(
    user_text: str,
    system_text: str = "You are a helpful assistant.",
    session_id: Optional[str] = None,
    prompt_id: str = "workshop.chat",
    prompt_version: str = "1.0.0",
) -> LLMResult:
    """
    LLM call wrapped with Datadog LLM Observability span (manual).
    - Keeps deterministic instrumentation and avoids double-capture.
    - Adds optional prompt metadata for Prompt Tracking (preview feature).  [oai_citation:5‡docs.datadoghq.com](https://docs.datadoghq.com/llm_observability/setup/?utm_source=chatgpt.com)
    """
    max_chars = int(os.getenv("WORKSHOP_MAX_INPUT_CHARS", "12000"))
    user_text = _truncate(user_text, max_chars)
    system_text = _truncate(system_text, max_chars)

    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    start = time.time()

    # Datadog LLMObs manual span
    span = None
    try:
        from ddtrace.llmobs import LLMObs  # type: ignore

        # Optional prompt tracking metadata (preview). Safe to ignore if not enabled.
        try:
            with LLMObs.annotation_context(
                prompt={
                    "id": prompt_id,
                    "version": prompt_version,
                    "variables": {"model": model},
                }
            ):
                pass
        except Exception:
            pass

        with LLMObs.llm(
            model_name=model,
            name="chat_completion",
            model_provider="openai",
            session_id=session_id,
        ) as s:
            span = s

            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.2,
            )

            content = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", None)

            input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            output_tokens = getattr(usage, "completion_tokens", None) if usage else None

            # Redact what we store as span annotations
            safe_in: Dict[str, Any] = {
                "system": redact_text(system_text),
                "user": redact_text(user_text),
            }
            safe_out: Dict[str, Any] = {"assistant": redact_output(content)}

            # annotate input/output on the span for LLM Observability UIs
            try:
                LLMObs.annotate(span=span, input_data=safe_in, output_data=safe_out)
            except Exception:
                # If annotate signature differs by version, we still return response.
                pass

            latency_ms = int((time.time() - start) * 1000)
            return LLMResult(
                content=content,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )
    except Exception:
        # Fallback: call without ddtrace if instrumentation isn't available
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            temperature=0.2,
        )
        content = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)

        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
        latency_ms = int((time.time() - start) * 1000)

        return LLMResult(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
