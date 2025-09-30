from __future__ import annotations

import os
import re
import json
import unicodedata
from functools import lru_cache
from typing import Optional, Dict, Any

# OpenAI SDK (opcjonalnie – używane tylko gdy jest OPENAI_API_KEY)
try:
    from openai import OpenAI  # type: ignore
except Exception:  # brak SDK nie powinien psuć regexowego fallbacku
    OpenAI = None  # type: ignore

# Langfuse (opcjonalny)
try:
    from langfuse.decorators import observe, langfuse_context  # type: ignore
except Exception:
    def observe(name: Optional[str] = None):
        def _decorator(func):
            return func
        return _decorator

    class _DummyCtx:
        @staticmethod
        def update_current_observation(**kwargs):  # no-op
            pass

        @staticmethod
        def update_current_trace(**kwargs):  # no-op
            pass

    langfuse_context = _DummyCtx()  # type: ignore

# ----------------------------
# Helpers
# ----------------------------

def _norm(s: str) -> str:
    """Lowercase + usunięcie ogonków (mężczyzna == mezczyzna)."""
    s = (s or "").lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _time_str_to_seconds(ts: str) -> Optional[int]:
    """Konwersja 'MM:SS' lub 'H:MM:SS' na sekundy."""
    try:
        parts = [int(p) for p in ts.split(":")]
        if len(parts) == 2:
            mm, ss = parts
            return mm * 60 + ss
        if len(parts) == 3:
            hh, mm, ss = parts
            return hh * 3600 + mm * 60 + ss
    except Exception:
        return None
    return None


def _accept_5k_range(sec: Optional[int]) -> Optional[int]:
    """Akceptuj tylko sensowne czasy 5 km (9–60 minut)."""
    if sec is None:
        return None
    return sec if (9 * 60) <= sec <= (60 * 60) else None


# ----------------------------
# Regexowy fallback (szybki i darmowy)
# ----------------------------

def _preparse_quick(text: str) -> Dict[str, Optional[int | str]]:
    """
    Szybka ekstrakcja bez LLM.
    Rozpoznaje:
      - płeć (PL/EN: mężczyzna/kobieta, m/k, male/female, man/men/woman)
      - wiek (np. '32 lata')
      - czas 5km: 'MM:SS', 'H:MM:SS', '27 minut', także w kontekście '5km ...'
    Odrzuca czasy poza zakresem 9–60 min.
    """
    t = _norm(text)
    out: Dict[str, Optional[int | str]] = {
        "gender": None,
        "age": None,
        "time_5km_seconds": None,
    }

    # --- GENDER ---
    # uwzględniamy 'men' (częsty skrót), 'm', 'k', itp.
    if re.search(r"\b(m|mezczyzna|facet|chlopak|male|man|men)\b", t):
        out["gender"] = "male"
    elif re.search(r"\b(k|kobieta|female|woman|dziewczyna)\b", t):
        out["gender"] = "female"

    # --- AGE ---
    m = re.search(r"\b(\d{1,2})\s*(?:lat|rok|lata|r\.|years?|yo)\b", t)
    if m:
        age = int(m.group(1))
        if 10 < age < 100:
            out["age"] = age

    # --- TIME preferencyjnie w kontekście 5 km ---
    # 5km ... 22:30
    m = re.search(r"(?:\b5\s*km\b|\b5k\b)\D{0,20}(\d{1,2}:\d{2}(?::\d{2})?)\b", t)
    if m:
        out["time_5km_seconds"] = _accept_5k_range(_time_str_to_seconds(m.group(1)))

    # 5km ... 27 minut
    if not out["time_5km_seconds"]:
        m = re.search(r"(?:\b5\s*km\b|\b5k\b)\D{0,20}\b(\d{1,3})\s*(?:min(?:ut(?:y|a)?)?\.?)\b", t)
        if m:
            out["time_5km_seconds"] = _accept_5k_range(int(m.group(1)) * 60)

    # --- TIME – ogólny fallback (poza kontekstem 5 km) ---
    if not out["time_5km_seconds"]:
        m = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", t)
        if m:
            out["time_5km_seconds"] = _accept_5k_range(_time_str_to_seconds(m.group(1)))

    if not out["time_5km_seconds"]:
        m = re.search(r"\b(\d{1,3})\s*(?:min(?:ut(?:y|a)?)?\.?)\b", t)
        if m:
            out["time_5km_seconds"] = _accept_5k_range(int(m.group(1)) * 60)

    return out


# ----------------------------
# LLM (opcjonalnie; z cache; bezpieczne gdy brak klucza)
# ----------------------------

_client: Optional["OpenAI"] = None  # type: ignore


def _get_openai_client():
    """Inicjalizacja klienta OpenAI. Zwraca None, jeśli brak klucza/SDK."""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None

    try:
        _client = OpenAI(api_key=api_key, timeout=30.0, max_retries=2)  # type: ignore
    except TypeError as e:
        # starsze SDK – bez paramów
        if "proxies" in str(e):
            _client = OpenAI(api_key=api_key)  # type: ignore
        else:
            return None
    return _client


# Cache dla LLM
@lru_cache(maxsize=100)
def _cached_llm_call(text: str, model: str) -> str:
    """
    Cached call do LLM. Gdy brak klienta/klucza – zwraca pusty string.
    """
    client = _get_openai_client()
    if client is None:
        return ""

    system_prompt = (
        "Jesteś asystentem do ekstrakcji danych dla predyktora czasu półmaratonu.\n\n"
        "Wydobądź następujące informacje z tekstu użytkownika:\n"
        "- gender: \"male\" lub \"female\" (wymagane)\n"
        "- age: liczba całkowita, wiek w latach (wymagane)\n"
        "- time_5km_seconds: czas na 5km w SEKUNDACH jako liczba całkowita (wymagane)\n\n"
        "Zwróć TYLKO poprawny JSON:\n"
        "{\"gender\": \"male\"|\"female\"|null, \"age\": int|null, \"time_5km_seconds\": int|null}\n\n"
        "Przykłady:\n"
        "Input: \"M 30 lat, 5km 24:30\"\n"
        "Output: {\"gender\": \"male\", \"age\": 30, \"time_5km_seconds\": 1470}\n\n"
        "Input: \"Kobieta 28 lat, 5k w 27 minut\"\n"
        "Output: {\"gender\": \"female\", \"age\": 28, \"time_5km_seconds\": 1620}"
    )

    try:
        resp = client.chat.completions.create(  # type: ignore
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=150,
        )
        return resp.choices[0].message.content or ""
    except Exception:
        return ""


@observe(name="llm_data_extraction")
def extract_user_data(text: str) -> Dict[str, Optional[int | str]]:
    """
    Ekstrakcja z użyciem LLM (gdy dostępny). Zawiera walidację zakresów.
    Zwraca puste pola, jeśli LLM niedostępny/błąd – aby fallback mógł działać.
    """
    out: Dict[str, Optional[int | str]] = {
        "gender": None,
        "age": None,
        "time_5km_seconds": None,
    }

    try:
        try:
            langfuse_context.update_current_observation(  # type: ignore
                input=text, metadata={"task": "data_extraction", "input_length": len(text)}
            )
        except Exception:
            pass

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response_text = _cached_llm_call(text, model)
        if not response_text:
            # brak LLM – wracamy z pustymi polami
            return out

        # Wyciągnij JSON
        m = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not m:
            return out

        data = json.loads(m.group())

        # gender
        g = str(data.get("gender") or "").lower()
        if g in {"male", "m", "man", "men", "mezczyzna"}:
            out["gender"] = "male"
        elif g in {"female", "f", "woman", "kobieta"}:
            out["gender"] = "female"

        # age
        try:
            age = int(data.get("age"))
            if 15 <= age <= 90:
                out["age"] = age
        except Exception:
            pass

        # time
        try:
            t5 = int(data.get("time_5km_seconds"))
            out["time_5km_seconds"] = _accept_5k_range(t5)
        except Exception:
            pass

        try:
            langfuse_context.update_current_observation(  # type: ignore
                output=out, metadata={"model": model, "success": all(out.values()), "cached": True}
            )
        except Exception:
            pass

    except Exception as e:
        print(f"[llm_extractor] LLM error: {e}")
        try:
            langfuse_context.update_current_observation(  # type: ignore
                output={"error": str(e)}, metadata={"success": False}
            )
        except Exception:
            pass

    return out


def extract_user_data_auto(text: str) -> Dict[str, Optional[int | str]]:
    """
    Warstwa 1: szybki REGEX.
    Warstwa 2: LLM tylko dla braków (jeśli dostępny).
    """
    quick = _preparse_quick(text)
    if all(quick.values()):
        return quick

    llm = extract_user_data(text)

    return {
        "gender": quick["gender"] or llm.get("gender"),
        "age": quick["age"] or llm.get("age"),
        "time_5km_seconds": quick["time_5km_seconds"] or llm.get("time_5km_seconds"),
    }


def clear_llm_cache():
    """Wyczyść cache LLM (użyj np. po zmianie modelu)."""
    _cached_llm_call.cache_clear()
    print("✅ LLM cache wyczyszczony")
