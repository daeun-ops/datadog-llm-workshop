import os, json
from contextlib import contextmanager

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

def enable_tracing_if_configured(service_name: str):
    if os.getenv("DD_APM_ENABLED", "1") != "1":
        return False
    try:
        from ddtrace import config, patch
        patch(flask=True, requests=True)
        config.service = service_name
        print(f"[DD] ddtrace enabled (service={service_name})")
        return True
    except Exception as e:
        print("[DD] ddtrace NOT enabled:", e)
        return False

def enable_otel_if_configured(service_name: str):
    if os.getenv("OTEL_ENABLED", "0") != "1":
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

        exporters = []

        # Datadog Exporter (Agent or Agentless)
        try:
            from opentelemetry.exporter.datadog import DatadogExporter
            agent_url = os.getenv("OTEL_EXPORTER_DATADOG_AGENT_URL")
            if agent_url:
                exporters.append(DatadogExporter(
                    agent_url=agent_url,
                    env=os.getenv("DD_ENV","workshop-local"),
                    service=service_name,
                    version=os.getenv("DD_VERSION","0.2.0"),
                ))
            elif os.getenv("DD_API_KEY"):
                exporters.append(DatadogExporter(
                    api_key=os.getenv("DD_API_KEY"),
                    site=os.getenv("DD_SITE","datadoghq.com"),
                    env=os.getenv("DD_ENV","workshop-local"),
                    service=service_name,
                    version=os.getenv("DD_VERSION","0.2.0"),
                ))
        except Exception as e:
            print("[OTEL] Datadog Exporter disabled:", e)

        # OTLP → Tempo Exporter
        if os.getenv("OTEL_EXPORT_TEMPO","0") == "1":
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                tempo_endpoint = os.getenv("OTEL_TEMPO_ENDPOINT","http://tempo:4318/v1/traces")
                exporters.append(OTLPSpanExporter(endpoint=tempo_endpoint, timeout=10))
            except Exception as e:
                print("[OTEL] OTLP (Tempo) Exporter disabled:", e)

        if not exporters:
            print("[OTEL] No exporters configured.")
            return False

        provider = TracerProvider(resource=Resource.create({
            "service.name": service_name,
            "deployment.environment": os.getenv("DD_ENV","workshop-local"),
            "service.version": os.getenv("DD_VERSION","0.2.0"),
        }))

        # 병렬 전송: Exporter마다 하나의 Processor 추가
        for exp in exporters:
            provider.add_span_processor(BatchSpanProcessor(exp))
            # 필요시 SimpleSpanProcessor(exp)로 교체 가능

        trace.set_tracer_provider(provider)
        print(f"[OTEL] Tracer configured → {len(exporters)} exporter(s) active")
        return True
    except Exception as e:
        print("[OTEL] NOT enabled:", e)
        return False

@contextmanager
def span(name: str, **tags):
    # ddtrace 우선, 실패 시 OTel
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
            return
    except Exception:
        pass
    yield None

def jlog(**kw):
    print(json.dumps(kw, ensure_ascii=False))
