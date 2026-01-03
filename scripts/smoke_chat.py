from __future__ import annotations

import os
import time
import httpx

API = os.getenv("WORKSHOP_API", "http://localhost:8000")


def main() -> None:
    payload = {
        "query": "Summarize what Datadog LLM Observability captures in one sentence.",
        "session_id": f"smoke-{int(time.time())}",
    }
    r = httpx.post(f"{API}/chat", json=payload, timeout=30)
    r.raise_for_status()
    print(r.json())


if __name__ == "__main__":
    main()
