import json
from lab2_rag.api.app import app

def client():
    app.testing = True
    return app.test_client()

def test_explain_mode_includes_trace_id():
    c = client()
    r = c.post("/ask", json={"question":"What model does this demo use?", "explain": True})
    if r.status_code == 200:
        body = r.get_json()
        assert "trace_id" in body
        assert "trace_link_tempo" in body
