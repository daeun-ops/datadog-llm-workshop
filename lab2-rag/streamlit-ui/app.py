import os, requests, streamlit as st
from observability.dd import enable_tracing_if_configured, enable_otel_if_configured, span

SERVICE="streamlit-ui"
enable_tracing_if_configured(SERVICE)
enable_otel_if_configured(SERVICE)

API_URL = os.getenv("API_URL","http://api_rag:8081")

st.set_page_config(page_title="RAG (Streamlit)", layout="centered")
st.title("RAG Playground (Streamlit)")

q = st.text_area("질문", height=160, placeholder="예: 이 시스템 아키텍처를 한 줄로 요약해줘")
if st.button("Ask"):
    if not q.strip():
        st.warning("what ever u want what... it is... tellme pls.")
    else:
        with st.spinner(" gomin gomin ..."):
            with span("ui.ask", ui="streamlit"):
                r = requests.post(f"{API_URL}/ask", json={"question": q}, timeout=120)
            if not r.ok:
                st.error(f"API error: {r.status_code}\n{r.text}")
            else:
                j = r.json()
                st.success(f"Sources={j.get('source_count',0)}")
                st.markdown(j.get("answer",""))
