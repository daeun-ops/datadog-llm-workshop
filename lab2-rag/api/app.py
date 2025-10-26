# ------------------------------------------------------------
# lab2-rag/api/app.py  (SECURE + MLOps)
# ------------------------------------------------------------
import os, json, time
from typing import List, Tuple, Optional

from flask import Flask, request, jsonify, make_response
from dotenv import load_dotenv
from chromadb import HttpClient
from openai import OpenAI

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, ValidationError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from utils.pii import mask_pii
from security.guardrails import contains_injection, external_links, is_external_domain

# ---- Observability helpers ----
try:
    from observability.dd import (
        enable_llmobs_if_configured,
        enable_tracing_if_configured,
        enable_otel_if_configured,
        span,
        jlog,
    )
except Exception:
    from contextlib import contextmanager
    @contextmanager
    def span(*_, **__): yield
    def jlog(**kw): print(json.dumps(kw, ensure_ascii=False))
    def enable_llmobs_if_configured(_): ...
    def enable_tracing_if_configured(_): ...
    def enable_otel_if_configured(_): ...

try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None
try:
    from FlagEmbedding import FlagReranker
except Exception:
    FlagReranker = None

load_dotenv()
SERVICE = "rag-api"
enable_llmobs_if_configured(SERVICE)
enable_tracing_if_configured(SERVICE)
enable_otel_if_configured(SERVICE)

if os.getenv("DD_LLMOBS_ENABLED","0") == "1":
    try:
        from ddtrace.llmobs import LLMObs
        LLMObs.enable(
            ml_app=os.getenv("DD_LLMOBS_ML_APP", "rag-api"),
            api_key=os.getenv("DD_API_KEY"),
            site=os.getenv("DD_SITE", "datadoghq.com"),
            agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED", "true"),
        )
    except Exception as e:
        print(f"[DD] LLMObs not active: {e}")

def openai_client() -> OpenAI:
    base = os.getenv("OPENAI_BASE_URL")
    key = os.getenv("OPENAI_API_KEY")
    if base:
        return OpenAI(base_url=base, api_key=key or "ollama")
    return OpenAI(api_key=key)

client = openai_client()
MODEL_MAIN = os.getenv("MODEL_NAME", "llama3.1")
MODEL_ALT  = os.getenv("MODEL_NAME_ALT", "llama3.1")

PROMPT_V1 = """You are a helpful assistant. Use ONLY the CONTEXT to answer.

CONTEXT:
{ctx}

QUESTION: {q}
Rules:
- If the answer is not in the context, say "I'm not sure."
- Be concise and cite short snippets if helpful.
"""
PROMPT_V2 = """ROLE: Knowledge-grounded assistant. Respond only from CONTEXT.

CONTEXT:
{ctx}

Q: {q}
ANSWER FORMAT (JSON):
{{
 "answer": "...",
 "citations": [],
 "confidence": 0.0
}}
If missing info: answer "I'm not sure."
"""
PROMPT_VERSION_DEFAULT = os.getenv("PROMPT_VERSION","v1")
CANARY_RATIO = float(os.getenv("CANARY_RATIO","0.0"))

TOP_K = int(os.getenv("TOP_K","8"))
HYBRID_W_VEC = float(os.getenv("HYBRID_W_VEC","0.7"))
HYBRID_W_KW  = float(os.getenv("HYBRID_W_KW","0.3"))
RERANK_ENABLED = os.getenv("RERANK_ENABLED","1") == "1"
RERANK_MODEL   = os.getenv("RERANK_MODEL","BAAI/bge-reranker-large")
RERANK_BATCH   = int(os.getenv("RERANK_BATCH","8"))

CHROMA_URL = os.getenv("CHROMA_URL","http://vector-store:8000")
INDEX_NAME = os.getenv("INDEX_NAME","kb_demo")
HOST = CHROMA_URL.split("://")[1].split(":")[0]
PORT = int(CHROMA_URL.split(":")[-1]) if ":" in CHROMA_URL else 8000
chroma = HttpClient(host=HOST, port=PORT)
try:
    col = chroma.get_collection(INDEX_NAME)
except Exception:
    col = chroma.create_collection(INDEX_NAME)

reranker = None
if RERANK_ENABLED and FlagReranker:
    try:
        reranker = FlagReranker(RERANK_MODEL, use_fp16=True)
        print(f"[RAG] Re-ranker ready: {RERANK_MODEL}")
    except Exception as e:
        print(f"[RAG] Re-ranker not available: {e}")

# --------------------------
# Metrics
# --------------------------
REQUESTS = Counter("rag_requests_total", "Total /ask calls", ["model", "prompt_version"])
RETRIEVE_LAT = Histogram("rag_retrieve_latency_seconds", "Retrieval latency (s)")
GENERATE_LAT = Histogram("rag_generate_latency_seconds", "Generation latency (s)")
ANSWER_LEN   = Histogram("rag_answer_length_chars", "Answer length (chars)")

def current_trace_id_hex() -> Optional[str]:
    try:
        from opentelemetry import trace
        sc = trace.get_current_span().get_span_context()
        if sc and sc.trace_id:
            return f"{sc.trace_id:032x}"
    except Exception:
        pass
    try:
        from ddtrace import tracer
        s = tracer.current_span()
        if s and s.trace_id:
            return f"{s.trace_id:016x}".rjust(32,"0")
    except Exception:
        pass
    return None

class AnswerV2(BaseModel):
    answer: str
    citations: list[str] = []
    confidence: float

def to_dense_similarity(dist: float) -> float:
    if dist is None: return 0.0
    return max(-1.0, min(1.0, 1.0 - float(dist)))

def sparse_score(query: str, text: str) -> float:
    if not fuzz: return 0.0
    try: return fuzz.partial_ratio((query or "").lower(), (text or "").lower()) / 100.0
    except Exception: return 0.0

def hybrid_score(query: str, text: str, dense_sim: float) -> float:
    return HYBRID_W_VEC * dense_sim + HYBRID_W_KW * sparse_score(query, text)

def hybrid_retrieve(query: str, topk: int = TOP_K):
    prefetch = max(topk * 2, topk + 2)
    with span("rag.retrieve.prefetch", top_k=prefetch, index=INDEX_NAME):
        res = col.query(query_texts=[query], n_results=prefetch,
                        include=["documents","distances","metadatas","ids"])
    docs = (res.get("documents") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    ids   = (res.get("ids") or [[]])[0]

    scored = []
    for i, text in enumerate(docs):
        dense_sim = to_dense_similarity(dists[i] if i < len(dists) else None)
        scored.append(({
            "id": ids[i] if i < len(ids) else None,
            "text": text,
            "metadata": metas[i] if i < len(metas) else {},
            "dense_sim": dense_sim,
        }, float(hybrid_score(query, text, dense_sim))))
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:topk]

    if reranker:
        with span("rag.rerank", model=RERANK_MODEL, batch=RERANK_BATCH):
            pairs = [(query, d["text"]) for (d, _) in top]
            try:
                scores = reranker.compute_score(pairs, batch_size=RERANK_BATCH)
                reranked = list(zip([t[0] for t in top], [float(s) for s in scores]))
                reranked.sort(key=lambda x: x[1], reverse=True)
                jlog(event="retrieval", stage="rerank", prefetch=prefetch, final_k=topk)
                return reranked
            except Exception as e:
                jlog(event="retrieval.rerank.error", error=str(e))
                return top
    jlog(event="retrieval", stage="hybrid-only", prefetch=prefetch, final_k=topk)
    return top

def choose_model() -> str:
    override = request.headers.get("X-Model-Override")
    if override: return override
    import random
    if CANARY_RATIO > 0 and random.random() < CANARY_RATIO:
        return MODEL_ALT
    return MODEL_MAIN

def choose_prompt_version() -> str:
    pv = request.headers.get("X-Prompt-Version")
    return pv if pv in ("v1","v2") else PROMPT_VERSION_DEFAULT

def build_prompt(pv: str, q: str, ctx: str) -> str:
    return (PROMPT_V2 if pv=="v2" else PROMPT_V1).format(q=q, ctx=ctx)

app = Flask(__name__)

# ---- Rate limit (IP 기준 + 헤더 우선) ----
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["120 per minute"],  # 전체 기본
    storage_uri="memory://",
)

@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": SERVICE}, 200

@app.get("/openapi")
def openapi():
    try:
        with open(os.path.join(os.path.dirname(__file__), "openapi.yaml"), "r", encoding="utf-8") as f:
            return make_response(f.read(), 200, {"Content-Type":"application/yaml"})
    except Exception:
        return {"error":"openapi_not_found"}, 404

@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

@app.post("/feedback")
@limiter.limit("10/minute")
def feedback():
    os.makedirs("./data", exist_ok=True)
    data = request.get_json(silent=True) or {}
    data["ts"] = time.time()
    with open("./data/feedback.jsonl","a",encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")
    jlog(event="feedback", payload=data)
    return {"ok": True}, 200

@app.post("/ask")
@limiter.limit("60/minute")  # per-IP rate limit
def ask():
    payload = request.get_json(silent=True) or {}
    raw_q = (payload.get("question") or "").strip()
    if not raw_q:
        return jsonify({"error":"question is required"}), 400

    # 1) 가드레일: PII 마스킹 + 인젝션/외부링크 차단
    q = mask_pii(raw_q)
    if contains_injection(q):
        return jsonify({"error":"prompt_injection_detected"}), 400
    urls = external_links(q)
    if any(is_external_domain(u, allowlist=set()) for u in urls):
        return jsonify({"error":"external_links_blocked", "urls": urls}), 400

    topk = int(payload.get("top_k", TOP_K))
    temperature = float(payload.get("temperature", os.getenv("TEMPERATURE","0.2")))

    model = choose_model()
    pv = choose_prompt_version()
    REQUESTS.labels(model=model, prompt_version=pv).inc()

    t0 = time.time()
    with span("rag.retrieve", top_k=topk, index=INDEX_NAME, rerank=bool(reranker)):
        docs = hybrid_retrieve(q, topk=topk)
    rt = time.time() - t0
    ex = current_trace_id_hex()
    if ex: RETRIEVE_LAT.observe(rt, exemplar={'trace_id': ex})
    else:  RETRIEVE_LAT.observe(rt)

    contexts = [d["text"] for (d, _) in docs]
    context_text = "\n\n".join(contexts)

    prompt = build_prompt(pv, q, context_text)
    resp_text = None
    tries, gen_latency, last_err = 0, 0.0, None

    while tries < 2 and resp_text is None:
        tries += 1
        t1 = time.time()
        with span("llm.generate", model=model, provider="ollama", temperature=temperature, prompt_version=pv, attempt=tries):
            try:
                out = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role":"system","content":"Answer using only the provided CONTEXT."},
                        {"role":"user","content": prompt},
                    ],
                    temperature=temperature,
                )
                resp_text = out.choices[0].message.content
            except Exception as e:
                last_err = str(e); resp_text = None
        gen_latency = time.time() - t1

        if resp_text and pv=="v2":
            try:
                AnswerV2.model_validate_json(resp_text)
            except ValidationError:
                if tries < 2:
                    temperature = max(0.0, temperature - 0.2)
                    resp_text = None
                else:
                    resp_text = json.dumps({"answer": resp_text, "citations": [], "confidence": 0.5})

    if ex: GENERATE_LAT.observe(gen_latency, exemplar={'trace_id': ex})
    else:  GENERATE_LAT.observe(gen_latency)

    if not resp_text:
        jlog(event="llm.error", error=last_err or "unknown")
        return jsonify({"error":"llm_failed","detail": last_err}), 500

    ANSWER_LEN.observe(len(resp_text))
    jlog(event="rag.answer", question=q, source_count=len(contexts),
         rerank=bool(reranker), top_k=topk, model=model, prompt_version=pv,
         latency_retrieve_ms=int(rt*1000), latency_generate_ms=int(gen_latency*1000))

    sources = [{"id": d["id"], "metadata": d["metadata"], "dense_sim": d["dense_sim"]} for (d, _) in docs]

    parsed_v2 = None
    if pv=="v2":
        try: parsed_v2 = AnswerV2.model_validate_json(resp_text).model_dump()
        except Exception: parsed_v2 = None

    return jsonify({
        "answer": resp_text,
        "parsed": parsed_v2,
        "sources": sources,
        "used_reranker": bool(reranker),
        "top_k": topk,
        "model": model,
        "prompt_version": pv,
        "temperature": temperature,
    })

if __name__ == "__main__":
    app.run(host=os.getenv("HOST","0.0.0.0"), port=int(os.getenv("PORT","8081")), debug=False)
