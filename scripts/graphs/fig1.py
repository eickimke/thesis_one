import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt


world = gpd.read_file("data/replacefilename") # see READ.ME for file download
germany = world[world['ADMIN'] == 'Germany']

positions = {
    'N1': (8.8, 54.0),     
    'N2': (12.5, 53.5),    
    'N3': (10.5, 51.5),    
    'N4': (7.0, 51.5),     
    'N5': (8.0, 49.0),     
    'N6': (11.0, 48.5)     
}
node_map = {1: 'N1', 2: 'N2', 3: 'N3', 4: 'N4', 5: 'N5', 6: 'N6'}

df = pd.read_csv("data/supply_adjusted.csv")  
df['node'] = df['node'].map(node_map)

gen_colors = {
    'onshorewind': 'blue',
    'offshorewind': 'deepskyblue',
    'solar': 'gold',
    'biomass': 'green',
    'otherres': 'lightgreen',
    'gas': 'orange',
    'hardcoal': 'black',
    'lignite': 'saddlebrown',
    'oil': 'gray',
    'waste': 'purple'
}

fig, ax = plt.subplots(figsize=(10, 10))
germany.plot(ax=ax, color='whitesmoke', edgecolor='gray')

for node, (x, y) in positions.items():
    node_data = df[df['node'] == node]
    sizes = node_data.set_index('type')['adjusted_capacity'].reindex(gen_colors.keys()).fillna(0)
    total = sizes.sum()
    if total == 0:
        continue
    ax_inset = fig.add_axes([0, 0, 0.1, 0.1], frameon=False)
    trans = ax.transData.transform((x, y))
    inv = fig.transFigure.inverted().transform(trans)
    ax_inset.set_position([inv[0]-0.03, inv[1]-0.06, 0.12, 0.12])  
    ax_inset.pie(sizes, colors=[gen_colors[t] for t in sizes.index], startangle=90)
    ax_inset.set_aspect('equal')

legend_labels = [plt.Line2D([0], [0], marker='o', color='w', label=label,
                            markerfacecolor=color, markersize=10)
                 for label, color in gen_colors.items()]
ax.legend(handles=legend_labels, title="Generation Type", loc='center left', bbox_to_anchor=(1, 0.5))

ax.set_xlim(5, 15)
ax.set_ylim(47, 55)
ax.set_title("Installed Generation Mix per Node", fontsize=14)
plt.axis('off')
plt.tight_layout()
plt.savefig("outputs/other/fig1.png", dpi=300, bbox_inches='tight')
plt.show()
