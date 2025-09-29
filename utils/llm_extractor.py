import os
import json
import re
from typing import Optional, Dict, Any
from openai import OpenAI

# ✅ Langfuse kompatybilność (każda wersja, także brak pakietu)
try:
    # Próba importu najnowszego API
    from langfuse.decorators import observe, langfuse_context  # type: ignore
except Exception:
    try:
        # Próba importu starszej wersji
        from langfuse import Langfuse  # type: ignore
        _lf = Langfuse()

        def observe(name: Optional[str] = None):
            def _decorator(func):
                return func
            return _decorator

        class _DummyCtx:
            @staticmethod
            def update_current_observation(**kwargs):
                pass

        langfuse_context = _DummyCtx()

    except Exception:
        # Brak pakietu Langfuse – fallback
        def observe(name: Optional[str] = None):
            def _decorator(func):
                return func
            return _decorator

        class _DummyCtx:
            @staticmethod
            def update_current_observation(**kwargs):
                pass

        langfuse_context = _DummyCtx()

# ✅ OpenAI client (lazy init)
_client: Optional[OpenAI] = None
def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("❌ Brak klucza OPENAI_API_KEY w środowisku")
        _client = OpenAI(api_key=api_key)
    return _client


@observe(name="llm_data_extraction")
def extract_user_data(user_input: str) -> Dict[str, Optional[int | str]]:
    """
    Ekstrakcja danych użytkownika (płeć, wiek, czas 5km) przez OpenAI
    """
    system_prompt = """Jesteś asystentem ekstrakcji danych dla systemu predykcji półmaratonu.

Twoim zadaniem jest wydobycie następujących informacji z tekstu użytkownika:
1. Płeć (mężczyzna/kobieta/M/K)
2. Wiek (w latach, jako liczba całkowita)
3. Czas biegu na 5km (w sekundach)

Zwróć TYLKO obiekt JSON:
{
    "gender": "male" lub "female" lub null,
    "age": liczba całkowita lub null,
    "time_5km_seconds": liczba całkowita lub null
}"""

    result = {"gender": None, "age": None, "time_5km_seconds": None}

    try:
        try:
            langfuse_context.update_current_observation(
                input=user_input, metadata={"task": "data_extraction"}
            )
        except Exception:
            pass

        client = get_openai_client()
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.1,
            max_tokens=200,
        )

        text = response.choices[0].message.content.strip()
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        extracted = json.loads(json_match.group() if json_match else text)

        # 🔹 Gender
        g = str(extracted.get("gender", "")).lower()
        if g in ["male", "m", "man", "mężczyzna", "męski"]:
            result["gender"] = "male"
        elif g in ["female", "f", "woman", "kobieta", "żeński"]:
            result["gender"] = "female"

        # 🔹 Age
        try:
            a = int(extracted.get("age"))
            if 15 <= a <= 90:
                result["age"] = a
        except Exception:
            pass

        # 🔹 Time
        try:
            t = int(extracted.get("time_5km_seconds"))
            if 900 <= t <= 3600:
                result["time_5km_seconds"] = t
        except Exception:
            pass

        try:
            langfuse_context.update_current_observation(output=result)
        except Exception:
            pass

        return result

    except Exception as e:
        print(f"[extract_user_data] Błąd: {e}")
        return result


def parse_time_to_seconds(time_str: str) -> Optional[int]:
    """Prosty parser czasu tekstowego na sekundy"""
    try:
        s = (
            time_str.lower()
            .replace("minuty", "min")
            .replace("minut", "min")
            .replace("minutes", "min")
            .replace("sekund", "s")
            .replace("sekundy", "s")
            .replace("seconds", "s")
            .replace(" ", "")
        )

        if ":" in s:
            parts = s.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

        if "min" in s:
            s = s.replace("min", "")
            return int(float(s) * 60)

        if "s" in s:
            s = s.replace("s", "")
            return int(float(s))

        val = float(s)
        return int(val * 60) if val < 100 else int(val)
    except Exception:
        return None
