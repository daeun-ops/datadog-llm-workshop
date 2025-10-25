# observability/dd.py
import json, os, time
from contextlib import contextmanager

# ——— LLM Observability (Agentless) ———
def enable_llmobs_if_configured(service_name: str):
    if os.getenv("DD_LLMOBS_ENABLED", "0") != "1":
        return False
    try:
        from ddtrace.llmobs import LLMObs
        LLMObs.enable(
            ml_app=os.getenv("DD_LLMOBS_ML_APP", service_name),
            api_key=os.getenv("DD_API_KEY"),
            site=os.getenv("DD_SITE", "datadoghq.com"),
            agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED", "true"),
        )
        print(f"[DD] LLMObs enabled (app={service_name})")
        return True
    except Exception as e:
        print("[DD] LLMObs NOT enabled:", e)
        return False

# ——— ddtrace APM (Agent 경유) ———
def enable_tracing_if_configured(service_name: str):
    if os.getenv("DD_APM_ENABLED", "0") != "1":
        return None
    try:
        from ddtrace import config, patch, tracer
        patch(flask=True, requests=True)
        config.service = service_name
        # DD_AGENT_HOST/ DD_TRACE_AGENT_URL는 에이전트가 읽음
        print(f"[DD] ddtrace enabled (service={service_name})")
        return tracer
    except Exception as e:
        print("[DD] ddtrace NOT enabled:", e)
        return None

# ——— 표준 스팬 컨텍스트 ———
@contextmanager
def span(name: str, **tags):
    try:
        from ddtrace import tracer
        with tracer.trace(name) as s:
            for k, v in tags.items():
                s.set_tag(k, v)
            yield s
    except Exception:
        # ddtrace 미설치 시 no-op
        yield None

def jlog(**kw):
    print(json.dumps(kw, ensure_ascii=False))
