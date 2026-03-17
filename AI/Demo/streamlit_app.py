import streamlit as st
import torch
import timm
from torchvision import transforms
from PIL import Image
import numpy as np
import plotly.graph_objects as go
import time
import os
from datetime import datetime
import pandas as pd
import io

# ===== Page Configuration =====
st.set_page_config(
    page_title="EL Image Classifier",
    page_icon="\U0001F50B",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== Custom CSS =====
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .prediction-good {
        font-size: 2rem;
        color: #00C853;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        background-color: #E8F5E9;
    }
    .prediction-defect {
        font-size: 2rem;
        color: #D32F2F;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        background-color: #FFEBEE;
    }
    .confidence-high {
        color: #00C853;
        font-weight: bold;
    }
    .confidence-low {
        color: #FFA000;
        font-weight: bold;
    }
    .confidence-very-low {
        color: #D32F2F;
        font-weight: bold;
    }
    .stButton > button {
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 2rem;
    }
    .stButton > button:hover {
        background-color: #1565C0;
    }
</style>
""", unsafe_allow_html=True)

# ===== Constants and Configuration =====
MODEL_PATH = "best_el_model.pth"
IMAGE_SIZE = 384
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CLASSES = ["defect", "good"]
DEFAULT_CONFIDENCE_THRESHOLD = 0.7

@st.cache_resource
def load_model():
    try:
        if not os.path.exists(MODEL_PATH):
            st.error(f"Model file not found: {MODEL_PATH}")
            st.info("Please ensure the model file is in the correct location.")
            return None
        
        model = timm.create_model(
            "efficientnet_b3",
            pretrained=False,
            num_classes=2
        )
        
        with st.spinner("Loading model..."):
            try:
                state_dict = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
            except:
                state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
            
            model.load_state_dict(state_dict)
        
        model = model.to(DEVICE)
        model.eval()
        
        return model
    
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None

@st.cache_resource
def get_transforms():
    return transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

def predict_image(image, model, transform):
    try:
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        image_tensor = transform(image).unsqueeze(0).to(DEVICE)
        
        with torch.no_grad():
            output = model(image_tensor)
            probs = torch.softmax(output, dim=1)
            pred_idx = torch.argmax(probs, dim=1).item()
            confidence = float(probs[0][pred_idx])
        
        return CLASSES[pred_idx], confidence
    
    except Exception as e:
        st.error(f"Error during prediction: {str(e)}")
        return None, None

def display_prediction(prediction, confidence, confidence_threshold):
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if prediction == "good":
            st.markdown(f"<div class='prediction-good'>✅ GOOD QUALITY</div>", 
                       unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='prediction-defect'>⚠️ DEFECT DETECTED</div>", 
                       unsafe_allow_html=True)
        
        confidence_percentage = confidence * 100
        
        if confidence >= 0.9:
            conf_class = "confidence-high"
            emoji = "🎯"
        elif confidence >= 0.7:
            conf_class = "confidence-high"
            emoji = "👍"
        elif confidence >= 0.5:
            conf_class = "confidence-low"
            emoji = "⚠️"
        else:
            conf_class = "confidence-very-low"
            emoji = "❓"
        
        st.markdown(f"<p style='text-align: center; font-size: 1.5rem;'>"
                   f"{emoji} Confidence: <span class='{conf_class}'>{confidence_percentage:.2f}%</span></p>", 
                   unsafe_allow_html=True)
        
        if confidence < confidence_threshold:
            st.warning("⚠️ Low confidence prediction. Please verify manually.")
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=confidence * 100,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Confidence Score", "font": {"size": 20}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": "darkblue" if prediction == "good" else "darkred"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 50], "color": "#FFEBEE"},
                    {"range": [50, 70], "color": "#FFF3E0"},
                    {"range": [70, 90], "color": "#E8F5E9"},
                    {"range": [90, 100], "color": "#C8E6C9"}
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": confidence_threshold * 100
                }
            }
        ))
        
        fig.update_layout(
            height=300,
            margin={"l": 20, "r": 20, "t": 40, "b": 20},
        )
        
        st.plotly_chart(fig, use_container_width=True)

def display_image_info(image, filename):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Image Size", f"{image.size[0]} x {image.size[1]}")
    with col2:
        st.metric("Format", image.format or "Unknown")
    with col3:
        st.metric("Mode", image.mode)

def init_session_state():
    if "confidence_threshold" not in st.session_state:
        st.session_state.confidence_threshold = DEFAULT_CONFIDENCE_THRESHOLD
    if "prediction_history" not in st.session_state:
        st.session_state.prediction_history = []

def main():
    init_session_state()
    
    st.markdown("<h1 class='main-header'>Solar Panel Image Classifier</h1>", 
                unsafe_allow_html=True)
    
    model = load_model()
    transform = get_transforms()
    
    if model is None:
        st.stop()
    
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/solar-panel.png", width=100)
        st.title("About")
        st.info("""
        This application uses a deep learning model (EfficientNet-B3) 
        to classify electroluminescence (EL) images of solar panels as 
        **good** or **defective**.
        """)
        
        st.markdown("---")
        
        st.subheader("📊 Model Information")
        st.write(f"- **Architecture:** EfficientNet-B3")
        st.write(f"- **Input Size:** {IMAGE_SIZE}x{IMAGE_SIZE}")
        st.write(f"- **Device:** {DEVICE.upper()}")
        st.write(f"- **Classes:** {', '.join(CLASSES)}")
        
        st.markdown("---")
        
        st.subheader("⚙️ Settings")
        new_threshold = st.slider(
            "Confidence Threshold", 
            min_value=0.0, 
            max_value=1.0, 
            value=st.session_state.confidence_threshold,
            step=0.05,
            help="Threshold for high confidence predictions",
            key="threshold_slider"
        )
        st.session_state.confidence_threshold = new_threshold
        
        st.markdown("---")
        
        st.subheader("📜 Prediction History")
        if st.session_state.prediction_history:
            for i, item in enumerate(st.session_state.prediction_history[-5:]):
                st.write(f"{i+1}. {item["filename"]}: {item["prediction"]} ({item["confidence"]:.1f}%)")
        else:
            st.write("No predictions yet")
        
        st.markdown("---")
        
        st.subheader("📝 Instructions")
        st.markdown("""
        1. Upload an EL image (JPG, PNG, JPEG)
        2. Wait for analysis
        3. View results with confidence score
        4. Download report if needed
        """)
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Predict", "📊 Batch Processing", "ℹ️ Help"])
    
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Choose an EL image...", 
                type=["jpg", "jpeg", "png"],
                help="Upload a single EL image for classification"
            )
        
        if uploaded_file is not None:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            image = Image.open(uploaded_file)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📸 Uploaded Image")
                st.image(image, use_container_width=True)
                display_image_info(image, uploaded_file.name)
            
            if st.button("🔍 Analyze Image", use_container_width=True, key="analyze_single"):
                with st.spinner("Analyzing image..."):
                    time.sleep(0.5)
                    
                    prediction, confidence = predict_image(
                        image, model, transform
                    )
                    
                    if prediction is not None:
                        st.session_state.prediction_history.append({
                            "filename": uploaded_file.name,
                            "prediction": prediction,
                            "confidence": confidence * 100,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        with col2:
                            st.subheader("📊 Analysis Results")
                            display_prediction(
                                prediction, 
                                confidence, 
                                st.session_state.confidence_threshold
                            )
                            
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            result_text = f"""EL Image Analysis Report
                            ================================
                            Filename: {uploaded_file.name}
                            Prediction: {prediction.upper()}
                            Confidence: {confidence*100:.2f}%
                            Threshold: {st.session_state.confidence_threshold*100:.0f}%
                            Timestamp: {timestamp}
                            Device: {DEVICE}
                            ================================
                            """
                            
                            st.download_button(
                                label="📥 Download Report",
                                data=result_text,
                                file_name=f"el_analysis_{timestamp}.txt",
                                mime="text/plain",
                                key="download_single"
                            )
        
        else:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image("https://img.icons8.com/color/96/000000/upload-to-cloud.png", 
                        use_container_width=True)
                st.info("👆 Please upload an image to begin analysis")
    
    with tab2:
        st.subheader("📊 Batch Processing")
        st.info("Upload multiple images for batch analysis")
        
        uploaded_files = st.file_uploader(
            "Choose multiple EL images...", 
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="Upload multiple images for batch processing",
            key="batch_uploader"
        )
        
        if uploaded_files:
            if st.button("🔍 Analyze All Images", use_container_width=True, key="analyze_batch"):
                results = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Processing: {file.name}")
                    
                    image = Image.open(file)
                    prediction, confidence = predict_image(
                        image, model, transform
                    )
                    
                    if prediction:
                        results.append({
                            "Filename": file.name,
                            "Prediction": prediction,
                            "Confidence (%)": f"{confidence*100:.2f}",
                            "Status": "✅" if prediction == "good" else "⚠️"
                        })
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.text("✅ Processing complete!")
                
                if results:
                    st.subheader("Batch Results")
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        good_count = sum(1 for r in results if r["Prediction"] == "good")
                        st.metric("Good Panels", good_count)
                    with col2:
                        defect_count = sum(1 for r in results if r["Prediction"] == "defect")
                        st.metric("Defective Panels", defect_count)
                    with col3:
                        st.metric("Total Panels", len(results))
                    
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Batch Results (CSV)",
                        data=csv,
                        file_name=f"batch_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv",
                        mime="text/csv",
                        key="download_batch"
                    )
    
    with tab3:
        st.subheader("ℹ️ Help & Information")
        
        st.markdown("""
        ### About Electroluminescence (EL) Imaging
        EL imaging is a technique used to detect defects in solar panels by making them 
        emit light (electroluminescence) and capturing the resulting image. Defects appear 
        as dark areas in the image.
        
        ### How to Use This Application
        
        1. **Single Image Analysis**
           - Go to the "Upload & Predict" tab
           - Upload a single EL image
           - Click "Analyze Image"
           - View results and download report
        
        2. **Batch Processing**
           - Go to the "Batch Processing" tab
           - Upload multiple images
           - Click "Analyze All Images"
           - View results table and download CSV
        
        ### Interpreting Results
        
        - **Good Quality (✅)**: No defects detected in the panel
        - **Defect Detected (⚠️)**: One or more defects found in the panel
        - **Confidence Score**: How confident the model is in its prediction
        - **Threshold**: Minimum confidence for reliable predictions
        
        ### Tips for Best Results
        
        - Use clear, well-lit EL images
        - Ensure the entire panel is visible
        - Avoid images with watermarks or text overlays
        - Images should be similar to the training data
        
        ### Technical Details
        
        - **Model**: EfficientNet-B3
        - **Input Size**: 384x384 pixels
        - **Framework**: PyTorch
        - **Device**: {DEVICE}
        
        ### Troubleshooting
        
        If you encounter issues:
        1. Check that the image format is supported (JPG, PNG)
        2. Ensure the image is not corrupted
        3. Try with a different image
        4. Check the model file exists in the same directory as the app
        5. Verify the model file name is "best_el_model.pth"
        
        ### Contact
        
        For support or questions, please contact your system administrator.
        """.replace("{DEVICE}", DEVICE))

if __name__ == "__main__":
    main()
