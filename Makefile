# =========================
# Makefile (root)
# =========================

# ---- Variables ----
DC            = docker compose -f docker.compose.yaml
API_URL       = http://localhost:8081
GRAFANA_URL   = http://localhost:3000
GRAFANA_USER  = admin
GRAFANA_PASS  = grafana
DASH_DIR      = observability/grafana/provisioning/dashboards
DASH_FILE     = $(DASH_DIR)/rag-overview.json
DATASET       = data/eval.jsonl
PYTHON        = python

# ---- Helpers ----
define set_env
$(PYTHON) - <<'PY'
import os, sys, re
path = ".env"
k, v = sys.argv[1], sys.argv[2]
lines = []
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
pat = re.compile(rf"^\s*{re.escape(k)}\s*=")
found = False
out = []
for line in lines:
    if pat.match(line):
        out.append(f"{k}={v}")
        found = True
    else:
        out.append(line)
if not found:
    out.append(f"{k}={v}")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + ("\n" if out else ""))
print(f"updated: {k}={v}")
PY
endef

# ---- Phony ----
.PHONY: help up up-all up-obs up-core up-ui down clean ps logs smoke \
        ab-on ab-off ab-status \
        ingest eval dashboards dashboards-list grafana-health

# ---- Help ----
help:
	@echo "Targets:"
	@echo "  up-obs            : Start observability stack (Datadog Agent, Tempo, Loki, Promtail, Grafana)"
	@echo "  up-core           : Start core services (Ollama, vector-store, api, text-embedder, kb_service, api_rag)"
	@echo "  up-ui             : Start UI (chatbot, dash-ui, streamlit-ui)"
	@echo "  up-all            : Start everything (obs+core+ui)"
	@echo "  down/clean        : Stop / Stop + remove volumes"
	@echo "  ps/logs           : Show status / Tail logs"
	@echo "  smoke             : Quick health checks for key ports/endpoints"
	@echo "  ingest            : Run KB ingestion once"
	@echo "  eval              : Run quick RAG eval against $(DATASET)"
	@echo "  dashboards        : Upload Grafana dashboards via API"
	@echo "  dashboards-list   : List Grafana dashboards"
	@echo "  grafana-health    : Check Grafana health API"
	@echo "  ab-on/ab-off      : Toggle Canary A/B (MODEL_NAME_ALT, PROMPT_VERSION, CANARY_RATIO)"
	@echo "  ab-status         : Print A/B settings from .env"

# ---- Compose profiles ----
up-obs:
	$(DC) --profile obs up -d

up-core:
	$(DC) --profile core up -d

up-ui:
	$(DC) --profile ui up -d

up-all:
	$(DC) --profile obs --profile core --profile ui up -d

down:
	$(DC) down

clean:
	$(DC) down -v

ps:
	$(DC) ps

logs:
	$(DC) logs -f --tail=150

# ---- Smoke tests ----
smoke:
	@echo "Checking services..."
	@curl -fsS $(API_URL)/healthz >/dev/null && echo "OK rag-api" || (echo "FAIL rag-api"; exit 1)
	@curl -fsS $(GRAFANA_URL)/api/health | grep -q '"database":"ok"' && echo "OK grafana" || (echo "FAIL grafana"; exit 1)
	@curl -fsS http://localhost:3100/ready >/dev/null && echo "OK loki" || (echo "WARN loki not ready")
	@curl -fsS http://localhost:3200/ready >/dev/null && echo "OK tempo" || (echo "WARN tempo not ready")
	@echo "Smoke OK"

# ---- KB Ingestion (once) ----
ingest:
	$(DC) run --rm kb_service python ingest_documents.py

# ---- Quick RAG eval ----
eval:
	@echo "Running eval against $(API_URL) with $(DATASET)"
	$(PYTHON) lab2-rag/api/eval_ragas.py --api $(API_URL) --dataset $(DATASET) --limit 30

# ---- Grafana dashboards ----
dashboards:
	@echo "Uploading dashboard(s) in $(DASH_DIR) to $(GRAFANA_URL)"
	@for f in $(DASH_DIR)/*.json; do \
	  echo "POST $$f"; \
	  curl -sS -u $(GRAFANA_USER):$(GRAFANA_PASS) \
	    -H "Content-Type: application/json" \
	    -X POST "$(GRAFANA_URL)/api/dashboards/db" \
	    -d @$$f | jq '.status,.slug' || true; \
	done
	@echo "Done."

dashboards-list:
	curl -sS -u $(GRAFANA_USER):$(GRAFANA_PASS) "$(GRAFANA_URL)/api/search?query=&type=dash-db" | jq '.[].title'

grafana-health:
	curl -sS -u $(GRAFANA_USER):$(GRAFANA_PASS) "$(GRAFANA_URL)/api/health" | jq

# ---- A/B (Canary) toggles ----
# ab-on: enable canary with ALT model + prompt v2 + ratio 0.2 (edit as needed)
ab-on:
	@$(call set_env,MODEL_NAME_ALT,${MODEL_NAME_ALT:-llama3.1})
	@$(call set_env,PROMPT_VERSION,v2)
	@$(call set_env,CANARY_RATIO,0.2)
	@echo "A/B Canary ON -> MODEL_NAME_ALT=$$(grep '^MODEL_NAME_ALT=' .env || echo MODEL_NAME_ALT=llama3.1); PROMPT_VERSION=v2; CANARY_RATIO=0.2"

# ab-off: return to main model + prompt v1 + ratio 0.0
ab-off:
	@$(call set_env,PROMPT_VERSION,v1)
	@$(call set_env,CANARY_RATIO,0.0)
	@echo "A/B Canary OFF -> PROMPT_VERSION=v1; CANARY_RATIO=0.0"

ab-status:
	@echo "---- .env A/B status ----"
	@grep -E '^(MODEL_NAME_ALT|PROMPT_VERSION|CANARY_RATIO)=' .env || echo "(keys not set yet)"
