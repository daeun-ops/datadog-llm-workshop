## 요야기ㅣ
- [ ] Hybrid retrieval & rerank verified
- [ ] Prompt versioning (v1/v2) & Canary routing
- [ ] Feedback loop wired (data/feedback.jsonl)
- [ ] Metrics (/metrics) with exemplars (trace_id)
- [ ] CI eval (RAG quick score)

## How to !!!!' 
```bash
docker compose --profile obs up -d
docker compose --profile core up -d
curl -s http://localhost:8081/healthz

# ask
curl -s -X POST localhost:8081/ask -H "Content-Type: application/json" -d '{"question":"What model?"}' | jq

# feedback
curl -s -X POST localhost:8081/feedback -H "Content-Type: application/json" \
  -d '{"question":"What model?","answer":"llama3.1","good":true,"model":"llama3.1","prompt_version":"v1"}'
