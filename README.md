# 🏃 Half Marathon Time Predictor

Professional ML application for predicting half-marathon finish times using XGBoost, OpenAI, and Langfuse monitoring.

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31-FF4B4B.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Setup Instructions](#setup-instructions)
- [Digital Ocean Spaces Setup](#digital-ocean-spaces-setup)
- [Training Pipeline](#training-pipeline)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Project Structure](#project-structure)

## ✨ Features

- 🤖 **XGBoost ML Model** - Trained on 20,000+ real race results
- 🧠 **LLM Data Extraction** - Uses OpenAI GPT-4o-mini to extract data from natural language
- 📊 **Langfuse Monitoring** - Track LLM performance and user interactions
- ☁️ **Digital Ocean Integration** - Data and models stored in Spaces
- 🚀 **Production Ready** - Dockerized application with health checks
- 📱 **Responsive UI** - Beautiful Streamlit interface

## 🏗️ Architecture

```
┌─────────────────┐
│   User Input    │
│  (Natural Lang) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  OpenAI GPT-4   │─────▶│   Langfuse   │
│  Data Extraction│      │  Monitoring  │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  XGBoost Model  │◀─────│ DO Spaces    │
│   Prediction    │      │ Model Store  │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  Streamlit UI   │
│  (Results)      │
└─────────────────┘
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.10+
- Digital Ocean account with Spaces enabled
- OpenAI API key
- Langfuse account (free tier available)

### 1. Clone Repository

```bash
git clone https://github.com/your-username/halfmarathon-predictor.git
cd halfmarathon-predictor
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

## ☁️ Digital Ocean Spaces Setup

### Step 1: Create Spaces Bucket

1. Log in to Digital Ocean
2. Navigate to **Spaces** → **Create Space**
3. Choose region (e.g., `fra1` for Frankfurt)
4. Name your space: `halfmarathon-ml`
5. Set access to **Private**

### Step 2: Generate API Keys

1. Go to **API** → **Spaces Keys**
2. Click **Generate New Key**
3. Save the Access Key and Secret Key
4. Add to your `.env` file

### Step 3: Upload Data Files

Using AWS CLI (Spaces is S3-compatible):

```bash
# Install AWS CLI
pip install awscli

# Configure
aws configure --profile digitalocean
# Enter your Spaces keys and region

# Upload data
aws s3 cp halfmarathon_wroclaw_2023__final.csv \
  s3://halfmarathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean

aws s3 cp halfmarathon_wroclaw_2024__final.csv \
  s3://halfmarathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

Or use the Digital Ocean web interface to upload manually.

## 🎓 Training Pipeline

### Run the Training Notebook

```bash
cd notebooks
jupyter notebook training_pipeline.ipynb
```

The pipeline will:
1. ✅ Load data from Digital Ocean Spaces
2. ✅ Clean and preprocess data
3. ✅ Perform feature engineering
4. ✅ Train XGBoost model with hyperparameter tuning
5. ✅ Evaluate model performance
6. ✅ Save model locally and upload to Spaces

### Expected Results

- **MAE**: ~4.5 minutes
- **RMSE**: ~6.2 minutes  
- **R² Score**: 0.92

## 🌐 Deployment

### Local Development

```bash
streamlit run app.py
```

Visit `http://localhost:8501`

### Deploy to Digital Ocean App Platform

#### Option 1: Using Web Interface

1. Go to **App Platform** → **Create App**
2. Connect your GitHub repository
3. Choose `Dockerfile` as build method
4. Set environment variables (see below)
5. Deploy!

#### Option 2: Using CLI

```bash
# Install doctl
brew install doctl  # macOS
# or download from: https://docs.digitalocean.com/reference/doctl/

# Authenticate
doctl auth init

# Create app
doctl apps create --spec app.yaml

# Monitor deployment
doctl apps list
```

#### Option 3: Using Docker

```bash
# Build image
docker build -t halfmarathon-predictor .

# Run locally
docker run -p 8080:8080 \
  -e DO_SPACES_KEY=$DO_SPACES_KEY \
  -e DO_SPACES_SECRET=$DO_SPACES_SECRET \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e LANGFUSE_SECRET_KEY=$LANGFUSE_SECRET_KEY \
  -e LANGFUSE_PUBLIC_KEY=$LANGFUSE_PUBLIC_KEY \
  halfmarathon-predictor
```

## 🔐 Environment Variables

Create a `.env` file with the following variables:

```bash
# Digital Ocean Spaces
DO_SPACES_KEY=your_spaces_access_key
DO_SPACES_SECRET=your_spaces_secret_key
DO_SPACES_REGION=fra1
DO_SPACES_BUCKET=halfmarathon-ml

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# Langfuse
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Getting API Keys

#### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy and save securely

#### Langfuse
1. Sign up at https://cloud.langfuse.com
2. Create new project
3. Go to Settings → API Keys
4. Copy both public and secret keys

## 📖 Usage

### Example Inputs

```
"Hi, I'm John, 32 years old male, and my 5km time is 23:45"

"I'm a 28-year-old woman and I can run 5km in 27 minutes"

"Male runner, age 45, 5k PR: 22:30"
```

### Required Information

The app extracts:
- **Gender**: male/female
- **Age**: in years (15-90)
- **5km Time**: in MM:SS format

### API Usage (Optional)

You can also use the model programmatically:

```python
from utils.model_predictor import HalfMarathonPredictor

predictor = HalfMarathonPredictor()

result = predictor.predict({
    'gender': 'male',
    'age': 30,
    'time_5km_seconds': 1425  # 23:45
})

print(f"Predicted time: {result['formatted_time']}")
```

## 📁 Project Structure

```
halfmarathon-predictor/
├── notebooks/
│   └── training_pipeline.ipynb    # ML training pipeline
├── app/
│   ├── app.py                     # Main Streamlit app
│   ├── requirements.txt           # Python dependencies
│   ├── Dockerfile                 # Container configuration
│   ├── .streamlit/
│   │   └── config.toml           # Streamlit settings
│   └── utils/
│       ├── __init__.py
│       ├── data_loader.py        # Data loading from Spaces
│       ├── llm_extractor.py      # OpenAI data extraction
│       └── model_predictor.py    # Model inference
├── .env.example                   # Environment template
├── app.yaml                       # DO App Platform spec
└── README.md                      # This file
```

## 🧪 Testing

### Test Data Extraction

```python
from utils.llm_extractor import extract_user_data

text = "I'm a 30-year-old male, 5km time is 24:30"
data = extract_user_data(text)
print(data)
# {'gender': 'male', 'age': 30, 'time_5km_seconds': 1470}
```

### Test Model Prediction

```python
from utils.model_predictor import HalfMarathonPredictor

predictor = HalfMarathonPredictor()
result = predictor.predict({
    'gender': 'male',
    'age': 30,
    'time_5km_seconds': 1470
})
print(result['formatted_time'])  # e.g., "1:45:32"
```

## 📊 Monitoring with Langfuse

Access your Langfuse dashboard to monitor:
- LLM extraction success rates
- Token usage and costs
- User input patterns
- Error rates and debugging
- Model prediction trends

Dashboard: https://cloud.langfuse.com

## 🐛 Troubleshooting

### Model not loading
- Check Digital Ocean Spaces credentials
- Verify bucket name and region
- Ensure model files are uploaded to `models/` folder

### OpenAI API errors
- Verify API key is valid and has credits
- Check rate limits
- Ensure proper error handling in code

### Deployment issues
- Check all environment variables are set
- Verify Docker image builds successfully
- Check Digital Ocean App Platform logs

## 🔄 Updating the Model

1. Run training pipeline with new data
2. New model automatically uploads to Spaces with timestamp
3. Update app to use new model version or use `_latest` suffix
4. Redeploy application

## 📈 Performance Optimization

- Model cached locally after first download
- Lazy loading of dependencies
- Efficient data preprocessing
- XGBoost optimized for inference

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 👨‍💻 Author

Your Name - [your-email@example.com](mailto:your-email@example.com)

## 🙏 Acknowledgments

- Wrocław Half Marathon for race data
- OpenAI for GPT-4o-mini API
- Langfuse for monitoring tools
- Digital Ocean for infrastructure

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check Langfuse logs for LLM issues
- Review Digital Ocean App Platform logs

---

**Built with ❤️ using Python, XGBoost, Streamlit, and Digital Ocean**