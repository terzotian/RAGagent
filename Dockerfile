FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY code ./code

ENV PYTHONPATH=/app/code
ENV DISABLE_LOCAL_LIBS=1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]

