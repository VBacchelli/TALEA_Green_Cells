import geopandas as gpd
import pandas as pd

GRID = "dataset/processed_data/full/aree_statistiche_grid.geojson"
INDEX = "dataset/processed_data/330300/bologna_3_30_300_stat_areas.csv"

MODELS = ["std", "diff", "inverse_uhei", "ndvi"]

grid = gpd.read_file(GRID)
idx = pd.read_csv(INDEX)

components = {}

for row in idx.itertuples():
    d3 = (100.0 - row.perc_buildings_near_3_trees) / 100.0
    d30 = max(0.0, (30.0 - row.perc_canopy_cover_30) / 30.0)
    d300 = (100.0 - row.perc_buildings_within_300m_park) / 100.0

    components[row.stat_area_id] = (d3, d30, d300)


def cell_330300(cell_id):
    parts = grid[grid["id"] == cell_id]

    d3 = d30 = d300 = 0.0

    for row in parts.itertuples():
        c3, c30, c300 = components[row.codice_area_statistica]
        weight = row.intersect_area_statistica / 10000.0

        d3 += c3 * weight
        d30 += c30 * weight
        d300 += c300 * weight

    return (d3 + d30 + d300) / 3.0


rows = []

for model in MODELS:
    a = gpd.read_file(
        f"results_original/full/{model}/default.geojson"
    )
    b = gpd.read_file(
        f"results_330300/full/{model}/default.geojson"
    )

    ids_a = set(a["id"])
    ids_b = set(b["id"])

    common = ids_a & ids_b
    only_a = ids_a - ids_b
    only_b = ids_b - ids_a
    union = ids_a | ids_b

    jaccard = len(common) / len(union)

    f_out = [cell_330300(i) for i in only_a]
    f_in = [cell_330300(i) for i in only_b]

    rows.append({
        "modello": model,
        "celle_sostituite": len(only_a),
        "percentuale": 100 * len(only_a) / len(ids_a),
        "jaccard": jaccard,
        "f330300_entrano": sum(f_in) / len(f_in),
        "f330300_escono": sum(f_out) / len(f_out),
    })

df = pd.DataFrame(rows)

print(
    df.round({
        "percentuale": 1,
        "jaccard": 4,
        "f330300_entrano": 4,
        "f330300_escono": 4,
    }).to_string(index=False)
)