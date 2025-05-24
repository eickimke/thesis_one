import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


df = pd.read_csv('data/weatherprofiles.csv')

def plot_scenario(scenario, title, output_file):
    df_s = df[df['scenario'] == scenario].copy()
    data = np.array([
        df_s['onshorewind_profile'].values,
        df_s['solar_profile'].values
    ])
    
    fig, ax = plt.subplots(figsize=(8, 3))

    for i, row in enumerate(data):
        global_min = data.min()
        global_max = data.max()
        normalized = (row - global_min) / (global_max - global_min)
        for j, val in enumerate(row):
            alpha = normalized[j]
            if i == 0:
                color = (0.4, 0.6, 0.8, alpha)  
            else:
                color = (0.9, 0.5, 0.5, alpha)  
            ax.add_patch(plt.Rectangle((j, 1 - i), 1, 1, color=color))
            ax.text(j + 0.5, 1 - i + 0.5, f"{val:.2f}", ha='center', va='center', fontsize=9, color='black')

    # Axis labels and ticks
    ax.set_xticks(np.arange(0.5, 6.5, 1))
    ax.set_xticklabels([f'N{i}' for i in range(1, 7)], fontsize=10)
    ax.set_yticks([0.5, 1.5])
    ax.set_yticklabels(['Solar', 'Wind'], fontsize=10)

    ax.set_title(title, fontsize=12)
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 2)
    ax.invert_yaxis()
    ax.set_aspect('equal')
    ax.tick_params(left=False, bottom=False)
    ax.grid(False)
    plt.box(False)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.show()


plot_scenario('hw', 'High Wind', 'outputs/other/high_wind_heatmap.png')
plot_scenario('hs', 'High Solar', 'outputs/other/high_solar_heatmap.png')
plot_scenario('lwls', 'Low Wind Low Solar', 'outputs/other/low_wind_solar_heatmap.png')
