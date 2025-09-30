#!/bin/bash
# entrypoint.sh - Proper Streamlit startup script

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

# Start Streamlit
echo "🎯 Starting Streamlit server..."
exec streamlit run app.py \
    --server.port=8080 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --server.runOnSave=false \
    --server.fileWatcherType=none \
    --browser.serverAddress=0.0.0.0 \
    --browser.gatherUsageStats=false \
    --logger.level=info