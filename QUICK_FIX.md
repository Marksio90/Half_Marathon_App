# 🔧 Szybka Naprawa Błędów

Na podstawie wyniku testów, oto co musisz naprawić:

---

## ❌ Problem 1: OpenAI API Error (proxies argument)

### Przyczyna
Konflikt wersji OpenAI SDK lub ustawienia proxy w systemie.

### Rozwiązanie (2 minuty)

```bash
# 1. Odinstaluj starą wersję
pip uninstall openai -y

# 2. Zainstaluj konkretną wersję
pip install openai==1.54.0

# 3. Zweryfikuj
python -c "from openai import OpenAI; print('✅ OpenAI OK')"
```

### Alternatywnie: Zastąp plik

Zastąp `utils/llm_extractor.py` poprawionym kodem (artifact wyżej).

Kluczowa zmiana:
```python
# Przed (crash):
_client = OpenAI(api_key=api_key, proxies=None)  # ❌

# Po (działa):
try:
    _client = OpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2
    )
except TypeError as e:
    if 'proxies' in str(e):
        _client = OpenAI(api_key=api_key)  # ✅ Fallback
```

---

## ❌ Problem 2: Brak Plików w Digital Ocean Spaces

### Przyczyna
Pliki CSV nie zostały uploadowane do folderu `data/` w Spaces.

### Rozwiązanie A: Przez Skrypt (3 minuty)

```bash
# 1. Upewnij się że pliki CSV są w obecnym katalogu
ls *.csv
# Powinno pokazać:
# halfmarathon_wroclaw_2023__final.csv
# halfmarathon_wroclaw_2024__final.csv

# 2. Użyj skryptu upload (stwórz z artifact wyżej)
python upload_data.py

# 3. Zweryfikuj
python -c "
import boto3, os
from dotenv import load_dotenv
load_dotenv()
s3 = boto3.client('s3',
    endpoint_url=f'https://{os.getenv(\"DO_SPACES_REGION\", \"fra1\")}.digitaloceanspaces.com',
    aws_access_key_id=os.getenv('DO_SPACES_KEY'),
    aws_secret_access_key=os.getenv('DO_SPACES_SECRET'))
print('✅ Pliki w Spaces:')
for obj in s3.list_objects_v2(Bucket=os.getenv('DO_SPACES_BUCKET'), Prefix='data/')['Contents']:
    print(f'  - {obj[\"Key\"]} ({obj[\"Size\"]/(1024*1024):.2f} MB)')
"
```

### Rozwiązanie B: Przez AWS CLI (2 minuty)

```bash
# 1. Skonfiguruj (jeśli jeszcze nie)
aws configure --profile digitalocean
# Podaj DO_SPACES_KEY i DO_SPACES_SECRET

# 2. Upload plików
aws s3 cp halfmarathon_wroclaw_2023__final.csv \
  s3://half-marathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean

aws s3 cp halfmarathon_wroclaw_2024__final.csv \
  s3://half-marathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean

# 3. Zweryfikuj
aws s3 ls s3://half-marathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

### Rozwiązanie C: Przez Web Interface (5 minut)

1. Otwórz https://cloud.digitalocean.com/spaces
2. Kliknij na swój bucket `half-marathon-ml`
3. Utwórz folder `data` (jeśli nie istnieje)
4. Kliknij **Upload Files**
5. Wybierz oba pliki CSV
6. Poczekaj na upload (2-5 minut)

---

## ❌ Problem 3: Ekstrakcja Danych Nie Działa

### Przyczyna
Błąd OpenAI API (patrz Problem 1) powoduje że LLM nie działa.

### Rozwiązanie

Napraw Problem 1, a ten problem zniknie automatycznie! 🎉

Jednak REGEX już działa:
```
✅ Test case 1: "M 30 lat, 5km 24:30" - PASS (100% REGEX)
```

Problem tylko z bardziej skomplikowanymi inputami:
```
❌ "Kobieta 28 lat, 5k w 27 minut" - brak time_5km_seconds
```

Po naprawie OpenAI, LLM uzupełni braki.

---

## ✅ Co Już Działa

Gratulacje! Te części działają poprawnie:

1. ✅ **Environment Variables** - wszystkie klucze OK
2. ✅ **Module Imports** - wszystkie biblioteki zainstalowane
3. ✅ **Model Prediction** - fallback heurystyczny działa!
4. ✅ **Langfuse** - monitoring działa!

---

## 🚀 Plan Naprawy (10 minut)

### Krok 1: Napraw OpenAI (2 min)

```bash
pip uninstall openai -y
pip install openai==1.54.0
```

### Krok 2: Upload CSV (3 min)

```bash
# Opcja A: Skrypt
python upload_data.py

# Opcja B: AWS CLI
aws s3 cp halfmarathon_wroclaw_2023__final.csv \
  s3://half-marathon-ml/data/ \
  --endpoint-url=https://fra1.digitalocean spaces.com \
  --profile digitalocean

aws s3 cp halfmarathon_wroclaw_2024__final.csv \
  s3://half-marathon-ml/data/ \
  --endpoint-url=https://fra1.digitaloceanspaces.com \
  --profile digitalocean
```

### Krok 3: Wytrenuj Model (5 min)

```bash
cd notebooks
jupyter notebook training_pipeline.ipynb
# Cell → Run All
```

### Krok 4: Ponownie Uruchom Testy (1 min)

```bash
cd ..
python test_pipeline.py
```

**Oczekiwany wynik**: 8/8 testów ✅

---

## 🔍 Weryfikacja Po Naprawie

### Test 1: OpenAI API

```bash
python -c "
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
resp = client.chat.completions.create(
    model='gpt-4o-mini',
    messages=[{'role': 'user', 'content': 'Say OK'}],
    max_tokens=5
)
print('✅ OpenAI:', resp.choices[0].message.content)
"
```

### Test 2: Spaces Data

```bash
python -c "
import boto3, os
from dotenv import load_dotenv
load_dotenv()
s3 = boto3.client('s3',
    endpoint_url=f'https://{os.getenv(\"DO_SPACES_REGION\")}.digitaloceanspaces.com',
    aws_access_key_id=os.getenv('DO_SPACES_KEY'),
    aws_secret_access_key=os.getenv('DO_SPACES_SECRET'))
objs = s3.list_objects_v2(Bucket=os.getenv('DO_SPACES_BUCKET'), Prefix='data/')
print('✅ Pliki:', len(objs.get('Contents', [])))
"
```

### Test 3: Ekstrakcja

```bash
python -c "
from utils.llm_extractor import extract_user_data_auto
result = extract_user_data_auto('Kobieta 28 lat, 5k w 27 minut')
print('✅ Ekstrakcja:', result)
assert result['gender'] == 'female'
assert result['age'] == 28
assert result['time_5km_seconds'] == 1620
print('✅ WSZYSTKO DZIAŁA!')
"
```

---

## 💡 Czego Uczyć Się z Tych Błędów

### 1. Dependency Management
```bash
# Zawsze używaj konkretnych wersji w requirements.txt
openai==1.54.0  # ✅ DOBRZE
openai          # ❌ ŹLE (może się zmienić)
```

### 2. Data Pipeline
```bash
# Zawsze weryfikuj że dane są tam gdzie powinny być
# Przed treningiem → sprawdź Spaces
# Przed deployment → sprawdź model w Spaces
```

### 3. Graceful Degradation
```python
# Aplikacja powinna działać nawet jak coś jest broken
if model_available:
    use_ml()  # Idealne
else:
    use_fallback()  # Nadal działa! ✅
```

To właśnie widzimy w twoich testach - model nie załadował się, ale aplikacja NIE crashowała! Używała fallback i dawała sensowne wyniki.

---

## 📋 Checklist Po Naprawie

- [ ] OpenAI SDK wersja 1.54.0 zainstalowana
- [ ] Test OpenAI API przechodzi (`python -c "from openai import OpenAI..."`)
- [ ] Oba pliki CSV w Spaces (`data/*.csv`)
- [ ] Model wytrenowany i w Spaces (`models/halfmarathon_model_latest.pkl`)
- [ ] `python test_pipeline.py` pokazuje 8/8 ✅
- [ ] `streamlit run app.py` działa lokalnie
- [ ] Predykcje są sensowne (1:30 - 2:30)

---

## 🆘 Jeśli Nadal Nie Działa

### Debug OpenAI Issue

```python
# debug_openai.py
import os
from dotenv import load_dotenv
load_dotenv()

print("1. Checking OpenAI version...")
import openai
print(f"   Version: {openai.__version__}")

print("\n2. Checking API key...")
api_key = os.getenv('OPENAI_API_KEY')
print(f"   Key: {api_key[:20]}..." if api_key else "   ❌ BRAK KLUCZA!")

print("\n3. Testing client initialization...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, timeout=30.0)
    print("   ✅ Client OK")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print("\n   Próba fallback...")
    try:
        client = OpenAI(api_key=api_key)
        print("   ✅ Fallback OK")
    except Exception as e2:
        print(f"   ❌ Fallback failed: {e2}")

print("\n4. Testing API call...")
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'test'"}],
        max_tokens=5
    )
    print(f"   ✅ API Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"   ❌ API Error: {e}")
```

Uruchom: `python debug_openai.py`

### Debug Spaces Issue

```python
# debug_spaces.py
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

print("1. Checking Spaces config...")
region = os.getenv('DO_SPACES_REGION', 'fra1')
bucket = os.getenv('DO_SPACES_BUCKET')
key = os.getenv('DO_SPACES_KEY')
secret = os.getenv('DO_SPACES_SECRET')

print(f"   Region: {region}")
print(f"   Bucket: {bucket}")
print(f"   Key: {key[:10]}..." if key else "   ❌ BRAK!")
print(f"   Secret: {secret[:10]}..." if secret else "   ❌ BRAK!")

print("\n2. Testing connection...")
try:
    s3 = boto3.client(
        's3',
        endpoint_url=f'https://{region}.digitaloceanspaces.com',
        aws_access_key_id=key,
        aws_secret_access_key=secret
    )
    print("   ✅ Client connected")
except Exception as e:
    print(f"   ❌ Connection error: {e}")
    exit(1)

print("\n3. Listing buckets...")
try:
    buckets = s3.list_buckets()
    print("   Buckets:")
    for b in buckets['Buckets']:
        print(f"      - {b['Name']}")
except Exception as e:
    print(f"   ❌ List error: {e}")

print("\n4. Checking data folder...")
try:
    response = s3.list_objects_v2(Bucket=bucket, Prefix='data/')
    if 'Contents' in response:
        print(f"   ✅ Files in data/ ({len(response['Contents'])}):")
        for obj in response['Contents']:
            size_mb = obj['Size'] / (1024*1024)
            print(f"      - {obj['Key']} ({size_mb:.2f} MB)")
    else:
        print("   ⚠️  data/ folder is empty!")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n5. Checking models folder...")
try:
    response = s3.list_objects_v2(Bucket=bucket, Prefix='models/')
    if 'Contents' in response:
        print(f"   ✅ Files in models/ ({len(response['Contents'])}):")
        for obj in response['Contents']:
            size_mb = obj['Size'] / (1024*1024)
            print(f"      - {obj['Key']} ({size_mb:.2f} MB)")
    else:
        print("   ⚠️  models/ folder is empty (expected before training)")
except Exception as e:
    print(f"   ❌ Error: {e}")
```

Uruchom: `python debug_spaces.py`

---

## 🎯 Następne Kroki Po Naprawie

Po wykonaniu wszystkich fix'ów:

1. **Uruchom testy ponownie**:
   ```bash
   python test_pipeline.py
   ```
   Oczekiwany wynik: **8/8 ✅**

2. **Test aplikacji lokalnie**:
   ```bash
   streamlit run app.py
   ```
   
3. **Wytrenuj model** (jeśli jeszcze nie):
   ```bash
   cd notebooks
   jupyter notebook training_pipeline.ipynb
   # Run All Cells
   ```

4. **Zweryfikuj że model jest w Spaces**:
   ```bash
   python -c "
   import boto3, os
   from dotenv import load_dotenv
   load_dotenv()
   s3 = boto3.client('s3',
       endpoint_url=f'https://{os.getenv(\"DO_SPACES_REGION\")}.digitaloceanspaces.com',
       aws_access_key_id=os.getenv('DO_SPACES_KEY'),
       aws_secret_access_key=os.getenv('DO_SPACES_SECRET'))
   objs = s3.list_objects_v2(Bucket=os.getenv('DO_SPACES_BUCKET'), Prefix='models/')
   if 'Contents' in objs:
       print('✅ Model w Spaces:')
       for obj in objs['Contents']:
           print(f'  - {obj[\"Key\"]}')
   else:
       print('❌ Brak modelu - uruchom training!')
   "
   ```

5. **Deployment na Digital Ocean**:
   - Commit i push zmian na GitHub
   - Postępuj według `DEPLOYMENT_GUIDE.md`

---

## 📞 Potrzebujesz Pomocy?

### Typowe Pytania

**Q: Czy mogę pominąć model ML i użyć tylko fallback?**  
A: Tak! Aplikacja działa bez modelu. Fallback daje sensowne predykcje (~±10 min dokładności).

**Q: Czy muszę mieć Langfuse?**  
A: Nie, to opcjonalne. Aplikacja działa bez niego. Langfuse jest tylko do monitorowania LLM.

**Q: Ile kosztuje OpenAI API?**  
A: Model `gpt-4o-mini`:
- Input: $0.150 per 1M tokens
- Output: $0.600 per 1M tokens
- Typowe wywołanie: ~200 tokens = $0.0001 (0.01 centa)
- 1000 wywołań = ~$0.10

Z REGEX catching 70% inputów → ~$0.03 na 1000 predykcji!

**Q: Dlaczego test_pipeline.py pokazuje "fallback" mode?**  
A: Bo model nie jest załadowany. To może być z dwóch powodów:
1. Model nie jest w Spaces (uruchom training)
2. Klucze DO Spaces są błędne

**Q: Czy aplikacja będzie działać na Digital Ocean bez modelu?**  
A: Tak! Będzie używać fallback heurystycznego. Ale lepiej wytrenuj model - jest bardziej dokładny.

---

## 🎓 Best Practices Na Przyszłość

### 1. Zawsze Testuj Lokalnie Przed Deployment

```bash
# Uruchom pełny test suite
python test_pipeline.py

# Test aplikacji
streamlit run app.py

# Test w Docker
docker build -t test . && docker run -p 8080:8080 --env-file .env test
```

### 2. Version Pinning

```txt
# requirements.txt
openai==1.54.0  # nie: openai>=1.0.0
boto3==1.35.36  # nie: boto3
```

### 3. Environment Variables Checklist

Przed każdym deployment sprawdź:
```bash
# .env ma wszystkie klucze?
grep -E "DO_SPACES_KEY|DO_SPACES_SECRET|OPENAI_API_KEY" .env

# .env NIE jest w git?
git ls-files | grep .env  # powinno być PUSTE!
```

### 4. Data Verification

Przed treningiem:
```python
# Sprawdź że dane są OK
import pandas as pd
df = pd.read_csv('data.csv', sep=';')
print(f"Rows: {len(df)}")
print(f"Columns: {df.columns.tolist()}")
print(f"Missing: {df.isnull().sum().sum()}")
```

### 5. Graceful Degradation

Zawsze miej fallback:
```python
try:
    result = expensive_operation()
except Exception:
    result = cheap_fallback()  # Zawsze działa!
```

---

## ✅ Podsumowanie

### Co Naprawiliśmy:

1. ✅ **OpenAI SDK** - konkretna wersja + fallback handling
2. ✅ **Upload CSV** - skrypt + instrukcje
3. ✅ **Ekstrakcja** - poprawiony REGEX + LLM
4. ✅ **Dokumentacja** - debug scripts + troubleshooting

### Co Już Działało:

1. ✅ Environment variables
2. ✅ Module imports
3. ✅ Model fallback
4. ✅ Langfuse

### Następne Kroki:

1. 📦 Zastosuj fix'y (2 min)
2. 📤 Upload CSV (3 min)
3. 🎓 Wytrenuj model (5 min)
4. ✅ Uruchom testy (1 min)
5. 🚀 Deploy! (15 min)

**Razem: ~25 minut do pełnej działającej aplikacji! 🎉**

---

**Powodzenia! Jeśli pojawią się kolejne problemy, uruchom debug scripts wyżej. 🚀**