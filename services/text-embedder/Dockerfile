FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] ddtrace opentelemetry-sdk opentelemetry-exporter-otlp
COPY services/text-embedder/app.py /app/app.py
EXPOSE 5001
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","5001"]
