FROM python:3.11-slim
WORKDIR /app
RUN pip install -U pip
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ingest_documents.py utils.py .
COPY ../kb_data /kb_data
CMD ["python","ingest_documents.py"]
