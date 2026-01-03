from __future__ import annotations

import logging
import os
from typing import Any, Optional

log = logging.getLogger("workshop.observability")


def init_datadog_llmobs() -> None:
    """
    Initialize Datadog tracing + LLM Observability.

    - Uses Datadog Agent if DD_LLMOBS_AGENTLESS_ENABLED=0 (default in docker-compose)
    - Can run in agentless if DD_LLMOBS_AGENTLESS_ENABLED=1 and DD_API_KEY/DD_SITE are set
    """
    try:
        from ddtrace.llmobs import LLMObs  # type: ignore
        from ddtrace import tracer  # noqa: F401

        ml_app = os.getenv("DD_LLMOBS_ML_APP", "datadog-llm-workshop")
        agentless_enabled = os.getenv("DD_LLMOBS_AGENTLESS_ENABLED", "0") == "1"

        # We keep integrations disabled here and create our own LLM spans explicitly.
        # Datadog supports auto-instrumentation too, but this is easier to teach/debug in a workshop.  [oai_citation:4‡docs.datadoghq.com](https://docs.datadoghq.com/llm_observability/setup/auto_instrumentation/?utm_source=chatgpt.com)
        LLMObs.enable(
            ml_app=ml_app,
            integrations_enabled=False,
            agentless_enabled=agentless_enabled,
        )

        log.info("Datadog LLMObs enabled (ml_app=%s, agentless=%s)", ml_app, agentless_enabled)
    except Exception as e:
        # No-op if ddtrace not installed or env not configured.
        log.warning("Datadog LLMObs init skipped: %s", e)


def current_trace_ids() -> dict[str, Optional[str]]:
    """
    Return trace_id/span_id (as strings) so workshop users can correlate requests in Datadog.
    """
    try:
        from ddtrace import tracer  # type: ignore

        span = tracer.current_span()
        if not span:
            return {"trace_id": None, "span_id": None}

        # ddtrace uses integers internally
        return {"trace_id": str(span.trace_id), "span_id": str(span.span_id)}
    except Exception:
        return {"trace_id": None, "span_id": None}


def safe_span_tag(span: Any, key: str, value: Any) -> None:
    try:
        if span and value is not None:
            span.set_tag(key, value)
    except Exception:
        pass
