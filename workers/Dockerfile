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

# Copy agent prompts
COPY ../agents /app/agents

# Create necessary directories
RUN mkdir -p /app/repos

# Run worker
CMD ["python", "start_worker.py", "all"]
