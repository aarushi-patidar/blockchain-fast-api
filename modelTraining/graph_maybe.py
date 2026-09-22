import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import xgboost as xgb
import joblib
import json
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# LOAD MODEL AND DATA
# ==========================================
print("Loading model and data...")

# Load model and metadata
model = xgb.XGBRegressor()
model.load_model('web3_battery_rul.json')
scaler = joblib.load('feature_scaler.pkl')

with open('model_metadata.json', 'r') as f:
    metadata = json.load(f)

feature_names = metadata['features']

# Load metadata for discharge cycles
df_meta = pd.read_csv('cleaned_dataset/metadata.csv')
df_discharge = df_meta[df_meta['type'] == 'discharge'].copy()
df_discharge['Capacity'] = pd.to_numeric(df_discharge['Capacity'], errors='coerce')
df_discharge = df_discharge.dropna(subset=['Capacity'])

print(f"Loaded {len(df_discharge)} discharge cycles")

# ==========================================
# 1. ESTIMATE SoH VS CYCLE COUNT
# ==========================================

def estimate_soh_degradation(initial_capacity, degradation_rate_pct):
    """
    Estimate SoH over cycles based on degradation rate.
    
    Args:
        initial_capacity: Initial battery capacity (Ahr)
        degradation_rate_pct: Degradation rate in %/cycle
    
    Returns:
        cycles, soh values
    """
    max_cycles = int(200 / (degradation_rate_pct / 100)) + 50
    cycles = np.arange(0, max_cycles, 1)
    
    # Linear degradation model
    soh = 1.0 - (cycles * degradation_rate_pct / 100)
    soh = np.maximum(soh, 0.65)  # Stop at 65% (before EOL at 70%)
    
    return cycles, soh


def extract_discharge_curve(csv_path):
    """Extract voltage vs capacity curve from a discharge cycle CSV."""
    try:
        df_cycle = pd.read_csv(csv_path)
        
        if 'Voltage_measured' in df_cycle.columns:
            # For a discharge cycle, voltage decreases as capacity is used
            # Normalize to get relative capacity from 100% to 0%
            voltage = df_cycle['Voltage_measured'].values
            
            # Create relative capacity axis (from 100% at start to 0% at end)
            relative_capacity = np.linspace(100, 0, len(voltage))
            
            # Filter out very short or corrupt curves
            if len(voltage) > 20:
                return relative_capacity, voltage
    
    except Exception as e:
        pass
    
    return None, None


def get_battery_discharge_curves(battery_id, max_curves=6):
    """
    Get discharge curves for different cycle points of a battery.
    Shows early, mid, and late-life discharge curves.
    """
    battery_cycles = df_discharge[df_discharge['battery_id'] == battery_id].copy()
    battery_cycles = battery_cycles.sort_values('test_id').reset_index(drop=True)
    
    if len(battery_cycles) < 3:
        return None
    
    # Select evenly spaced cycles
    indices = np.linspace(0, len(battery_cycles) - 1, min(max_curves, len(battery_cycles)), dtype=int)
    
    curves_data = []
    data_dir = Path('cleaned_dataset/data')
    
    for idx in indices:
        cycle_row = battery_cycles.iloc[idx]
        csv_path = data_dir / cycle_row['filename']
        
        if csv_path.exists():
            relative_cap, voltage = extract_discharge_curve(str(csv_path))
            
            if voltage is not None:
                cycle_num = idx + 1
                soh = cycle_row['Capacity'] / battery_cycles['Capacity'].iloc[0]
                curves_data.append({
                    'cycle_num': cycle_num,
                    'soh': soh,
                    'capacity': relative_cap,
                    'voltage': voltage,
                    'test_id': cycle_row['test_id']
                })
    
    return curves_data if curves_data else None


# ==========================================
# 2. CREATE VISUALIZATIONS
# ==========================================

def plot_soh_vs_cycles_and_discharge_curves(battery_id, output_file='battery_health_analysis.png'):
    """
    Create a comprehensive figure showing:
    - Left: SoH degradation vs Cycle Count
    - Right: Voltage discharge curves at different cycle points
    """
    
    # Get battery discharge data
    battery_cycles = df_discharge[df_discharge['battery_id'] == battery_id].copy()
    battery_cycles = battery_cycles.sort_values('test_id').reset_index(drop=True)
    
    if len(battery_cycles) < 3:
        print(f"Not enough cycles for battery {battery_id}")
        return False
    
    # Calculate SoH for each cycle
    initial_cap = battery_cycles['Capacity'].iloc[0]
    cycle_nums = np.arange(1, len(battery_cycles) + 1)
    soh_values = battery_cycles['Capacity'].values / initial_cap
    
    # Get discharge curves
    discharge_curves = get_battery_discharge_curves(battery_id, max_curves=5)
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # ===== LEFT PLOT: SoH vs Cycle Count =====
    ax1.plot(cycle_nums, soh_values, 'o-', linewidth=2.5, markersize=6, 
             color='#2E86AB', label='Actual SoH')
    
    # Add EOL threshold line
    ax1.axhline(y=0.70, color='red', linestyle='--', linewidth=2, label='EOL Threshold (70%)')
    ax1.axhline(y=0.80, color='orange', linestyle='--', linewidth=1.5, alpha=0.7, label='Warning Level (80%)')
    
    # Fill degradation zone
    ax1.fill_between(cycle_nums, 0, soh_values, alpha=0.1, color='#2E86AB')
    
    # Formatting
    ax1.set_xlabel('Cycle Count', fontsize=12, fontweight='bold')
    ax1.set_ylabel('State of Health (SoH)', fontsize=12, fontweight='bold')
    ax1.set_title(f'Battery {battery_id}: Health Degradation Over Cycles', 
                  fontsize=13, fontweight='bold')
    ax1.set_ylim([0.65, 1.05])
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=10)
    
    # Add percentage labels on y-axis
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y*100:.0f}%'))
    
    # ===== RIGHT PLOT: Voltage Discharge Curves =====
    if discharge_curves:
        colors = plt.cm.viridis(np.linspace(0, 1, len(discharge_curves)))
        
        for i, curve_data in enumerate(discharge_curves):
            label = f"Cycle {curve_data['cycle_num']} (SoH: {curve_data['soh']*100:.1f}%)"
            ax2.plot(curve_data['capacity'], curve_data['voltage'], 
                    color=colors[i], linewidth=2.5, label=label, alpha=0.8)
        
        ax2.set_xlabel('Relative Capacity (%)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Voltage (V)', fontsize=12, fontweight='bold')
        ax2.set_title(f'Battery {battery_id}: Discharge Curve Degradation', 
                     fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=9)
        ax2.invert_xaxis()  # Capacity goes from 100% to 0% (left to right)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.show()
    
    return True


def plot_multiple_batteries_soh_comparison(battery_ids, output_file='multi_battery_comparison.png'):
    """
    Compare SoH degradation across multiple batteries.
    """
    fig, ax = plt.subplots(figsize=(14, 7))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(battery_ids)))
    
    for idx, bat_id in enumerate(battery_ids):
        battery_cycles = df_discharge[df_discharge['battery_id'] == bat_id].copy()
        battery_cycles = battery_cycles.sort_values('test_id').reset_index(drop=True)
        
        if len(battery_cycles) < 3:
            continue
        
        initial_cap = battery_cycles['Capacity'].iloc[0]
        cycle_nums = np.arange(1, len(battery_cycles) + 1)
        soh_values = battery_cycles['Capacity'].values / initial_cap
        
        ax.plot(cycle_nums, soh_values, 'o-', linewidth=2, markersize=5,
               color=colors[idx], label=f'{bat_id}', alpha=0.8)
    
    # Add EOL threshold
    ax.axhline(y=0.70, color='red', linestyle='--', linewidth=2, label='EOL (70%)')
    ax.axhline(y=0.80, color='orange', linestyle='--', linewidth=1.5, alpha=0.7, label='Warning (80%)')
    
    ax.set_xlabel('Cycle Count', fontsize=12, fontweight='bold')
    ax.set_ylabel('State of Health (SoH)', fontsize=12, fontweight='bold')
    ax.set_title('Multi-Battery SoH Degradation Comparison', fontsize=13, fontweight='bold')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y*100:.0f}%'))
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=10, ncol=2)
    ax.set_ylim([0.65, 1.05])
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.show()
    
    return True


def plot_voltage_heatmap_degradation(battery_id, output_file='voltage_heatmap.png'):
    """
    Create a heatmap showing how voltage curves degrade over cycles.
    X-axis: Relative Capacity, Y-axis: Cycle Number, Color: Voltage
    """
    battery_cycles = df_discharge[df_discharge['battery_id'] == battery_id].copy()
    battery_cycles = battery_cycles.sort_values('test_id').reset_index(drop=True)
    
    if len(battery_cycles) < 5:
        print(f"Not enough cycles for heatmap analysis")
        return False
    
    # Sample cycles evenly
    num_samples = min(15, len(battery_cycles))
    indices = np.linspace(0, len(battery_cycles) - 1, num_samples, dtype=int)
    
    data_dir = Path('cleaned_dataset/data')
    voltage_matrix = []
    cycle_labels = []
    
    for idx in indices:
        cycle_row = battery_cycles.iloc[idx]
        csv_path = data_dir / cycle_row['filename']
        
        if csv_path.exists():
            relative_cap, voltage = extract_discharge_curve(str(csv_path))
            
            if voltage is not None:
                # Interpolate to standard length
                standard_length = 100
                voltage_interp = np.interp(
                    np.linspace(0, len(voltage)-1, standard_length),
                    np.arange(len(voltage)),
                    voltage
                )
                voltage_matrix.append(voltage_interp)
                cycle_labels.append(f"C{idx+1}")
    
    if not voltage_matrix:
        return False
    
    voltage_matrix = np.array(voltage_matrix)
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(14, 8))
    
    im = ax.imshow(voltage_matrix, aspect='auto', cmap='RdYlGn_r', interpolation='bilinear')
    
    ax.set_xlabel('Relative Capacity (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Cycle Number', fontsize=12, fontweight='bold')
    ax.set_title(f'Battery {battery_id}: Voltage Heatmap Over Cycles', fontsize=13, fontweight='bold')
    
    # Set y-axis labels
    ax.set_yticks(range(len(cycle_labels)))
    ax.set_yticklabels(cycle_labels)
    
    # Set x-axis labels
    x_ticks = np.linspace(0, len(voltage_matrix[0])-1, 6)
    x_labels = [f'{int(100 - i*100/len(voltage_matrix[0]))}%' for i in x_ticks]
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_labels)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Voltage (V)', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.show()
    
    return True


# ==========================================
# 3. MAIN EXECUTION
# ==========================================

def main():
    print("\n" + "="*70)
    print("BATTERY HEALTH & DISCHARGE CURVE ANALYZER")
    print("="*70 + "\n")
    
    # Get list of available batteries
    available_batteries = sorted(df_discharge['battery_id'].unique())
    print(f"Available batteries: {', '.join(available_batteries)}\n")
    
    # Get user input
    print("Options:")
    print("1. Analyze a single battery (SoH + Discharge curves)")
    print("2. Compare multiple batteries (SoH comparison)")
    print("3. View voltage heatmap for a battery")
    print("4. Analyze all batteries")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        bat_id = input(f"Enter battery ID (e.g., {available_batteries[0]}): ").strip()
        if bat_id in available_batteries:
            plot_soh_vs_cycles_and_discharge_curves(bat_id)
        else:
            print(f"Battery {bat_id} not found!")
    
    elif choice == "2":
        bat_ids = input(f"Enter battery IDs (comma-separated, e.g., {available_batteries[0]},{available_batteries[1]}): ").strip()
        battery_list = [b.strip() for b in bat_ids.split(',')]
        battery_list = [b for b in battery_list if b in available_batteries]
        if battery_list:
            plot_multiple_batteries_soh_comparison(battery_list)
        else:
            print("No valid batteries found!")
    
    elif choice == "3":
        bat_id = input(f"Enter battery ID: ").strip()
        if bat_id in available_batteries:
            plot_voltage_heatmap_degradation(bat_id)
        else:
            print(f"Battery {bat_id} not found!")
    
    elif choice == "4":
        print("\nGenerating reports for all batteries...")
        # Analyze top batteries with good data
        top_batteries = df_discharge.groupby('battery_id').size().nlargest(5).index.tolist()
        
        for bat_id in top_batteries:
            print(f"\nProcessing {bat_id}...")
            plot_soh_vs_cycles_and_discharge_curves(
                bat_id, 
                output_file=f'battery_analysis_{bat_id}.png'
            )
        
        print("\nGenerating comparison chart...")
        plot_multiple_batteries_soh_comparison(
            top_batteries,
            output_file='battery_comparison_all.png'
        )
    
    else:
        print("Invalid option!")
        return
    
    print("\n" + "="*70)
    print("✓ Analysis Complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
