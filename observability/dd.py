import os, json
from contextlib import contextmanager

# ---------------- LLMObs (agentless) ----------------
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

# ---------------- ddtrace (APM - Agent 경유) ----------------
def enable_tracing_if_configured(service_name: str):
    if os.getenv("DD_APM_ENABLED", "1") != "1":
        return None
    try:
        from ddtrace import config, patch
        patch(flask=True, requests=True)
        config.service = service_name
        print(f"[DD] ddtrace enabled (service={service_name})")
        return True
    except Exception as e:
        print("[DD] ddtrace NOT enabled:", e)
        return False

# ---------------- OpenTelemetry → Datadog Exporter ----------------
def enable_otel_if_configured(service_name: str):
    if os.getenv("OTEL_ENABLED", "0") != "1":
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.datadog import DatadogExporter

        # 우선순위: Agent 경유 → Agentless
        agent_url = os.getenv("OTEL_EXPORTER_DATADOG_AGENT_URL")
        if agent_url:
            exporter = DatadogExporter(agent_url=agent_url,
                                       env=os.getenv("DD_ENV", "workshop-local"),
                                       service=service_name,
                                       version=os.getenv("DD_VERSION", "0.1.0"))
        else:
            exporter = DatadogExporter(
                api_key=os.getenv("DD_API_KEY"),
                site=os.getenv("DD_SITE", "datadoghq.com"),
                env=os.getenv("DD_ENV", "workshop-local"),
                service=service_name,
                version=os.getenv("DD_VERSION", "0.1.0")
            )

        provider = TracerProvider(resource=Resource.create({
            "service.name": service_name,
            "deployment.environment": os.getenv("DD_ENV", "workshop-local"),
            "service.version": os.getenv("DD_VERSION", "0.1.0"),
        }))
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        print(f"[OTEL] Tracer configured → Datadog Exporter ({'agent' if agent_url else 'agentless'})")
        return True
    except Exception as e:
        print("[OTEL] NOT enabled:", e)
        return False

# ---------------- Unified helpers ----------------
@contextmanager
def span(name: str, **tags):
    # ddtrace 우선 사용, 없으면 OTel
    try:
        from ddtrace import tracer
        with tracer.trace(name) as s:
            for k, v in tags.items():
                s.set_tag(k, v)
            yield s
            return
    except Exception:
        pass
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer("app")
        with tracer.start_as_current_span(name) as s:
            for k, v in tags.items():
                try: s.set_attribute(k, v)
                except Exception: pass
            yield s
    except Exception:
        yield None

def jlog(**kw):
    print(json.dumps(kw, ensure_ascii=False))
