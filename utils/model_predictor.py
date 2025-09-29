# utils/model_predictor.py
from __future__ import annotations

import os
import math
from typing import Optional, Dict, Any

# Ładowanie modelu (opcjonalnie)
def _try_load_joblib(path: str):
    try:
        import joblib  # scikit-learn joblib (albo standalone joblib)
        return joblib.load(path)
    except Exception:
        return None

def _download_from_spaces(
    bucket: str,
    key: str,
    dest_path: str,
    endpoint: Optional[str],
    region: Optional[str],
    access_key: Optional[str],
    secret_key: Optional[str],
) -> bool:
    """
    Opcjonalne pobieranie z DigitalOcean Spaces (S3 API).
    Zwraca True, jeśli udało się pobrać; False w przeciwnym razie.
    """
    try:
        import boto3  # tylko jeśli masz w env; w przeciwnym razie zwróci False
        session = boto3.session.Session()
        s3 = session.client(
            "s3",
            endpoint_url=endpoint or None,
            region_name=region or None,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
        )
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        s3.download_file(bucket, key, dest_path)
        return True
    except Exception:
        return False


class HalfMarathonPredictor:
    """
    Predyktor czasu półmaratonu.
    - Jeśli podasz MODEL_PATH (lub poprawne zmienne Spaces), użyje modelu .joblib.
    - W przeciwnym razie użyje **stabilnego fallbacku** opartego na czasie 5km + korektach.
    """

    def __init__(self) -> None:
        self.model = None
        self.model_metadata: Dict[str, Any] = {
            "name": "HalfMarathonPredictor",
            "version": "fallback-1.0",
            "source": "heuristic",
        }
        self.feature_order = ["time_5km_seconds", "age", "gender_male"]  # jeżeli masz własny model, dopasuj

        # 1) Spróbuj wczytać lokalny model
        model_path = os.getenv("MODEL_PATH")
        if model_path and os.path.isfile(model_path):
            m = _try_load_joblib(model_path)
            if m is not None:
                self.model = m
                self.model_metadata.update(
                    {"version": "joblib-local", "source": model_path}
                )
                return

        # 2) Jeśli nie ma lokalnie – spróbuj pobrać z Spaces (jeśli zmienne są ustawione)
        bucket = os.getenv("SPACES_BUCKET")
        key = os.getenv("MODEL_KEY")
        endpoint = os.getenv("SPACES_ENDPOINT")  # np. https://fra1.digitaloceanspaces.com
        region = os.getenv("SPACES_REGION", None)
        access_key = os.getenv("SPACES_KEY")
        secret_key = os.getenv("SPACES_SECRET")
        cache_path = os.getenv("MODEL_PATH", ".cache/models/best_model.joblib")

        if bucket and key and access_key and secret_key:
            ok = _download_from_spaces(
                bucket=bucket,
                key=key,
                dest_path=cache_path,
                endpoint=endpoint,
                region=region,
                access_key=access_key,
                secret_key=secret_key,
            )
            if ok and os.path.isfile(cache_path):
                m = _try_load_joblib(cache_path)
                if m is not None:
                    self.model = m
                    self.model_metadata.update(
                        {"version": "joblib-spaces", "source": f"s3://{bucket}/{key}"}
                    )
                    return

        # 3) Jeżeli nic się nie udało – zostajemy w trybie fallback (zero crashy)
        #    self.model = None już ustawione

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────
    def predict(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Oczekuje słownika z kluczami:
        - gender: 'male'/'female'
        - age: int
        - time_5km_seconds: int
        Zwraca:
        {
            'success': bool,
            'prediction_seconds': int,
            'formatted_time': 'H:MM:SS',
            'details': {...}
        }
        """
        # Walidacja danych
        gender = (extracted.get("gender") or "").strip().lower()
        age = extracted.get("age")
        t5 = extracted.get("time_5km_seconds")

        if gender not in {"male", "female"}:
            return {"success": False, "error": "Brak lub niepoprawna płeć (male/female)."}
        try:
            age = int(age)
        except Exception:
            return {"success": False, "error": "Brak lub niepoprawny wiek (liczba całkowita)."}
        try:
            t5 = int(t5)
        except Exception:
            return {"success": False, "error": "Brak lub niepoprawny czas 5km w sekundach (int)."}

        if not (15 <= age <= 90):
            return {"success": False, "error": "Wiek poza zakresem (15–90)."}
        if not (9 * 60 <= t5 <= 60 * 60):
            return {"success": False, "error": "Czas 5km poza sensownym zakresem (9–60 min)."}

        # Próba predykcji modelem .joblib
        if self.model is not None:
            try:
                # Przyjmujemy prosty układ cech (dostosuj jeśli Twój model ma inny):
                gender_male = 1 if gender == "male" else 0
                X = [[t5, age, gender_male]]
                y = self._predict_with_loaded_model(X)
                pred = float(y)
                if not math.isfinite(pred) or pred <= 0:
                    raise ValueError("Model zwrócił niefinansowy/niepoprawny wynik.")
                secs = int(round(pred))
                return {
                    "success": True,
                    "prediction_seconds": secs,
                    "formatted_time": self._format_time(secs),
                    "details": {
                        "mode": "joblib",
                        "model_source": self.model_metadata.get("source"),
                        "version": self.model_metadata.get("version"),
                    },
                }
            except Exception:
                # Jeżeli model nie pasuje do featurów lub coś pójdzie nie tak – miękki fallback
                pass

        # Heurystyczny fallback – działa zawsze
        secs = self._predict_fallback_seconds(t5, age, gender)
        return {
            "success": True,
            "prediction_seconds": secs,
            "formatted_time": self._format_time(secs),
            "details": {
                "mode": "fallback",
                "version": self.model_metadata.get("version"),
            },
        }

    # ──────────────────────────────────────────────────────────────────────
    # Implementacje wewnętrzne
    # ──────────────────────────────────────────────────────────────────────
    def _predict_with_loaded_model(self, X):
        """
        Minimalna abstrakcja – większość modeli scikit-learn/xgboost ma .predict().
        """
        if hasattr(self.model, "predict"):
            y = self.model.predict(X)
            # y może być np. [czas_w_sekundach]
            return y[0] if hasattr(y, "__len__") else y
        # jeśli to inny typ modelu, spróbuj wywołać:
        raise AttributeError("Załadowany model nie posiada metody predict().")

    def _predict_fallback_seconds(self, t5: int, age: int, gender: str) -> int:
        """
        Fallback: estymacja czasu HM na bazie 5 km + korekty wieku/płci.
        Dobrze działa jako rozsądny baseline.
        """
        # Bazowy mnożnik (kalibrowany tak, by odpowiadał typowym kalkulatorom):
        # HM ≈ 4.46 * 5k_time
        base = 4.46 * t5

        # Korekta płci (średnio kobiety ~3% wolniej na długim dystansie – uśrednienie):
        if gender == "female":
            base *= 1.03

        # Korekta wieku:
        # 20–35: 0%, 36–50: +0.3%/rok powyżej 35, 51–65: +0.5%/rok powyżej 50, >65: +1.0%/rok
        if age < 20:
            base *= 1.005 * (20 - age)  # młodsi rzadko mają lepszą wytrzymałość
        elif 36 <= age <= 50:
            base *= 1 + 0.003 * (age - 35)
        elif 51 <= age <= 65:
            base *= 1 + 0.003 * (50 - 35) + 0.005 * (age - 50)
        elif age > 65:
            base *= 1 + 0.003 * (50 - 35) + 0.005 * (65 - 50) + 0.01 * (age - 65)

        # Delikatne „wypłaszczenie” dla bardzo szybkich i bardzo wolnych
        base = max(base, 60 * 60)          # min 1h (bez absurdów)
        base = min(base, 4 * 60 * 60)      # max 4h

        return int(round(base))

    @staticmethod
    def _format_time(total_seconds: int) -> str:
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h}:{m:02d}:{s:02d}"
