# Use 3.12 to match user's local env
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    # Needed for some python packages
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Upgrade pip first
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire code directory
COPY code ./code

# Set working directory to where main.py is relative to PYTHONPATH
WORKDIR /app/code

ENV PYTHONPATH=/app/code
# ENV DISABLE_LOCAL_LIBS=1  <-- Commented out unless your app specifically checks this

# Cloud Run expects port 8080 by default
# Use explicit python -m uvicorn to ensure correct path
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "debug", "--timeout-keep-alive", "120"]

