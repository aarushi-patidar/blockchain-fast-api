import sys
from pathlib import Path
import json
import joblib
import xgboost as xgb
import pandas as pd
import numpy as np

# Add models directory to path
models_dir = Path(__file__).parent.parent.parent / "models"
sys.path.insert(0, str(models_dir))

# Load model and scaler
model_path = Path(__file__).parent.parent.parent / "modelTraining" / "web3_battery_rul.json"
scaler_path = Path(__file__).parent.parent.parent / "modelTraining" / "feature_scaler.pkl"
metadata_path = Path(__file__).parent.parent.parent / "modelTraining" / "model_metadata.json"

model = xgb.XGBRegressor()
model.load_model(str(model_path))

scaler = joblib.load(str(scaler_path))

with open(str(metadata_path), 'r') as f:
    metadata = json.load(f)

feature_names = metadata['features']


def predict_battery_rul(features: dict):
    """
    Predict battery RUL (Remaining Useful Life) from features
    
    Args:
        features: Dictionary of battery parameters including cycle features
        
    Returns:
        tuple: (rul_prediction, soh)
    """
    try:
        # Prepare feature vector
        X = np.array([[features.get(name, 0.0) for name in feature_names]])
        
        # Scale features
        X_scaled = scaler.transform(X)
        
        # Make prediction
        rul_model = model.predict(X_scaled)[0]
        
        # Apply correction based on gradient
        training_avg_gradient = 0.17
        actual_gradient = features.get('capacity_gradient_pct', training_avg_gradient)
        
        if actual_gradient > 0.0001:
            gradient_ratio = training_avg_gradient / actual_gradient
            
            if gradient_ratio > 1.2 or gradient_ratio < 0.8:
                dampening_factor = np.sqrt(gradient_ratio)
                rul_corrected = rul_model * dampening_factor
                soh = features.get('SoH', 0)
                
                if soh > 0.70:
                    rul_from_math = (soh - 0.70) / (actual_gradient / 100)
                    rul_prediction = max(rul_corrected, rul_from_math * 0.8)
                else:
                    rul_prediction = rul_corrected
            else:
                rul_prediction = rul_model
        else:
            rul_prediction = rul_model
        
        soh = features.get('SoH', 0)
        rul_prediction = max(0, rul_prediction)
        
        return float(rul_prediction), float(soh)
    
    except Exception as e:
        raise Exception(f"Prediction error: {str(e)}")


def get_health_status(soh: float):
    """Determine battery health status based on State of Health"""
    if soh >= 0.95:
        return "EXCELLENT", "New or near-new condition"
    elif soh >= 0.85:
        return "GOOD", "Minimal degradation, normal operation"
    elif soh >= 0.70:
        return "FAIR", "Noticeable degradation, approaching EOL"
    elif soh >= 0.60:
        return "POOR", "Significant degradation, limited lifespan"
    else:
        return "CRITICAL", "Near end-of-life, replacement recommended"


def get_recommendations(rul: float, soh: float, cycle_count: int):
    """Generate recommendations based on battery state"""
    status, description = get_health_status(soh)
    
    recommendations = {
        "EXCELLENT": [
            "Primary power source for all applications including critical ones",
            "No action needed - battery in excellent condition",
        ],
        "GOOD": [
            "Suitable for primary power applications",
            "Continue normal operation",
            "Monitor capacity periodically",
        ],
        "FAIR": [
            "Acceptable for non-critical applications",
            "Plan for replacement within next cycle",
            "Monitor battery health closely",
        ],
        "POOR": [
            "Limit to non-critical backup applications only",
            "Schedule replacement soon",
            "Avoid high-power draw applications",
        ],
        "CRITICAL": [
            "Emergency use only - replacement urgent",
            "Avoid critical applications",
            "Plan replacement immediately",
        ]
    }
    
    return recommendations.get(status, [])
