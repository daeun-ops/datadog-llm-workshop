FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] ddtrace opentelemetry-sdk opentelemetry-exporter-otlp prometheus-client chromadb
COPY services/rag_api/app.py /app/app.py
EXPOSE 7000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","7000"]
