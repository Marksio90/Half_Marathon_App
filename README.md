# 🏃 Half Marathon Time Predictor

Profesjonalna aplikacja ML do predykcji czasu półmaratonu wykorzystująca XGBoost, OpenAI GPT-4o-mini i monitoring Langfuse.

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-FF4B4B.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

![Demo](https://via.placeholder.com/800x400/667eea/ffffff?text=Half+Marathon+Predictor+Demo)

---

## ✨ Funkcjonalności

- 🤖 **Model XGBoost** - wytrenowany na 20,000+ rzeczywistych wynikach z półmaratonów
- 🧠 **Inteligentna ekstrakcja danych** - automatyczne wyłuskiwanie informacji z tekstu naturalnego (REGEX + LLM)
- 📊 **Monitoring Langfuse** - śledzenie wydajności i kosztów LLM
- ☁️ **Digital Ocean Integration** - dane i modele w Spaces
- 🚀 **Production Ready** - Docker, health checks, CI/CD
- 📱 **Responsive UI** - piękny interfejs Streamlit

---

## 🎯 Jak to działa

1. **User Input**: Użytkownik wpisuje dane w naturalnym języku
   ```
   Przykład: "M 30 lat, 5km 24:30"
   ```

2. **Ekstrakcja Danych**: 
   - Warstwa 1: Szybki REGEX (bez kosztów API)
   - Warstwa 2: OpenAI LLM dla trudnych przypadków

3. **Predykcja**:
   - Model XGBoost (jeśli dostępny)
   - Fallback heurystyczny (zawsze działa)

4. **Wynik**: Predykcja czasu półmaratonu z analizą tempa

---

## 🚀 Quick Start

### Wymagania

- Python 3.10+
- Digital Ocean Account (Spaces + App Platform)
- OpenAI API Key
- Langfuse Account (opcjonalne)

### Instalacja Lokalna

```bash
# 1. Sklonuj repo
git clone https://github.com/TWOJA_NAZWA/halfmarathon-predictor.git
cd halfmarathon-predictor

# 2. Utwórz virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Zainstaluj zależności
pip install -r requirements.txt

# 4. Skonfiguruj .env
cp .env.example .env
# Edytuj .env i uzupełnij API keys

# 5. Uruchom aplikację
streamlit run app.py
```

Otwórz http://localhost:8501

### Deployment na Digital Ocean

📖 **Pełna instrukcja**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

Krótka wersja:
1. Upload danych CSV do Digital Ocean Spaces
2. Wytrenuj model (notebook `training_pipeline.ipynb`)
3. Push kodu na GitHub
4. Utwórz App w Digital Ocean App Platform
5. Ustaw environment variables
6. Deploy! 🎉

---

## 📊 Architektura

```
┌─────────────────────┐
│   User Input        │
│  (Natural Language) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      ┌──────────────┐
│  REGEX Parser       │      │              │
│  (Fast, Local)      │──────▶  Langfuse    │
└──────────┬──────────┘      │  Monitoring  │
           │                 │              │
           ▼                 └──────────────┘
┌─────────────────────┐
│  OpenAI GPT-4o-mini │
│  (Fallback for gaps)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      ┌──────────────┐
│  XGBoost Model      │◀─────│ DO Spaces    │
│  Prediction         │      │ Model Store  │
└──────────┬──────────┘      └──────────────┘
           │
           ▼
┌─────────────────────┐
│  Streamlit UI       │
│  (Beautiful Results)│
└─────────────────────┘
```

---

## 📁 Struktura Projektu

```
halfmarathon-predictor/
├── app.py                      # Główna aplikacja Streamlit
├── Dockerfile                  # Konfiguracja Docker
├── requirements.txt            # Zależności Python
├── app.yaml                    # Digital Ocean App spec
│
├── .streamlit/
│   └── config.toml            # Konfiguracja Streamlit
│
├── notebooks/
│   └── training_pipeline.ipynb # Pipeline trenowania modelu
│
├── utils/
│   ├── __init__.py
│   ├── data_loader.py         # Ładowanie danych z Spaces
│   ├── llm_extractor.py       # Ekstrakcja danych (REGEX + LLM)
│   ├── model_predictor.py     # Predykcja modelem ML
│   └── langfuse_shim.py       # Langfuse fallback wrapper
│
├── model_cache/               # Cache dla pobranych modeli
└── tests/
    └── test_app.py            # Unit testy
```

---

## 🎓 Trenowanie Modelu

### Dataset

Model trenowany na danych z Wrocław Half Marathon 2023-2024:
- **20,000+** wyników zawodów
- Features: płeć, wiek, czas 5km, tempo 5km
- Target: czas półmaratonu w sekundach

### Metryki Modelu

| Metryka | Wartość |
|---------|---------|
| MAE | ~4.5 minuty |
| RMSE | ~6.2 minuty |
| R² Score | 0.92 |

### Pipeline Treningowy

```bash
# Uruchom notebook
cd notebooks
jupyter notebook training_pipeline.ipynb

# Wykonaj wszystkie komórki (Cell → Run All)
# Model automatycznie uploaduje się do Spaces
```

Pipeline automatycznie:
1. ✅ Ładuje dane z Digital Ocean Spaces
2. ✅ Czyści dane (outliers, missing values)
3. ✅ Inżynieria cech (tempo, korekty wieku/płci)
4. ✅ Trenuje XGBoost z hyperparameter tuning
5. ✅ Waliduje model (cross-validation)
6. ✅ Zapisuje lokalnie i uploaduje do Spaces

---

## 🔧 Konfiguracja

### Environment Variables

Utwórz plik `.env`:

```bash
# Digital Ocean Spaces
DO_SPACES_KEY=your_access_key
DO_SPACES_SECRET=your_secret_key
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

---

## 📖 Użycie

### Przykładowe Inputy

Aplikacja akceptuje naturalny język (PL/EN):

```
✅ "M 30 lat, 5km 24:30"
✅ "Mężczyzna 32 lata, czas na 5 km to 23:45"
✅ "Kobieta 28 lat, 5k w 27 minut"
✅ "Male, 45 years old, 5k time 22:30"
✅ "Female runner, age 35, 5km: 25:15"
```

### API Usage (Programmatic)

```python
from utils.model_predictor import HalfMarathonPredictor

predictor = HalfMarathonPredictor()

result = predictor.predict({
    'gender': 'male',
    'age': 30,
    'time_5km_seconds': 1470  # 24:30
})

print(f"Predicted time: {result['formatted_time']}")
# Output: Predicted time: 1:45:23
```

---

## 🧪 Testowanie

```bash
# Uruchom wszystkie testy
python test_app.py

# Testy z coverage
pytest test_app.py --cov=utils --cov-report=html

# Testy konkretnego modułu
python -m pytest test_app.py::TestTimeParser -v
```

---

## 📊 Monitoring

### Langfuse Dashboard

Monitoruj:
- **LLM Calls**: Ilość i sukces ekstrakcji
- **Token Usage**: Koszty OpenAI API
- **Latency**: Czas odpowiedzi
- **Error Rate**: Nieudane ekstrakcje

Dashboard: https://cloud.langfuse.com

### Digital Ocean Logs

```bash
# Real-time logs
doctl apps logs YOUR_APP_ID --follow

# Last 100 lines
doctl apps logs YOUR_APP_ID --tail 100
```

---

## 🐛 Troubleshooting

### Model nie ładuje się

```bash
# Sprawdź czy model jest w Spaces
aws s3 ls s3://halfmarathon-ml/models/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

### OpenAI API Error

- Sprawdź klucz w `.env`
- Zweryfikuj kredyty: https://platform.openai.com/usage
- Upewnij się że model `gpt-4o-mini` jest dostępny

### Aplikacja nie startuje

```bash
# Test lokalny
streamlit run app.py

# Test Docker
docker build -t halfmarathon-test .
docker run -p 8080:8080 --env-file .env halfmarathon-test
```

---

## 🚀 Roadmap

- [ ] Dodanie więcej features (czas 10km, doświadczenie)
- [ ] A/B testing różnych modeli ML
- [ ] Eksport predykcji do PDF
- [ ] Porównanie z historycznymi wynikami
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Social sharing funkcjonalności

---

## 🤝 Contributing

Contributions are welcome! Przeczytaj [CONTRIBUTING.md](./CONTRIBUTING.md)

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 🙏 Acknowledgments

- **Wrocław Half Marathon** - dane treningowe
- **OpenAI** - GPT-4o-mini API
- **Langfuse** - monitoring LLM
- **Digital Ocean** - infrastruktura cloud
- **Streamlit** - framework UI

---

**Zbudowane z ❤️ używając Python, XGBoost, Streamlit i Digital Ocean**
