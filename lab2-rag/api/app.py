# lab2-rag/api/app.py
# ------------------------------------------------------------
# RAG API with Hybrid Retrieval (Dense + Sparse) + Re-ranking,
# plus full observability (ddtrace, OTel, LLMObs) hooks.
# - Dense: Chroma similarity
# - Sparse: RapidFuzz keyword match
# - Re-ranker: Cross-Encoder (BAAI/bge-reranker-large), optional
# ------------------------------------------------------------

import os
import math
from typing import List, Tuple

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from chromadb import HttpClient
from openai import OpenAI

# ---- Observability helpers (datadog + otel) ----
try:
    from observability.dd import (
        enable_llmobs_if_configured,
        enable_tracing_if_configured,
        enable_otel_if_configured,
        span,
        jlog,
    )
except Exception:
    # Fallback no-op shims so the app still runs if helper isn’t present
    def span(name, **kw):
        from contextlib import contextmanager
        @contextmanager
        def _cm():
            yield
        return _cm()
    def jlog(**kw):  # print JSON-ish
        print(kw)
    def enable_llmobs_if_configured(_): ...
    def enable_tracing_if_configured(_): ...
    def enable_otel_if_configured(_): ...

# Optional sparse+rERANK deps (graceful fallback)
try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None

try:
    # pip install FlagEmbedding
    from FlagEmbedding import FlagReranker
except Exception:
    FlagReranker = None


# --------------------------
# Boot
# --------------------------
load_dotenv()

SERVICE = "rag-api"
enable_llmobs_if_configured(SERVICE)
enable_tracing_if_configured(SERVICE)
enable_otel_if_configured(SERVICE)

# ---- LLMObs (agentless) optional explicit (redundant-safe) ----
if os.getenv("DD_LLMOBS_ENABLED", "0") == "1":
    try:
        from ddtrace.llmobs import LLMObs
        LLMObs.enable(
            ml_app=os.getenv("DD_LLMOBS_ML_APP", "rag-api"),
            api_key=os.getenv("DD_API_KEY"),
            site=os.getenv("DD_SITE", "datadoghq.com"),
            agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED", "true"),
        )
        print("[DD] LLMObs enabled (rag-api)")
    except Exception as e:
        print(f"[DD] LLMObs not active: {e}")

# ---- OpenAI/Ollama client ----
def openai_client() -> OpenAI:
    base = os.getenv("OPENAI_BASE_URL")
    key = os.getenv("OPENAI_API_KEY")
    if base:
        return OpenAI(base_url=base, api_key=key or "ollama")
    return OpenAI(api_key=key)

client = openai_client()
MODEL = os.getenv("MODEL_NAME", "llama3.1")

# ---- Chroma (Vector) ----
CHROMA_URL = os.getenv("CHROMA_URL", "http://vector-store:8000")
INDEX_NAME = os.getenv("INDEX_NAME", "kb_demo")
TOP_K = int(os.getenv("TOP_K", "8"))  # we’ll do topk*2 for pre-fetch then cut down

# Hybrid knobs
HYBRID_W_VEC = float(os.getenv("HYBRID_W_VEC", "0.7"))   # Dense weight
HYBRID_W_KW  = float(os.getenv("HYBRID_W_KW", "0.3"))   # Sparse weight
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "1") == "1"
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-large")
RERANK_BATCH = int(os.getenv("RERANK_BATCH", "8"))

HOST = CHROMA_URL.split("://")[1].split(":")[0]
PORT = int(CHROMA_URL.split(":")[-1]) if ":" in CHROMA_URL else 8000
chroma = HttpClient(host=HOST, port=PORT)
try:
    col = chroma.get_collection(INDEX_NAME)
except Exception:
    col = chroma.create_collection(INDEX_NAME)

# ---- Optional re-ranker init (graceful fallback) ----
reranker = None
if RERANK_ENABLED and FlagReranker:
    try:
        reranker = FlagReranker(RERANK_MODEL, use_fp16=True)
        print(f"[RAG] Re-ranker ready: {RERANK_MODEL}")
    except Exception as e:
        print(f"[RAG] Re-ranker not available: {e}")

# --------------------------
# Retrieval (Hybrid + Rerank)
# --------------------------

def to_dense_similarity(dist: float) -> float:
    """
    Chroma's default 'distance' for cosine is (1 - cosine_sim).
    If you pass include=["distances"], we convert: sim = 1 - distance.
    Guard rails if distance is None.
    """
    if dist is None:
        return 0.0
    # clamp mildly for safety
    try:
        return max(-1.0, min(1.0, 1.0 - float(dist)))
    except Exception:
        return 0.0

def sparse_score(query: str, text: str) -> float:
    """
    Keyword-ish match using RapidFuzz partial_ratio.
    If RapidFuzz missing, return 0.
    """
    if not fuzz:
        return 0.0
    try:
        return fuzz.partial_ratio((query or "").lower(), (text or "").lower()) / 100.0
    except Exception:
        return 0.0

def hybrid_score(query: str, text: str, dense_sim: float,
                 w_vec: float = HYBRID_W_VEC, w_kw: float = HYBRID_W_KW) -> float:
    kw = sparse_score(query, text)
    return w_vec * dense_sim + w_kw * kw

def hybrid_retrieve(query: str, topk: int = TOP_K) -> List[Tuple[dict, float]]:
    """
    Returns list of (doc, score), doc is a dict: {id, text, metadata}
    """
    prefetch = max(topk * 2, topk + 2)
    with span("rag.retrieve.prefetch", top_k=prefetch, index=INDEX_NAME):
        res = col.query(
            query_texts=[query],
            n_results=prefetch,
            include=["documents", "distances", "metadatas", "ids"],
        )
    docs = (res.get("documents") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    ids   = (res.get("ids") or [[]])[0]

    # Compute hybrid scores
    with span("rag.retrieve.hybrid_score", w_vec=HYBRID_W_VEC, w_kw=HYBRID_W_KW):
        scored = []
        for i, text in enumerate(docs):
            dense_sim = to_dense_similarity(dists[i] if i < len(dists) else None)
            score = hybrid_score(query, text, dense_sim)
            scored.append(({
                "id": ids[i] if i < len(ids) else None,
                "text": text,
                "metadata": metas[i] if i < len(metas) else {},
                "dense_sim": dense_sim,
            }, float(score)))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:topk]

    # Optional cross-encoder re-rank
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
                # fallback to original
                return top
    else:
        jlog(event="retrieval", stage="hybrid-only", prefetch=prefetch, final_k=topk)
        return top


# --------------------------
# Flask App
# --------------------------
app = Flask(__name__)

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": SERVICE}, 200

@app.post("/ask")
def ask():
    data = request.get_json(silent=True) or {}
    q = (data.get("question") or "").strip()
    temperature = float(data.get("temperature", os.getenv("TEMPERATURE", "0.2")))
    topk = int(data.get("top_k", TOP_K))
    if not q:
        return jsonify({"error": "question is required"}), 400

    # 1) Hybrid retrieval (+ optional re-rank)
    with span("rag.retrieve", top_k=topk, index=INDEX_NAME, rerank=bool(reranker)):
        docs = hybrid_retrieve(q, topk=topk)

    contexts = [d["text"] for (d, _) in docs]
    context_text = "\n\n".join(contexts)

    # 2) Prompt
    prompt = f"""You are a helpful assistant. Use ONLY the CONTEXT to answer.

CONTEXT:
{context_text}

QUESTION: {q}

Rules:
- If the answer is not in the context, say "I'm not sure."
- Keep it concise and cite brief snippets if helpful.
"""

    # 3) Generation
    with span("llm.generate", model=MODEL, provider="ollama", temperature=temperature):
        out = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You answer using only the provided CONTEXT."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
    answer = out.choices[0].message.content

    # 4) Log & return
    jlog(
        event="rag.answer",
        question=q,
        source_count=len(contexts),
        rerank=bool(reranker),
        top_k=topk,
        model=MODEL,
    )
    return jsonify({
        "answer": answer,
        "sources": [
            {"id": d["id"], "metadata": d["metadata"], "dense_sim": d["dense_sim"]}
            for (d, _) in docs
        ],
        "used_reranker": bool(reranker),
        "top_k": topk,
        "model": MODEL,
        "temperature": temperature,
    })


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8081")), debug=False)
