import os, time, random
from flask import Flask, jsonify
from prometheus_client import Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from ddtrace import patch, tracer as ddtracer

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"), insecure=True)))
trace.set_tracer_provider(provider)
otel_tracer = trace.get_tracer("demo-app")

patch(flask=True)
ddtracer.configure(hostname=os.getenv("DD_AGENT_HOST", "localhost"), port=8126)
# Histogram for latency with Exemplars
REQ_LAT = Histogram("app_request_latency", "demo latency seconds", buckets=[0.05,0.1,0.2,0.5,1,2,5])

app = Flask(__name__)

@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

@app.get("/healthz")
def healthz():
    return "ok", 200

@app.get("/demo")
def demo():
    start = time.time()
    with otel_tracer.start_as_current_span("demo-work"):
        # simulated work
        time.sleep(random.uniform(0.05, 0.5))
        # exemplar: add current trace id to histogram observation metadata
        ctx = trace.get_current_span().get_span_context()
        trace_id_hex = f"{ctx.trace_id:032x}"
        duration = time.time() - start
        REQ_LAT.observe(duration, exemplar={"trace_id": trace_id_hex})
    app.logger.info("demo completed trace_id=%s duration=%.3f", trace_id_hex, duration)
    return jsonify({"ok": True, "trace_id": trace_id_hex, "latency_s": duration})
