.PHONY: help install test run docker-build docker-run deploy clean

help:
	@echo "Half Marathon Predictor - Available Commands"
	@echo "============================================"
	@echo "make install       - Install dependencies"
	@echo "make test          - Run tests"
	@echo "make run           - Run app locally"
	@echo "make docker-build  - Build Docker image"
	@echo "make docker-run    - Run Docker container"
	@echo "make deploy        - Deploy to Digital Ocean"
	@echo "make clean         - Clean temporary files"
	@echo "make format        - Format code with black"
	@echo "make lint          - Lint code"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "✅ Dependencies installed"

test:
	.venv/bin/python test_app.py
	@echo "✅ Tests completed"

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
	.venv/bin/flake8 . --max-line-length=120
	@echo "✅ Linting complete"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/
	@echo "✅ Cleaned temporary files"

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