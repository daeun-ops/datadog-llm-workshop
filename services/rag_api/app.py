import os,random,time
from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_client import Histogram,Counter,generate_latest,CONTENT_TYPE_LATEST

import chromadb
from chromadb.config import Settings
from ddtrace import patch,tracer as ddtracer
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
patch(fastapi=True)

tp=TracerProvider()
tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT","http://localhost:4317"),insecure=True)))
trace.set_tracer_provider(tp)

tr=trace.get_tracer("rag-api")
CHROMA_DIR=os.getenv("CHROMA_DIR","/chroma")
client=chromadb.PersistentClient(path=CHROMA_DIR,settings=Settings(allow_reset=False,anonymized_telemetry=False))
col=client.get_or_create_collection("kb")

AB_MODE=os.getenv("AB_MODE","auto")
AB_SPLIT=int(os.getenv("AB_SPLIT","80"))

LAT=Histogram("rag_request_latency","seconds",buckets=[0.05,0.1,0.2,0.5,1,2,5])
REQS=Counter("rag_requests_total","count",["variant"])

class Q(BaseModel):
    q:str
def choose_variant():
    if AB_MODE in ("A","B"):
        return AB_MODE
    return "A" if random.randint(1,100)<=AB_SPLIT else "B"
  
def answer_template(variant,query,context):
    if variant=="A":
        return f"Answer(A): {query}\nContext:\n{context}"
    else:
        return f"Answer(B): {query}\nContext:\n{context}\nRefined."
      
app=FastAPI()

@app.get("/healthz")
def healthz():
    return {"ok":True,"ab_mode":AB_MODE,"ab_split":AB_SPLIT}
  
@app.get("/metrics")
def metrics():
    return generate_latest(),200,{"Content-Type":CONTENT_TYPE_LATEST}
  
@app.post("/query")
def query(body:Q,top_k:int=3):
    start=time.time()
    with tr.start_as_current_span("rag.query"):
        v=choose_variant()
        REQS.labels(v).inc()
        res=col.query(query_texts=[body.q],n_results=top_k,include=["documents","metadatas","distances"])
        ctxs=[]
        for d in res.get("documents",[[]])[0]:
            ctxs.append(d[:800])
        context="\n---\n".join(ctxs)
        duration=time.time()-start
        span=trace.get_current_span().get_span_context()
        trace_id=f"{span.trace_id:032x}"
        LAT.observe(duration,exemplar={"trace_id":trace_id})
        ddtracer.set_tags({"ab.variant":v,"rag.top_k":top_k})
        return {"variant":v,"trace_id":trace_id,"latency_s":duration,"answer":answer_template(v,body.q,context)}
