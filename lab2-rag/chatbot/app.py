import os, requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from observability.dd import enable_llmobs_if_configured, enable_tracing_if_configured, span
SERVICE = "chatbot"
enable_llmobs_if_configured(SERVICE)
enable_tracing_if_configured(SERVICE)
enable_otel_if_configured(SERVICE)
with span("chatbot.forward", target="api_rag"):
    r = requests.post(f"{API_URL}/ask", json={"question":q}, timeout=120)

load_dotenv()

# --- Datadog LLMObs (옵션) ---
if os.getenv("DD_LLMOBS_ENABLED","0") == "1":
    try:
        from ddtrace.llmobs import LLMObs
        LLMObs.enable(
            ml_app=os.getenv("DD_LLMOBS_ML_APP","chatbot"),
            api_key=os.getenv("DD_API_KEY"),
            site=os.getenv("DD_SITE","datadoghq.com"),
            agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED","true"),
        )
        print("[DD] LLMObs enabled (chatbot)")
    except Exception as e:
        print(f"[DD] LLMObs not active: {e}")

API_URL = os.getenv("API_URL","http://api_rag:8081")

app = Flask(__name__)

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    q = (data.get("message") or "").strip()
    if not q:
        return jsonify({"error":"message is required"}), 400
    r = requests.post(f"{API_URL}/ask", json={"question":q}, timeout=120)
    return jsonify(r.json()), r.status_code

@app.get("/")
def health():
    return {"ok": True, "api_url": API_URL}

if __name__ == "__main__":
    app.run(host=os.getenv("HOST","0.0.0.0"), port=int(os.getenv("PORT","8082")))

@app.get("/healthz")
def healthz():
    return {"ok": True}, 200
