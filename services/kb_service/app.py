import os,glob,json,requests
from fastapi import FastAPI
from ddtrace import patch
from pydantic import BaseModel

import chromadb
from chromadb.config import Settings
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
patch(fastapi=True)

tp=TracerProvider()
tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT","http://localhost:4317"),insecure=True)))
trace.set_tracer_provider(tp)

app=FastAPI()
CHROMA_DIR=os.getenv("CHROMA_DIR","/chroma")
KB_PATH=os.getenv("KB_PATH","/workspace/kb_data")
RAW_PATH=os.getenv("RAW_PATH","/workspace/data")
EMBEDDER=os.getenv("EMBEDDER_URL","http://text-embedder:5001/embed")

client=chromadb.PersistentClient(path=CHROMA_DIR,settings=Settings(allow_reset=True,anonymized_telemetry=False))
col=client.get_or_create_collection("kb")

class RebuildResp(BaseModel):
    added:int
def read_sources():
    paths=glob.glob(f"{KB_PATH}/**/*",recursive=True)+glob.glob(f"{RAW_PATH}/**/*",recursive=True)
    out=[]
    for p in paths:
        if os.path.isfile(p):
            try:
                with open(p,"r",encoding="utf-8",errors="ignore") as f:
                    text=f.read()
                if text.strip():
                    out.append((p,text))
            except:
                continue
    return out
  
def embed(txt):
    r=requests.post(EMBEDDER,json={"text":txt},timeout=10)
    r.raise_for_status()
    return r.json()["vector"]
  
@app.get("/healthz")
def healthz():
    return {"ok":True}
  
@app.post("/rebuild",response_model=RebuildResp)
def rebuild():
    client.reset()
    global col
    col=client.get_or_create_collection("kb")
    src=read_sources()
    ids=[]
    docs=[]
    vecs=[]
    for i,(p,t) in enumerate(src):
        ids.append(f"doc-{i}")
        docs.append(t)
        vecs.append(embed(t))
    if ids:
        col.add(ids=ids,documents=docs,embeddings=vecs,metadatas=[{"source":s[0]} for s in src])
    return {"added":len(ids)}
  
@app.post("/search")
def search(q:str,top_k:int=3):
    v=embed(q)
    res=col.query(query_embeddings=[v],n_results=top_k,include=["documents","metadatas","distances"])
    return res
