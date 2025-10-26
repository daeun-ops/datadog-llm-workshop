FROM python:3.11-slim
WORKDIR /app
COPY scripts/emit_demo.py /app/emit_demo.py
RUN pip install --no-cache-dir prometheus-client opentelemetry-sdk opentelemetry-exporter-otlp protobuf flask ddtrace
EXPOSE 8080
CMD ["python", "/app/emit_demo.py"]
