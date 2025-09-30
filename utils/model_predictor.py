from __future__ import annotations

import hashlib
import os
import math
import pickle
import logging
from typing import Optional, Dict, Any

import pandas as pd

from botocore.config import Config
import boto3

def _sha256_file(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _try_load_model(path: str):
    """Próba załadowania modelu z pliku .pkl lub .joblib"""
    try:
        import joblib
        return joblib.load(path)
    except Exception:
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None


def _download_from_spaces(bucket, key, dest_path, endpoint, access_key, secret_key) -> bool:
    try:
        s3 = boto3.client(
            "s3",
            region_name=os.getenv("DO_SPACES_REGION", "fra1"),
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        s3.download_file(bucket, key, dest_path)
        print(f"✅ Model pobrany z Spaces: s3://{bucket}/{key}")
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
        self.feature_order = None  # ← zapamiętana kolejność cech
        self.model_metadata = {
            "name": "HalfMarathonPredictor",
            "version": "1.0",
            "source": "fallback",
        }

        # 1) Próba załadowania lokalnego modelu
        model_path = os.getenv("MODEL_PATH", "model_cache/halfmarathon_model_latest.pkl")
        metadata_path = model_path.replace(".pkl", "_metadata.pkl")

        if os.path.isfile(model_path):
            m = _try_load_model(model_path)
            if m is not None:
                self.model = m

                # Załaduj metadata jeśli istnieje
                if os.path.isfile(metadata_path):
                    meta = _try_load_model(metadata_path)
                    if meta and isinstance(meta, dict):
                        self.model_metadata.update(meta)
                        self.feature_order = meta.get("features")

                self.model_metadata.update(
                    {"version": "ml-local", "source": model_path}
                )
                print(f"✅ Model załadowany lokalnie: {model_path}")
                if self.feature_order:
                    print(f"   Features: {self.feature_order}")
                return

        # 2) Próba pobrania z Digital Ocean Spaces
        bucket = os.getenv("DO_SPACES_BUCKET")
        region = os.getenv("DO_SPACES_REGION", "fra1")
        access_key = os.getenv("DO_SPACES_KEY")
        secret_key = os.getenv("DO_SPACES_SECRET")

        if bucket and access_key and secret_key:
            endpoint = f"https://{region}.digitaloceanspaces.com"
            model_key = "models/halfmarathon_model_latest.pkl"
            metadata_key = "models/model_metadata_latest.pkl"
            cache_path = "model_cache/halfmarathon_model_latest.pkl"
            cache_meta_path = "model_cache/model_metadata_latest.pkl"

            ok = _download_from_spaces(
                bucket=bucket,
                key=model_key,
                dest_path=cache_path,
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
            )

            # Pobierz też metadata (nie blokujące)
            _download_from_spaces(
                bucket=bucket,
                key=metadata_key,
                dest_path=cache_meta_path,
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
            )

            if ok and os.path.isfile(cache_path):
                # Weryfikacja checksumy (opcjonalna)
                checksum_ok = True
                model_sha_env = os.getenv("MODEL_SHA256")
                if model_sha_env:
                    actual = _sha256_file(cache_path)
                    if actual and actual.lower() != model_sha_env.lower():
                        logging.warning(
                            "Model checksum mismatch: expected %s, got %s",
                            model_sha_env,
                            actual,
                        )
                        checksum_ok = False

                if checksum_ok:
                    m = _try_load_model(cache_path)
                    if m is not None:
                        self.model = m

                        # Załaduj metadata jeśli pobrano
                        if os.path.isfile(cache_meta_path):
                            meta = _try_load_model(cache_meta_path)
                            if meta and isinstance(meta, dict):
                                self.model_metadata.update(meta)
                                self.feature_order = meta.get("features")

                        self.model_metadata.update(
                            {"version": "ml-spaces", "source": f"s3://{bucket}/{model_key}"}
                        )
                        print("✅ Model załadowany z Spaces")
                        if self.feature_order:
                            print(f"   Features: {self.feature_order}")
                        return

        # 3) Fallback - algorytm heurystyczny
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
                'confidence': str,
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
                "error": "Brak lub niepoprawna płeć. Wymagane: 'male' lub 'female'.",
                "hint": "Podaj płeć: M/K, mężczyzna/kobieta, male/female",
            }

        try:
            age = int(age)
        except Exception:
            return {
                "success": False,
                "error": "Brak lub niepoprawny wiek. Wymagana liczba całkowita.",
                "hint": "Podaj wiek: liczba od 15 do 90 lat",
            }

        try:
            t5 = int(t5)
        except Exception:
            return {
                "success": False,
                "error": "Brak lub niepoprawny czas 5km. Wymagana liczba sekund (int).",
                "hint": "Podaj czas 5km w formacie MM:SS (np. 24:30)",
            }

        # Walidacja zakresów
        if not (15 <= age <= 90):
            return {"success": False, "error": f"Wiek {age} poza zakresem 15-90 lat."}

        if not (9 * 60 <= t5 <= 60 * 60):
            return {
                "success": False,
                "error": "Czas 5km poza sensownym zakresem (9-60 minut).",
            }

        # Predykcja modelem ML (jeśli dostępny)
        if self.model is not None:
            try:
                pred = self._predict_ml(t5, age, gender)
                if pred and math.isfinite(pred) and pred > 0:
                    return self._format_prediction(pred, mode="ml", confidence="high")
            except Exception as e:
                print(f"⚠️ Błąd predykcji ML: {e}, przełączam na fallback")

        # Fallback heurystyczny
        pred = self._predict_fallback(t5, age, gender)
        return self._format_prediction(pred, mode="fallback", confidence="medium")

    def _predict_ml(self, t5: int, age: int, gender: str) -> float | None:
        """Predykcja za pomocą modelu ML - z uwzględnieniem feature_order"""
        gender_encoded = 1 if gender == "male" else 0
        pace_5k = t5 / 5

        # Użyj feature_order jeśli dostępne
        if self.feature_order:
            feature_values = {
                "Płeć_encoded": gender_encoded,
                "Wiek": age,
                "5 km Czas_seconds": t5,
                "5 km Tempo": pace_5k,
                "10 km Tempo": pace_5k * 1.05,  # estymacja
                "15 km Tempo": pace_5k * 1.08,  # estymacja
                "Tempo Stabilność": 0.03,       # średnia wartość
            }
            X = pd.DataFrame(
                [{feat: feature_values.get(feat, 0) for feat in self.feature_order}]
            )
            return float(self.model.predict(X)[0])

        # Fallback do starej logiki (próba różnych kombinacji)
        try:
            X = [[gender_encoded, age, t5, pace_5k]]
            return float(self.model.predict(X)[0])
        except Exception:
            try:
                X = [[gender_encoded, age, t5]]
                return float(self.model.predict(X)[0])
            except Exception:
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
            base *= 1 + 0.005 * (20 - age)
        elif 20 <= age <= 35:
            pass  # peak performance
        elif 36 <= age <= 50:
            base *= 1 + 0.003 * (age - 35)
        elif 51 <= age <= 65:
            base *= 1 + 0.003 * 15 + 0.005 * (age - 50)
        else:  # > 65
            base *= 1 + 0.003 * 15 + 0.005 * 15 + 0.01 * (age - 65)

        # Ograniczenia
        base = max(base, 60 * 60)
        base = min(base, 4 * 60 * 60)

        return int(round(base))

    def _format_prediction(
        self, total_seconds: int, mode: str, confidence: str = "medium"
    ) -> Dict[str, Any]:
        """Formatowanie wyniku predykcji"""
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        # Tempo średnie (min/km)
        half_marathon_km = 21.0975
        avg_pace_sec_per_km = total_seconds / half_marathon_km
        avg_pace_min_per_km = avg_pace_sec_per_km / 60

        confidence_text = {
            "high": "Wysoka (model ML)",
            "medium": "Średnia (heurystyka)",
            "low": "Niska (brak danych)",
        }

        return {
            "success": True,
            "prediction_seconds": total_seconds,
            "formatted_time": f"{hours}:{minutes:02d}:{seconds:02d}",
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "average_pace_min_per_km": round(avg_pace_min_per_km, 2),
            "confidence": confidence_text.get(confidence, "medium"),
            "details": {
                "mode": mode,
                "model_version": self.model_metadata.get("version"),
                "model_source": self.model_metadata.get("source"),
                "features_used": self.feature_order if self.feature_order else "basic",
            },
        }
