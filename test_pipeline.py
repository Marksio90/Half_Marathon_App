#!/usr/bin/env python3
"""
Skrypt do testowania całego pipeline'u Half Marathon Predictor
Sprawdza: ekstrakcję danych, model, API, deployment
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def test_environment():
    """Test 1: Sprawdź zmienne środowiskowe"""
    print_section("TEST 1: Zmienne Środowiskowe")
    
    required_vars = {
        'DO_SPACES_KEY': 'Digital Ocean Spaces Access Key',
        'DO_SPACES_SECRET': 'Digital Ocean Spaces Secret Key',
        'DO_SPACES_BUCKET': 'Digital Ocean Spaces Bucket',
        'OPENAI_API_KEY': 'OpenAI API Key'
    }
    
    optional_vars = {
        'LANGFUSE_SECRET_KEY': 'Langfuse Secret Key',
        'LANGFUSE_PUBLIC_KEY': 'Langfuse Public Key'
    }
    
    all_good = True
    
    print("Wymagane zmienne:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." if len(value) > 8 else value
            print(f"  ✅ {var}: {masked}")
        else:
            print(f"  ❌ {var}: BRAK!")
            all_good = False
    
    print("\nOpcjonalne zmienne:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." if len(value) > 8 else value
            print(f"  ✅ {var}: {masked}")
        else:
            print(f"  ⚠️  {var}: brak (opcjonalne)")
    
    return all_good

def test_imports():
    """Test 2: Sprawdź czy wszystkie moduły się importują"""
    print_section("TEST 2: Importy Modułów")
    
    modules = {
        'streamlit': 'Streamlit',
        'openai': 'OpenAI SDK',
        'boto3': 'Boto3 (AWS SDK)',
        'pandas': 'Pandas',
        'numpy': 'NumPy',
        'sklearn': 'Scikit-learn',
        'xgboost': 'XGBoost'
    }
    
    all_good = True
    for module, name in modules.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError as e:
            print(f"  ❌ {name}: {e}")
            all_good = False
    
    return all_good

def test_openai_connection():
    """Test 3: Sprawdź połączenie z OpenAI"""
    print_section("TEST 3: OpenAI API")
    
    try:
        from openai import OpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("  ❌ Brak OPENAI_API_KEY")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # Prosty test
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test' if you can hear me"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"  ✅ OpenAI API działa!")
        print(f"  📊 Model: gpt-4o-mini")
        print(f"  💬 Test response: {result}")
        return True
        
    except Exception as e:
        print(f"  ❌ OpenAI API error: {e}")
        return False

def test_spaces_connection():
    """Test 4: Sprawdź połączenie z Digital Ocean Spaces"""
    print_section("TEST 4: Digital Ocean Spaces")
    
    try:
        import boto3
        
        region = os.getenv('DO_SPACES_REGION', 'fra1')
        bucket = os.getenv('DO_SPACES_BUCKET')
        endpoint = f'https://{region}.digitaloceanspaces.com'
        
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv('DO_SPACES_KEY'),
            aws_secret_access_key=os.getenv('DO_SPACES_SECRET')
        )
        
        # Lista plików w folderze data
        response = s3.list_objects_v2(Bucket=bucket, Prefix='')
        
        if 'Contents' in response:
            print(f"  ✅ Połączenie z Spaces OK!")
            print(f"  📦 Bucket: {bucket}")
            print(f"  📁 Pliki w bucket:")
            for obj in response['Contents']:
                size_mb = obj['Size'] / (1024 * 1024)
                print(f"     - {obj['Key']} ({size_mb:.2f} MB)")
            
            # Sprawdź czy są oba pliki CSV
            files = [obj['Key'] for obj in response['Contents']]
            required_files = [
                'halfmarathon_wroclaw_2023__final.csv',
                'halfmarathon_wroclaw_2024__final.csv'
            ]
            
            missing = [f for f in required_files if f not in files]
            if missing:
                print(f"\n  ⚠️  Brakujące pliki:")
                for f in missing:
                    print(f"     - {f}")
                return False
            
            return True
        else:
            print(f"  ❌ Folder data/ jest pusty!")
            return False
            
    except Exception as e:
        print(f"  ❌ Spaces connection error: {e}")
        return False

def test_data_extraction():
    """Test 5: Sprawdź ekstrakcję danych"""
    print_section("TEST 5: Ekstrakcja Danych (REGEX + LLM)")
    
    try:
        from utils.llm_extractor import extract_user_data_auto
        
        test_cases = [
            {
                'input': 'M 30 lat, 5km 24:30',
                'expected': {'gender': 'male', 'age': 30, 'time_5km_seconds': 1470}
            },
            {
                'input': 'Kobieta 28 lat, 5k w 27 minut',
                'expected': {'gender': 'female', 'age': 28, 'time_5km_seconds': 1620}
            },
            {
                'input': 'Male runner, 45 years old, 5km time is 22:30',
                'expected': {'gender': 'male', 'age': 45, 'time_5km_seconds': 1350}
            }
        ]
        
        all_passed = True
        for i, case in enumerate(test_cases, 1):
            print(f"\n  Test case {i}: \"{case['input']}\"")
            result = extract_user_data_auto(case['input'])
            
            expected = case['expected']
            if (result['gender'] == expected['gender'] and 
                result['age'] == expected['age'] and 
                result['time_5km_seconds'] == expected['time_5km_seconds']):
                print(f"    ✅ PASS - {result}")
            else:
                print(f"    ❌ FAIL")
                print(f"       Expected: {expected}")
                print(f"       Got: {result}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ❌ Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_prediction():
    """Test 6: Sprawdź predykcję modelu"""
    print_section("TEST 6: Predykcja Modelu")
    
    try:
        from utils.model_predictor import HalfMarathonPredictor
        
        predictor = HalfMarathonPredictor()
        
        test_cases = [
            {
                'input': {'gender': 'male', 'age': 30, 'time_5km_seconds': 1470},
                'expected_range': (5400, 7200)  # 1:30:00 - 2:00:00
            },
            {
                'input': {'gender': 'female', 'age': 28, 'time_5km_seconds': 1620},
                'expected_range': (6000, 8400)  # 1:40:00 - 2:20:00
            }
        ]
        
        all_passed = True
        for i, case in enumerate(test_cases, 1):
            inp = case['input']
            print(f"\n  Test case {i}:")
            print(f"    Input: {inp['gender']}, {inp['age']} lat, 5km={inp['time_5km_seconds']}s")
            
            result = predictor.predict(inp)
            
            if result['success']:
                pred_sec = result['prediction_seconds']
                min_exp, max_exp = case['expected_range']
                
                if min_exp <= pred_sec <= max_exp:
                    print(f"    ✅ PASS")
                    print(f"       Predicted: {result['formatted_time']}")
                    print(f"       Mode: {result['details']['mode']}")
                else:
                    print(f"    ⚠️  WARNING: Prediction outside expected range")
                    print(f"       Predicted: {result['formatted_time']} ({pred_sec}s)")
                    print(f"       Expected: {min_exp}-{max_exp}s")
            else:
                print(f"    ❌ FAIL: {result.get('error')}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ❌ Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_pipeline():
    """Test 7: Pełny pipeline (ekstrakcja + predykcja)"""
    print_section("TEST 7: Pełny Pipeline")
    
    try:
        from utils.llm_extractor import extract_user_data_auto
        from utils.model_predictor import HalfMarathonPredictor
        
        predictor = HalfMarathonPredictor()
        
        test_input = "Jestem 32-letnim mężczyzną, mój czas na 5 km to 23:45"
        
        print(f"  Input: \"{test_input}\"")
        print("\n  Krok 1: Ekstrakcja danych...")
        extracted = extract_user_data_auto(test_input)
        print(f"    ✅ Extracted: {extracted}")
        
        if not all(extracted.values()):
            print(f"    ❌ Niepełne dane!")
            return False
        
        print("\n  Krok 2: Predykcja...")
        result = predictor.predict(extracted)
        
        if result['success']:
            print(f"    ✅ Prediction: {result['formatted_time']}")
            print(f"    📊 Pace: {result['average_pace_min_per_km']:.2f} min/km")
            print(f"    🔧 Mode: {result['details']['mode']}")
            return True
        else:
            print(f"    ❌ Prediction failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_langfuse():
    """Test 8: Sprawdź Langfuse (opcjonalnie)"""
    print_section("TEST 8: Langfuse Integration (Opcjonalne)")
    
    secret = os.getenv('LANGFUSE_SECRET_KEY')
    public = os.getenv('LANGFUSE_PUBLIC_KEY')
    
    if not secret or not public:
        print("  ⚠️  Langfuse nie skonfigurowany (opcjonalne)")
        return True  # Not a failure
    
    try:
        from langfuse import Langfuse
        
        langfuse = Langfuse()
        
        # Prosty test trace
        trace = langfuse.trace(
            name="test_trace",
            input={"test": "data"},
            output={"result": "ok"}
        )
        
        print(f"  ✅ Langfuse działa!")
        print(f"  📊 Trace ID: {trace.id if hasattr(trace, 'id') else 'N/A'}")
        return True
        
    except Exception as e:
        print(f"  ⚠️  Langfuse warning: {e}")
        return True  # Not critical

def main():
    """Uruchom wszystkie testy"""
    print("\n" + "🏃 "*20)
    print("  HALF MARATHON PREDICTOR - TEST SUITE")
    print("🏃 "*20)
    
    tests = [
        ("Environment Variables", test_environment),
        ("Module Imports", test_imports),
        ("OpenAI API", test_openai_connection),
        ("Digital Ocean Spaces", test_spaces_connection),
        ("Data Extraction", test_data_extraction),
        ("Model Prediction", test_model_prediction),
        ("Full Pipeline", test_full_pipeline),
        ("Langfuse Integration", test_langfuse)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ❌ CRITICAL ERROR in {name}: {e}")
            results.append((name, False))
    
    # Podsumowanie
    print_section("PODSUMOWANIE")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  📊 Wynik: {passed}/{total} testów przeszło")
    
    if passed == total:
        print("\n  🎉 WSZYSTKIE TESTY PRZESZŁY! 🎉")
        print("  ✅ Aplikacja jest gotowa do deployment!")
        return 0
    else:
        print("\n  ⚠️  NIEKTÓRE TESTY NIE PRZESZŁY")
        print("  🔧 Napraw błędy przed deployment!")
        return 1

if __name__ == "__main__":
    sys.exit(main())