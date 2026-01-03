from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from workshop_app.llm_client import chat
from workshop_app.observability import current_trace_ids, init_datadog_llmobs

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("workshop.main")

app = FastAPI(title="Datadog LLM Workshop API", version=os.getenv("DD_VERSION", "0.1.0"))


class ChatRequest(BaseModel):
    query: str
    system: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    model: str
    latency_ms: int
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


@app.on_event("startup")
def _startup() -> None:
    # Enable Datadog LLM Observability (manual spans)
    init_datadog_llmobs()
    log.info("startup complete")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest) -> ChatResponse:
    system_text = req.system or "You are a helpful assistant. Be concise and correct."
    result = chat(
        user_text=req.query,
        system_text=system_text,
        session_id=req.session_id,
    )
    ids = current_trace_ids()
    return ChatResponse(
        answer=result.content,
        model=result.model,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        trace_id=ids["trace_id"],
        span_id=ids["span_id"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "workshop_app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=os.getenv("UVICORN_LOG_LEVEL", "info"),
    )
