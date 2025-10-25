FROM python:3.11-slim
WORKDIR /app
RUN pip install -U pip
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8082
CMD ["python","app.py"]
