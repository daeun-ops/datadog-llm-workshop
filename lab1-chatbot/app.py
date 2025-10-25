import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

# --- Datadog LLMObs (옵션) ---
if os.getenv("DD_LLMOBS_ENABLED","0") == "1":
    try:
        from ddtrace.llmobs import LLMObs
        LLMObs.enable(
            ml_app=os.getenv("DD_LLMOBS_ML_APP","lab1-chat"),
            api_key=os.getenv("DD_API_KEY"),
            site=os.getenv("DD_SITE","datadoghq.com"),
            agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED","true"),
        )
        print("[DD] LLMObs enabled")
    except Exception as e:
        print(f"[DD] LLMObs not active: {e}")

from openai import OpenAI

def make_client():
    provider = os.getenv("LLM_PROVIDER","ollama")
    base = os.getenv("OPENAI_BASE_URL")
    key  = os.getenv("OPENAI_API_KEY")

    if provider.lower() == "ollama":
        base = base or "http://localllama:11434/v1"
        key  = key or "ollama"
        return OpenAI(base_url=base, api_key=key)
    return OpenAI(api_key=key)

client = make_client()
MODEL = os.getenv("MODEL_NAME","llama3.1")

app = Flask(__name__)

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"error":"message is required"}), 400

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role":"system","content":"You are a concise assistant."},
            {"role":"user","content":msg},
        ],
        temperature=0.3,
    )
    text = resp.choices[0].message.content
    return jsonify({"reply": text})

if __name__ == "__main__":
    app.run(host=os.getenv("HOST","0.0.0.0"), port=int(os.getenv("PORT","8080")))
