#!/bin/bash

# Automatyczna naprawa wszystkich problemów Half Marathon Predictor
# Uruchom: bash fix_all.sh

set -e  # Exit on error

echo "🔧 HALF MARATHON PREDICTOR - AUTO FIX"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. FIX OPENAI SDK
echo "📦 Krok 1/5: Naprawianie OpenAI SDK..."
echo "------------------------------------"

pip uninstall openai -y > /dev/null 2>&1 || true
pip install openai==1.54.0 > /dev/null 2>&1

if python -c "from openai import OpenAI; print('OK')" 2>/dev/null; then
    echo -e "${GREEN}✅ OpenAI SDK naprawiony (v1.54.0)${NC}"
else
    echo -e "${RED}❌ Błąd instalacji OpenAI${NC}"
    exit 1
fi

echo ""

# 2. VERIFY ENV VARIABLES
echo "🔐 Krok 2/5: Weryfikacja zmiennych środowiskowych..."
echo "---------------------------------------------------"

if [ ! -f .env ]; then
    echo -e "${RED}❌ Brak pliku .env!${NC}"
    echo "Skopiuj .env.example i uzupełnij klucze:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

source .env 2>/dev/null || true

REQUIRED_VARS=("DO_SPACES_KEY" "DO_SPACES_SECRET" "DO_SPACES_BUCKET" "OPENAI_API_KEY")
MISSING=0

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}❌ Brak zmiennej: $var${NC}"
        MISSING=1
    else
        echo -e "${GREEN}✅ $var${NC}"
    fi
done

if [ $MISSING -eq 1 ]; then
    echo -e "${RED}Uzupełnij brakujące zmienne w .env${NC}"
    exit 1
fi

echo ""

# 3. TEST OPENAI API
echo "🤖 Krok 3/5: Test OpenAI API..."
echo "-------------------------------"

python - <<EOF 2>/dev/null
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=30.0)
resp = client.chat.completions.create(
    model='gpt-4o-mini',
    messages=[{'role': 'user', 'content': 'Say OK'}],
    max_tokens=5
)
print('✅ OpenAI API działa:', resp.choices[0].message.content)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ OpenAI API OK${NC}"
else
    echo -e "${RED}❌ OpenAI API error${NC}"
    echo "Sprawdź:"
    echo "  1. Czy klucz OPENAI_API_KEY jest poprawny"
    echo "  2. Czy masz kredyty na koncie OpenAI"
    exit 1
fi

echo ""

# 4. CHECK CSV FILES
echo "📁 Krok 4/5: Sprawdzanie plików CSV..."
echo "---------------------------------------"

CSV_FILES=("halfmarathon_wroclaw_2023__final.csv" "halfmarathon_wroclaw_2024__final.csv")
CSV_MISSING=0

for file in "${CSV_FILES[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        echo -e "${GREEN}✅ $file ($size)${NC}"
    else
        echo -e "${YELLOW}⚠️  $file - nie znaleziono${NC}"
        CSV_MISSING=1
    fi
done

if [ $CSV_MISSING -eq 1 ]; then
    echo -e "${YELLOW}Uwaga: Brak niektórych plików CSV${NC}"
    echo "To normalne jeśli używasz własnych danych."
    echo "Upewnij się że pliki są w Digital Ocean Spaces!"
fi

echo ""

# 5. UPLOAD TO SPACES (optional)
echo "☁️  Krok 5/5: Upload do Digital Ocean Spaces..."
echo "-----------------------------------------------"

if [ $CSV_MISSING -eq 0 ]; then
    echo "Znaleziono wszystkie pliki CSV. Chcesz je uploadować do Spaces? (y/n)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        python - <<EOF
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

region = os.getenv('DO_SPACES_REGION', 'fra1')
bucket = os.getenv('DO_SPACES_BUCKET')
endpoint = f'https://{region}.digitaloceanspaces.com'

s3 = boto3.client(
    's3',
    endpoint_url=endpoint,
    aws_access_key_id=os.getenv('DO_SPACES_KEY'),
    aws_secret_access_key=os.getenv('DO_SPACES_SECRET')
)

files = [
    'halfmarathon_wroclaw_2023__final.csv',
    'halfmarathon_wroclaw_2024__final.csv'
]

for filename in files:
    if os.path.isfile(filename):
        key = f'data/{filename}'
        print(f'📤 Uploading {filename}...')
        s3.upload_file(filename, bucket, key, ExtraArgs={'ACL': 'private'})
        print(f'✅ Uploaded: {key}')

print('\n✅ Wszystkie pliki uploaded!')
EOF
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Upload zakończony${NC}"
        else
            echo -e "${RED}❌ Błąd uploadu${NC}"
        fi
    else
        echo "⏭️  Pominięto upload"
    fi
else
    echo "⏭️  Pominięto upload (brak plików lokalnie)"
fi

echo ""
echo "======================================"
echo "🎉 AUTO FIX ZAKOŃCZONY!"
echo "======================================"
echo ""
echo "✅ Co zostało naprawione:"
echo "   1. OpenAI SDK (v1.54.0)"
echo "   2. Zmienne środowiskowe"
echo "   3. OpenAI API"
echo "   4. Pliki CSV"
echo "   5. Upload do Spaces (opcjonalnie)"
echo ""
echo "📋 Następne kroki:"
echo "   1. Uruchom testy: python test_pipeline.py"
echo "   2. Wytrenuj model: jupyter notebook notebooks/training_pipeline.ipynb"
echo "   3. Test aplikacji: streamlit run app.py"
echo "   4. Deploy: Zobacz DEPLOYMENT_GUIDE.md"
echo ""
echo "🚀 Powodzenia!"