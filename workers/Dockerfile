FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Create necessary directories (agents mounted via docker-compose volumes)
RUN mkdir -p /app/repos /app/agents /app/data

# Run worker
CMD ["python", "start_worker.py", "all"]
