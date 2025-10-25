import os, requests
from dash import Dash, html, dcc, Input, Output, State

from observability.dd import enable_tracing_if_configured, enable_otel_if_configured, span
SERVICE="dash-ui"
enable_tracing_if_configured(SERVICE)
enable_otel_if_configured(SERVICE)

API_URL = os.getenv("API_URL", "http://api_rag:8081")

app = Dash(__name__)
app.title = "RAG Dashboard"

app.layout = html.Div([
    html.H3("RAG Dashboard (Dash)"),
    dcc.Textarea(id="q", style={"width":"100%","height":"120px"}, placeholder="질문을 입력하세요"),
    html.Br(),
    html.Button("Ask", id="ask"),
    html.Div(id="answer", style={"whiteSpace":"pre-wrap","marginTop":"1rem"})
])

@app.callback(Output("answer","children"), Input("ask","n_clicks"), State("q","value"))
def ask(n, q):
    if not n: return ""
    q = (q or "").strip()
    if not q: return "what ever u want tell me telme."
    with span("ui.ask", ui="dash"):
        r = requests.post(f"{API_URL}/ask", json={"question": q}, timeout=120)
    if not r.ok:
        return f"API error: {r.status_code}\n{r.text}"
    j = r.json()
    return f"[sources={j.get('source_count',0)}]\n{j.get('answer','')}"
    
if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8050)
