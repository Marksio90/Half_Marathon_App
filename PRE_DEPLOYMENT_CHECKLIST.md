# ✅ Pre-Deployment Checklist

Sprawdź wszystkie punkty przed deployment na Digital Ocean!

## 📋 1. Digital Ocean Spaces

- [ ] Space `halfmarathon-ml` utworzony w regionie `fra1`
- [ ] API Keys wygenerowane (Access Key + Secret Key)
- [ ] Folder `data/` utworzony w Space
- [ ] Plik `halfmarathon_wroclaw_2023__final.csv` uploadowany
- [ ] Plik `halfmarathon_wroclaw_2024__final.csv` uploadowany
- [ ] Pliki CSV mają poprawny separator (`;`)
- [ ] Space ustawiony jako **Private**

**Test:**
```bash
aws s3 ls s3://halfmarathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

---

## 🤖 2. OpenAI API

- [ ] Konto OpenAI założone
- [ ] API Key wygenerowany (zaczyna się od `sk-proj-` lub `sk-`)
- [ ] Kredyty dodane ($5+ zalecane)
- [ ] Dostęp do modelu `gpt-4o-mini` potwierdzony
- [ ] Rate limits sprawdzone (Tier 1: 500 RPM)

**Test:**
```bash
curl https://api.openai.com/v1/models/gpt-4o-mini \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## 📊 3. Langfuse (Opcjonalne)

- [ ] Konto Langfuse utworzone
- [ ] Projekt "Half Marathon Predictor" utworzony
- [ ] Public Key skopiowany (pk-lf-...)
- [ ] Secret Key skopiowany (sk-lf-...)
- [ ] Dashboard Langfuse otwarty i działający

**Test:**
```python
from langfuse import Langfuse
langfuse = Langfuse()
trace = langfuse.trace(name="test")
print(f"Trace ID: {trace.id}")
```

---

## 🎓 4. Model ML

- [ ] Notebook `training_pipeline.ipynb` uruchomiony
- [ ] Trenowanie zakończone bez błędów
- [ ] Metryki modelu akceptowalne (MAE < 6 min, R² > 0.90)
- [ ] Model zapisany lokalnie
- [ ] Model uploadowany do Spaces: `models/halfmarathon_model_latest.pkl`
- [ ] Metadata uploadowane: `models/model_metadata_latest.pkl`
- [ ] Gender encoder uploadowany: `models/gender_encoder.pkl`

**Test:**
```bash
# Sprawdź czy model jest w Spaces
aws s3 ls s3://halfmarathon-ml/models/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean

# Powinno pokazać:
# halfmarathon_model_latest.pkl
# model_metadata_latest.pkl
# gender_encoder.pkl
```

---

## 🔧 5. Konfiguracja Lokalna

- [ ] Python 3.10+ zainstalowany
- [ ] Virtual environment utworzony (`.venv`)
- [ ] Wszystkie zależności zainstalowane (`pip install -r requirements.txt`)
- [ ] Plik `.env` utworzony z wszystkimi kluczami
- [ ] `.env` dodany do `.gitignore` (nie commituj kluczy!)

**Test:**
```bash
python test_pipeline.py
# Wszystkie testy powinny przejść ✅
```

---

## 🧪 6. Test Lokalny Aplikacji

- [ ] Aplikacja startuje bez błędów: `streamlit run app.py`
- [ ] Interfejs otwiera się na `http://localhost:8501`
- [ ] Test input 1: `M 30 lat, 5km 24:30` → działa
- [ ] Test input 2: `Kobieta 28 lat, 5k 27 minut` → działa
- [ ] Test input 3: `Male 45 yo, 5km 22:30` → działa
- [ ] Predykcje są sensowne (1:30 - 2:30 dla typowych przypadków)
- [ ] UI wygląda poprawnie (brak błędów CSS)
- [ ] Health check działa: `http://localhost:8501/_stcore/health`

---

## 🐳 7. Test Docker (Opcjonalny)

- [ ] Docker zainstalowany
- [ ] Build image: `docker build -t halfmarathon-test .`
- [ ] Build zakończony bez błędów
- [ ] Container startuje: `docker run -p 8080:8080 --env-file .env halfmarathon-test`
- [ ] App dostępny na `http://localhost:8080`
- [ ] Health check w Docker: `curl http://localhost:8080/_stcore/health`

---

## 📦 8. GitHub Repository

- [ ] Repozytorium utworzone na GitHub
- [ ] Nazwa repo: `halfmarathon-predictor` (lub inna)
- [ ] `.gitignore` poprawnie skonfigurowany
- [ ] `.env` NIE jest w repo (sprawdź!)
- [ ] Wszystkie pliki commitowane
- [ ] Code pushed do branch `main`
- [ ] `app.yaml` ma poprawną nazwę repo (`TWOJA_NAZWA/halfmarathon-predictor`)

**Test:**
```bash
# Sprawdź czy .env nie jest tracked
git status | grep .env
# Powinno być puste!

# Sprawdź remote
git remote -v
```

---

## ☁️ 9. Digital Ocean App Platform

- [ ] Konto Digital Ocean aktywne
- [ ] Billing method dodany (karta kredytowa)
- [ ] GitHub połączony z Digital Ocean
- [ ] App Platform otwarty: https://cloud.digitalocean.com/apps

---

## 🔐 10. Environment Variables (Production)

Przygotuj te wartości do wpisania w Digital Ocean:

### Wymagane (SECRET):
```
DO_SPACES_KEY=DO...
DO_SPACES_SECRET=...
OPENAI_API_KEY=sk-proj-...
```

### Wymagane (zwykłe):
```
DO_SPACES_REGION=fra1
DO_SPACES_BUCKET=halfmarathon-ml
OPENAI_MODEL=gpt-4o-mini
```

### Opcjonalne (SECRET):
```
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
```

### Opcjonalne (zwykłe):
```
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 📝 11. Dokumentacja

- [ ] README.md zaktualizowany
- [ ] DEPLOYMENT_GUIDE.md przeczytany
- [ ] CONTRIBUTING.md obecny (jeśli open source)
- [ ] LICENSE obecny

---

## 🚀 12. Gotowość do Deployment

- [ ] **WSZYSTKIE** powyższe punkty zaznaczone ✅
- [ ] Backup lokalny plików `.env` (bezpieczne miejsce)
- [ ] Klusze API zapisane w password manager
- [ ] Kontakt do Digital Ocean Support znany (jeśli problemy)

---

## 🎯 Finalne Kroki Deployment

Kiedy wszystkie checklisty są ✅:

1. **Otwórz Digital Ocean**: https://cloud.digitalocean.com/apps
2. **Kliknij "Create App"**
3. **Wybierz GitHub** → autoryzuj → wybierz repo
4. **Branch**: `main`
5. **Detect Dockerfile**: Powinien wykryć automatycznie
6. **Environment Variables**: Wklej wszystkie z sekcji 10
7. **Region**: Frankfurt
8. **Instance Size**: Basic (512MB)
9. **Health Check**: `/_stcore/health`
10. **Kliknij "Create Resources"**

---

## ⏱️ Czasy Deployment

- **First deploy**: 10-15 minut
- **Subsequent deploys**: 5-8 minut
- **Cold start**: 30-60 sekund

---

## 🎉 Po Deployment

- [ ] URL aplikacji działa
- [ ] Test predykcji: `M 30 lat, 5km 24:30`
- [ ] Logi sprawdzone (brak ERROR)
- [ ] Langfuse dashboard pokazuje traces
- [ ] Dodaj URL do README.md
- [ ] Share link z kolegami/koleżankami! 🚀

---

## 📞 W Razie Problemów

1. **Sprawdź logi**: `doctl apps logs YOUR_APP_ID --follow`
2. **Sprawdź health**: `curl https://your-app.ondigitalocean.app/_stcore/health`
3. **Rebuild**: W Apps → Deployments → "Force Rebuild"
4. **Support**: https://cloud.digitalocean.com/support

---

**Powodzenia! 🏃💨**