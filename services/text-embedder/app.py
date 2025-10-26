import os,hashlib,math
from fastapi import FastAPI
from pydantic import BaseModel
from ddtrace import patch
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
patch(fastapi=True)
tp=TracerProvider()
tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT","http://localhost:4317"),insecure=True)))
trace.set_tracer_provider(tp)
app=FastAPI()
class EmbReq(BaseModel):
    text:str
def to_vec(s,dim=128):
    h=hashlib.sha256(s.encode()).digest()
    vals=[h[i%len(h)]/255.0 for i in range(dim)]
    n=math.sqrt(sum(v*v for v in vals)) or 1.0
    return [v/n for v in vals]
@app.get("/healthz")
def healthz():
    return {"ok":True}
@app.post("/embed")
def embed(r:EmbReq):
    return {"vector":to_vec(r.text)}
