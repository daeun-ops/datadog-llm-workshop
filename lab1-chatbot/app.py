import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from observability.dd import enable_llmobs_if_configured, enable_tracing_if_configured, enable_otel_if_configured, span, jlog
SERVICE = "rag-api"  
enable_llmobs_if_configured(SERVICE)
enable_tracing_if_configured(SERVICE)
enable_otel_if_configured(SERVICE)     # ← OTel 추가
load_dotenv()

from observability.dd import (
    enable_llmobs_if_configured,
    enable_tracing_if_configured,
    span, jlog
)

SERVICE = "lab1-chat"
enable_llmobs_if_configured(SERVICE)
enable_tracing_if_configured(SERVICE)

from openai import OpenAI
def make_client():
    base = os.getenv("OPENAI_BASE_URL") or "http://localllama:11434/v1"
    key  = os.getenv("OPENAI_API_KEY") or "ollama"
    return OpenAI(base_url=base, api_key=key)

client = make_client()
MODEL = os.getenv("MODEL_NAME","llama3.1")

app = Flask(__name__)

@app.get("/healthz")
def healthz(): return {"ok": True}

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    msg  = (data.get("message") or "").strip()
    if not msg: return jsonify({"error":"message required"}), 400

    with span("llm.generate", model=MODEL, provider="ollama"):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role":"system","content":"You are a concise assistant."},
                {"role":"user","content": msg},
            ],
            temperature=0.3,
        )
    text = resp.choices[0].message.content
    usage = getattr(resp, "usage", None)
    jlog(event="chat.reply", model=MODEL, prompt=msg, reply=text[:200])
    out = {"reply": text}
    if usage:
        out["usage"] = {"total_tokens": getattr(usage,"total_tokens", None)}
    return jsonify(out)

if __name__ == "__main__":
    app.run(host=os.getenv("HOST","0.0.0.0"), port=int(os.getenv("PORT","8080")))
