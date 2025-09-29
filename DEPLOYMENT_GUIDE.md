# 🚀 Kompletna Instrukcja Deployment

## Krok 1: Przygotowanie Danych (5 min)

### 1.1. Utwórz Space w Digital Ocean

1. Zaloguj się do [Digital Ocean](https://cloud.digitalocean.com)
2. Przejdź do **Spaces** → **Create Space**
3. Wybierz:
   - **Region**: Frankfurt (`fra1`)
   - **Name**: `halfmarathon-ml`
   - **Restrict File Listing**: ✅ Włącz (Private)
4. Kliknij **Create Space**

### 1.2. Wygeneruj API Keys

1. W Spaces, kliknij **Settings** → **Spaces Keys**
2. Kliknij **Generate New Key**
3. Zapisz:
   - **Access Key** (np. `DO1234567...`)
   - **Secret Key** (np. `abc123xyz...`)

⚠️ **WAŻNE**: Secret Key wyświetla się tylko raz!

### 1.3. Upload Danych CSV

**Opcja A: Przez interfejs web**
1. W swoim Space `halfmarathon-ml`
2. Utwórz folder `data`
3. Upload:
   - `halfmarathon_wroclaw_2023__final.csv`
   - `halfmarathon_wroclaw_2024__final.csv`

**Opcja B: Przez AWS CLI**
```bash
# Zainstaluj AWS CLI
pip install awscli

# Skonfiguruj profil
aws configure --profile digitalocean
# Podaj Access Key, Secret Key, region: fra1

# Upload plików
aws s3 cp halfmarathon_wroclaw_2023__final.csv \
  s3://halfmarathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean

aws s3 cp halfmarathon_wroclaw_2024__final.csv \
  s3://halfmarathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

---

## Krok 2: Skonfiguruj OpenAI (2 min)

1. Przejdź do [OpenAI Platform](https://platform.openai.com/api-keys)
2. Kliknij **Create new secret key**
3. Nazwij klucz: `Half Marathon App`
4. Zapisz klucz (zaczyna się od `sk-...`)
5. Upewnij się, że masz kredyty ($5+)

---

## Krok 3: Skonfiguruj Langfuse (3 min) - OPCJONALNE

1. Zarejestruj się na [Langfuse Cloud](https://cloud.langfuse.com)
2. Utwórz nowy projekt: **Half Marathon Predictor**
3. Przejdź do **Settings** → **API Keys**
4. Zapisz:
   - **Public Key** (zaczyna się od `pk-lf-...`)
   - **Secret Key** (zaczyna się od `sk-lf-...`)

---

## Krok 4: Trenowanie Modelu (10 min)

### 4.1. Przygotuj środowisko lokalne

```bash
# Sklonuj repo
git clone https://github.com/TWOJA_NAZWA/halfmarathon-predictor.git
cd halfmarathon-predictor

# Utwórz virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Zainstaluj zależności
pip install -r requirements.txt
```

### 4.2. Skonfiguruj .env

```bash
# Skopiuj template
cp .env.example .env

# Edytuj .env i uzupełnij:
nano .env
```

Twój `.env` powinien wyglądać tak:

```bash
# Digital Ocean Spaces
DO_SPACES_KEY=DO1234567...
DO_SPACES_SECRET=abc123xyz...
DO_SPACES_REGION=fra1
DO_SPACES_BUCKET=halfmarathon-ml

# OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini

# Langfuse (opcjonalne)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 4.3. Uruchom notebook treningowy

```bash
# Zainstaluj Jupyter
pip install jupyter

# Uruchom notebook
cd notebooks
jupyter notebook training_pipeline.ipynb
```

W Jupyter:
1. Kliknij **Cell** → **Run All**
2. Poczekaj ~5-10 minut na trenowanie
3. Model automatycznie uploaduje się do Digital Ocean Spaces

**Oczekiwane metryki:**
- MAE: ~4-5 minut
- RMSE: ~6-7 minut
- R² Score: ~0.90-0.92

---

## Krok 5: Test Lokalny (3 min)

```bash
# Wróć do głównego katalogu
cd ..

# Uruchom aplikację
streamlit run app.py
```

Otwórz http://localhost:8501 i przetestuj z:
```
M 30 lat, 5km 24:30
```

Powinno pokazać predykcję ~1:45:00 - 1:50:00

---

## Krok 6: Deployment na Digital Ocean (15 min)

### 6.1. Przygotuj repozytorium GitHub

```bash
# Zainicjuj git (jeśli jeszcze nie)
git init
git add .
git commit -m "Initial commit - Half Marathon Predictor"

# Utwórz repo na GitHub
# Przejdź do https://github.com/new
# Nazwij: halfmarathon-predictor

# Dodaj remote i wypchnij
git remote add origin https://github.com/TWOJA_NAZWA/halfmarathon-predictor.git
git branch -M main
git push -u origin main
```

### 6.2. Edytuj app.yaml

Otwórz `app.yaml` i zmień:
```yaml
github:
  repo: TWOJA_NAZWA_UŻYTKOWNIKA/halfmarathon-predictor  # ← TUTAJ!
```

Commit i push:
```bash
git add app.yaml
git commit -m "Update repo name in app.yaml"
git push
```

### 6.3. Utwórz aplikację w Digital Ocean

**Opcja A: Przez interfejs web** (łatwiejsze)

1. Przejdź do [Digital Ocean Apps](https://cloud.digitalocean.com/apps)
2. Kliknij **Create App**
3. **Source**: Wybierz **GitHub**
4. Autoryzuj GitHub i wybierz repo `halfmarathon-predictor`
5. **Branch**: `main`
6. Kliknij **Next**

7. **Resources**:
   - Detect: Dockerfile ✅
   - HTTP Port: `8080`
   - Health Check: `/_stcore/health`
   
8. **Environment Variables** (kliknij **Edit** przy web service):

   Dodaj te zmienne (zaznacz **Encrypt** dla sekretów):

   | Key | Value | Encrypted? |
   |-----|-------|------------|
   | DO_SPACES_KEY | `DO1234567...` | ✅ |
   | DO_SPACES_SECRET | `abc123xyz...` | ✅ |
   | DO_SPACES_REGION | `fra1` | ❌ |
   | DO_SPACES_BUCKET | `halfmarathon-ml` | ❌ |
   | OPENAI_API_KEY | `sk-proj-...` | ✅ |
   | OPENAI_MODEL | `gpt-4o-mini` | ❌ |
   | LANGFUSE_SECRET_KEY | `sk-lf-...` | ✅ |
   | LANGFUSE_PUBLIC_KEY | `pk-lf-...` | ✅ |
   | LANGFUSE_HOST | `https://cloud.langfuse.com` | ❌ |

9. **Info**:
   - Name: `halfmarathon-predictor`
   - Region: Frankfurt

10. Kliknij **Next** → **Create Resources**

**Opcja B: Przez CLI** (dla zaawansowanych)

```bash
# Zainstaluj doctl
brew install doctl  # macOS
# lub pobierz z: https://docs.digitalocean.com/reference/doctl/

# Autoryzuj
doctl auth init

# Utwórz app
doctl apps create --spec app.yaml

# Ustaw environment variables
doctl apps update YOUR_APP_ID --spec app.yaml
```

### 6.4. Monitoruj deployment

1. W Digital Ocean Apps, otwórz swoją aplikację
2. Przejdź do zakładki **Deployments**
3. Poczekaj ~10-15 minut na pierwszy deploy
4. Status zmieni się na **Active** ✅

---

## Krok 7: Testowanie Produkcji (2 min)

1. W Apps, kliknij **Live App** albo otwórz URL
2. URL będzie wyglądał: `https://halfmarathon-predictor-xxxxx.ondigitalocean.app`
3. Przetestuj aplikację z różnymi danymi:

```
Przykłady testowe:

1. M 30 lat, 5km 24:30
   → Oczekiwane: ~1:45:00

2. Kobieta 28 lat, 5k w 27 minut
   → Oczekiwane: ~2:00:00

3. Mężczyzna 45 lat, 5km 22:30
   → Oczekiwane: ~1:40:00
```

---

## Krok 8: Monitorowanie (ciągłe)

### 8.1. Digital Ocean Logs

```bash
# Pobierz ID aplikacji
doctl apps list

# Zobacz logi live
doctl apps logs YOUR_APP_ID --follow
```

Lub w interfejsie: **Apps** → Twoja app → **Runtime Logs**

### 8.2. Langfuse Dashboard

1. Przejdź do [Langfuse](https://cloud.langfuse.com)
2. Otwórz projekt **Half Marathon Predictor**
3. Zobacz:
   - **Traces**: Wszystkie wywołania LLM
   - **Metrics**: Sukces ekstrakcji, użycie tokenów
   - **Costs**: Koszty API OpenAI

---

## 🎯 Checklist Finalny

- [ ] Space utworzony i dane CSV uploadowane
- [ ] OpenAI API key działa (sprawdź kredyty)
- [ ] Langfuse skonfigurowany (opcjonalne)
- [ ] Model wytrenowany i uploadowany do Spaces
- [ ] Aplikacja działa lokalnie
- [ ] GitHub repo utworzone i kod wypchnięty
- [ ] Digital Ocean App utworzona
- [ ] Environment variables ustawione
- [ ] Deployment zakończony (status: Active)
- [ ] Aplikacja testowana w produkcji
- [ ] Logi sprawdzone (brak błędów)

---

## 🐛 Troubleshooting

### Problem: Model nie ładuje się

**Objawy**: Aplikacja używa fallback heurystyczny

**Rozwiązanie**:
```bash
# Sprawdź czy model jest w Spaces
aws s3 ls s3://halfmarathon-ml/models/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean

# Powinno pokazać: halfmarathon_model_latest.pkl
```

Jeśli brak pliku:
- Uruchom ponownie notebook treningowy
- Sprawdź logi notebooka czy upload się powiódł

### Problem: OpenAI API error

**Objawy**: `Error: OpenAI API key not found`

**Rozwiązanie**:
1. Sprawdź czy klucz jest w environment variables
2. Upewnij się, że klucz zaczyna się od `sk-proj-` lub `sk-`
3. Sprawdź kredyty na https://platform.openai.com/usage

### Problem: Aplikacja nie startuje

**Objawy**: Build failed lub Health check failed

**Rozwiązanie**:
```bash
# Sprawdź logi
doctl apps logs YOUR_APP_ID --type BUILD

# Typowe problemy:
# 1. Błąd w Dockerfile - sprawdź syntax
# 2. Brak requirements.txt - upewnij się że jest w repo
# 3. Port 8080 nie odpowiada - sprawdź Streamlit config
```

### Problem: Ekstrakator nie działa

**Objawy**: "Nie udało się automatycznie wyodrębnić danych"

**Rozwiązanie**:
- Sprawdź format inputu użytkownika
- Zobacz logi Langfuse - czy LLM odpowiada poprawnie
- Przetestuj z prostszym inputem: `M 30 lat, 5km 24:30`

---

## 📊 Koszty Miesięczne (Szacunkowe)

| Usługa | Koszt |
|--------|-------|
| Digital Ocean App (Basic) | $5/mies |
| Digital Ocean Spaces (250GB) | $5/mies |
| OpenAI API (~1000 wywołań) | $0.50/mies |
| Langfuse (Free tier) | $0 |
| **RAZEM** | **~$10.50/mies** |

---

## 🚀 Następne Kroki (Opcjonalne)

1. **Custom Domain**: 
   - Kup domenę (np. `halfmarathon.pl`)
   - W Digital Ocean Apps: Settings → Domains

2. **CI/CD**:
   - Włącz automatyczny deployment przy push do `main`
   - Dodaj testy w GitHub Actions

3. **Monitoring**:
   - Dodaj Sentry dla error tracking
   - Ustaw alerty w Digital Ocean

4. **Ulepszenia modelu**:
   - Dodaj więcej features (czas 10km, doświadczenie)
   - A/B testing różnych modeli
   - Regularny retraining z nowymi danymi

---

## 📞 Wsparcie

- **Digital Ocean Docs**: https://docs.digitalocean.com/products/app-platform/
- **Streamlit Docs**: https://docs.streamlit.io
- **Langfuse Docs**: https://langfuse.com/docs
- **OpenAI API Docs**: https://platform.openai.com/docs

---

**Powodzenia! 🎉🏃**