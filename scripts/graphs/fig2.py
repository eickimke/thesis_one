import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx

world = gpd.read_file("data/replacefilename") #see README.md for file download
print(world.columns)
germany = world[world['ADMIN'] == 'Germany']

positions = {
    'N1': (8.8, 53.5),   # Bremen/Hamburg/Lower Saxony/Schleswig-Holstein
    'N2': (13.5, 53.0),  # Berlin/Brandenburg/Mecklenburg-Vorpommern
    'N3': (11.5, 51.2),  # Hesse/Thuringia/Saxony-Anhalt
    'N4': (7.0, 51.5),   # North-Rhine-Westphalia
    'N5': (8.0, 49.0),   # Baden-Württemberg/RLP/Saarland
    'N6': (12.0, 49.5)   # Bavaria/Saxony
}

edges = [
    ('N1', 'N2', 2000),
    ('N1', 'N3', 3000),
    ('N1', 'N4', 2500),
    ('N2', 'N3', 2500),
    ('N3', 'N5', 3000),
    ('N3', 'N6', 2500),
    ('N4', 'N5', 2000),
    ('N5', 'N6', 1500)
]

G = nx.Graph()
for node in positions:
    G.add_node(node)
for n1, n2, cap in edges:
    G.add_edge(n1, n2, capacity=cap)

fig, ax = plt.subplots(figsize=(10, 10))
germany.plot(ax=ax, color='whitesmoke', edgecolor='gray')

nx.draw_networkx_nodes(G, pos=positions, ax=ax, node_size=500, node_color='skyblue')
nx.draw_networkx_labels(G, pos=positions, ax=ax, font_size=12)
nx.draw_networkx_edges(G, pos=positions, ax=ax, width=2, edge_color='gray')
edge_labels = {(u, v): f"{d['capacity']} MW" for u, v, d in G.edges(data=True)}
nx.draw_networkx_edge_labels(G, pos=positions, edge_labels=edge_labels, ax=ax, font_size=9)

ax.set_title("Stylised German Power Network (Nodal Overlay)", fontsize=14)
ax.set_xlim(5, 15)
ax.set_ylim(47, 55)
plt.axis('off')
plt.tight_layout()
plt.savefig("outputs/other/fig2.png", dpi=300)
plt.show()
