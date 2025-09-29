# ❓ FAQ - Często Zadawane Pytania

## 📚 Spis Treści

1. [Ogólne](#ogólne)
2. [Instalacja i Setup](#instalacja-i-setup)
3. [Trenowanie Modelu](#trenowanie-modelu)
4. [Aplikacja](#aplikacja)
5. [Deployment](#deployment)
6. [Koszty](#koszty)
7. [Performance](#performance)

---

## Ogólne

### Q: Czym jest Half Marathon Predictor?

**A:** To aplikacja ML, która przewiduje czas ukończenia półmaratonu (21.1km) na podstawie płci, wieku i czasu na 5km. Używa modelu XGBoost trenowanego na rzeczywistych danych z zawodów.

### Q: Jak dokładne są predykcje?

**A:** Model ma średni błąd ~4-5 minut (MAE) i R² score ~0.92. Dla większości biegaczy predykcja jest w zakresie ±5-7 minut.

### Q: Czy mogę używać aplikacji bez kluczy API?

**A:** Nie dla pełnej funkcjonalności. Potrzebujesz:
- **Digital Ocean Spaces**: przechowywanie modelu i danych
- **OpenAI API**: ekstrakcja danych z tekstu naturalnego
- **Langfuse** (opcjonalnie): monitoring

Możesz jednak uruchomić lokalnie z fallback heurystycznym (bez ML modelu).

---

## Instalacja i Setup

### Q: Jakie są wymagania systemowe?

**A:**
- Python 3.10 lub nowszy
- 2GB RAM (4GB zalecane)
- 1GB miejsca na dysku
- Połączenie internetowe

### Q: Nie mogę zainstalować XGBoost

**A:** Typowe problemy:

```bash
# Problem: Brak kompilatora C++
# Rozwiązanie macOS:
xcode-select --install

# Rozwiązanie Ubuntu/Debian:
sudo apt-get install build-essential

# Rozwiązanie Windows:
# Zainstaluj Visual Studio Build Tools
```

Alternatywnie, użyj binarnej wersji:
```bash
pip install xgboost --only-binary :all:
```

### Q: `ModuleNotFoundError: No module named 'dotenv'`

**A:**
```bash
pip install python-dotenv
# lub
pip install -r requirements.txt
```

### Q: Jak skonfigurować AWS CLI dla Spaces?

**A:**
```bash
# Zainstaluj
pip install awscli

# Skonfiguruj profil
aws configure --profile digitalocean

# Podaj:
AWS Access Key ID: [Twój DO_SPACES_KEY]
AWS Secret Access Key: [Twój DO_SPACES_SECRET]
Default region name: fra1
Default output format: json

# Test
aws s3 ls --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

---

## Trenowanie Modelu

### Q: Jak długo trwa trenowanie modelu?

**A:**
- Z hiperparameter tuning: 5-10 minut
- Bez tuningu: 2-3 minuty
- Zależy od CPU (zalecane: 4+ cores)

### Q: `FileNotFoundError` podczas ładowania danych

**A:** Sprawdź:
1. Czy pliki CSV są w Digital Ocean Spaces (`data/`)
2. Czy klucze DO Spaces są poprawne w `.env`
3. Czy bucket name jest poprawny

```bash
# Debug:
aws s3 ls s3://halfmarathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

### Q: Model ma słabą wydajność (MAE > 10 min)

**A:** Możliwe przyczyny:
1. **Za mało danych**: Potrzebujesz min. 5000+ rekordów
2. **Outlier nie usunięte**: Sprawdź czas > 4h lub < 1h
3. **Słabe features**: Dodaj więcej (tempo, korekty wieku)
4. **Hiperparametry**: Uruchom GridSearchCV ponownie

```python
# Sprawdź rozkład danych:
df['Czas_seconds'].describe()
df['Czas_seconds'].hist(bins=50)
```

### Q: Jak dodać własne dane treningowe?

**A:**
1. Przygotuj CSV z kolumnami:
   - `Płeć` (M/K)
   - `Rocznik` (rok urodzenia)
   - `5 km Czas` (HH:MM:SS)
   - `Czas` (czas półmaratonu, HH:MM:SS)

2. Upload do Spaces:
```bash
aws s3 cp moje_dane.csv s3://halfmarathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

3. Zmodyfikuj notebook:
```python
df_custom = load_csv_from_spaces('moje_dane.csv')
df = pd.concat([df_2023, df_2024, df_custom])
```

---

## Aplikacja

### Q: Aplikacja nie startuje lokalnie

**A:** Sprawdź logi:

```bash
streamlit run app.py 2>&1 | tee app.log
```

Typowe błędy:
- `OPENAI_API_KEY not found`: Brak klucza w `.env`
- `Port 8501 already in use`: Zabij proces lub zmień port
- `Module not found`: Reinstaluj requirements

### Q: LLM nie wydobywa danych poprawnie

**A:** Przykłady problematycznych inputów:

```python
# ❌ Za mało informacji
"Jestem biegaczem"

# ✅ Poprawny format
"M 30 lat, 5km 24:30"
"Mężczyzna 30 lat, czas na 5 km to 24 minuty 30 sekund"
```

LLM próbuje wydobyć:
1. Płeć (male/female)
2. Wiek (15-90)
3. Czas 5km w sekundach

### Q: Predykcje są nierealistyczne

**A:** Sprawdź tryb predykcji:

```python
# W wyniku:
"details": {
    "mode": "ml"  # ✅ Używa XGBoost
    # lub
    "mode": "fallback"  # ⚠️ Używa heurystyki
}
```

Jeśli `fallback`, to model nie załadował się. Sprawdź:
1. Czy model jest w Spaces
2. Czy klucze DO są poprawne
3. Czy `model_cache/` istnieje

### Q: Jak zmienić język interfejsu?

**A:** Edytuj `app.py`:

```python
# Polskie teksty:
st.header("📝 Powiedz nam o sobie")

# Angielskie:
st.header("📝 Tell us about yourself")
```

Lub dodaj st.selectbox dla wyboru języka.

---

## Deployment

### Q: Build fails w Digital Ocean

**A:** Typowe przyczyny:

1. **Dockerfile syntax error**:
```bash
# Test lokalnie:
docker build -t test .
```

2. **requirements.txt missing**:
```bash
git ls-files | grep requirements.txt
```

3. **Port configuration**:
```dockerfile
# W Dockerfile MUSI być:
EXPOSE 8080
# W app.yaml MUSI być:
http_port: 8080
```

### Q: Health check fails

**A:** Sprawdź:
```bash
# Lokalnie:
curl http://localhost:8501/_stcore/health

# Production:
curl https://your-app.ondigitalocean.app/_stcore/health
```

Jeśli nie działa, w `.streamlit/config.toml`:
```toml
[server]
headless = true
enableCORS = false
```

### Q: Environment variables nie działają

**A:** W Digital Ocean App Platform:

1. Kliknij **Settings** → **Environment Variables**
2. Sprawdź czy są w **scope: RUN_TIME** (nie BUILD_TIME)
3. Sprawdź typ: **SECRET** dla kluczy API
4. Po zmianie: **Actions** → **Force Rebuild and Deploy**

### Q: Aplikacja jest wolna po deployment

**A:** Typowe optymalizacje:

1. **Cache model**:
```python
@st.cache_resource
def load_model():
    return HalfMarathonPredictor()
```

2. **Zwiększ instance size**:
```yaml
# app.yaml
instance_size_slug: basic-xs  # było: basic-xxs
```

3. **Użyj CDN** dla statycznych plików

### Q: Jak dodać custom domain?

**A:**
1. W Digital Ocean App: **Settings** → **Domains**
2. Kliknij **Add Domain**
3. Wprowadź: `halfmarathon.twojadomena.pl`
4. Dodaj rekord CNAME u swojego providera DNS:
   ```
   halfmarathon.twojadomena.pl CNAME your-app.ondigitalocean.app
   ```
5. Poczekaj 5-10 minut na propagację DNS

---

## Koszty

### Q: Ile kosztuje uruchomienie aplikacji?

**A:** Miesięczne koszty (USD):

| Usługa | Plan | Koszt |
|--------|------|-------|
| DO App Platform | Basic (512MB) | $5 |
| DO Spaces | 250GB | $5 |
| OpenAI API | ~1000 calls | $0.50 |
| Langfuse | Free tier | $0 |
| **RAZEM** | | **~$10.50/mies** |

### Q: Jak zmniejszyć koszty OpenAI?

**A:** Optymalizacje:

1. **Użyj REGEX first** (już zaimplementowane):
```python
# REGEX łapie ~70% przypadków BEZ kosztów API
quick = _preparse_quick(text)
if all(quick.values()):
    return quick  # Nie wywołuj LLM!
```

2. **Cache odpowiedzi**:
```python
@lru_cache(maxsize=1000)
def extract_cached(text):
    return extract_user_data(text)
```

3. **Zmniejsz max_tokens**:
```python
# Było: max_tokens=200
# Zmień na: max_tokens=100
```

4. **Użyj tańszego modelu**:
```python
# gpt-4o-mini: $0.150/1M tokens (input)
# gpt-3.5-turbo: $0.50/1M tokens
```

### Q: Czy mogę uruchomić za darmo?

**A:** Opcje free tier:

1. **Local only**: Tak, lokalnie jest za darmo
2. **Fly.io**: Free tier (256MB RAM)
3. **Hugging Face Spaces**: Free tier (Streamlit)
4. **Render.com**: Free tier (512MB RAM)

⚠️ Ograniczenia free tier:
- Wolniejsza wydajność
- Auto-sleep po 15 min nieaktywności
- Ograniczony bandwidth

---

## Performance

### Q: Ile czasu trwa predykcja?

**A:** Typowe czasy:

- **REGEX extraction**: 10-50ms
- **LLM extraction**: 500-1500ms
- **ML prediction**: 50-200ms
- **Total**: 100ms - 2s

### Q: Jak przyspieszyć ekstrakcję danych?

**A:**
1. Większość przypadków łapie REGEX (szybko)
2. LLM tylko dla skomplikowanych inputów
3. Cache dla powtarzających się zapytań

```python
# Już zaimplementowane:
quick = _preparse_quick(text)  # Fast!
if all(quick.values()):
    return quick  # Skip LLM
```

### Q: Jak zwiększyć dokładność modelu?

**A:** Możliwości:

1. **Więcej danych**:
```python
# Dodaj więcej zawodów/lat
df = pd.concat([df_2023, df_2024, df_2025, ...])
```

2. **Lepsze features**:
```python
# Dodaj:
- 'czas_10km'
- 'doświadczenie_w_zawodach'
- 'czas_treningu_tygodniowo'
- 'BMI'
```

3. **Ensemble models**:
```python
# Połącz XGBoost + RandomForest + LightGBM
predictions = (xgb_pred + rf_pred + lgb_pred) / 3
```

4. **Feature engineering**:
```python
# Relacje między features:
df['pace_5km'] = df['time_5km'] / 5
df['age_pace_interaction'] = df['age'] * df['pace_5km']
```

### Q: Monitoring - jakie metryki śledzić?

**A:** Kluczowe metryki:

**Langfuse (LLM)**:
- Success rate ekstrakcji (target: >95%)
- Średni cost per call (target: <$0.001)
- Latency (target: <2s)

**Digital Ocean (App)**:
- CPU usage (target: <70%)
- Memory usage (target: <400MB)
- Response time (target: <3s)
- Error rate (target: <1%)

**Model (Business)**:
- MAE (target: <5 min)
- User satisfaction
- Daily active users

---

## Zaawansowane

### Q: Jak dodać A/B testing modeli?

**A:**
```python
import random

def predict_with_ab_test(data):
    if random.random() < 0.5:
        # Model A (XGBoost)
        return xgb_predictor.predict(data)
    else:
        # Model B (RandomForest)
        return rf_predictor.predict(data)
```

Loguj wyniki do Langfuse i analizuj.

### Q: Jak dodać więcej języków?

**A:**
```python
# app.py
language = st.selectbox("Language", ["Polski", "English"])

if language == "Polski":
    TEXTS = {
        "title": "Predyktor Czasu Półmaratonu",
        "input_label": "Opisz siebie:",
        # ...
    }
else:
    TEXTS = {
        "title": "Half Marathon Time Predictor",
        "input_label": "Tell us about yourself:",
        # ...
    }

st.title(TEXTS["title"])
```

### Q: Jak zapisywać historię predykcji użytkowników?

**A:**
```python
# W app.py
if 'history' not in st.session_state:
    st.session_state.history = []

# Po predykcji:
st.session_state.history.append({
    'timestamp': datetime.now(),
    'input': user_input,
    'prediction': result,
    'user_id': st.session_state.get('user_id')
})

# Sidebar:
with st.sidebar:
    st.header("📜 Historia")
    for item in st.session_state.history[-5:]:
        st.write(f"{item['timestamp']}: {item['prediction']['formatted_time']}")
```

### Q: Jak dodać eksport predykcji do PDF?

**A:**
```python
from fpdf import FPDF

def export_to_pdf(result, user_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Half Marathon Prediction", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Predicted Time: {result['formatted_time']}", ln=2)
    pdf.cell(200, 10, txt=f"Age: {user_data['age']}", ln=3)
    # ...
    
    return pdf.output(dest='S').encode('latin-1')

# W Streamlit:
if st.button("Export to PDF"):
    pdf_bytes = export_to_pdf(result, extracted_data)
    st.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name="prediction.pdf",
        mime="application/pdf"
    )
```

### Q: Jak dodać autentykację użytkowników?

**A:**
```python
import streamlit_authenticator as stauth

# config.yaml
credentials:
  usernames:
    jsmith:
      email: jsmith@example.com
      name: John Smith
      password: hashed_password

authenticator = stauth.Authenticate(
    credentials,
    'some_cookie_name',
    'some_signature_key',
    cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status:
    st.write(f'Welcome *{name}*')
    # Pokaż aplikację
elif authentication_status == False:
    st.error('Username/password is incorrect')
```

### Q: Jak dodać rate limiting?

**A:**
```python
from datetime import datetime, timedelta
import streamlit as st

def check_rate_limit(user_id, max_calls=10, window_minutes=60):
    if 'rate_limit' not in st.session_state:
        st.session_state.rate_limit = {}
    
    now = datetime.now()
    user_calls = st.session_state.rate_limit.get(user_id, [])
    
    # Usuń stare wywołania
    user_calls = [t for t in user_calls if now - t < timedelta(minutes=window_minutes)]
    
    if len(user_calls) >= max_calls:
        return False, f"Rate limit exceeded. Try again in {window_minutes} minutes."
    
    user_calls.append(now)
    st.session_state.rate_limit[user_id] = user_calls
    return True, None

# Użycie:
allowed, error_msg = check_rate_limit(user_id)
if not allowed:
    st.error(error_msg)
    st.stop()
```

---

## Troubleshooting Szybkie Rozwiązania

### Problem: "ModuleNotFoundError: No module named 'X'"
```bash
# Rozwiązanie:
pip install -r requirements.txt
# Lub konkretnie:
pip install X
```

### Problem: "Permission denied" podczas instalacji
```bash
# Rozwiązanie:
pip install --user -r requirements.txt
# Lub użyj venv:
python -m venv .venv
source .venv/bin/activate
```

### Problem: Streamlit nie otwiera przeglądarki
```bash
# Rozwiązanie:
streamlit run app.py --server.headless=false
# Lub ręcznie otwórz: http://localhost:8501
```

### Problem: "Address already in use"
```bash
# Znajdź proces:
lsof -i :8501
# Zabij proces:
kill -9 PID
# Lub użyj innego portu:
streamlit run app.py --server.port=8502
```

### Problem: Model predictions są None
```python
# Debug:
print(f"Model loaded: {predictor.model is not None}")
print(f"Model type: {type(predictor.model)}")
print(f"Model metadata: {predictor.model_metadata}")

# Sprawdź features:
print(f"Features expected: {predictor.feature_order}")
```

### Problem: LLM extraction zwraca puste wartości
```python
# Debug:
extracted = extract_user_data_auto(user_input)
print(f"REGEX result: {_preparse_quick(user_input)}")
print(f"LLM result: {extract_user_data(user_input)}")
print(f"Final result: {extracted}")
```

### Problem: Digital Ocean deployment timeout
```yaml
# app.yaml - zwiększ timeout:
health_check:
  initial_delay_seconds: 120  # było: 60
  timeout_seconds: 10  # było: 5
```

### Problem: Out of memory w Docker
```dockerfile
# Dockerfile - zmniejsz workers:
CMD streamlit run app.py \
    --server.maxUploadSize=10 \
    --server.maxMessageSize=10
```

---

## 🆘 Gdzie Szukać Pomocy

1. **GitHub Issues**: https://github.com/TWOJA_NAZWA/halfmarathon-predictor/issues
2. **Digital Ocean Docs**: https://docs.digitalocean.com
3. **Streamlit Forum**: https://discuss.streamlit.io
4. **OpenAI Community**: https://community.openai.com
5. **Stack Overflow**: Taguj z `streamlit`, `xgboost`, `digital-ocean`

---

## 📚 Przydatne Linki

- **Streamlit Docs**: https://docs.streamlit.io
- **XGBoost Docs**: https://xgboost.readthedocs.io
- **OpenAI API Docs**: https://platform.openai.com/docs
- **Langfuse Docs**: https://langfuse.com/docs
- **Digital Ocean Tutorials**: https://www.digitalocean.com/community/tutorials
- **Boto3 Docs (Spaces)**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

---

**Pytania? Otwórz issue na GitHub! 🚀**