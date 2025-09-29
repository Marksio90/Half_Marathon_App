import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils.llm_extractor import extract_user_data
from utils.model_predictor import HalfMarathonPredictor
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

# Page configuration
st.set_page_config(
    page_title="Half Marathon Time Predictor",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Langfuse
langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# Initialize session state
if 'prediction_history' not in st.session_state:
    st.session_state.prediction_history = []

# Custom CSS
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

# Header
st.markdown('<div class="main-header">🏃 Half Marathon Time Predictor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Predict your half-marathon finish time using AI and machine learning</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📊 About")
    st.info("""
    This application uses machine learning to predict your half-marathon finish time based on:
    
    - Gender
    - Age
    - 5km personal best time
    
    The model was trained on **20,000+ real race results** from Wrocław Half Marathon 2023-2024.
    """)
    
    st.header("🎯 How to use")
    st.markdown("""
    1. Enter your information in the text box
    2. Include: gender, age, and 5km time
    3. Click "Predict My Time"
    4. Get your estimated finish time!
    """)
    
    st.header("📈 Model Performance")
    st.metric("Mean Absolute Error", "~4.5 minutes")
    st.metric("R² Score", "0.92")
    
    if st.session_state.prediction_history:
        st.header("📜 History")
        st.write(f"Predictions made: {len(st.session_state.prediction_history)}")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Tell us about yourself")
    
    # Example prompts
    with st.expander("💡 Example inputs (click to see)"):
        st.code("""
Example 1:
"Hi, I'm John, 32 years old male, and my 5km time is 23:45"

Example 2:
"I'm a 28-year-old woman and I can run 5km in 27 minutes"

Example 3:
"Male runner, age 45, 5k PR: 22:30"
        """)
    
    # User input
    user_input = st.text_area(
        "Describe yourself:",
        placeholder="e.g., I'm a 30-year-old male runner and my 5km best time is 24:30",
        height=120,
        help="Include your gender, age, and 5km time for the most accurate prediction"
    )
    
    predict_button = st.button("🚀 Predict My Time", type="primary")

with col2:
    st.header("ℹ️ Required Information")
    st.markdown("""
    <div class="info-box">
        <h4>We need:</h4>
        <ul>
            <li>👤 Gender (male/female)</li>
            <li>🎂 Age (in years)</li>
            <li>⏱️ 5km time (MM:SS or HH:MM:SS)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Process prediction
if predict_button:
    if not user_input.strip():
        st.error("❌ Please enter some information about yourself!")
    else:
        with st.spinner("🤖 Analyzing your information..."):
            try:
                # Extract data using LLM with Langfuse tracking
                @observe(name="user_data_extraction")
                def extract_and_track(text):
                    langfuse_context.update_current_trace(
                        user_id=f"user_{datetime.now().timestamp()}",
                        metadata={"input_length": len(text)}
                    )
                    return extract_user_data(text)
                
                extracted_data = extract_and_track(user_input)
                
                # Validate extracted data
                missing_fields = []
                if not extracted_data.get('gender'):
                    missing_fields.append("Gender")
                if not extracted_data.get('age'):
                    missing_fields.append("Age")
                if not extracted_data.get('time_5km_seconds'):
                    missing_fields.append("5km time")
                
                if missing_fields:
                    st.warning(f"⚠️ Missing information: {', '.join(missing_fields)}")
                    st.info("💡 Please provide all required information for an accurate prediction.")
                    
                    # Show what was extracted
                    if any(extracted_data.values()):
                        st.write("✅ What I understood:")
                        for key, value in extracted_data.items():
                            if value:
                                st.write(f"- **{key}**: {value}")
                else:
                    # Make prediction
                    predictor = HalfMarathonPredictor()
                    prediction = predictor.predict(extracted_data)
                    
                    if prediction['success']:
                        # Display prediction
                        st.markdown(f"""
                        <div class="prediction-box">
                            <h2>🎯 Your Predicted Half-Marathon Time</h2>
                            <div class="prediction-time">{prediction['formatted_time']}</div>
                            <p style="font-size: 1.2rem;">Based on your profile</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Show extracted data
                        st.success("✅ Successfully processed your information!")
                        
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Gender", extracted_data['gender'].capitalize())
                        with col_b:
                            st.metric("Age", f"{extracted_data['age']} years")
                        with col_c:
                            time_5km = extracted_data['time_5km_seconds']
                            st.metric("5km Time", f"{int(time_5km//60)}:{int(time_5km%60):02d}")
                        
                        # Additional insights
                        st.header("📊 Performance Insights")
                        
                        col_x, col_y = st.columns(2)
                        
                        with col_x:
                            st.markdown("""
                            <div class="info-box">
                                <h4>📈 Pace Information</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            avg_pace = prediction['prediction_seconds'] / 21.0975
                            st.write(f"**Average pace**: {int(avg_pace//60)}:{int(avg_pace%60):02d} min/km")
                            
                            pace_5k = extracted_data['time_5km_seconds'] / 5
                            st.write(f"**5km pace**: {int(pace_5k//60)}:{int(pace_5k%60):02d} min/km")
                            
                        with col_y:
                            st.markdown("""
                            <div class="info-box">
                                <h4>💪 Training Tips</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if prediction['prediction_seconds'] < 5400:
                                st.write("🏆 Elite runner! Focus on maintaining consistency.")
                            elif prediction['prediction_seconds'] < 7200:
                                st.write("💪 Strong performance! Consider interval training.")
                            else:
                                st.write("🎯 Great goal! Focus on building endurance.")
                        
                        # Save to history
                        st.session_state.prediction_history.append({
                            'timestamp': datetime.now(),
                            'input': user_input,
                            'prediction': prediction['formatted_time'],
                            'data': extracted_data
                        })
                        
                        # Langfuse tracking for prediction
                        langfuse.trace(
                            name="halfmarathon_prediction",
                            input=extracted_data,
                            output=prediction,
                            metadata={
                                "model_version": predictor.model_metadata.get('version', 'unknown'),
                                "success": True
                            }
                        )
                        
                    else:
                        st.error(f"❌ Prediction error: {prediction.get('error', 'Unknown error')}")
                        
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                st.info("Please try again with different information.")
                
                # Track error in Langfuse
                langfuse.trace(
                    name="halfmarathon_prediction_error",
                    input={"user_input": user_input},
                    output={"error": str(e)},
                    metadata={"success": False}
                )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 2rem;">
    <p>🏃 Half Marathon Predictor v2.0 | Powered by XGBoost & OpenAI</p>
    <p>Trained on 20,000+ race results | Monitored with Langfuse</p>
</div>
""", unsafe_allow_html=True)