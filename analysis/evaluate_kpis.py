from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "dataset").is_dir() and (parent / "results").is_dir()
)

models = {
    "STD": "std",
    "Counterfactual": "std_330300",
    "MaxCoverage": "std_330300_maxcoverage",
}

# Carica i risultati disponibili senza attribuire KPI ai modelli assenti.
solutions = {}
for name, folder in models.items():
    path = ROOT / f"results/full/{folder}/default.geojson"
    if not path.is_file():
        print(f"ATTENZIONE: risultato assente per {name}: {path}")
        continue
    solutions[name] = gpd.read_file(path)

if not solutions:
    raise FileNotFoundError("Nessun risultato GeoJSON disponibile")

# Relazioni precalcolate tra celle candidate ed edifici inizialmente scoperti.
coverage = pd.read_csv(
    ROOT / "dataset/processed_data/330300/cell_300_coverage.csv"
)
if not {"cell_id", "building_id"}.issubset(coverage.columns):
    raise ValueError("Colonne cell_id/building_id mancanti in cell_300_coverage.csv")
if coverage[["cell_id", "building_id"]].isna().any().any():
    raise ValueError("ID nulli in cell_300_coverage.csv")

# Denominatore: tutti gli edifici inizialmente scoperti, anche quelli
# irraggiungibili da qualunque cella candidata.
buildings_path = ROOT / "dataset/processed_data/330300/buildings_330300.gpkg"
if not buildings_path.is_file():
    raise FileNotFoundError(f"Dataset iniziale mancante: {buildings_path}")

buildings = gpd.read_file(
    buildings_path, layer="buildings_330300", ignore_geometry=True
)
if not {"building_id", "meet_300"}.issubset(buildings.columns):
    raise ValueError("Colonne building_id/meet_300 mancanti in buildings_330300.gpkg")
if buildings["building_id"].isna().any() or buildings["building_id"].duplicated().any():
    raise ValueError("ID edifici iniziali nulli o duplicati")
if buildings["meet_300"].isna().any() or not buildings["meet_300"].isin([0, 1, False, True]).all():
    raise ValueError("Valori meet_300 non validi nel dataset iniziale")

uncovered_ids = set(buildings.loc[buildings["meet_300"] == 0, "building_id"])
total_deficit = len(uncovered_ids)
if total_deficit <= 0:
    raise ValueError("Nessun edificio inizialmente scoperto: P300 non definibile")

# Il CSV deve riferirsi agli stessi edifici inizialmente scoperti.
if not set(coverage["building_id"]).issubset(uncovered_ids):
    raise ValueError("Relazioni 300 incoerenti con buildings_330300.gpkg")

rows = []
for name, solution in solutions.items():
    required = {"id", "street_cells", "yard_cells"}
    if not required.issubset(solution.columns):
        raise ValueError(f"Colonne mancanti nella soluzione {name}: {required - set(solution.columns)}")
    if solution["id"].isna().any() or solution["id"].duplicated().any():
        raise ValueError(f"ID celle nulli o duplicati nella soluzione {name}")
    if solution[["street_cells", "yard_cells"]].isna().any().any():
        raise ValueError(f"Allocazioni nulle nella soluzione {name}")

    selected = solution.loc[
        (solution["street_cells"] + solution["yard_cells"]) > 0,
        "id",
    ]
    covered = int(coverage.loc[
        coverage["cell_id"].isin(selected), "building_id"
    ].nunique())

    if covered > total_deficit:
        raise ValueError(f"Dati di copertura 300 incoerenti per {name}")

    rows.append({
        "model": name,
        "selected_cells": int(selected.nunique()),
        "initial_uncovered_buildings": total_deficit,
        "new_buildings_covered": covered,
        "P300_percent": 100 * covered / total_deficit,
    })

comparison = pd.DataFrame(rows)
print(comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

output = ROOT / "analysis/kpi300_comparison.csv"
output.parent.mkdir(parents=True, exist_ok=True)
comparison.to_csv(output, index=False)
print(f"\nConfronto salvato in: {output}")
