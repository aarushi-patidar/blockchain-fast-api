import pandas as pd
import numpy as np
import xgboost as xgb
import re
import warnings
import joblib
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

def parse_matlab_date(date_str):
    if pd.isna(date_str):
        return pd.NaT
    try:
        clean_str = re.sub(r'[\[\]]', '', str(date_str))
        parts = re.split(r'[, ]+', clean_str.strip())
        parts = [float(p) for p in parts if p]
        
        if len(parts) >= 6:
            return pd.Timestamp(
                year=int(parts[0]), month=int(parts[1]), day=int(parts[2]),
                hour=int(parts[3]), minute=int(parts[4]), second=int(parts[5])
            )
    except:
        pass
    return pd.NaT

def extract_discharge_features(csv_path):
    try:
        df_cycle = pd.read_csv(csv_path)
        features = {}
        
        if 'Voltage_measured' in df_cycle.columns:
            voltage = df_cycle['Voltage_measured'].dropna()
            features['voltage_mean'] = voltage.mean()
            features['voltage_max'] = voltage.max()
            features['voltage_drop'] = voltage.iloc[0] - voltage.iloc[-1] if len(voltage) > 1 else 0.0
        
        if 'Current_measured' in df_cycle.columns:
            current = df_cycle['Current_measured'].dropna()
            features['current_mean'] = current.mean()
        
        if 'Temperature_measured' in df_cycle.columns:
            temp = df_cycle['Temperature_measured'].dropna()
            features['temp_mean'] = temp.mean()
            features['temp_max'] = temp.max()
        
        return features
        
    except:
        return {}

print("Loading and cleaning metadata...")
df_meta = pd.read_csv('cleaned_dataset/metadata.csv')

df = df_meta[df_meta['type'] == 'discharge'].copy()

df['parsed_time'] = df['start_time'].apply(parse_matlab_date)

df = df.dropna(subset=['Capacity', 'parsed_time', 'filename'])
df = df.sort_values(by=['battery_id', 'parsed_time']).reset_index(drop=True)

print(f"Loaded {len(df)} discharge cycles from {df['battery_id'].nunique()} batteries")

print("Extracting features from cycle data")

cycle_features_list = []
data_dir = Path('cleaned_dataset/data')

for idx, row in df.iterrows():
    csv_path = data_dir / row['filename']
    
    if csv_path.exists():
        cycle_features = extract_discharge_features(str(csv_path))
        cycle_features['filename'] = row['filename']
        cycle_features['battery_id'] = row['battery_id']
        cycle_features['Capacity'] = row['Capacity']
        cycle_features['ambient_temperature'] = row['ambient_temperature']
        cycle_features['parsed_time'] = row['parsed_time']
        cycle_features['test_id'] = row['test_id']
        cycle_features_list.append(cycle_features)
    
    if (idx + 1) % 1000 == 0:
        print(f"  Processed {idx + 1} cycles...")

df_features = pd.DataFrame(cycle_features_list)
print(f"Extracted features from {len(df_features)} cycles")

df_features['Capacity'] = pd.to_numeric(df_features['Capacity'], errors='coerce')

print("Engineering essential features")

df_features['cycle_count'] = df_features.groupby('battery_id').cumcount() + 1

first_cycles = df_features.groupby('battery_id')['parsed_time'].transform('min')
df_features['age_days'] = (df_features['parsed_time'] - first_cycles).dt.total_seconds() / (24 * 3600)

initial_capacities = df_features.groupby('battery_id')['Capacity'].transform('first')
df_features['initial_capacity'] = initial_capacities

df_features['SoH'] = df_features['Capacity'] / df_features['initial_capacity']

df_features['capacity_degradation'] = 1.0 - df_features['SoH']

df_features['capacity_slope'] = df_features.groupby('battery_id')['Capacity'].transform(
    lambda x: np.polyfit(np.arange(len(x)), x.values, 1)[0] if len(x) > 1 else 0.0
)

df_features['capacity_gradient_pct'] = (df_features['capacity_degradation'] / df_features['cycle_count']) * 100

print("Computing target variable (RUL)...")

EOL_THRESHOLD = 0.70

def calculate_rul_improved(group):
    eol_condition = group['SoH'] <= EOL_THRESHOLD
    
    if eol_condition.any():
        eol_cycle = group[eol_condition]['cycle_count'].iloc[0]
    else:
        rul_values = []
        for idx, row in group.iterrows():
            current_soh = row['SoH']
            degradation_rate = row.get('capacity_gradient_pct', 0) / 100
            
            if degradation_rate > 0.0001:
                cycles_to_eol = (current_soh - EOL_THRESHOLD) / degradation_rate
                rul_values.append(max(0, cycles_to_eol))
            else:
                eol_cycle = group['cycle_count'].max() + group['cycle_count'].max() * 2
                rul_values.append(eol_cycle - row['cycle_count'])
        
        if rul_values:
            median_rul = np.median(rul_values)
            group['RUL'] = median_rul - (group['cycle_count'] - group['cycle_count'].min())
            return group
        else:
            eol_cycle = group['cycle_count'].max()
    
    group['RUL'] = eol_cycle - group['cycle_count']
    return group

df_features = df_features.groupby('battery_id', group_keys=False).apply(calculate_rul_improved)


df_features = df_features[df_features['RUL'] >= 0].copy()

df_features = df_features[df_features['RUL'] < 500].copy()

print(f"Final dataset: {len(df_features)} cycles with RUL values")

print("\nPreparing features for model training...")

extracted_feature_cols = ['voltage_mean', 'voltage_max', 'voltage_drop', 'current_mean', 'temp_mean', 'temp_max']

engineered_feature_cols = ['Capacity', 'ambient_temperature', 'cycle_count', 'SoH', 'capacity_degradation', 'capacity_gradient_pct']

feature_cols = extracted_feature_cols + engineered_feature_cols
X = df_features[feature_cols].fillna(0.0)
y = df_features['RUL']

X = X.replace([np.inf, -np.inf], 0.0)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
X = pd.DataFrame(X_scaled, columns=feature_cols)

print(f"Using {len(feature_cols)} features:")
print(f"  - {len(extracted_feature_cols)} extracted from cycle measurements")
print(f"  - {len(engineered_feature_cols)} engineered from metadata")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"\nTraining set: {len(X_train)} samples")
print(f"Test set: {len(X_test)} samples")
print(f"RUL distribution in training set:")
print(f"  Min: {y_train.min():.0f}, Max: {y_train.max():.0f}, Mean: {y_train.mean():.1f} ± {y_train.std():.1f} cycles")

print("\nTraining XGBoost model...")

model = xgb.XGBRegressor(
    n_estimators=400,
    max_depth=6,
    learning_rate=0.025,
    subsample=0.85,
    colsample_bytree=0.85,
    reg_alpha=0.05,
    reg_lambda=0.5,
    random_state=42,
    verbosity=0
)

model.fit(X_train, y_train)

print("Model training complete")


print("\n" + "="*60)
print("MODEL PERFORMANCE METRICS")
print("="*60)

y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

rmse_train = np.sqrt(mean_squared_error(y_train, y_pred_train))
mae_train = mean_absolute_error(y_train, y_pred_train)
r2_train = r2_score(y_train, y_pred_train)

rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
mae_test = mean_absolute_error(y_test, y_pred_test)
r2_test = r2_score(y_test, y_pred_test)

print(f"\nTraining Set:")
print(f"  RMSE: {rmse_train:.2f} cycles")
print(f"  MAE:  {mae_train:.2f} cycles")
print(f"  R²:   {r2_train:.4f}")

print(f"\nTest Set:")
print(f"  RMSE: {rmse_test:.2f} cycles")
print(f"  MAE:  {mae_test:.2f} cycles")
print(f"  R²:   {r2_test:.4f}")

errors = np.abs(y_test.values - y_pred_test)
print(f"\nTest Error Distribution:")
print(f"  Median Error: {np.median(errors):.2f} cycles")
print(f"  90th Percentile: {np.percentile(errors, 90):.2f} cycles")
print(f"  95th Percentile: {np.percentile(errors, 95):.2f} cycles")

print(f"\nTop 10 Most Important Features:")
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.head(10).iterrows():
    print(f"  {row['feature']:30s}: {row['importance']:.4f}")

model.save_model('web3_battery_rul.json')
print("\nModel saved: web3_battery_rul.json")

joblib.dump(scaler, 'feature_scaler.pkl')
print("Feature scaler saved: feature_scaler.pkl")

feature_names_df = pd.DataFrame({
    'feature_names': feature_cols
})
feature_names_df.to_csv('model_feature_names.csv', index=False)
print("Feature names saved: model_feature_names.csv")

metadata = {
    'n_features': len(feature_cols),
    'features': feature_cols,
    'extracted_features': extracted_feature_cols,
    'engineered_features': engineered_feature_cols,
    'rmse_test': float(rmse_test),
    'r2_test': float(r2_test),
    'mae_test': float(mae_test),
    'eol_threshold': EOL_THRESHOLD,
    'training_samples': len(X_train),
    'test_samples': len(X_test),
    'uses_scaling': True,
    'scaler_mean': scaler.mean_.tolist(),
    'scaler_scale': scaler.scale_.tolist()
}

import json
with open('model_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)
print("Model metadata saved: model_metadata.json")