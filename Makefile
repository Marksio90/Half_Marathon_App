.PHONY: help install test test-integration run docker-build docker-run deploy clean format lint

help:
	@echo "Half Marathon Predictor - Available Commands"
	@echo "============================================"
	@echo "make install          - Install dependencies"
	@echo "make test             - Run unit tests"
	@echo "make test-integration - Run integration tests"
	@echo "make test-all         - Run all tests"
	@echo "make run              - Run app locally"
	@echo "make docker-build     - Build Docker image"
	@echo "make docker-run       - Run Docker container"
	@echo "make deploy           - Deploy to Digital Ocean"
	@echo "make clean            - Clean temporary files"
	@echo "make format           - Format code with black"
	@echo "make lint             - Lint code"
	@echo "make cache-clear      - Clear LLM cache"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "✅ Dependencies installed"

test:
	.venv/bin/python test_app.py
	@echo "✅ Unit tests completed"

test-integration:
	.venv/bin/python test_integration.py
	@echo "✅ Integration tests completed"

test-all: test test-integration
	@echo "✅ All tests completed"

run:
	.venv/bin/streamlit run app.py
	@echo "🚀 App running at http://localhost:8501"

docker-build:
	docker build -t halfmarathon-predictor:latest .
	@echo "✅ Docker image built"

docker-run:
	docker run -p 8080:8080 --env-file .env halfmarathon-predictor:latest

deploy:
	chmod +x deploy.sh
	./deploy.sh

format:
	.venv/bin/black .
	@echo "✅ Code formatted"

lint:
	.venv/bin/flake8 . --max-line-length=120 --exclude=.venv
	@echo "✅ Linting complete"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/
	@echo "✅ Cleaned temporary files"

cache-clear:
	.venv/bin/python -c "from utils.llm_extractor import clear_llm_cache; clear_llm_cache()"
	@echo "✅ LLM cache cleared"

setup-spaces:
	@echo "Setting up Digital Ocean Spaces..."
	@bash -c 'source .env && \
		aws s3 mb s3://$$DO_SPACES_BUCKET \
		--endpoint-url=https://$$DO_SPACES_REGION.digitaloceanspaces.com \
		--profile digitalocean'
	@echo "✅ Spaces bucket created"

upload-data:
	@echo "Uploading data to Spaces..."
	@bash -c 'source .env && \
		aws s3 cp halfmarathon_wroclaw_2023__final.csv \
		s3://$$DO_SPACES_BUCKET/data/ \
		--endpoint-url=https://$$DO_SPACES_REGION.digitaloceanspaces.com \
		--profile digitalocean && \
		aws s3 cp halfmarathon_wroclaw_2024__final.csv \
		s3://$$DO_SPACES_BUCKET/data/ \
		--endpoint-url=https://$$DO_SPACES_REGION.digitaloceanspaces.com \
		--profile digitalocean'
	@echo "✅ Data uploaded"

train:
	@echo "Training model..."
	.venv/bin/jupyter nbconvert --to notebook --execute notebooks/training_pipeline.ipynb
	@echo "✅ Model trained"

# ← NOWE: Quick start dla nowych użytkowników
quickstart: install
	@echo ""
	@echo "🎉 Quick Start Guide:"
	@echo "1. Copy .env.example to .env"
	@echo "2. Fill in your API keys in .env"
	@echo "3. Run: make run"
	@echo ""
	@echo "For deployment:"
	@echo "1. Run: make upload-data"
	@echo "2. Run: make train"
	@echo "3. Run: make deploy"
	@echo ""

# ← NOWE: Health check
health-check:
	@echo "Running health checks..."
	@.venv/bin/python -c "import streamlit; import openai; import boto3; import xgboost; print('✅ All modules OK')"
	@curl -f http://localhost:8501/_stcore/health 2>/dev/null && echo "✅ Streamlit running" || echo "⚠️  Streamlit not running"

# ← NOWE: Development mode (auto-reload)
dev:
	.venv/bin/streamlit run app.py --server.runOnSave=true --server.fileWatcherType=auto