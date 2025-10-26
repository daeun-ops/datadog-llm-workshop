SHELL := /bin/bash
ENV_FILE := .env

include $(ENV_FILE)

.PHONY: up down logs tail trace-demo dashboards:push smoke kb:rebuild ab:on ab:off ab:status eval

up:
	docker compose --env-file $(ENV_FILE) -f docker.compose.yaml up -d --build

down:
	docker compose --env-file $(ENV_FILE) -f docker.compose.yaml down -v

logs:
	docker compose -f docker.compose.yaml ps
	docker compose -f docker.compose.yaml logs --no-color --tail=200

tail:
	docker compose -f docker.compose.yaml logs -f --tail=50 rag-api kb-service text-embedder otel-collector datadog-agent

trace-demo:
	curl -s localhost:8080/demo | jq .

kb:rebuild:
	./scripts/rebuild_kb.sh

ab:on:
	docker compose exec rag-api sh -lc 'sed -i "s/^AB_MODE=.*/AB_MODE=auto/" /proc/1/environ || true'

ab:off:
	docker compose exec rag-api sh -lc 'sed -i "s/^AB_MODE=.*/AB_MODE=A/" /proc/1/environ || true'

ab:status:
	curl -s localhost:7000/healthz | jq .

dashboards:push:
	@echo "Grafana dashboards are provisioned from ./observability/grafana/dashboards"

eval:
	python scripts/eval.py

PROFILE ?= tempo

ENV_FILE := .env.local.$(PROFILE)

up:
	docker compose --env-file $(ENV_FILE) -f docker.compose.yaml up -d --build
