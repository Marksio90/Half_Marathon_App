# utils/llm_extractor.py
from __future__ import annotations
import os, json, re
from typing import Optional, Dict, Any

# OpenAI SDK (>=1.0)
from openai import OpenAI

# ── Langfuse fallback (no-op) ────────────────────────────────────────────────
try:
    from langfuse.decorators import observe, langfuse_context  # type: ignore
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
        @staticmethod
        def update_current_span(**kwargs): pass
    langfuse_context = _DummyCtx()  # type: ignore

_client: Optional[OpenAI] = None
def _get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Brak OPENAI_API_KEY w środowisku.")
        _client = OpenAI(api_key=api_key)
    return _client

# ── Parser czasu (publiczny) ────────────────────────────────────────────────
def parse_time_to_seconds(time_str: str) -> Optional[int]:
    if not time_str:
        return None
    s = (
        time_str.lower()
        .replace("minutes", "min").replace("minute", "min")
        .replace("minuty", "min").replace("minut", "min").replace("min.", "min")
        .replace("sekundy", "s").replace("sekund", "s")
        .replace("seconds", "s").replace("second", "s")
        .strip()
    )
    # HH:MM:SS lub MM:SS
    if ":" in s:
        parts = [p for p in s.split(":") if p != ""]
        try:
            if len(parts) == 2:
                mm, ss = int(parts[0]), int(parts[1])
                return mm * 60 + ss
            if len(parts) == 3:
                hh, mm, ss = int(parts[0]), int(parts[1]), int(parts[2])
                return hh * 3600 + mm * 60 + ss
        except Exception:
            pass
    # "23 min 45 s", "23m 45s"
    m = re.search(r"(?P<m>\d+)\s*m(in)?\b", s)
    sec = re.search(r"(?P<s>\d+)\s*s(ec)?\b", s)
    if m and sec:
        try:
            return int(m.group("m")) * 60 + int(sec.group("s"))
        except Exception:
            pass
    if m:
        try:
            return int(m.group("m")) * 60
        except Exception:
            pass
    if sec:
        try:
            return int(sec.group("s"))
        except Exception:
            pass
    # Liczba: <100 → minuty, >=100 → sekundy
    try:
        val = float(re.sub(r"[^\d.]", "", s))
        return int(val * 60) if val < 100 else int(val)
    except Exception:
        return None

# ── Szybki parser REGEX (PL/EN) ─────────────────────────────────────────────
def _preparse_quick(text: str) -> Dict[str, Optional[int | str]]:
    t = " " + (text or "").lower() + " "
    out: Dict[str, Optional[int | str]] = {
        "gender": None, "age": None, "time_5km_seconds": None
    }

    # Płeć: wzorce bez fałszywych pozytywów na 'm' (np. "mam")
    if re.search(r"\bpłe[ćc]\s*[:=]?\s*m\b", t) or re.search(r"\bmężczyzn\w+|\bmęsk\w+|\bfacet\b|\bchłopak\b|\bpan\b|\bmale\b", t):
        out["gender"] = "male"
    elif re.search(r"\bpłe[ćc]\s*[:=]?\s*k\b", t) or re.search(r"\bkobiet\w+|\bżeńsk\w+|\bdziewczyn\w+|\bpani\b|\bfemale\b", t):
        out["gender"] = "female"
    else:
        # pojedyncze M/K na początku wyrazu
        if re.search(r"\b[Mm]\b", text) and not out["gender"]:
            out["gender"] = "male"
        if re.search(r"\b[Kk]\b", text) and not out["gender"]:
            out["gender"] = "female"

    # Wiek: "30-letni/a", "30 lat", "lat 30"
    age_patterns = [
        r"(\d{1,2})\s*-\s*letni[aeym]?",
        r"(\d{1,2})\s*(?:lat|lata|roku|r\.|yo|y/o)\b",
        r"\blat\s*(\d{1,2})\b",
    ]
    for pat in age_patterns:
        m = re.search(pat, t)
        if m:
            try:
                age = int(m.group(1))
                if 15 <= age <= 90:
                    out["age"] = age
                    break
            except Exception:
                pass

    # Czas 5 km: priorytet dla formatu z dwukropkiem
    colon = re.search(r"(?<!\d)(\d{1,2}):([0-5]\d)(?::([0-5]\d))?", t)
    if colon:
        h = int(colon.group(1))
        m = int(colon.group(2))
        s = int(colon.group(3)) if colon.group(3) else 0
        out["time_5km_seconds"] = h * 3600 + m * 60 + s if colon.group(3) else h * 60 + m
    else:
        # słowna forma: "27 min", "23 min 45 s", "23m45s"
        m1 = re.search(r"(\d{1,2})\s*min(?:ut[ay]?)?\s*(\d{1,2})?\s*s?", t)
        if m1:
            mm = int(m1.group(1))
            ss = int(m1.group(2)) if m1.group(2) else 0
            out["time_5km_seconds"] = mm * 60 + ss
        else:
            m2 = re.search(r"(\d+)\s*s(ec)?\b", t)
            if m2:
                out["time_5km_seconds"] = int(m2.group(1))
            else:
                # "24.5 min"
                m3 = re.search(r"(\d{1,2}(?:[.,]\d+)?)\s*min", t)
                if m3:
                    val = float(m3.group(1).replace(",", "."))
                    out["time_5km_seconds"] = int(round(val * 60))

    # sanity check czasu
    if out["time_5km_seconds"] is not None:
        if not (9 * 60 <= int(out["time_5km_seconds"]) <= 60 * 60):
            out["time_5km_seconds"] = None

    return out

# ── LLM ekstrakcja (jak dotychczas) ─────────────────────────────────────────
@observe(name="llm_data_extraction")
def extract_user_data(text: str) -> Dict[str, Optional[int | str]]:
    """LLM-only extractor (pozostawiony dla kompatybilności)."""
    system_prompt = """Jesteś asystentem ekstrakcji danych dla systemu predykcji półmaratonu.
Twoim zadaniem jest wydobycie: gender (male/female), age (int), time_5km_seconds (int).
Zwróć TYLKO obiekt JSON o strukturze:
{"gender": "male"|"female"|null, "age": int|null, "time_5km_seconds": int|null}"""
    out = {"gender": None, "age": None, "time_5km_seconds": None}
    try:
        try:
            langfuse_context.update_current_observation(input=text, metadata={"task": "data_extraction"})
        except Exception:
            pass

        client = _get_openai_client()
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":text}],
            temperature=0.1, max_tokens=200
        )
        response_text = (resp.choices[0].message.content or "").strip()
        m = re.search(r"\{.*\}", response_text, re.DOTALL)
        data = json.loads(m.group() if m else response_text)

        # normalizacja
        g = str(data.get("gender") or "").lower()
        if g in {"male","m","man","mężczyzna","męski"}:
            out["gender"] = "male"
        elif g in {"female","f","woman","kobieta","żeński"}:
            out["gender"] = "female"

        a = data.get("age")
        try:
            a = int(a)
            if 15 <= a <= 90:
                out["age"] = a
        except Exception:
            pass

        t5 = data.get("time_5km_seconds")
        try:
            t5 = int(t5)
            if 9*60 <= t5 <= 60*60:
                out["time_5km_seconds"] = t5
        except Exception:
            pass

        try:
            used_tokens = getattr(getattr(resp, "usage", None), "total_tokens", None)
            langfuse_context.update_current_observation(output=out, metadata={"tokens_used": used_tokens})
        except Exception:
            pass
    except Exception as e:
        print(f"[llm_extractor] LLM error: {e}")
    return out

# ── GŁÓWNA FUNKCJA: automat (regex ➜ LLM ➜ merge) ──────────────────────────
def extract_user_data_auto(text: str) -> Dict[str, Optional[int | str]]:
    """
    Warstwa 1: szybki regex (lokalny, bez kosztów)
    Warstwa 2: LLM uzupełnia tylko braki
    Zwraca pełny wynik, jeśli to możliwe.
    """
    quick = _preparse_quick(text)
    if all(quick.values()):
        return quick

    llm = extract_user_data(text)  # uzupełnij braki
    result = {
        "gender": quick["gender"] or llm.get("gender"),
        "age": quick["age"] or llm.get("age"),
        "time_5km_seconds": quick["time_5km_seconds"] or llm.get("time_5km_seconds"),
    }
    return result
