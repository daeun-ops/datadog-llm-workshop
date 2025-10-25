import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from chromadb import HttpClient
from openai import OpenAI

load_dotenv()

# --- Datadog LLMObs (옵션) ---
if os.getenv("DD_LLMOBS_ENABLED","0") == "1":
    try:
        from ddtrace.llmobs import LLMObs
        LLMObs.enable(
            ml_app=os.getenv("DD_LLMOBS_ML_APP","rag-api"),
            api_key=os.getenv("DD_API_KEY"),
            site=os.getenv("DD_SITE","datadoghq.com"),
            agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED","true"),
        )
        print("[DD] LLMObs enabled (rag-api)")
    except Exception as e:
        print(f"[DD] LLMObs not active: {e}")

def openai_client():
    base = os.getenv("OPENAI_BASE_URL")
    key = os.getenv("OPENAI_API_KEY")
    if base:
        return OpenAI(base_url=base, api_key=key or "ollama")
    return OpenAI(api_key=key)

client = openai_client()
MODEL = os.getenv("MODEL_NAME","llama3.1")

# Chroma
CHROMA_URL = os.getenv("CHROMA_URL","http://vector-store:8000")
HOST = CHROMA_URL.split("://")[1].split(":")[0]
chroma = HttpClient(host=HOST, port=8000)
INDEX_NAME = os.getenv("INDEX_NAME","kb_demo")
try:
    col = chroma.get_collection(INDEX_NAME)
except Exception:
    col = chroma.create_collection(INDEX_NAME)

TOP_K = int(os.getenv("TOP_K","4"))

app = Flask(__name__)

@app.post("/ask")
def ask():
    data = request.get_json(silent=True) or {}
    q = (data.get("question") or "").strip()
    if not q:
        return jsonify({"error":"question is required"}), 400

    res = col.query(query_texts=[q], n_results=TOP_K, include=["documents"])
    contexts = (res.get("documents") or [[]])[0]
    context_text = "\n\n".join(contexts)

    prompt = f"""You are a helpful assistant. Use the CONTEXT to answer.
CONTEXT:
{context_text}

QUESTION: {q}
If the answer is not in the context, say you are not sure.
"""

    out = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content": prompt}],
        temperature=0.2,
    )
    answer = out.choices[0].message.content
    return jsonify({"answer": answer, "source_count": len(contexts)})

if __name__ == "__main__":
    app.run(host=os.getenv("HOST","0.0.0.0"), port=int(os.getenv("PORT","8081")))
