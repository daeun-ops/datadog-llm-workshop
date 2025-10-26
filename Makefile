SHELL := /bin/bash
ENV_FILE := .env

include $(ENV_FILE)

.PHONY: up down logs tail trace-demo dashboards:push smoke

up:
	docker compose --env-file $(ENV_FILE) -f docker.compose.yaml up -d --build

down: 
	docker compose --env-file $(ENV_FILE) -f docker.compose.yaml down -v

logs:
	docker compose -f docker.compose.yaml ps
	docker compose -f docker.compose.yaml logs --no-color --tail=200

tail:
	docker compose -f docker.compose.yaml logs -f --tail=50 demo-app otel-collector datadog-agent

trace-demo:
	curl -s localhost:8080/demo | jq .
	sleep 2
	open "http://localhost:3000" || true

dashboards:push:
	@echo "Grafana dashboards are provisioned from ./observability/grafana/dashboards"

smoke: up
	@echo "[*] Wait for health..."
	sleep 8
	@echo "[*] Hit demo endpoint"
	$(MAKE) trace-demo
