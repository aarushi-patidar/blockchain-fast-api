import pandas as pd
import numpy as np
import xgboost as xgb
import json
import joblib
from pathlib import Path
from sklearn.preprocessing import StandardScaler


model = xgb.XGBRegressor()
model.load_model('web3_battery_rul.json')

scaler = joblib.load('feature_scaler.pkl')

with open('model_metadata.json', 'r') as f:
    metadata = json.load(f)

feature_names = metadata['features']
print(f"\nModel loaded successfully")
print(f"Using {len(feature_names)} features for prediction")
print(f"Features are scaled for cross-battery generalization\n")


def extract_cycle_features(csv_path):
    """Extract features from a discharge cycle CSV file"""
    try:
        df_cycle = pd.read_csv(csv_path)
        
        features = {}
        
        if 'Time' in df_cycle.columns:
            features['cycle_duration'] = df_cycle['Time'].max() - df_cycle['Time'].min()
            features['measurement_count'] = len(df_cycle)
        else:
            features['cycle_duration'] = 0.0
            features['measurement_count'] = 0
        
        if 'Voltage_measured' in df_cycle.columns:
            voltage = df_cycle['Voltage_measured'].dropna()
            features['voltage_mean'] = voltage.mean()
            features['voltage_std'] = voltage.std() if len(voltage) > 1 else 0.0
            features['voltage_min'] = voltage.min()
            features['voltage_max'] = voltage.max()
            features['voltage_range'] = voltage.max() - voltage.min()
            features['voltage_drop'] = voltage.iloc[0] - voltage.iloc[-1] if len(voltage) > 1 else 0.0
        else:
            features.update({
                'voltage_mean': 3.8, 'voltage_std': 0.1, 'voltage_min': 3.5, 
                'voltage_max': 4.2, 'voltage_range': 0.7, 'voltage_drop': 0.5
            })
        
        if 'Current_measured' in df_cycle.columns:
            current = df_cycle['Current_measured'].dropna()
            features['current_mean'] = current.mean()
            features['current_std'] = current.std() if len(current) > 1 else 0.0
            features['current_min'] = current.min()
            features['current_max'] = current.max()
        else:
            features.update({
                'current_mean': -2.0, 'current_std': 0.1, 
                'current_min': -2.2, 'current_max': -1.8
            })
        
        if 'Temperature_measured' in df_cycle.columns:
            temp = df_cycle['Temperature_measured'].dropna()
            features['temp_mean'] = temp.mean()
            features['temp_std'] = temp.std() if len(temp) > 1 else 0.0
            features['temp_min'] = temp.min()
            features['temp_max'] = temp.max()
            features['temp_range'] = temp.max() - temp.min()
        else:
            features.update({
                'temp_mean': 25.0, 'temp_std': 2.0, 
                'temp_min': 23.0, 'temp_max': 28.0, 'temp_range': 5.0
            })
        
        if 'Voltage_measured' in df_cycle.columns and 'Current_measured' in df_cycle.columns:
            voltage = df_cycle['Voltage_measured'].dropna()
            current = df_cycle['Current_measured'].dropna()
            if len(voltage) == len(current):
                power = np.abs(voltage * current)
                features['power_mean'] = power.mean()
                features['power_max'] = power.max()
        else:
            features.update({'power_mean': 7.6, 'power_max': 9.2})
        
        return features
        
    except Exception as e:
        print(f"Error reading cycle file: {e}")
        return None


def input_method_selection():
    """Allow user to choose input method"""
    print("\nHow would you like to input parameters?")
    print("1. Manual input (simple parameters)")
    print("2. From discharge cycle CSV file")
    print("3. Use example values")
    
    choice = input("\nSelect option (1-3): ").strip()
    return choice


def manual_input():
    """Get manual parameter input from user"""
    print("\n" + "-"*70)
    print("MANUAL PARAMETER INPUT")
    print("-"*70)
    
    try:
        current_capacity = float(input("Current Capacity (Ahr) [e.g., 1.5]: "))
        initial_capacity = float(input("Initial/Rated Capacity (Ahr) [e.g., 2.0]: "))
        ambient_temperature = float(input("Ambient Temperature (°C) [e.g., 25]: "))
        cycle_count = int(input("Cycle Count (number) [e.g., 50]: "))
        age_days = float(input("Age (days) [e.g., 100]: "))
        
        soh = current_capacity / initial_capacity
        degradation_level = 1.0 - soh

        cycle_duration = 3600 * (2.0 / abs(-2.0))
        measurement_count = 500 + int(cycle_count * 10)
        
        voltage_mean = 3.8 - (degradation_level * 0.3)
        voltage_drop = 0.5 + (degradation_level * 0.3)
        
        capacity_slope = -initial_capacity / (cycle_count + 1) if cycle_count > 0 else -0.01
        normalized_degradation_rate = capacity_slope / initial_capacity if initial_capacity > 0 else 0
        capacity_gradient_pct = (degradation_level / max(cycle_count, 1)) * 100
        cycle_utilization = cycle_count / (cycle_count + 100)
        degradation_acceleration = (degradation_level ** 2) / max(cycle_count, 1)
        daily_degradation_rate = degradation_level / (age_days + 1)

        if capacity_gradient_pct > 0.0001:
            extrapolated_rul = (soh - 0.70) / (capacity_gradient_pct / 100)
        else:
            extrapolated_rul = 0
        extrapolated_rul = max(0, min(extrapolated_rul, 1000))
        
        features = {
            'cycle_duration': cycle_duration,
            'measurement_count': measurement_count,
            'voltage_mean': max(voltage_mean, 3.5),
            'voltage_std': 0.1 + (degradation_level * 0.1),
            'voltage_min': 3.5,
            'voltage_max': 4.1,
            'voltage_range': 0.6,
            'voltage_drop': voltage_drop,
            'current_mean': -2.0,
            'current_std': 0.05 + (degradation_level * 0.1),
            'current_min': -2.1,
            'current_max': -1.9,
            'temp_mean': ambient_temperature,
            'temp_std': 1.0 + (degradation_level * 2.0),
            'temp_min': ambient_temperature - 2,
            'temp_max': ambient_temperature + 5,
            'temp_range': 7.0,
            'power_mean': 7.6 - (degradation_level * 1.5),
            'power_max': 8.8 - (degradation_level * 1.5),
            'Capacity': current_capacity,
            'ambient_temperature': ambient_temperature,
            'cycle_count': cycle_count,
            'age_days': age_days,
            'initial_capacity': initial_capacity,
            'SoH': soh,
            'capacity_degradation': degradation_level,
            'capacity_slope': capacity_slope,
            'normalized_degradation_rate': normalized_degradation_rate,
            'capacity_gradient_pct': capacity_gradient_pct,
            'cycle_utilization': cycle_utilization,
            'degradation_acceleration': degradation_acceleration,
            'daily_degradation_rate': daily_degradation_rate,
            'extrapolated_rul_from_gradient': extrapolated_rul
        }
        
        return features
        
    except ValueError as e:
        print(f"Invalid input: {e}")
        return None


def csv_input():
    """Get parameters from a discharge cycle CSV file"""
    print("\n" + "-"*70)
    print("CSV FILE INPUT")
    print("-"*70)
    
    csv_path = input("Path to discharge cycle CSV file: ").strip()
    
    if not Path(csv_path).exists():
        print(f"File not found: {csv_path}")
        return None
    
    try:
        current_capacity = float(input("Current Capacity (Ahr) [from metadata]: "))
        initial_capacity = float(input("Initial Capacity (Ahr) [from metadata]: "))
        ambient_temperature = float(input("Ambient Temperature (°C): "))
        cycle_count = int(input("Cycle Count (number): "))
        age_days = float(input("Age (days): "))
        
        cycle_features = extract_cycle_features(csv_path)
        if cycle_features is None:
            return None
        
        soh = current_capacity / initial_capacity
        degradation_level = 1.0 - soh
        capacity_slope = -initial_capacity / (cycle_count + 1) if cycle_count > 0 else -0.01
        normalized_degradation_rate = capacity_slope / initial_capacity if initial_capacity > 0 else 0
        capacity_gradient_pct = (degradation_level / max(cycle_count, 1)) * 100
        cycle_utilization = cycle_count / (cycle_count + 100)
        degradation_acceleration = (degradation_level ** 2) / max(cycle_count, 1)
        daily_degradation_rate = degradation_level / (age_days + 1)
        
        if capacity_gradient_pct > 0.0001:
            extrapolated_rul = (soh - 0.70) / (capacity_gradient_pct / 100)
        else:
            extrapolated_rul = 0
        extrapolated_rul = max(0, min(extrapolated_rul, 1000))
        
        cycle_features.update({
            'Capacity': current_capacity,
            'ambient_temperature': ambient_temperature,
            'cycle_count': cycle_count,
            'age_days': age_days,
            'initial_capacity': initial_capacity,
            'SoH': soh,
            'capacity_degradation': degradation_level,
            'capacity_slope': capacity_slope,
            'normalized_degradation_rate': normalized_degradation_rate,
            'capacity_gradient_pct': capacity_gradient_pct,
            'cycle_utilization': cycle_utilization,
            'degradation_acceleration': degradation_acceleration,
            'daily_degradation_rate': daily_degradation_rate,
            'extrapolated_rul_from_gradient': extrapolated_rul
        })
        
        return cycle_features
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def example_input():
    """Use example battery parameters"""
    print("\nUsing example battery parameters (early degradation stage)...\n")
    
    features = {
        'cycle_duration': 3600.0,
        'measurement_count': 800,
        'voltage_mean': 3.75,
        'voltage_std': 0.12,
        'voltage_min': 3.5,
        'voltage_max': 4.1,
        'voltage_range': 0.6,
        'voltage_drop': 0.45,
        'current_mean': -2.0,
        'current_std': 0.08,
        'current_min': -2.1,
        'current_max': -1.9,
        'temp_mean': 24.0,
        'temp_std': 2.5,
        'temp_min': 22.0,
        'temp_max': 28.0,
        'temp_range': 6.0,
        'power_mean': 7.5,
        'power_max': 8.2,
        'Capacity': 1.85,
        'ambient_temperature': 24.0,
        'cycle_count': 45,
        'age_days': 120.0,
        'initial_capacity': 2.0,
        'SoH': 0.925,
        'capacity_degradation': 0.075,
        'capacity_slope': -0.0444,
        'normalized_degradation_rate': -0.0222,
        'capacity_gradient_pct': 0.1667,
        'cycle_utilization': 0.3103,
        'degradation_acceleration': 0.000125,
        'daily_degradation_rate': 0.000625,
        'extrapolated_rul_from_gradient': 0.225 / 0.001667 if 0.001667 > 0.0001 else 0  # (0.925-0.70) / (0.1667/100)
    }
    
    return features

def predict_rul(features):
    """Predict RUL and assess battery health"""

    X = pd.DataFrame([features])
    X = X[feature_names]

    X = X.replace([np.inf, -np.inf], 0.0)
    
    X_scaled = scaler.transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=feature_names)
    
    rul_model = model.predict(X_scaled)[0]
    
    training_avg_gradient = 0.17  
    actual_gradient = features.get('capacity_gradient_pct', training_avg_gradient)
    
    if actual_gradient > 0.0001:
        gradient_ratio = training_avg_gradient / actual_gradient

        if gradient_ratio > 1.2 or gradient_ratio < 0.8:
            dampening_factor = np.sqrt(gradient_ratio)
            rul_corrected = rul_model * dampening_factor
            soh = features.get('SoH', 0)
            
            # If at 88% SoH and degrading at 0.12%/cycle, should have ~150+ cycles
            if soh > 0.70:
                rul_from_math = (soh - 0.70) / (actual_gradient / 100)
                # Use the higher of model prediction vs mathematical extrapolation
                rul_prediction = max(rul_corrected, rul_from_math * 0.8)
            else:
                rul_prediction = rul_corrected
        else:
            rul_prediction = rul_model
    else:
        rul_prediction = rul_model
    
    soh = features.get('SoH', 0)
    
    return rul_prediction, soh


def get_health_status(soh):
    """Determine battery health status"""
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


def get_recommended_use_case(rul, soh, cycle_count):
    """Provide recommended use case based on battery state"""
    
    status, description = get_health_status(soh)
    
    recommendations = {
        "EXCELLENT": [
            "Primary power source - all applications including critical ones",
        ],
        "GOOD": [
            "Primary power source - general use",
        ],
        "FAIR": [
            "Secondary power source or backup, can be repurposed to be used in microgrids",
        ],
        "POOR": [
            "Emergency backup only, can be used in rare scenarios like EXIT lights,etc"
        ],
        "CRITICAL": [
            "NOT RECOMMENDED for any application, Recycling recommended"
        ]
    }
    
    return recommendations.get(status, [])


def main():

    choice = input_method_selection()
    
    if choice == "1":
        features = manual_input()
    elif choice == "2":
        features = csv_input()
    elif choice == "3":
        features = example_input()
    else:
        print("Invalid choice. Using example values.")
        features = example_input()
    
    if features is None:
        print("\nFailed to load parameters. Exiting.")
        return
    
    print("\n" + "="*70)
    print("PREDICTING RUL")
    print("="*70)
    
    rul_prediction, soh = predict_rul(features)
    
    status, health_description = get_health_status(soh)

    recommendations = get_recommended_use_case(
        rul_prediction, 
        soh, 
        features.get('cycle_count', 0)
    )
    
    print(f"\nBATTERY METRICS:")
    print(f"   Initial Capacity:        {features.get('initial_capacity', 'N/A'):.2f} Ahr")
    print(f"   Current Capacity:        {features.get('Capacity', 'N/A'):.2f} Ahr")
    print(f"   Cycle Count:             {features.get('cycle_count', 'N/A')} cycles")
    print(f"   Age:                     {features.get('age_days', 'N/A'):.1f} days")
    
    print(f"\nHEALTH STATUS:")
    print(f"   State of Health (SoH):   {soh*100:.1f}%")
    print(f"   Health Level:            {status} - {health_description}")
    print(f"   Degrad. Factor:          {features.get('capacity_degradation', 0)*100:.1f}%")
    
    print(f"\n⏱PREDICTED REMAINING USEFUL LIFE:")
    print(f"   RUL Cycles:              {max(0, rul_prediction):.0f} cycles")
    
    if features.get('age_days', 0) > 0 and features.get('cycle_count', 0) > 0:
        cycles_per_day = features['cycle_count'] / features['age_days']
        if cycles_per_day > 0:
            days_to_eol = max(0, rul_prediction) / cycles_per_day
            print(f"   Est. Time to EOL:        {days_to_eol:.0f} days (~{days_to_eol/30:.1f} months)")
    
    print(f"\nRECOMMENDED USE CASES:")
    for rec in recommendations:
        print(f"   {rec}")
    
    print("\n" + "="*70)
    
    results = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'battery_metrics': {
            'initial_capacity': float(features.get('initial_capacity', 0)),
            'current_capacity': float(features.get('Capacity', 0)),
            'cycle_count': int(features.get('cycle_count', 0)),
            'age_days': float(features.get('age_days', 0))
        },
        'health_status': {
            'SoH': float(soh),
            'status': status,
            'description': health_description
        },
        'predictions': {
            'predicted_rul_cycles': float(max(0, rul_prediction)),
            'model_r2_score': metadata.get('r2_test', 0)
        },
        'recommendations': recommendations
    }
    
    with open('last_prediction.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("Results saved to: last_prediction.json\n")


if __name__ == "__main__":
    main()
