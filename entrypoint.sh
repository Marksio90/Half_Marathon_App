#!/bin/bash
# entrypoint.sh - Enhanced Streamlit startup script

set -e

echo "🚀 Starting Half Marathon Predictor..."

# Export environment variables explicitly
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_SERVER_PORT=8080
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_RUN_ON_SAVE=false
export STREAMLIT_SERVER_FILE_WATCHER_TYPE=none
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Print environment info
echo "📊 Environment:"
echo "   - Port: $STREAMLIT_SERVER_PORT"
echo "   - Headless: $STREAMLIT_SERVER_HEADLESS"
echo "   - Python: $(python --version)"
echo "   - Streamlit: $(streamlit --version)"

# Check if model cache exists
if [ ! -d "model_cache" ]; then
    echo "📁 Creating model_cache directory..."
    mkdir -p model_cache
fi

# ← NOWE: Kill old Streamlit processes (prevents restart loops)
if pgrep -f "streamlit run" > /dev/null 2>&1; then
    echo "⚠️  Found existing Streamlit process, cleaning up..."
    pkill -9 -f "streamlit run" || true
    sleep 2
fi

# ← NOWE: Health check przed startem
echo "🔍 Pre-flight checks..."

# Check Python modules
python -c "import streamlit, openai, boto3, xgboost" 2>/dev/null && echo "✅ Core modules OK" || echo "⚠️  Some modules missing"

# Check environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY not set"
fi

if [ -z "$DO_SPACES_KEY" ]; then
    echo "⚠️  WARNING: DO_SPACES_KEY not set"
fi

# ← NOWE: Ensure single instance (Docker-specific)
if [ -f "/.dockerenv" ]; then
    echo "🐳 Running in Docker container"
    
    # Create PID file
    PIDFILE="/tmp/streamlit.pid"
    if [ -f "$PIDFILE" ]; then
        OLD_PID=$(cat "$PIDFILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo "⚠️  Killing old Streamlit PID: $OLD_PID"
            kill -9 "$OLD_PID" || true
        fi
        rm -f "$PIDFILE"
    fi
fi

# Start Streamlit with proper error handling
echo "🎯 Starting Streamlit server..."

# ← NOWE: Trap signals for graceful shutdown
trap 'echo "🛑 Received shutdown signal, stopping Streamlit..."; pkill -TERM streamlit; exit 0' SIGTERM SIGINT

# Start Streamlit in background and capture PID
streamlit run app.py \
    --server.port=8080 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --server.runOnSave=false \
    --server.fileWatcherType=none \
    --browser.serverAddress=0.0.0.0 \
    --browser.gatherUsageStats=false \
    --logger.level=info &

STREAMLIT_PID=$!

# Save PID
if [ -f "/.dockerenv" ]; then
    echo $STREAMLIT_PID > /tmp/streamlit.pid
fi

echo "✅ Streamlit started with PID: $STREAMLIT_PID"

# Wait for Streamlit to be ready
echo "⏳ Waiting for Streamlit to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8080/_stcore/health >/dev/null 2>&1; then
        echo "✅ Streamlit is ready!"
        break
    fi
    echo "   Attempt $i/30..."
    sleep 2
done

# Check if Streamlit is still running
if ! ps -p $STREAMLIT_PID > /dev/null 2>&1; then
    echo "❌ ERROR: Streamlit failed to start!"
    exit 1
fi

# Keep container running and monitor Streamlit
echo "👀 Monitoring Streamlit process..."
while true; do
    if ! ps -p $STREAMLIT_PID > /dev/null 2>&1; then
        echo "❌ ERROR: Streamlit process died unexpectedly!"
        exit 1
    fi
    sleep 10
done