import os, requests
from dotenv import load_dotenv
from observability.dd import (
    enable_llmobs_if_configured, enable_tracing_if_configured, span, jlog
)
SERVICE = "kb_service"
enable_llmobs_if_configured(SERVICE)
enable_tracing_if_configured(SERVICE)

with span("rag.embed", count=len(texts), index=INDEX_NAME):
    vectors = embed(texts)
jlog(event="kb.ingested", count=len(ids), index=INDEX_NAME)
load_dotenv()

# --- Datadog LLMObs (옵션) ---
if os.getenv("DD_LLMOBS_ENABLED","0") == "1":
    try:
        from ddtrace.llmobs import LLMObs
        LLMObs.enable(
            ml_app=os.getenv("DD_LLMOBS_ML_APP","kb_service"),
            api_key=os.getenv("DD_API_KEY"),
            site=os.getenv("DD_SITE","datadoghq.com"),
            agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED","true"),
        )
        print("[DD] LLMObs enabled (kb_service)")
    except Exception as e:
        print(f"[DD] LLMObs not active: {e}")

from utils import load_md_docs
from chromadb import HttpClient
from chromadb.utils import embedding_functions

CHROMA_URL = os.getenv("CHROMA_URL","http://vector-store:8000")
INDEX_NAME = os.getenv("INDEX_NAME","kb_demo")
EMBEDDER_URL = os.getenv("EMBEDDER_URL","http://text-embedder:5001")

def embed(texts):
    r = requests.post(f"{EMBEDDER_URL}/embed", json={"texts": texts}, timeout=60)
    r.raise_for_status()
    return r.json()["embeddings"]

def main():
    client = HttpClient(host=CHROMA_URL.split("://")[1].split(":")[0], port=8000)
    try:
        collection = client.get_collection(INDEX_NAME)
    except Exception:
        collection = client.create_collection(INDEX_NAME)
    docs = load_md_docs()
    if not docs:
        print("No docs to ingest.")
        return
    ids = [d["id"] for d in docs]
    texts = [d["text"] for d in docs]
    vectors = embed(texts)
    collection.upsert(documents=texts, ids=ids, embeddings=vectors)
    print(f"Ingested {len(ids)} documents into collection '{INDEX_NAME}'")

if __name__ == "__main__":
    main()
