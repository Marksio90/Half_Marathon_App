FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create necessary directories
RUN mkdir -p model_cache .streamlit

# Ensure config is in place
COPY .streamlit/config.toml .streamlit/config.toml

# Expose port
EXPOSE 8080

# Health check - zmniejszony dla szybszego feedback
HEALTHCHECK --interval=20s --timeout=10s --start-period=60s --retries=3 \
    CMD curl --fail http://localhost:8080/_stcore/health || exit 1

# CRITICAL: Use entrypoint script to prevent restart loops
ENTRYPOINT ["/app/entrypoint.sh"]