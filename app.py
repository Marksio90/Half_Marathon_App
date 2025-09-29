# Załaduj zmienne środowiskowe NA POCZĄTKU
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
import os
from datetime import datetime

from utils.llm_extractor import extract_user_data
from utils.model_predictor import HalfMarathonPredictor

# ✅ UŻYJ SHIMU ZAMIAST BEZPOŚREDNIEGO LANGFUSE
# (zapewnia no-op jeśli brakuje dekoratorów/metod lub całej biblioteki)
from utils.langfuse_shim import observe, langfuse_context, langfuse

# Konfiguracja strony
st.set_page_config(
    page_title="Predykcja Czasu Półmaratonu",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicjalizacja session state
if 'prediction_history' not in st.session_state:
    st.session_state.prediction_history = []

# Własne style CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #555;
        margin-bottom: 2rem;
    }
    .prediction-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 2rem 0;
    }
    .prediction-time {
        font-size: 3.5rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
        background-color: #1E88E5;
        color: white;
        font-size: 1.1rem;
        padding: 0.75rem;
        border-radius: 10px;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    </style>
""", unsafe_allow_html=True)

# Nagłówek
st.markdown('<div class="main-header">🏃 Predyktor Czasu Półmaratonu</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Przewidź swój czas ukończenia półmaratonu używając AI i uczenia maszynowego</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📊 O aplikacji")
    st.info("""
    Ta aplikacja wykorzystuje uczenie maszynowe do przewidywania czasu ukończenia półmaratonu na podstawie:
    
    - Płci
    - Wieku
    - Najlepszego czasu na 5km
    
    Model został wytrenowany na **ponad 20 000 rzeczywistych wynikach** z Wrocław Półmaratonu 2023-2024.
    """)
    
    st.header("🎯 Jak używać")
    st.markdown("""
    1. Wprowadź swoje dane w polu tekstowym
    2. Podaj: płeć, wiek i czas na 5km
    3. Kliknij "Przewiduj Mój Czas"
    4. Otrzymaj szacowany czas mety!
    """)
    
    st.header("📈 Wydajność modelu")
    st.metric("Średni błąd bezwzględny", "~4,5 minuty")
    st.metric("Wynik R²", "0,92")
    
    if st.session_state.prediction_history:
        st.header("📜 Historia")
        st.write(f"Wykonanych predykcji: {len(st.session_state.prediction_history)}")

# Główna treść
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Powiedz nam o sobie")
    
    # Przykładowe dane wejściowe
    with st.expander("💡 Przykładowe dane (kliknij aby zobaczyć)"):
        st.code("""
Przykład 1:
"Cześć, mam na imię Jan, mam 32 lata, jestem mężczyzną i mój czas na 5km to 23:45"

Przykład 2:
"Jestem 28-letnią kobietą i potrafię przebiec 5km w 27 minut"

Przykład 3:
"Mężczyzna, wiek 45 lat, rekord na 5km: 22:30"
        """)
    
    # Pole wprowadzania danych użytkownika
    user_input = st.text_area(
        "Opisz siebie:",
        placeholder="np. Jestem 30-letnim mężczyzną i mój najlepszy czas na 5km to 24:30",
        height=120,
        help="Podaj swoją płeć, wiek i czas na 5km dla najdokładniejszej predykcji"
    )
    
    predict_button = st.button("🚀 Przewiduj Mój Czas", type="primary")

with col2:
    st.header("ℹ️ Wymagane informacje")
    st.markdown("""
    <div class="info-box">
        <h4>Potrzebujemy:</h4>
        <ul>
            <li>👤 Płeć (mężczyzna/kobieta)</li>
            <li>🎂 Wiek (w latach)</li>
            <li>⏱️ Czas na 5km (MM:SS lub GG:MM:SS)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Przetwarzanie predykcji
if predict_button:
    if not user_input.strip():
        st.error("❌ Proszę wprowadzić informacje o sobie!")
    else:
        with st.spinner("🤖 Analizuję Twoje dane..."):
            try:
                # Ekstrakcja danych za pomocą LLM z trackingiem Langfuse (shim obsłuży no-op)
                @observe(name="user_data_extraction")
                def extract_and_track(text):
                    try:
                        langfuse_context.update_current_trace(
                            user_id=f"user_{datetime.now().timestamp()}",
                            metadata={"input_length": len(text)}
                        )
                    except Exception:
                        pass
                    return extract_user_data(text)
                
                extracted_data = extract_and_track(user_input)
                
                # Walidacja wyekstraktowanych danych
                missing_fields = []
                if not extracted_data.get('gender'):
                    missing_fields.append("Płeć")
                if not extracted_data.get('age'):
                    missing_fields.append("Wiek")
                if not extracted_data.get('time_5km_seconds'):
                    missing_fields.append("Czas na 5km")
                
                if missing_fields:
                    st.warning(f"⚠️ Brakujące informacje: {', '.join(missing_fields)}")
                    st.info("💡 Proszę podać wszystkie wymagane informacje dla dokładnej predykcji.")
                    
                    # Pokaż co zostało zrozumiane
                    if any(extracted_data.values()):
                        st.write("✅ Co zrozumiałem:")
                        for key, value in extracted_data.items():
                            if value:
                                key_pl = {
                                    'gender': 'Płeć',
                                    'age': 'Wiek', 
                                    'time_5km_seconds': 'Czas 5km (sekundy)'
                                }.get(key, key)
                                st.write(f"- **{key_pl}**: {value}")
                else:
                    # Wykonaj predykcję
                    try:
                        predictor = HalfMarathonPredictor()
                    except Exception as e:
                        st.error("❌ Nie udało się zainicjalizować predyktora (modelu).")
                        st.info("Upewnij się, że MODEL_PATH wskazuje na istniejący plik modelu lub poprawnie skonfigurowano pobieranie z Spaces.")
                        st.code(f"MODEL_PATH={os.getenv('MODEL_PATH', '(brak)')}")
                        # Trackuj błąd inicjalizacji modelu
                        try:
                            langfuse.trace(
                                name="halfmarathon_model_init_error",
                                input={"user_input": user_input},
                                output={"error": str(e)},
                                metadata={"success": False}
                            )
                        except Exception:
                            pass
                        raise

                    prediction = {}
                    try:
                        prediction = predictor.predict(extracted_data)
                    except Exception as e:
                        st.error(f"❌ Błąd podczas predykcji: {e}")
                        try:
                            langfuse.trace(
                                name="halfmarathon_prediction_runtime_error",
                                input=extracted_data,
                                output={"error": str(e)},
                                metadata={"success": False}
                            )
                        except Exception:
                            pass
                        raise
                    
                    if prediction.get('success'):
                        # Wyświetl predykcję
                        st.markdown(f"""
                        <div class="prediction-box">
                            <h2>🎯 Twój Przewidywany Czas Półmaratonu</h2>
                            <div class="prediction-time">{prediction['formatted_time']}</div>
                            <p style="font-size: 1.2rem;">Na podstawie Twojego profilu</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Pokaż wyekstraktowane dane
                        st.success("✅ Pomyślnie przetworzono Twoje informacje!")
                        
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            gender_pl = "Mężczyzna" if extracted_data['gender'] == 'male' else "Kobieta"
                            st.metric("Płeć", gender_pl)
                        with col_b:
                            st.metric("Wiek", f"{extracted_data['age']} lat")
                        with col_c:
                            time_5km = extracted_data['time_5km_seconds']
                            st.metric("Czas 5km", f"{int(time_5km//60)}:{int(time_5km%60):02d}")
                        
                        # Dodatkowe insighty
                        st.header("📊 Analiza wydajności")
                        
                        col_x, col_y = st.columns(2)
                        
                        with col_x:
                            st.markdown("""
                            <div class="info-box">
                                <h4>📈 Informacje o tempie</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            avg_pace = prediction['prediction_seconds'] / 21.0975
                            st.write(f"**Średnie tempo**: {int(avg_pace//60)}:{int(avg_pace%60):02d} min/km")
                            
                            pace_5k = extracted_data['time_5km_seconds'] / 5
                            st.write(f"**Tempo na 5km**: {int(pace_5k//60)}:{int(pace_5k%60):02d} min/km")
                            
                        with col_y:
                            st.markdown("""
                            <div class="info-box">
                                <h4>💪 Wskazówki treningowe</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if prediction['prediction_seconds'] < 5400:
                                st.write("🏆 Elitarny biegacz! Skup się na utrzymaniu konsystencji.")
                            elif prediction['prediction_seconds'] < 7200:
                                st.write("💪 Świetna forma! Rozważ trening interwałowy.")
                            else:
                                st.write("🎯 Dobry cel! Skup się na budowaniu wytrzymałości.")
                        
                        # Zapisz do historii
                        st.session_state.prediction_history.append({
                            'timestamp': datetime.now(),
                            'input': user_input,
                            'prediction': prediction['formatted_time'],
                            'data': extracted_data
                        })
                        
                        # Tracking w Langfuse (działa jeśli SDK wspiera trace; shim zrobi no-op)
                        try:
                            langfuse.trace(
                                name="halfmarathon_prediction",
                                input=extracted_data,
                                output=prediction,
                                metadata={
                                    "model_version": getattr(getattr(predictor, "model_metadata", {}), "get", lambda *_: "unknown")("version", "unknown") if hasattr(predictor, "model_metadata") else "unknown",
                                    "success": True
                                }
                            )
                        except Exception:
                            pass
                        
                    else:
                        st.error(f"❌ Błąd predykcji: {prediction.get('error', 'Nieznany błąd')}")
                        
            except Exception as e:
                st.error(f"❌ Wystąpił błąd: {str(e)}")
                st.info("Proszę spróbować ponownie z innymi danymi.")
                
                # Trackuj błąd w Langfuse (no-op jeśli brak)
                try:
                    langfuse.trace(
                        name="halfmarathon_prediction_error",
                        input={"user_input": user_input},
                        output={"error": str(e)},
                        metadata={"success": False}
                    )
                except Exception:
                    pass

# Stopka
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 2rem;">
    <p>🏃 Predyktor Półmaratonu v2.0 | Zasilany przez XGBoost & OpenAI</p>
    <p>Wytrenowany na 20 000+ wynikach zawodów | Monitorowany przez Langfuse</p>
</div>
""", unsafe_allow_html=True)
