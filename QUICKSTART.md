# 🚀 Quick Start Guide

Get your Half Marathon Predictor up and running in 15 minutes!

## Prerequisites Checklist

- [ ] Digital Ocean account
- [ ] OpenAI API key
- [ ] Langfuse account (free)
- [ ] Python 3.10+ installed
- [ ] Git installed

## Step 1: Clone & Setup (2 min)

```bash
# Clone repository
git clone https://github.com/your-username/halfmarathon-predictor.git
cd halfmarathon-predictor

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Get API Keys (5 min)

### Digital Ocean Spaces

1. Go to https://cloud.digitalocean.com/spaces
2. Click **Create a Space**
3. Choose region: `Frankfurt (fra1)`
4. Name: `halfmarathon-ml`
5. Set to **Private**
6. Go to **API** → **Spaces Keys** → **Generate New Key**
7. Save your **Access Key** and **Secret Key**

### OpenAI

1. Visit https://platform.openai.com/api-keys
2. Click **Create new secret key**
3. Copy and save the key (starts with `sk-`)

### Langfuse

1. Sign up at https://cloud.langfuse.com
2. Create a new project: "Half Marathon Predictor"
3. Go to **Settings** → **API Keys**
4. Copy **Public Key** (pk-lf-...) and **Secret Key** (sk-lf-...)

## Step 3: Configure Environment (1 min)

```bash
# Copy example env file
cp .env.example .env

# Edit .env file with your keys
nano .env  # or use your favorite editor
```

Your `.env` should look like:

```bash
DO_SPACES_KEY=YOUR_SPACES_ACCESS_KEY
DO_SPACES_SECRET=YOUR_SPACES_SECRET_KEY
DO_SPACES_REGION=fra1
DO_SPACES_BUCKET=halfmarathon-ml

OPENAI_API_KEY=sk-YOUR_OPENAI_KEY

LANGFUSE_SECRET_KEY=sk-lf-YOUR_SECRET_KEY
LANGFUSE_PUBLIC_KEY=pk-lf-YOUR_PUBLIC_KEY
LANGFUSE_HOST=https://cloud.langfuse.com
```

## Step 4: Upload Data to Spaces (2 min)

### Option A: Using AWS CLI (Recommended)

```bash
# Install AWS CLI
pip install awscli

# Configure for Digital Ocean
aws configure --profile digitalocean
# Enter your Spaces keys when prompted
# Region: fra1
# Output format: json

# Upload data files
aws s3 cp halfmarathon_wroclaw_2023__final.csv \
  s3://halfmarathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean

aws s3 cp halfmarathon_wroclaw_2024__final.csv \
  s3://halfmarathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

### Option B: Using Web Interface

1. Go to your Space in Digital Ocean
2. Click **Upload Files**
3. Create folder `data`
4. Upload both CSV files to the `data` folder

## Step 5: Train Model (3 min)

```bash
# Install Jupyter
pip install jupyter

# Run training notebook
cd notebooks
jupyter notebook training_pipeline.ipynb
```

In Jupyter:
1. Click **Cell** → **Run All**
2. Wait for training to complete (~2-3 minutes)
3. Model will automatically upload to Digital Ocean Spaces

## Step 6: Test Locally (1 min)

```bash
# Return to root directory
cd ..

# Run Streamlit app
streamlit run app.py
```

Visit http://localhost:8501 and test with:

```
I'm a 30-year-old male, my 5km time is 24:30
```

## Step 7: Deploy to Production (5 min)

### Using Digital Ocean App Platform

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-username/halfmarathon-predictor.git
   git push -u origin main
   ```

2. **Create App on Digital Ocean**
   - Go to https://cloud.digitalocean.com/apps
   - Click **Create App**
   - Select **GitHub** as source
   - Choose your repository
   - Select branch: `main`
   - **Build method**: Select "Dockerfile"
   - Click **Next**

3. **Configure Environment Variables**
   
   Add these variables (mark as SECRET):
   ```
   DO_SPACES_KEY
   DO_SPACES_SECRET
   OPENAI_API_KEY
   LANGFUSE_SECRET_KEY
   LANGFUSE_PUBLIC_KEY
   ```
   
   Add these as regular variables:
   ```
   DO_SPACES_REGION=fra1
   DO_SPACES_BUCKET=halfmarathon-ml
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

4. **Configure Resources**
   - Instance size: Basic (512MB RAM)
   - HTTP Port: 8080
   - Health check path: `/_stcore/health`

5. **Deploy**
   - Click **Create Resources**
   - Wait 5-10 minutes for deployment
   - Your app will be available at `https://your-app.ondigitalocean.app`

## 🎉 You're Done!

Your app is now live! Share the URL with others.

## 📊 Monitor Performance

1. **Langfuse Dashboard**: https://cloud.langfuse.com
   - View LLM extraction metrics
   - Monitor token usage
   - Track user interactions

2. **Digital Ocean Logs**:
   ```bash
   doctl apps logs <app-id> --follow
   ```

## 🐛 Troubleshooting

### "Model not loading"
- Check if training notebook completed successfully
- Verify files in Spaces: `models/halfmarathon_model_latest.pkl`
- Check DO Spaces credentials in `.env`

### "OpenAI API Error"
- Verify API key is correct
- Check you have credits: https://platform.openai.com/usage
- Rate limits: Wait a moment and try again

### "App won't start"
- Check Digital Ocean App Platform logs
- Verify all environment variables are set
- Ensure Dockerfile builds successfully locally

### "Predictions are wrong"
- Retrain model with latest data
- Check input data format
- Verify feature engineering matches training

## 💡 Next Steps

- [ ] Add more features (10km time, race experience)
- [ ] Collect user feedback
- [ ] A/B test different models
- [ ] Add historical race results comparison
- [ ] Create mobile-responsive design improvements

## 📞 Need Help?

- Check full README.md for detailed documentation
- Review Langfuse logs for LLM issues
- Check Digital Ocean support for infrastructure issues
- Open GitHub issue for bugs

---

**Enjoy your Half Marathon Predictor! 🏃‍♂️💨**