from __future__ import annotations
import os
import math
import pickle
from typing import Optional, Dict, Any

def _try_load_model(path: str):
    """Próba załadowania modelu z pliku .pkl lub .joblib"""
    try:
        import joblib
        return joblib.load(path)
    except:
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except:
            return None

def _download_from_spaces(
    bucket: str,
    key: str,
    dest_path: str,
    endpoint: str,
    access_key: str,
    secret_key: str,
) -> bool:
    """Pobieranie modelu z Digital Ocean Spaces"""
    try:
        import boto3
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        s3.download_file(bucket, key, dest_path)
        print(f"✅ Model pobrany z Spaces: {key}")
        return True
    except Exception as e:
        print(f"⚠️ Nie udało się pobrać modelu z Spaces: {e}")
        return False

class HalfMarathonPredictor:
    """
    Predyktor czasu półmaratonu.
    - Próbuje załadować model ML (XGBoost/RandomForest)
    - Jeśli nie ma modelu, używa fallback heurystycznego
    """
    
    def __init__(self):
        self.model = None
        self.model_metadata = {
            "name": "HalfMarathonPredictor",
            "version": "1.0",
            "source": "fallback"
        }
        
        # 1. Próba załadowania lokalnego modelu
        model_path = os.getenv("MODEL_PATH", "model_cache/halfmarathon_model_latest.pkl")
        
        if os.path.isfile(model_path):
            m = _try_load_model(model_path)
            if m is not None:
                self.model = m
                self.model_metadata.update({
                    "version": "ml-local",
                    "source": model_path
                })
                print(f"✅ Model załadowany lokalnie: {model_path}")
                return
        
        # 2. Próba pobrania z Digital Ocean Spaces
        bucket = os.getenv("DO_SPACES_BUCKET")
        region = os.getenv("DO_SPACES_REGION", "fra1")
        access_key = os.getenv("DO_SPACES_KEY")
        secret_key = os.getenv("DO_SPACES_SECRET")
        
        if bucket and access_key and secret_key:
            endpoint = f"https://{region}.digitaloceanspaces.com"
            model_key = "models/halfmarathon_model_latest.pkl"
            cache_path = "model_cache/halfmarathon_model_latest.pkl"
            
            ok = _download_from_spaces(
                bucket=bucket,
                key=model_key,
                dest_path=cache_path,
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key
            )
            
            if ok and os.path.isfile(cache_path):
                m = _try_load_model(cache_path)
                if m is not None:
                    self.model = m
                    self.model_metadata.update({
                        "version": "ml-spaces",
                        "source": f"s3://{bucket}/{model_key}"
                    })
                    print(f"✅ Model załadowany z Spaces")
                    return
        
        # 3. Fallback - algorytm heurystyczny
        print("⚠️ Model ML niedostępny - używam fallback heurystycznego")
    
    def predict(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predykcja czasu półmaratonu.
        
        Input:
            {
                'gender': 'male'/'female',
                'age': int,
                'time_5km_seconds': int
            }
        
        Output:
            {
                'success': bool,
                'prediction_seconds': int,
                'formatted_time': 'H:MM:SS',
                'hours': int,
                'minutes': int,
                'seconds': int,
                'average_pace_min_per_km': float,
                'details': {...}
            }
        """
        # Walidacja danych wejściowych
        gender = (extracted.get("gender") or "").strip().lower()
        age = extracted.get("age")
        t5 = extracted.get("time_5km_seconds")
        
        if gender not in {"male", "female"}:
            return {
                "success": False,
                "error": "Brak lub niepoprawna płeć. Wymagane: 'male' lub 'female'."
            }
        
        try:
            age = int(age)
        except:
            return {
                "success": False,
                "error": "Brak lub niepoprawny wiek. Wymagana liczba całkowita."
            }
        
        try:
            t5 = int(t5)
        except:
            return {
                "success": False,
                "error": "Brak lub niepoprawny czas 5km. Wymagana liczba sekund (int)."
            }
        
        # Walidacja zakresów
        if not (15 <= age <= 90):
            return {
                "success": False,
                "error": f"Wiek {age} poza zakresem 15-90 lat."
            }
        
        if not (9*60 <= t5 <= 60*60):
            return {
                "success": False,
                "error": f"Czas 5km poza sensownym zakresem (9-60 minut)."
            }
        
        # Predykcja modelem ML (jeśli dostępny)
        if self.model is not None:
            try:
                pred = self._predict_ml(t5, age, gender)
                if pred and math.isfinite(pred) and pred > 0:
                    return self._format_prediction(pred, mode="ml")
            except Exception as e:
                print(f"⚠️ Błąd predykcji ML: {e}, przełączam na fallback")
        
        # Fallback heurystyczny
        pred = self._predict_fallback(t5, age, gender)
        return self._format_prediction(pred, mode="fallback")
    
    def _predict_ml(self, t5: int, age: int, gender: str) -> float:
        """Predykcja za pomocą modelu ML"""
        gender_encoded = 1 if gender == "male" else 0
        
        # Podstawowe features (dostosuj do swojego modelu)
        pace_5k = t5 / 5  # tempo w sekundach na km
        
        # Próba z różnymi układami cech
        try:
            # Wariant 1: podstawowe cechy
            X = [[gender_encoded, age, t5, pace_5k]]
            return float(self.model.predict(X)[0])
        except:
            try:
                # Wariant 2: tylko podstawowe
                X = [[gender_encoded, age, t5]]
                return float(self.model.predict(X)[0])
            except:
                # Jeśli nic nie działa, zwróć None
                return None
    
    def _predict_fallback(self, t5: int, age: int, gender: str) -> int:
        """
        Heurystyczna predykcja oparta na współczynnikach.
        Bazuje na klasycznych kalkulatorach czasu półmaratonu.
        """
        # Bazowy współczynnik (HM ≈ 4.46 * 5k_time)
        base = 4.46 * t5
        
        # Korekta płci (kobiety średnio ~3% wolniej na dłuższym dystansie)
        if gender == "female":
            base *= 1.03
        
        # Korekta wieku
        if age < 20:
            base *= 1 + 0.005 * (20 - age)  # młodsi mogą być wolniejsi
        elif 20 <= age <= 35:
            pass  # peak performance
        elif 36 <= age <= 50:
            base *= 1 + 0.003 * (age - 35)  # +0.3% na rok
        elif 51 <= age <= 65:
            base *= 1 + 0.003 * 15 + 0.005 * (age - 50)  # +0.5% na rok
        else:  # > 65
            base *= 1 + 0.003 * 15 + 0.005 * 15 + 0.01 * (age - 65)  # +1% na rok
        
        # Ograniczenia
        base = max(base, 60 * 60)      # min 1h
        base = min(base, 4 * 60 * 60)  # max 4h
        
        return int(round(base))
    
    def _format_prediction(self, total_seconds: int, mode: str) -> Dict[str, Any]:
        """Formatowanie wyniku predykcji"""
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        # Tempo średnie (min/km)
        half_marathon_km = 21.0975
        avg_pace_sec_per_km = total_seconds / half_marathon_km
        avg_pace_min_per_km = avg_pace_sec_per_km / 60
        
        return {
            "success": True,
            "prediction_seconds": total_seconds,
            "formatted_time": f"{hours}:{minutes:02d}:{seconds:02d}",
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "average_pace_min_per_km": round(avg_pace_min_per_km, 2),
            "details": {
                "mode": mode,
                "model_version": self.model_metadata.get("version"),
                "model_source": self.model_metadata.get("source")
            }
        }