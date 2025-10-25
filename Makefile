.PHONY: up pull ingest down logs ps clean

ENV_FILE=.env
DC=docker compose -f docker.compose.yaml

pull:
	$(DC) up -d localllama
	docker exec -it localllama ollama pull llama3.1

up:
	$(DC) up -d

ingest:
	$(DC) run --rm kb_service python ingest_documents.py

logs:
	$(DC) logs -f --tail=100

ps:
	$(DC) ps

down:
	$(DC) down

clean:
	$(DC) down -v
