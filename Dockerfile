FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory (Railway mounts persistent volume at /data)
RUN mkdir -p /data

# Default environment values (override in Railway)
ENV DATABASE_PATH=/data/keyword_alert.db
ENV TIMEZONE=Asia/Kolkata
ENV LOG_LEVEL=INFO
ENV PORT=8080

EXPOSE 8080

CMD ["python", "main.py"]
