FROM python:3.10-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p model_cache .streamlit

# Ensure config is in place
COPY .streamlit/config.toml .streamlit/config.toml

# Expose port
EXPOSE 8080

# Health check - zwiększony start period i timeout
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=5 \
    CMD curl --fail http://localhost:8080/_stcore/health || exit 1

# KRYTYCZNA ZMIANA: Użyj exec form + dodaj --server.runOnSave=false
CMD ["streamlit", "run", "app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false", \
     "--server.runOnSave=false", \
     "--browser.serverAddress=0.0.0.0", \
     "--browser.gatherUsageStats=false", \
     "--logger.level=info"]