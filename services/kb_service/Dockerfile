FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] ddtrace opentelemetry-sdk opentelemetry-exporter-otlp chromadb requests
COPY services/kb_service/app.py /app/app.py
EXPOSE 5002
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","5002"]
