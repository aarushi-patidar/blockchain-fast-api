#!/usr/bin/env python
"""
Batch visualization utility for generating all battery analysis reports.
Run this to automatically generate comprehensive reports for all batteries.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from graph_maybe import (
    plot_soh_vs_cycles_and_discharge_curves,
    plot_multiple_batteries_soh_comparison,
    plot_voltage_heatmap_degradation,
    df_discharge
)

def generate_all_reports():
    """Generate comprehensive reports for all batteries."""
    
    print("\n" + "="*70)
    print("GENERATING COMPREHENSIVE BATTERY ANALYSIS REPORTS")
    print("="*70 + "\n")
    
    # Get all batteries
    all_batteries = sorted(df_discharge['battery_id'].unique())
    print(f"Found {len(all_batteries)} batteries\n")
    
    # Get top batteries by cycle count
    top_batteries = df_discharge.groupby('battery_id').size().nlargest(10).index.tolist()
    print(f"Top 10 batteries by data volume:")
    for i, bat_id in enumerate(top_batteries, 1):
        count = len(df_discharge[df_discharge['battery_id'] == bat_id])
        print(f"  {i:2d}. {bat_id}: {count} cycles")
    
    # Generate individual reports
    print("\n" + "-"*70)
    print("GENERATING INDIVIDUAL BATTERY REPORTS")
    print("-"*70 + "\n")
    
    successful = []
    failed = []
    
    for i, bat_id in enumerate(top_batteries, 1):
        try:
            print(f"[{i}/{len(top_batteries)}] Generating report for {bat_id}...", end=" ")
            output_file = f"battery_analysis_{bat_id}.png"
            result = plot_soh_vs_cycles_and_discharge_curves(bat_id, output_file)
            if result:
                successful.append(bat_id)
                print("✓")
            else:
                failed.append(bat_id)
                print("✗ (insufficient data)")
        except Exception as e:
            failed.append(bat_id)
            print(f"✗ ({str(e)[:30]}...)")
    
    # Generate comparison report
    print("\n" + "-"*70)
    print("GENERATING COMPARISON REPORTS")
    print("-"*70 + "\n")
    
    try:
        print("Creating overview comparison chart...", end=" ")
        plot_multiple_batteries_soh_comparison(
            successful[:10],
            output_file='battery_comparison_overview.png'
        )
        print("✓")
    except Exception as e:
        print(f"✗ ({str(e)[:40]}...)")
    
    # Generate heatmaps for top 5
    print("\nGenerating voltage heatmaps for top 5 batteries...")
    for bat_id in successful[:5]:
        try:
            print(f"  {bat_id}...", end=" ")
            plot_voltage_heatmap_degradation(
                bat_id,
                output_file=f'heatmap_{bat_id}.png'
            )
            print("✓")
        except Exception as e:
            print(f"✗ ({str(e)[:30]}...)")
    
    # Summary
    print("\n" + "="*70)
    print("REPORT GENERATION COMPLETE")
    print("="*70)
    print(f"\n✓ Successfully generated: {len(successful)} individual reports")
    print(f"✗ Failed: {len(failed)} batteries")
    
    if failed:
        print(f"\nFailed batteries: {', '.join(failed)}")
    
    print("\n" + "-"*70)
    print("OUTPUT FILES")
    print("-"*70)
    print("\nGenerated files:")
    output_dir = Path('.')
    for img_file in sorted(output_dir.glob('*.png')):
        size_kb = img_file.stat().st_size / 1024
        print(f"  • {img_file.name} ({size_kb:.0f} KB)")
    
    print("\n" + "="*70 + "\n")


def generate_summary_statistics():
    """Print summary statistics about the dataset."""
    
    print("\n" + "="*70)
    print("DATASET STATISTICS")
    print("="*70 + "\n")
    
    print("Total Discharge Cycles and Degradation:")
    stats = []
    
    for bat_id in sorted(df_discharge['battery_id'].unique()):
        bat_data = df_discharge[df_discharge['battery_id'] == bat_id].copy()
        bat_data = bat_data.sort_values('test_id').reset_index(drop=True)
        
        if len(bat_data) >= 3:
            initial_cap = bat_data['Capacity'].iloc[0]
            final_cap = bat_data['Capacity'].iloc[-1]
            cycles = len(bat_data)
            degradation = (1 - final_cap/initial_cap) * 100
            rate = degradation / cycles
            
            stats.append({
                'Battery': bat_id,
                'Cycles': cycles,
                'Initial (Ahr)': f"{initial_cap:.2f}",
                'Final (Ahr)': f"{final_cap:.2f}",
                'Degradation %': f"{degradation:.1f}%",
                'Rate %/cycle': f"{rate:.3f}%"
            })
    
    if stats:
        df_stats = pd.DataFrame(stats)
        print(df_stats.to_string(index=False))
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--stats':
        generate_summary_statistics()
    else:
        generate_all_reports()
