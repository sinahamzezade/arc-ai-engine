FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY app.py .
COPY contracts/ ./contracts/
COPY engine/ ./engine/

ENV PYTHONUNBUFFERED=1
ENV ROADMAP_ENGINE_VERSION=2

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
