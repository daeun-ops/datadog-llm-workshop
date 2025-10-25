import os
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.getenv("EMBED_MODEL","sentence-transformers/all-MiniLM-L6-v2")
_model = SentenceTransformer(MODEL_NAME)

app = Flask(__name__)

@app.post("/embed")
def embed():
    data = request.get_json(silent=True) or {}
    texts = data.get("texts") or []
    if not isinstance(texts, list) or not texts:
        return jsonify({"error":"texts(list) required"}), 400
    vectors = _model.encode(texts, normalize_embeddings=True).tolist()
    return jsonify({"embeddings": vectors})

if __name__ == "__main__":
    app.run(host=os.getenv("HOST","0.0.0.0"), port=int(os.getenv("PORT","5001")))
