# app.py
from __future__ import annotations

import os
import logging
from datetime import datetime

# --- Streamlit runtime configuration (ważne dla DigitalOcean) ---
port = os.getenv("PORT", "8080")
os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
os.environ["STREAMLIT_SERVER_PORT"] = port
os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("halfmarathon")
logger.info(
    "Using STREAMLIT port=%s address=%s",
    os.environ.get("STREAMLIT_SERVER_PORT"),
    os.environ.get("STREAMLIT_SERVER_ADDRESS"),
)

# Załaduj .env tylko lokalnie (nie w kontenerze prod – tam są env vars)
if os.path.exists(".env"):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

import streamlit as st

# --- Cache'owane importy (ważne dla szybkości i stabilności) ---
@st.cache_resource
def get_predictor():
    from utils.model_predictor import HalfMarathonPredictor
    return HalfMarathonPredictor()

@st.cache_resource
def get_extractor():
    from utils.llm_extractor import extract_user_data_auto
    return extract_user_data_auto

# Langfuse shim – bezpieczny import
try:
    from utils.langfuse_shim import observe, langfuse_context, langfuse
except Exception:
    def observe(name=None):
        def decorator(func):
            return func
        return decorator

    class _DummyContext:
        @staticmethod
        def update_current_trace(**kwargs): pass
        @staticmethod
        def update_current_observation(**kwargs): pass
    langfuse_context = _DummyContext()
    langfuse = None

# --- Konfiguracja strony ---
st.set_page_config(
    page_title="Predykcja Czasu Półmaratonu",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Session state ---
if "prediction_history" not in st.session_state:
    st.session_state.prediction_history = []
if "initialized" not in st.session_state:
    st.session_state.initialized = True
if "metrics" not in st.session_state:
    st.session_state.metrics = {
        "total_predictions": 0,
        "regex_only": 0,
        "llm_needed": 0,
        "ml_mode": 0,
        "fallback_mode": 0,
    }

# --- CSS ---
st.markdown(
    """
    <style>
    .main-header {font-size:3rem;font-weight:bold;text-align:center;color:#1E88E5;margin-bottom:1rem;}
    .sub-header {font-size:1.2rem;text-align:center;color:#555;margin-bottom:2rem;}
    .prediction-box {background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:2rem;border-radius:15px;color:white;text-align:center;margin:2rem 0;}
    .prediction-time {font-size:3.5rem;font-weight:bold;margin:1rem 0;}
    .info-box {background-color:#f0f2f6;padding:1.5rem;border-radius:10px;margin:1rem 0;}
    .warning-box {background-color:#fff3cd;border-left:4px solid #ffc107;padding:1rem;margin:1rem 0;}
    .stButton>button {width:100%;background-color:#1E88E5;color:white;font-size:1.1rem;padding:0.75rem;border-radius:10px;border:none;font-weight:bold;}
    .stButton>button:hover {background-color:#1565C0;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header ---
st.markdown('<div class="main-header">🏃 Predyktor Czasu Półmaratonu</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Przewidź swój czas ukończenia półmaratonu używając AI i uczenia maszynowego</div>', unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("📊 O aplikacji")
    st.info(
        """
        Aplikacja przewiduje czas półmaratonu na podstawie:
        - Płci
        - Wieku
        - Najlepszego czasu na 5km
        """
    )

    st.header("🎯 Jak używać")
    st.markdown('Wpisz dane w jednym zdaniu, np.: **"M 30 lat, 5 km 24:30"**.')

    st.header("📈 Wydajność modelu")
    st.metric("Średni błąd bezwzględny", "~4,5 minuty")
    st.metric("Wynik R²", "0,92")

    # Metryki użycia
    m = st.session_state.metrics
    if m["total_predictions"] > 0:
        st.header("📊 Statystyki")
        st.metric("Predykcje ogółem", m["total_predictions"])
        regex_pct = (m["regex_only"] / m["total_predictions"]) * 100
        st.metric("REGEX only", f"{m['regex_only']} ({regex_pct:.0f}%)")
        ml_pct = (m["ml_mode"] / m["total_predictions"]) * 100
        st.metric("Model ML", f"{m['ml_mode']} ({ml_pct:.0f}%)")

    if st.checkbox("🔧 Info o modelu"):
        predictor = get_predictor()
        st.json(predictor.model_metadata)

    if st.session_state.prediction_history:
        st.header("📜 Historia")
        st.write(f"Wykonanych predykcji: {len(st.session_state.prediction_history)}")
        if st.button("🗑️ Wyczyść historię"):
            st.session_state.prediction_history = []
            st.rerun()

# --- Main content ---
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Powiedz nam o sobie")
    with st.expander("💡 Przykładowe dane (kliknij aby zobaczyć)"):
        st.code(
            "M 32 lata, 5 km 23:45\n"
            "Kobieta 28 lat, 5km w 27 minut\n"
            "Mężczyzna 45 lat, rekord na 5km: 22:30"
        )

    user_input = st.text_area(
        "Opisz siebie:",
        placeholder="np. M 30 lat, 5 km 24:30",
        height=120,
    )

    predict_button = st.button("🚀 Przewiduj Mój Czas", type="primary")

with col2:
    st.header("ℹ️ Wymagane informacje")
    st.markdown(
        """
        <div class="info-box">
            <ul>
                <li>👤 Płeć (mężczyzna/kobieta lub M/K)</li>
                <li>🎂 Wiek (15–90 lat)</li>
                <li>⏱️ Czas na 5km (MM:SS lub GG:MM:SS, np. 24:30)</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Prediction logic ---
if predict_button:
    if not user_input.strip():
        st.error("❌ Proszę wprowadzić informacje o sobie!")
    else:
        with st.spinner("🤖 Analizuję Twoje dane..."):
            try:
                extract_user_data_auto = get_extractor()
                predictor = get_predictor()

                @observe(name="user_data_extraction_auto")
                def do_extract(text: str):
                    try:
                        if langfuse_context:
                            langfuse_context.update_current_trace(
                                user_id=f"user_{datetime.now().timestamp()}",
                                metadata={"input_length": len(text)},
                            )
                    except Exception:
                        pass
                    return extract_user_data_auto(text)

                extracted_data = do_extract(user_input)

                # Ustal, czy wystarczył regex
                from utils.llm_extractor import _preparse_quick
                quick_result = _preparse_quick(user_input)
                was_regex_only = all(quick_result.values())
                if was_regex_only:
                    st.session_state.metrics["regex_only"] += 1
                else:
                    st.session_state.metrics["llm_needed"] += 1

                # Podgląd rozpoznanych danych
                with st.expander("🔍 Rozpoznane dane", expanded=False):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        g_icon = "✅" if extracted_data.get("gender") else "❌"
                        g_text = extracted_data.get("gender", "BRAK")
                        st.metric("Płeć", f"{g_icon} {g_text}")
                    with col_b:
                        a_icon = "✅" if extracted_data.get("age") else "❌"
                        a_text = extracted_data.get("age", "BRAK")
                        st.metric("Wiek", f"{a_icon} {a_text}")
                    with col_c:
                        t_icon = "✅" if extracted_data.get("time_5km_seconds") else "❌"
                        if extracted_data.get("time_5km_seconds"):
                            t = extracted_data["time_5km_seconds"]
                            t_text = f"{t//60}:{t%60:02d}"
                        else:
                            t_text = "BRAK"
                        st.metric("Czas 5km", f"{t_icon} {t_text}")

                    if was_regex_only:
                        st.success("⚡ Dane rozpoznane przez REGEX (szybko, bez kosztów API)")
                    else:
                        st.info("🤖 Użyto LLM do ekstrakcji danych")

                # Walidacja kompletu danych
                if not all(
                    [
                        extracted_data.get("gender"),
                        extracted_data.get("age"),
                        extracted_data.get("time_5km_seconds"),
                    ]
                ):
                    st.error("⛔ Nie udało się automatycznie wyodrębnić wszystkich danych.")
                    missing = []
                    if not extracted_data.get("gender"):
                        missing.append("• **Płeć**: Podaj M/K, mężczyzna/kobieta, male/female")
                    if not extracted_data.get("age"):
                        missing.append("• **Wiek**: Podaj liczbę od 15 do 90 lat")
                    if not extracted_data.get("time_5km_seconds"):
                        missing.append("• **Czas 5km**: Podaj w formacie MM:SS (np. 24:30)")
                    st.markdown("**Brakujące informacje:**")
                    for m in missing:
                        st.markdown(m)
                    st.markdown('**Przykład poprawnego formatu:** *"M 30 lat, 5 km 24:30"*')
                    st.stop()

                # Predykcja
                try:
                    prediction = predictor.predict(extracted_data)
                except Exception as e:
                    st.error(f"❌ Błąd podczas predykcji: {e}")
                    if langfuse:
                        try:
                            langfuse.trace(
                                name="halfmarathon_prediction_runtime_error",
                                input=extracted_data,
                                output={"error": str(e)},
                                metadata={"success": False},
                            )
                        except Exception:
                            pass
                    st.stop()

                if prediction.get("success"):
                    # Metryki
                    st.session_state.metrics["total_predictions"] += 1
                    if prediction["details"]["mode"] == "ml":
                        st.session_state.metrics["ml_mode"] += 1
                    else:
                        st.session_state.metrics["fallback_mode"] += 1

                    # Wynik
                    st.markdown(
                        f"""
                        <div class="prediction-box">
                            <h2>🎯 Twój Przewidywany Czas Półmaratonu</h2>
                            <div class="prediction-time">{prediction['formatted_time']}</div>
                            <p style="font-size: 1.2rem;">Pewność predykcji: {prediction.get('confidence', 'Średnia')}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.success("✅ Dane rozpoznane automatycznie!")

                    # Podsumowanie danych
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Płeć", "Mężczyzna" if extracted_data["gender"] == "male" else "Kobieta")
                    with col_b:
                        st.metric("Wiek", f"{extracted_data['age']} lat")
                    with col_c:
                        t5 = extracted_data["time_5km_seconds"]
                        st.metric("Czas 5km", f"{t5//60}:{t5%60:02d}")

                    # Analiza tempa
                    st.header("📊 Analiza wydajności")
                    col_x, col_y = st.columns(2)

                    with col_x:
                        st.markdown('<div class="info-box"><h4>📈 Informacje o tempie</h4></div>', unsafe_allow_html=True)
                        avg_pace = prediction["prediction_seconds"] / 21.0975
                        st.write(f"**Średnie tempo**: {int(avg_pace//60)}:{int(avg_pace%60):02d} min/km")
                        pace_5k = t5 / 5
                        st.write(f"**Tempo na 5km**: {int(pace_5k//60)}:{int(pace_5k%60):02d} min/km")
                        pace_diff = avg_pace - pace_5k
                        if pace_diff > 30:
                            st.warning(f"⚠️ Spodziewaj się spowolnienia o ~{int(pace_diff)}s/km na półmaratonie")
                        elif pace_diff > 15:
                            st.info(f"ℹ️ Naturalne spowolnienie ~{int(pace_diff)}s/km na dłuższym dystansie")
                        else:
                            st.success(f"✅ Świetna stabilność tempa! (~{int(pace_diff)}s/km różnicy)")

                    with col_y:
                        st.markdown('<div class="info-box"><h4>💪 Wskazówki treningowe</h4></div>', unsafe_allow_html=True)
                        pred_min = prediction["prediction_seconds"] / 60
                        if pred_min < 90:
                            st.write("🏆 **Elitarny biegacz!**")
                            st.write("• Skup się na utrzymaniu konsystencji")
                            st.write("• Rozważ tempo runs 4:00-4:15 min/km")
                        elif pred_min < 120:
                            st.write("💪 **Świetna forma!**")
                            st.write("• Trening interwałowy 2x tydzień")
                            st.write("• Long runs 18-20km w weekendy")
                        elif pred_min < 150:
                            st.write("🎯 **Dobry cel!**")
                            st.write("• Buduj bazę aerobową (70% treningu)")
                            st.write("• Tempo runs 1x tydzień")
                        else:
                            st.write("🌱 **Świetny start!**")
                            st.write("• Skup się na regularności")
                            st.write("• Zwiększaj dystans o max 10% tygodniowo")

                    # Szczegóły techniczne
                    with st.expander("🔬 Szczegóły techniczne"):
                        st.write(f"**Tryb predykcji:** {prediction['details']['mode']}")
                        st.write(f"**Wersja modelu:** {prediction['details'].get('model_version', 'N/A')}")
                        st.write(f"**Źródło modelu:** {prediction['details'].get('model_source', 'N/A')}")
                        if "features_used" in prediction["details"]:
                            st.write(f"**Użyte cechy:** {prediction['details']['features_used']}")

                    # Zapis do historii
                    st.session_state.prediction_history.append(
                        {
                            "timestamp": datetime.now(),
                            "input": user_input,
                            "prediction": prediction["formatted_time"],
                            "data": extracted_data,
                            "mode": prediction["details"]["mode"],
                            "confidence": prediction.get("confidence", "N/A"),
                        }
                    )

                    # -------------------------------
                    # Eksport wyników (TXT / JSON)
                    # -------------------------------
                    import json as _json
                    from datetime import datetime as _dt

                    st.markdown("---")

                    _pred_seconds = prediction.get("prediction_seconds", None)
                    if _pred_seconds is not None:
                        _avg_pace_sec = _pred_seconds / 21.0975
                    else:
                        h, m, s = map(int, prediction["formatted_time"].split(":"))
                        _pred_seconds = h * 3600 + m * 60 + s
                        _avg_pace_sec = _pred_seconds / 21.0975

                    _avg_pace_txt = f"{int(_avg_pace_sec//60)}:{int(_avg_pace_sec%60):02d}"
                    _t5 = extracted_data["time_5km_seconds"]
                    _t5_txt = f"{_t5//60}:{_t5%60:02d}"
                    _gender_txt = "Mężczyzna" if extracted_data["gender"] == "male" else "Kobieta"

                    _result_text = f"""\
🏃 PREDYKCJA CZASU PÓŁMARATONU
==============================

DANE WEJŚCIOWE:
- Płeć: {_gender_txt}
- Wiek: {extracted_data['age']} lat
- Czas 5km: {_t5_txt}

PREDYKCJA:
- Czas: {prediction['formatted_time']}
- Średnie tempo: {_avg_pace_txt} min/km
- Pewność: {prediction.get('confidence', 'N/A')}
- Tryb: {prediction['details']['mode']}

Data: {_dt.now().strftime('%Y-%m-%d %H:%M')}
"""

                    _export_payload = {
                        "timestamp": _dt.now().isoformat(),
                        "input": extracted_data,
                        "prediction": prediction,
                        "user_input_raw": user_input,
                    }
                    _export_json = _json.dumps(_export_payload, indent=2, ensure_ascii=False)

                    col_save1, col_save2 = st.columns(2)
                    with col_save1:
                        st.download_button(
                            label="📥 Pobierz TXT",
                            data=_result_text,
                            file_name=f"predykcja_{_dt.now().strftime('%Y%m%d_%H%M')}.txt",
                            mime="text/plain",
                            key="dl_txt",
                            use_container_width=True,
                        )
                    with col_save2:
                        st.download_button(
                            label="📥 Pobierz JSON",
                            data=_export_json,
                            file_name=f"predykcja_{_dt.now().strftime('%Y%m%d_%H%M')}.json",
                            mime="application/json",
                            key="dl_json",
                            use_container_width=True,
                        )

                    # Log do Langfuse (opcjonalnie)
                    if langfuse:
                        try:
                            langfuse.trace(
                                name="halfmarathon_prediction_auto",
                                input=extracted_data,
                                output=prediction,
                                metadata={
                                    "mode": "auto",
                                    "success": True,
                                    "extraction_method": "regex" if was_regex_only else "llm",
                                    "prediction_mode": prediction["details"]["mode"],
                                },
                            )
                        except Exception:
                            pass

                else:
                    # Błąd predykcji z hints
                    error_msg = prediction.get("error", "Nieznany błąd")
                    hint = prediction.get("hint", "")
                    st.error(f"❌ Błąd predykcji: {error_msg}")
                    if hint:
                        st.markdown(
                            f"""
                            <div class="warning-box">
                                <strong>💡 Wskazówka:</strong><br>
                                {hint}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            except Exception as e:
                st.error(f"❌ Wystąpił błąd: {e}")
                import traceback
                with st.expander("🔍 Szczegóły błędu (dla debugowania)"):
                    st.code(traceback.format_exc())
                if langfuse:
                    try:
                        langfuse.trace(
                            name="halfmarathon_prediction_error",
                            input={"user_input": user_input},
                            output={"error": str(e)},
                            metadata={"success": False},
                        )
                    except Exception:
                        pass

# --- Footer ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; padding: 2rem;">
        <p>🏃 Predyktor Półmaratonu v2.1 | Zasilany przez XGBoost & OpenAI</p>
        <p>Wytrenowany na 20 000+ wynikach zawodów | Monitorowany przez Langfuse</p>
    </div>
    """,
    unsafe_allow_html=True,
)
