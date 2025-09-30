# utils/input_parser.py
import re
from typing import Optional, Dict, Any, Tuple

_GENDER_SYNONYMS = {
    # male
    "m": "male", "m.": "male", "mezczyzna": "male", "mężczyzna": "male",
    "facet": "male", "chłopak": "male", "chlopak": "male",
    "male": "male", "man": "male",
    # female
    "k": "female", "k.": "female", "kobieta": "female",
    "female": "female", "woman": "female",
}

def _norm(s: str) -> str:
    # prosty lowercase + usunięcie ogonków PL
    s = s.lower()
    s = (s
         .replace("ą","a").replace("ć","c").replace("ę","e")
         .replace("ł","l").replace("ń","n").replace("ó","o")
         .replace("ś","s").replace("ż","z").replace("ź","z"))
    return s

def _parse_gender(text: str) -> Optional[str]:
    t = _norm(text)
    # typowe szybkie trafienia na początku
    m = re.search(r"\b(m|m\.|mezczyzna|chlopak|facet|male|man)\b", t)
    if m: return "male"
    f = re.search(r"\b(k|k\.|kobieta|female|woman)\b", t)
    if f: return "female"
    # pojedyncze litery na starcie wpisu, np. "M 32 lata"
    head = _norm(text.split(",",1)[0]).strip()
    if head in _GENDER_SYNONYMS:
        return _GENDER_SYNONYMS[head]
    return None

def _parse_age(text: str) -> Optional[int]:
    # wzorce: "30 lat", "30l", "wiek 30", "mam 30", "age 30"
    t = _norm(text)
    for pat in [
        r"\b(\d{1,2})\s*(lat|l)\b",
        r"\b(wiek|age|mam)\s*[:=]?\s*(\d{1,2})\b",
        r"\b(\d{1,2})\b",  # ostatnia deska ratunku
    ]:
        m = re.search(pat, t)
        if m:
            # numer moze byc w grupie 1 albo 2 zależnie od wzorca
            groups = [g for g in m.groups() if g and g.isdigit()]
            if groups:
                age = int(groups[0])
                if 15 <= age <= 90:
                    return age
    return None

def _hms_to_seconds(h: int, m: int, s: int) -> int:
    return h*3600 + m*60 + s

def _parse_time_5k(text: str) -> Optional[int]:
    """
    Łapie:
      - '5 km 24:30', '5km 24:30', 'czas 5k 00:24:30'
      - same czasy '24:30' lub '1:05:00' (preferencyjnie te najbliżej '5k')
    """
    t = _norm(text)

    # 1) preferuj czas w poblizu '5k'/'5 km'
    near_5k = re.search(r"(5\s*km|5k)\D{0,15}(\d{1,2}:\d{2}(?::\d{2})?)", t)
    if near_5k:
        val = near_5k.group(2)
        return _time_str_to_seconds(val)

    # 2) ogólne czasy w tekscie (pierwszy sensowny)
    m = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", t)
    if m:
        return _time_str_to_seconds(m.group(1))

    return None

def _time_str_to_seconds(ts: str) -> Optional[int]:
    parts = ts.split(":")
    try:
        if len(parts) == 2:
            mm, ss = map(int, parts)
            return _hms_to_seconds(0, mm, ss)
        if len(parts) == 3:
            hh, mm, ss = map(int, parts)
            return _hms_to_seconds(hh, mm, ss)
    except ValueError:
        return None
    return None

def parse_free_text(s: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Zwraca (wynik, braki)
    wynik: {'gender': 'male'/'female', 'age': int, 'time_5km_seconds': int}
    braki: dict z kluczami brakujących pól i podpowiedziami
    """
    result: Dict[str, Any] = {}
    missing: Dict[str, str] = {}

    g = _parse_gender(s)
    if g: result["gender"] = g
    else:
        missing["gender"] = "Podaj M/K, mężczyzna/kobieta, male/female"

    a = _parse_age(s)
    if a is not None: result["age"] = a
    else:
        missing["age"] = "Podaj wiek (15–90 lat), np. '30 lat'"

    t5 = _parse_time_5k(s)
    if t5 is not None: result["time_5km_seconds"] = t5
    else:
        missing["time_5km_seconds"] = "Podaj czas 5 km, np. '5 km 24:30'"

    return result, missing
