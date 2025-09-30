# app.py - FIXED VERSION
import os
import sys

# KRYTYCZNE: Ustaw zmienne środowiskowe PRZED jakimkolwiek importem Streamlit
os.environ.setdefault('STREAMLIT_SERVER_HEADLESS', 'true')
os.environ.setdefault('STREAMLIT_SERVER_PORT', '8080')
os.environ.setdefault('STREAMLIT_SERVER_ADDRESS', '0.0.0.0')

# Załaduj zmienne środowowiskowe z .env (tylko jeśli lokalnie)
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

import streamlit as st
from datetime import datetime

# KRYTYCZNE: Cache'uj importy modułów
@st.cache_resource
def get_predictor():
    """Inicjalizacja predyktora - tylko raz"""
    from utils.model_predictor import HalfMarathonPredictor
    return HalfMarathonPredictor()

@st.cache_resource
def get_extractor():
    """Import ekstraktora - tylko raz"""
    from utils.llm_extractor import extract_user_data_auto
    return extract_user_data_auto

# Langfuse shim - bezpieczny import
try:
    from utils.langfuse_shim import observe, langfuse_context, langfuse
except Exception:
    # Fallback jeśli brak langfuse
    def observe(name=None):
        def decorator(func):
            return func
        return decorator
    
    class DummyContext:
        @staticmethod
        def update_current_trace(**kwargs):
            pass
    
    langfuse_context = DummyContext()
    langfuse = None

# Konfiguracja strony
st.set_page_config(
    page_title="Predykcja Czasu Półmaratonu",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if 'prediction_history' not in st.session_state:
    st.session_state.prediction_history = []
if 'initialized' not in st.session_state:
    st.session_state.initialized = True

# CSS Styles
st.markdown("""
    <style>
    .main-header {font-size:3rem;font-weight:bold;text-align:center;color:#1E88E5;margin-bottom:1rem;}
    .sub-header {font-size:1.2rem;text-align:center;color:#555;margin-bottom:2rem;}
    .prediction-box {background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:2rem;border-radius:15px;color:white;text-align:center;margin:2rem 0;}
    .prediction-time {font-size:3.5rem;font-weight:bold;margin:1rem 0;}
    .info-box {background-color:#f0f2f6;padding:1.5rem;border-radius:10px;margin:1rem 0;}
    .stButton>button {width:100%;background-color:#1E88E5;color:white;font-size:1.1rem;padding:0.75rem;border-radius:10px;border:none;font-weight:bold;}
    .stButton>button:hover {background-color:#1565C0;}
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🏃 Predyktor Czasu Półmaratonu</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Przewidź swój czas ukończenia półmaratonu używając AI i uczenia maszynowego</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📊 O aplikacji")
    st.info("""
    Aplikacja przewiduje czas półmaratonu na podstawie:
    - Płci
    - Wieku
    - Najlepszego czasu na 5km
    """)
    st.header("🎯 Jak używać")
    st.markdown("Wpisz dane w jednym zdaniu, np.: **„M 30 lat, 5 km 24:30"**.")
    st.header("📈 Wydajność modelu")
    st.metric("Średni błąd bezwzględny", "~4,5 minuty")
    st.metric("Wynik R²", "0,92")
    
    if st.session_state.prediction_history:
        st.header("📜 Historia")
        st.write(f"Wykonanych predykcji: {len(st.session_state.prediction_history)}")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Powiedz nam o sobie")
    with st.expander("💡 Przykładowe dane (kliknij aby zobaczyć)"):
        st.code(
            'M 32 lata, 5 km 23:45\n'
            'Kobieta 28 lat, 5km w 27 minut\n'
            'Mężczyzna 45 lat, rekord na 5km: 22:30'
        )
    
    user_input = st.text_area(
        "Opisz siebie:",
        placeholder="np. M 30 lat, 5 km 24:30",
        height=120
    )
    
    predict_button = st.button("🚀 Przewiduj Mój Czas", type="primary")

with col2:
    st.header("ℹ️ Wymagane informacje")
    st.markdown("""
    <div class="info-box">
        <ul>
            <li>👤 Płeć (mężczyzna/kobieta lub M/K)</li>
            <li>🎂 Wiek (15–90 lat)</li>
            <li>⏱️ Czas na 5km (MM:SS lub GG:MM:SS, np. 24:30)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Prediction logic
if predict_button:
    if not user_input.strip():
        st.error("❌ Proszę wprowadzić informacje o sobie!")
    else:
        with st.spinner("🤖 Analizuję Twoje dane..."):
            try:
                # Get cached functions
                extract_user_data_auto = get_extractor()
                predictor = get_predictor()
                
                # Extract data
                @observe(name="user_data_extraction_auto")
                def do_extract(text):
                    try:
                        if langfuse_context:
                            langfuse_context.update_current_trace(
                                user_id=f"user_{datetime.now().timestamp()}",
                                metadata={"input_length": len(text)}
                            )
                    except Exception:
                        pass
                    return extract_user_data_auto(text)

                extracted_data = do_extract(user_input)

                # Validate extraction
                if not all([
                    extracted_data.get('gender'),
                    extracted_data.get('age'),
                    extracted_data.get('time_5km_seconds')
                ]):
                    st.error("⛔ Nie udało się automatycznie wyodrębnić wszystkich danych. "
                             "Podaj je w jednym zdaniu, np.: **„M 30 lat, 5 km 24:30"**.")
                    st.stop()

                # Predict
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
                                metadata={"success": False}
                            )
                        except Exception:
                            pass
                    st.stop()

                if prediction.get('success'):
                    # Display prediction
                    st.markdown(f"""
                    <div class="prediction-box">
                        <h2>🎯 Twój Przewidywany Czas Półmaratonu</h2>
                        <div class="prediction-time">{prediction['formatted_time']}</div>
                        <p style="font-size: 1.2rem;">Na podstawie automatycznie rozpoznanego profilu</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.success("✅ Dane rozpoznane automatycznie!")
                    
                    # Display extracted data
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Płeć", "Mężczyzna" if extracted_data['gender'] == 'male' else "Kobieta")
                    with col_b:
                        st.metric("Wiek", f"{extracted_data['age']} lat")
                    with col_c:
                        t5 = extracted_data['time_5km_seconds']
                        st.metric("Czas 5km", f"{t5//60}:{t5%60:02d}")

                    # Performance analysis
                    st.header("📊 Analiza wydajności")
                    col_x, col_y = st.columns(2)
                    
                    with col_x:
                        st.markdown('<div class="info-box"><h4>📈 Informacje o tempie</h4></div>', unsafe_allow_html=True)
                        avg_pace = prediction['prediction_seconds'] / 21.0975
                        st.write(f"**Średnie tempo**: {int(avg_pace//60)}:{int(avg_pace%60):02d} min/km")
                        pace_5k = t5 / 5
                        st.write(f"**Tempo na 5km**: {int(pace_5k//60)}:{int(pace_5k%60):02d} min/km")
                    
                    with col_y:
                        st.markdown('<div class="info-box"><h4>💪 Wskazówki treningowe</h4></div>', unsafe_allow_html=True)
                        if prediction['prediction_seconds'] < 5400:
                            st.write("🏆 Elitarny biegacz! Skup się na utrzymaniu konsystencji.")
                        elif prediction['prediction_seconds'] < 7200:
                            st.write("💪 Świetna forma! Rozważ trening interwałowy.")
                        else:
                            st.write("🎯 Dobry cel! Skup się na budowaniu wytrzymałości.")

                    # Save to history
                    st.session_state.prediction_history.append({
                        'timestamp': datetime.now(),
                        'input': user_input,
                        'prediction': prediction['formatted_time'],
                        'data': extracted_data
                    })
                    
                    # Log to Langfuse
                    if langfuse:
                        try:
                            langfuse.trace(
                                name="halfmarathon_prediction_auto",
                                input=extracted_data,
                                output=prediction,
                                metadata={"mode": "auto", "success": True}
                            )
                        except Exception:
                            pass
                else:
                    st.error(f"❌ Błąd predykcji: {prediction.get('error', 'Nieznany błąd')}")

            except Exception as e:
                st.error(f"❌ Wystąpił błąd: {e}")
                if langfuse:
                    try:
                        langfuse.trace(
                            name="halfmarathon_prediction_error",
                            input={"user_input": user_input},
                            output={"error": str(e)},
                            metadata={"success": False}
                        )
                    except Exception:
                        pass

# Footer - ZAWSZE WIDOCZNY (poza blokiem if)
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 2rem;">
    <p>🏃 Predyktor Półmaratonu v2.0 | Zasilany przez XGBoost & OpenAI</p>
    <p>Wytrenowany na 20 000+ wynikach zawodów | Monitorowany przez Langfuse</p>
</div>
""", unsafe_allow_html=True)