#!/bin/bash

# Half Marathon Predictor - Deployment Script
# This script automates the deployment process

set -e

echo "🚀 Half Marathon Predictor - Deployment Script"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create .env file from .env.example"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

echo -e "${GREEN}✅ Environment variables loaded${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required tools
echo ""
echo "🔍 Checking required tools..."

if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python 3 found${NC}"

if ! command_exists docker; then
    echo -e "${YELLOW}⚠️  Docker not found (optional for local testing)${NC}"
else
    echo -e "${GREEN}✅ Docker found${NC}"
fi

if ! command_exists doctl; then
    echo -e "${YELLOW}⚠️  doctl not found (required for DO deployment)${NC}"
    echo "Install from: https://docs.digitalocean.com/reference/doctl/"
else
    echo -e "${GREEN}✅ doctl found${NC}"
fi

# Menu
echo ""
echo "📋 Deployment Options:"
echo "1. Upload data to Digital Ocean Spaces"
echo "2. Run training pipeline locally"
echo "3. Test application locally"
echo "4. Build Docker image"
echo "5. Deploy to Digital Ocean App Platform"
echo "6. Full deployment (all steps)"
echo "0. Exit"
echo ""

read -p "Select option (0-6): " choice

case $choice in
    1)
        echo ""
        echo "📤 Uploading data to Digital Ocean Spaces..."
        
        if ! command_exists aws; then
            echo -e "${RED}❌ AWS CLI not found${NC}"
            echo "Install with: pip install awscli"
            exit 1
        fi
        
        # Configure AWS CLI for DO Spaces
        aws configure set aws_access_key_id $DO_SPACES_KEY --profile digitalocean
        aws configure set aws_secret_access_key $DO_SPACES_SECRET --profile digitalocean
        aws configure set default.region $DO_SPACES_REGION --profile digitalocean
        
        ENDPOINT="https://${DO_SPACES_REGION}.digitaloceanspaces.com"
        
        # Upload CSV files
        if [ -f "halfmarathon_wroclaw_2023__final.csv" ]; then
            aws s3 cp halfmarathon_wroclaw_2023__final.csv \
                s3://${DO_SPACES_BUCKET}/data/ \
                --endpoint-url=$ENDPOINT \
                --profile digitalocean
            echo -e "${GREEN}✅ Uploaded 2023 data${NC}"
        fi
        
        if [ -f "halfmarathon_wroclaw_2024__final.csv" ]; then
            aws s3 cp halfmarathon_wroclaw_2024__final.csv \
                s3://${DO_SPACES_BUCKET}/data/ \
                --endpoint-url=$ENDPOINT \
                --profile digitalocean
            echo -e "${GREEN}✅ Uploaded 2024 data${NC}"
        fi
        
        echo -e "${GREEN}✅ Data upload complete${NC}"
        ;;
        
    2)
        echo ""
        echo "🎓 Running training pipeline..."
        
        # Check if virtual environment exists
        if [ ! -d ".venv" ]; then
            echo "Creating virtual environment..."
            python3 -m venv .venv
        fi
        
        source .venv/bin/activate
        pip install -r requirements.txt
        
        # Run notebook
        if command_exists jupyter; then
            jupyter nbconvert --to notebook --execute notebooks/training_pipeline.ipynb
            echo -e "${GREEN}✅ Training complete${NC}"
        else
            echo -e "${RED}❌ Jupyter not found${NC}"
            echo "Install with: pip install jupyter"
        fi
        ;;
        
    3)
        echo ""
        echo "🧪 Testing application locally..."
        
        if [ ! -d ".venv" ]; then
            python3 -m venv .venv
        fi
        
        source .venv/bin/activate
        pip install -r requirements.txt
        
        echo -e "${GREEN}✅ Starting Streamlit app...${NC}"
        echo "Access at: http://localhost:8501"
        streamlit run app.py
        ;;
        
    4)
        echo ""
        echo "🐳 Building Docker image..."
        
        docker build -t halfmarathon-predictor:latest .
        
        echo -e "${GREEN}✅ Docker image built${NC}"
        echo ""
        echo "Test locally with:"
        echo "docker run -p 8080:8080 --env-file .env halfmarathon-predictor:latest"
        ;;
        
    5)
        echo ""
        echo "☁️  Deploying to Digital Ocean App Platform..."
        
        if ! command_exists doctl; then
            echo -e "${RED}❌ doctl not found${NC}"
            exit 1
        fi
        
        # Check if app exists
        APP_ID=$(doctl apps list --format ID,Spec.Name | grep "halfmarathon-predictor" | awk '{print $1}')
        
        if [ -z "$APP_ID" ]; then
            echo "Creating new app..."
            doctl apps create --spec app.yaml
        else
            echo "Updating existing app (ID: $APP_ID)..."
            doctl apps update $APP_ID --spec app.yaml
        fi
        
        echo -e "${GREEN}✅ Deployment initiated${NC}"
        echo "Monitor progress with: doctl apps list"
        ;;
        
    6)
        echo ""
        echo "🚀 Full deployment process..."
        
        # Step 1: Upload data
        echo -e "${YELLOW}Step 1/4: Uploading data...${NC}"
        bash $0 1
        
        # Step 2: Train model
        echo -e "${YELLOW}Step 2/4: Training model...${NC}"
        bash $0 2
        
        # Step 3: Build Docker
        echo -e "${YELLOW}Step 3/4: Building Docker image...${NC}"
        bash $0 4
        
        # Step 4: Deploy
        echo -e "${YELLOW}Step 4/4: Deploying to Digital Ocean...${NC}"
        bash $0 5
        
        echo -e "${GREEN}✅ Full deployment complete!${NC}"
        ;;
        
    0)
        echo "Exiting..."
        exit 0
        ;;
        
    *)
        echo -e "${RED}❌ Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Done!${NC}"