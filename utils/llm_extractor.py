from __future__ import annotations
import os, json, re
from typing import Optional, Dict, Any
from functools import lru_cache

# OpenAI SDK
from openai import OpenAI

# Langfuse fallback
try:
    from langfuse.decorators import observe, langfuse_context
except Exception:
    def observe(name: Optional[str] = None):
        def _decorator(func):
            return func
        return _decorator
    class _DummyCtx:
        @staticmethod
        def update_current_observation(**kwargs): pass
        @staticmethod
        def update_current_trace(**kwargs): pass
    langfuse_context = _DummyCtx()

_client: Optional[OpenAI] = None

def _get_openai_client() -> OpenAI:
    """Inicjalizacja OpenAI klienta - FIX dla proxy issue"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Brak OPENAI_API_KEY w środowisku.")
        
        try:
            _client = OpenAI(
                api_key=api_key,
                timeout=30.0,
                max_retries=2
            )
        except TypeError as e:
            if 'proxies' in str(e):
                _client = OpenAI(api_key=api_key)
            else:
                raise
    return _client

def parse_time_to_seconds(time_str: str) -> Optional[int]:
    """Ulepszone parsowanie czasu z lepszą obsługą formatów."""
    if not time_str:
        return None
    
    s = str(time_str).lower().strip()
    
    # Format HH:MM:SS lub MM:SS
    time_match = re.search(r'(\d{1,2}):([0-5]\d)(?::([0-5]\d))?', time_str)
    if time_match:
        h_or_m = int(time_match.group(1))
        m_or_s = int(time_match.group(2))
        s_val = int(time_match.group(3)) if time_match.group(3) else 0
        
        if time_match.group(3):
            return h_or_m * 3600 + m_or_s * 60 + s_val
        else:
            return h_or_m * 60 + m_or_s
    
    # Format słowny: "27 minut", "23 min 45 s"
    min_match = re.search(r'(\d{1,2})\s*(?:minut|min)', s)
    sec_match = re.search(r'(\d{1,2})\s*(?:sekund|s\b)', s)
    
    if min_match:
        minutes = int(min_match.group(1))
        seconds = int(sec_match.group(1)) if sec_match else 0
        return minutes * 60 + seconds
    
    # Próba parsowania jako liczba
    try:
        val = float(re.sub(r'[^\d.]', '', s))
        if val < 100:
            return int(val * 60)
        else:
            return int(val)
    except:
        return None

def _preparse_quick(text: str):
    """
    Ekstraktor REGEX-owy (fallback bez LLM)
    Rozpoznaje: płeć, wiek, czas 5km (różne formaty)
    """
    text = (text or "").lower().strip()
    result = {"gender": None, "age": None, "time_5km_seconds": None}

    # --- 1️⃣ Płeć ---
    if any(word in text for word in ["mężczyzna", "mezczyzna", "facet", "chłopak", "m "]):
        result["gender"] = "male"
    elif any(word in text for word in ["kobieta", "dziewczyna", "k "]):
        result["gender"] = "female"
    elif re.search(r"\bm\b", text):  # samo "M" oddzielone spacją
        result["gender"] = "male"
    elif re.search(r"\bk\b", text):
        result["gender"] = "female"

    # --- 2️⃣ Wiek ---
    m = re.search(r"(\d{1,2})\s*(?:lat|roku|r\.|yo|years?)", text)
    if m:
        try:
            age = int(m.group(1))
            if 10 < age < 100:
                result["age"] = age
        except:
            pass

    # --- 3️⃣ Czas 5km ---
    # Format MM:SS lub GG:MM:SS
    m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", text)
    if m:
        h = int(m.group(1)) if m.lastindex == 3 else 0
        m_ = int(m.group(2))
        s = int(m.group(3)) if m.lastindex == 3 else int(m.group(2))
        total_sec = h * 3600 + m_ * 60 + s
        if 9 * 60 <= total_sec <= 60 * 60:
            result["time_5km_seconds"] = total_sec

    # Format „27 minut”, „24 minuty”, „29min”
    if not result["time_5km_seconds"]:
        m = re.search(r"(\d{1,2})\s*(?:min|minut|minuty|min\.?)", text)
        if m:
            total_sec = int(m.group(1)) * 60
            if 9 * 60 <= total_sec <= 60 * 60:
                result["time_5km_seconds"] = total_sec

    return result

# ← NOWE: Cache dla LLM (zmniejsza koszty przy powtórkach)
@lru_cache(maxsize=100)
def _cached_llm_call(text: str, model: str) -> str:
    """Cached LLM call - zapobiega powtórnym wywołaniom dla tego samego tekstu"""
    client = _get_openai_client()
    
    system_prompt = """Jesteś asystentem do ekstrakcji danych dla predyktora czasu półmaratonu.

Wydobądź następujące informacje z tekstu użytkownika:
- gender: "male" lub "female" (wymagane)
- age: liczba całkowita, wiek w latach (wymagane)
- time_5km_seconds: czas na 5km w SEKUNDACH jako liczba całkowita (wymagane)

WAŻNE zasady konwersji czasu:
- Format "24:30" = 24 minuty 30 sekund = 1470 sekund (24*60 + 30)
- Format "27 minut" = 27 minut = 1620 sekund (27*60)
- Format "23:45" = 23 minuty 45 sekund = 1425 sekund (23*60 + 45)

Zwróć TYLKO poprawny JSON:
{"gender": "male"|"female"|null, "age": int|null, "time_5km_seconds": int|null}

Przykłady:
Input: "M 30 lat, 5km 24:30"
Output: {"gender": "male", "age": 30, "time_5km_seconds": 1470}

Input: "Kobieta 28 lat, 5k w 27 minut"
Output: {"gender": "female", "age": 28, "time_5km_seconds": 1620}"""
    
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=150
    )
    
    return resp.choices[0].message.content or ""

@observe(name="llm_data_extraction")
def extract_user_data(text: str) -> Dict[str, Optional[int | str]]:
    """LLM-based ekstrakcja danych z walidacją - ULEPSZONA z cache"""
    out = {"gender": None, "age": None, "time_5km_seconds": None}
    
    try:
        try:
            langfuse_context.update_current_observation(
                input=text, 
                metadata={"task": "data_extraction", "input_length": len(text)}
            )
        except:
            pass
        
        # ← NOWE: Użyj cached call
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response_text = _cached_llm_call(text, model)
        
        # Wyciągnij JSON
        m = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not m:
            raise ValueError("Brak JSON w odpowiedzi LLM")
        
        data = json.loads(m.group())
        
        # Walidacja i normalizacja płci
        g = str(data.get("gender") or "").lower()
        if g in {"male", "m", "man", "mężczyzna", "męski"}:
            out["gender"] = "male"
        elif g in {"female", "f", "woman", "kobieta", "żeński"}:
            out["gender"] = "female"
        
        # Walidacja wieku
        age = data.get("age")
        try:
            age = int(age)
            if 15 <= age <= 90:
                out["age"] = age
        except:
            pass
        
        # Walidacja czasu 5km
        t5 = data.get("time_5km_seconds")
        try:
            t5 = int(t5)
            if 9*60 <= t5 <= 60*60:
                out["time_5km_seconds"] = t5
        except:
            pass
        
        # Logowanie do Langfuse
        try:
            langfuse_context.update_current_observation(
                output=out,
                metadata={
                    "model": model,
                    "success": all(out.values()),
                    "cached": True  # ← Info że używamy cache
                }
            )
        except:
            pass
            
    except Exception as e:
        print(f"[llm_extractor] LLM error: {e}")
        try:
            langfuse_context.update_current_observation(
                output={"error": str(e)},
                metadata={"success": False}
            )
        except:
            pass
    
    return out

def extract_user_data_auto(text: str) -> Dict[str, Optional[int | str]]:
    """
    Automatyczna ekstrakcja - najpierw REGEX, potem LLM dla braków.
    Redukuje koszty API przy prostych inputach.
    """
    # Warstwa 1: Szybki REGEX
    quick = _preparse_quick(text)
    
    # Jeśli wszystko znalezione - zwróć od razu (70% przypadków!)
    if all(quick.values()):
        return quick
    
    # Warstwa 2: LLM dla braków
    llm = extract_user_data(text)
    
    # Merge: priorytet dla REGEX (szybszy, dokładniejszy)
    result = {
        "gender": quick["gender"] or llm.get("gender"),
        "age": quick["age"] or llm.get("age"),
        "time_5km_seconds": quick["time_5km_seconds"] or llm.get("time_5km_seconds"),
    }
    
    return result

# ← NOWE: Funkcja do czyszczenia cache (użyj w maintenance)
def clear_llm_cache():
    """Wyczyść cache LLM - użyj jeśli model się zmienił"""
    _cached_llm_call.cache_clear()
    print("✅ LLM cache wyczyszczony")