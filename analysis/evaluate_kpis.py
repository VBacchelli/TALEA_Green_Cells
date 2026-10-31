import argparse
from itertools import combinations
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

# Valutazione ex-post: stessi dati e stesse assunzioni per ogni modello.
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

# Densità comuni della valutazione ex-post, modificabili senza nuovo solving.
# I default coincidono con quelli di src/data_parser.py; il CSV conserva
# i valori effettivamente usati, anche per STD.
parser = argparse.ArgumentParser(
    description="Confronto ex-post KPI 3 e KPI 300, Jaccard celle e spaziale"
)
parser.add_argument(
    "--tree-density-street",
    type=float,
    default=0.2,
    help="Alberi stimati per m² di strada convertita (default: 0.2)",
)
parser.add_argument(
    "--tree-density-yard",
    type=float,
    default=0.2,
    help="Alberi stimati per m² di cortile convertito (default: 0.2)",
)
parser.add_argument(
    "--spatial-buffer-m",
    type=float,
    default=100.0,
    help="Buffer esterno ai poligoni delle celle, in metri (default: 100)",
)
args = parser.parse_args()
TREE_DENSITY_STREET = args.tree_density_street
TREE_DENSITY_YARD = args.tree_density_yard
SPATIAL_BUFFER_M = args.spatial_buffer_m
# Coefficienti fisici della canopy, uguali per tutti i modelli.
# Default coerenti con src/data_parser.py.
CANOPY_DENSITY_STREET = 0.3
CANOPY_DENSITY_YARD = 0.3
if not (np.isfinite(TREE_DENSITY_STREET) and TREE_DENSITY_STREET >= 0):
    parser.error("--tree-density-street deve essere un numero finito >= 0")
if not (np.isfinite(TREE_DENSITY_YARD) and TREE_DENSITY_YARD >= 0):
    parser.error("--tree-density-yard deve essere un numero finito >= 0")
if not (np.isfinite(SPATIAL_BUFFER_M) and SPATIAL_BUFFER_M > 0):
    parser.error("--spatial-buffer-m deve essere un numero finito > 0")

solutions = {}
for name, folder in models.items():
    path = ROOT / f"results/full/{folder}/default.geojson"
    if not path.is_file():
        print(f"ATTENZIONE: risultato assente per {name}: {path}")
        continue
    solutions[name] = gpd.read_file(path)

if not solutions:
    raise FileNotFoundError("Nessun risultato GeoJSON disponibile")

# Il GeoPackage contiene TUTTI gli edifici iniziali: i denominatori non
# devono escludere quelli irraggiungibili dalle celle candidate.
buildings_path = ROOT / "dataset/processed_data/330300/buildings_330300.gpkg"
if not buildings_path.is_file():
    raise FileNotFoundError(f"Dataset iniziale mancante: {buildings_path}")
buildings = gpd.read_file(
    buildings_path, layer="buildings_330300", ignore_geometry=True
)
required_building_columns = {"building_id", "meet_3", "n_trees_50m", "meet_300"}
if not required_building_columns.issubset(buildings.columns):
    raise ValueError(
        f"Campi mancanti in buildings_330300.gpkg: "
        f"{required_building_columns - set(buildings.columns)}"
    )
if buildings["building_id"].isna().any() or buildings["building_id"].duplicated().any():
    raise ValueError("ID edifici iniziali nulli o duplicati")
for column in ["meet_3", "meet_300"]:
    if (
        buildings[column].isna().any()
        or not buildings[column].isin([0, 1, False, True]).all()
    ):
        raise ValueError(f"Valori {column} non validi nel dataset iniziale")
if buildings["n_trees_50m"].isna().any():
    raise ValueError("Valori n_trees_50m mancanti nel dataset iniziale")

# KPI 3: edifici che non soddisfano la condizione iniziale TALEA.
# 'meet_3' considera già conformi anche gli edifici vicini a un parco.
# Per ciascun altro edificio il deficit d_b è pari a 3 - alberi esistenti.
noncompliant_3 = buildings.loc[
    buildings["meet_3"] == 0, ["building_id", "n_trees_50m"]
].copy()
noncompliant_3["required_trees"] = 3 - noncompliant_3["n_trees_50m"]
if (
    not noncompliant_3["required_trees"].isin([1, 2, 3]).all()
    or not (noncompliant_3["n_trees_50m"] >= 0).all()
):
    raise ValueError("Deficit iniziali del criterio 3 incoerenti")

# Serie indicizzata per edificio: include anche gli edifici senza relazioni.
deficit_3 = noncompliant_3.set_index("building_id")["required_trees"].astype(int)
initial_noncompliant_3 = len(deficit_3)
initial_missing_trees_3 = int(deficit_3.sum())
if initial_noncompliant_3 <= 0 or initial_missing_trees_3 <= 0:
    raise ValueError("Nessun deficit iniziale per il criterio 3")

# KPI 300: stesso denominatore completo già utilizzato nella prima versione.
uncovered_300 = set(buildings.loc[buildings["meet_300"] == 0, "building_id"])
total_deficit_300 = len(uncovered_300)
if total_deficit_300 <= 0:
    raise ValueError("Nessun edificio inizialmente scoperto: P300 non definibile")

# KPI 30: deficit iniziale di canopy per area statistica.
# Il denominatore include anche le aree non raggiungibili dalle celle.
stat_areas_path = ROOT / "dataset/processed_data/330300/stat_areas.gpkg"
stat_areas = gpd.read_file(stat_areas_path, layer="stat_areas").to_crs("EPSG:32632")

required_columns_30 = {"codice_area_statistica", "perc_canopy_cover_30"}
if not required_columns_30.issubset(stat_areas.columns):
    raise ValueError("Campi mancanti nel dataset delle aree statistiche")

if (
    stat_areas["codice_area_statistica"].isna().any()
    or stat_areas["codice_area_statistica"].duplicated().any()
):
    raise ValueError("ID aree statistiche nulli o duplicati")

if stat_areas.geometry.isna().any() or stat_areas.geometry.is_empty.any():
    raise ValueError("Geometrie delle aree statistiche mancanti o vuote")

canopy_pct = stat_areas["perc_canopy_cover_30"].astype(float)
if not (np.isfinite(canopy_pct).all() and canopy_pct.between(0, 100).all()):
    raise ValueError("Percentuali iniziali di canopy non valide")

stat_areas["required_canopy_30"] = (
    stat_areas.geometry.area * (0.30 - canopy_pct / 100)
).clip(lower=0)

# Solo le aree inizialmente non conformi.
deficit_30 = stat_areas.loc[
    stat_areas["required_canopy_30"] > 0,
    ["codice_area_statistica", "required_canopy_30"],
].set_index("codice_area_statistica")["required_canopy_30"]

initial_noncompliant_30 = len(deficit_30)
total_deficit_30 = float(deficit_30.sum())

if initial_noncompliant_30 <= 0 or total_deficit_30 <= 0:
    raise ValueError("Nessun deficit iniziale per il criterio 30")

print(f"Deficit globale canopy: {total_deficit_30:.6f} m²")
print(f"Aree statistiche inizialmente non conformi: {initial_noncompliant_30}")

# Relazioni spaziali precomputate: nessun nuovo calcolo geometrico.
coverage_3 = pd.read_csv(ROOT / "dataset/processed_data/330300/cell_3_coverage.csv")
coverage_300 = pd.read_csv(ROOT / "dataset/processed_data/330300/cell_300_coverage.csv")
coverage_30 = pd.read_csv(ROOT / "dataset/processed_data/330300/cell_30_coverage.csv")

required_30_columns = {
    "cell_id",
    "codice_area_statistica",
    "cell_share",
    "required_canopy_30",
}

if not required_30_columns.issubset(coverage_30.columns):
    raise ValueError("Campi mancanti nel CSV 30")

if coverage_30[list(required_30_columns)].isna().any().any():
    raise ValueError("Valori mancanti nelle relazioni 30")

if coverage_30.duplicated(["cell_id", "codice_area_statistica"]).any():
    raise ValueError("Relazioni cella-area duplicate nel CSV 30")

if not coverage_30["cell_share"].between(0, 1).all():
    raise ValueError("Valori cell_share non validi")

# Ogni relazione deve riferirsi a un'area inizialmente non conforme
# e riportare il deficit iniziale corretto.
expected_deficit_30 = coverage_30["codice_area_statistica"].map(deficit_30)

if (
    expected_deficit_30.isna().any()
    or not np.isclose(
        coverage_30["required_canopy_30"], expected_deficit_30, rtol=1e-9, atol=1e-6
    ).all()
):
    raise ValueError("Relazioni 30 incoerenti con i deficit iniziali")
if not {"cell_id", "building_id", "required_trees"}.issubset(coverage_3.columns):
    raise ValueError("Campi cell_id/building_id/required_trees mancanti nel CSV 3")
if not {"cell_id", "building_id"}.issubset(coverage_300.columns):
    raise ValueError("Campi cell_id/building_id mancanti nel CSV 300")
if (
    coverage_3[["cell_id", "building_id", "required_trees"]].isna().any().any()
    or coverage_300[["cell_id", "building_id"]].isna().any().any()
):
    raise ValueError("ID o deficit nulli nei CSV di copertura")
if coverage_3.duplicated(["cell_id", "building_id"]).any():
    raise ValueError("Relazioni cella-edificio duplicate in cell_3_coverage.csv")
if not set(coverage_300["building_id"]).issubset(uncovered_300):
    raise ValueError("Relazioni 300 incoerenti con gli edifici inizialmente scoperti")

# Le relazioni 3 devono riferirsi a edifici NON conformi e riportare lo
# stesso deficit individuale del GeoPackage, prima di considerare i modelli.
expected_deficit = coverage_3["building_id"].map(deficit_3)
if (
    expected_deficit.isna().any()
    or not coverage_3["required_trees"].eq(expected_deficit).all()
):
    raise ValueError("Relazioni 3 incoerenti con i deficit del GeoPackage")

rows = []
selected_ids_by_model = {}
buffered_areas_by_model = {}
for name, solution in solutions.items():
    required = {"id", "street_cells", "yard_cells"}
    if not required.issubset(solution.columns):
        raise ValueError(
            f"Colonne mancanti nella soluzione {name}: {required - set(solution.columns)}"
        )
    if solution["id"].isna().any() or solution["id"].duplicated().any():
        raise ValueError(f"ID celle nulli o duplicati nella soluzione {name}")
    if solution[["street_cells", "yard_cells"]].isna().any().any():
        raise ValueError(f"Allocazioni nulle nella soluzione {name}")
    if (solution[["street_cells", "yard_cells"]] < 0).any().any():
        raise ValueError(f"Allocazioni negative nella soluzione {name}")

    # Cella attiva = superficie convertita strettamente positiva.
    selected_allocations = solution.loc[
        (solution["street_cells"] + solution["yard_cells"]) > 0,
        ["id", "street_cells", "yard_cells"],
    ].copy()
    selected = selected_allocations["id"]
    # Stesso reticolo per tutti i modelli: il set di ID identifica
    # le posizioni effettivamente scelte, senza conteggi duplicati.
    selected_ids_by_model[name] = set(selected)

    # Jaccard spaziale: l'area di influenza e' l'unione dei poligoni
    # delle celle convertite, ciascuno esteso di 100 m (configurabile).
    # Il buffer va costruito in un CRS metrico, MAI in gradi o EPSG:3857.
    if solution.crs is None:
        raise ValueError(f"Sistema di coordinate assente nella soluzione {name}")
    selected_geometries = solution.loc[selected_allocations.index, ["geometry"]]
    if (
        selected_geometries.geometry.isna().any()
        or selected_geometries.geometry.is_empty.any()
    ):
        raise ValueError(f"Geometrie selezionate mancanti o vuote per {name}")
    if not selected_geometries.geometry.is_valid.all():
        raise ValueError(f"Geometrie selezionate non valide per {name}")
    buffered_areas_by_model[name] = (
        selected_geometries.to_crs("EPSG:32632")
        .geometry.buffer(SPATIAL_BUFFER_M)
        .union_all()
        if not selected_geometries.empty
        else None
    )

    # KPI 300 invariato: un edificio raggiunto da più celle conta una sola volta.
    covered_300 = int(
        coverage_300.loc[
            coverage_300["cell_id"].isin(selected), "building_id"
        ].nunique()
    )
    if covered_300 > total_deficit_300:
        raise ValueError(f"Copertura 300 incoerente per {name}")

    # KPI 3: alberi aggiunti da ogni singola cella attiva, in m² metrici.
    # Il floor si applica PER CELLA, come nel modello MiniZinc.
    selected_allocations["added_trees"] = np.floor(
        TREE_DENSITY_STREET * selected_allocations["street_cells"]
        + TREE_DENSITY_YARD * selected_allocations["yard_cells"]
    ).astype(int)
    trees_by_cell = selected_allocations.set_index("id")["added_trees"]

    # Ogni edificio riceve gli alberi da tutte le celle attive che lo
    # raggiungono (relazioni a 50 m già calcolate dal preprocessing).
    reachable_3 = coverage_3.loc[coverage_3["cell_id"].isin(selected)].copy()
    reachable_3["added_trees"] = reachable_3["cell_id"].map(trees_by_cell)
    if reachable_3["added_trees"].isna().any():
        raise ValueError(f"Relazioni 3 senza allocazione corrispondente per {name}")
    added_trees_by_building = (
        reachable_3.groupby("building_id")["added_trees"]
        .sum()
        .reindex(deficit_3.index, fill_value=0)
    )

    # g_b = min(d_b, alberi aggiunti raggiungibili): il beneficio di ciascun
    # edificio è limitato agli alberi che gli mancavano inizialmente.
    gains_3 = added_trees_by_building.clip(upper=deficit_3)
    new_compliant_3 = int((gains_3 == deficit_3).sum())
    filled_deficit_3 = int(gains_3.sum())

    # KPI 30: canopy aggiunta da ogni cella attiva [m²].
    # Nessun floor: la canopy è una superficie continua.
    selected_allocations["added_canopy"] = (
        CANOPY_DENSITY_STREET * selected_allocations["street_cells"]
        + CANOPY_DENSITY_YARD * selected_allocations["yard_cells"]
    )

    canopy_by_cell = selected_allocations.set_index("id")["added_canopy"]

    # Relazioni tra celle selezionate e aree statistiche.
    reachable_30 = coverage_30.loc[coverage_30["cell_id"].isin(selected)].copy()

    # Distribuzione della canopy attraverso cell_share.
    reachable_30["added_canopy_area"] = (
        reachable_30["cell_id"].map(canopy_by_cell) * reachable_30["cell_share"]
    )

    # Somma dei contributi di tutte le celle per ogni area.
    # Le aree senza celle raggiungibili ricevono beneficio zero.
    added_canopy_by_area = (
        reachable_30.groupby("codice_area_statistica")["added_canopy_area"]
        .sum()
        .reindex(deficit_30.index, fill_value=0.0)
    )

    # Beneficio limitato al deficit iniziale di ogni area.
    gains_30 = added_canopy_by_area.clip(upper=deficit_30)

    # P30: superficie totale del deficit recuperata.
    filled_deficit_30 = float(gains_30.sum())

    # C30: aree inizialmente non conformi che raggiungono il 30%.
    # Tolleranza numerica di 1e-6 m².
    new_compliant_30 = int((added_canopy_by_area >= deficit_30 - 1e-6).sum())

    # Verifica C30: area più vicina alla conformità.
    recovery_ratio_30 = gains_30 / deficit_30

    best_area_id = recovery_ratio_30.idxmax()
    best_recovery_percent = 100 * recovery_ratio_30.loc[best_area_id]

    best_initial_deficit = deficit_30.loc[best_area_id]
    best_added_canopy = gains_30.loc[best_area_id]
    best_remaining_deficit = best_initial_deficit - best_added_canopy

    print(
        f"\n{name} - Verifica C30:"
        f"\n  Area statistica: {best_area_id}"
        f"\n  Deficit iniziale: {best_initial_deficit:.2f} m²"
        f"\n  Canopy recuperata: {best_added_canopy:.2f} m²"
        f"\n  Deficit residuo: {best_remaining_deficit:.2f} m²"
        f"\n  Deficit recuperato: {best_recovery_percent:.4f}%"
        f"\n  Aree diventate conformi: {new_compliant_30}/{initial_noncompliant_30}"
    )

    # P30 medio: media delle percentuali di deficit recuperato
    # nelle 22 aree inizialmente non conformi.
    progress_30_by_area = gains_30 / deficit_30
    P30_mean_percent = 100 * progress_30_by_area.mean()

    # Verifica indipendente di C30:
    # ricostruiamo la percentuale effettiva di canopy post-intervento.
    areas_30 = stat_areas.set_index("codice_area_statistica").loc[deficit_30.index]

    initial_pct = areas_30["perc_canopy_cover_30"].astype(float)
    area_m2 = areas_30.geometry.area

    final_pct = initial_pct + 100 * added_canopy_by_area / area_m2

    # Stessa tolleranza di 1e-6 m² usata nel calcolo di C30.
    recomputed_compliant = int((final_pct >= 30 - 100 * 1e-6 / area_m2).sum())

    if recomputed_compliant != new_compliant_30:
        raise ValueError(f"C30 incoerente per {name}")

    print(
        f"\n{name} - Criterio 30:"
        f"\n  P30 globale: {100 * filled_deficit_30 / total_deficit_30:.4f}%"
        f"\n  P30 medio per area: {P30_mean_percent:.4f}%"
        f"\n  C30: {new_compliant_30}/{initial_noncompliant_30}"
        f"\n  Massima canopy post-intervento: {final_pct.max():.4f}%"
    )

    rows.append(
        {
            "model": name,
            "tree_density_street": TREE_DENSITY_STREET,
            "tree_density_yard": TREE_DENSITY_YARD,
            "selected_cells": int(selected.nunique()),
            "initial_noncompliant_buildings_3": initial_noncompliant_3,
            "initial_missing_trees_3": initial_missing_trees_3,
            "new_buildings_meeting_3": new_compliant_3,
            "C3_percent": 100 * new_compliant_3 / initial_noncompliant_3,
            "P3_percent": 100 * filled_deficit_3 / initial_missing_trees_3,
            "canopy_density_street": CANOPY_DENSITY_STREET,
            "canopy_density_yard": CANOPY_DENSITY_YARD,
            "initial_noncompliant_areas_30": initial_noncompliant_30,
            "initial_missing_canopy_30_m2": total_deficit_30,
            "recovered_canopy_30_m2": filled_deficit_30,
            "new_areas_meeting_30": new_compliant_30,
            "P30_percent": 100 * filled_deficit_30 / total_deficit_30,
            "C30_percent": 100 * new_compliant_30 / initial_noncompliant_30,
            "initial_uncovered_buildings": total_deficit_300,
            "new_buildings_covered": covered_300,
            "P300_percent": 100 * covered_300 / total_deficit_300,
        }
    )

comparison = pd.DataFrame(rows)
print(comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

# Un unico confronto, estendibile al KPI 30 nel prossimo passo.
output = ROOT / "analysis/kpi_comparison.csv"
output.parent.mkdir(parents=True, exist_ok=True)
comparison.to_csv(output, index=False)
print(f"\nConfronto salvato in: {output}")

# Jaccard tra posizioni esatte e tra zone di influenza delle celle.
# Il primo confronta gli ID delle celle; il secondo confronta superfici
# geometriche dopo un buffer di 100 m intorno ai POLIGONI selezionati.
# Le geometrie sono gia' in EPSG:32632 (metri), non in EPSG:3857.
jaccard_rows = []
for (model_a, ids_a), (model_b, ids_b) in combinations(
    selected_ids_by_model.items(), 2
):
    common = len(ids_a & ids_b)
    union = len(ids_a | ids_b)

    geom_a = buffered_areas_by_model[model_a]
    geom_b = buffered_areas_by_model[model_b]
    if geom_a is None or geom_b is None:
        # Se uno dei due insiemi e' vuoto, la sovrapposizione e' zero;
        # se lo sono entrambi, il Jaccard non e' definito.
        spatial_intersection = 0.0
        spatial_union = (geom_a.area if geom_a is not None else 0.0) + (
            geom_b.area if geom_b is not None else 0.0
        )
    else:
        spatial_intersection = geom_a.intersection(geom_b).area
        spatial_union = geom_a.union(geom_b).area

    jaccard_rows.append(
        {
            "model_a": model_a,
            "model_b": model_b,
            "selected_cells_a": len(ids_a),
            "selected_cells_b": len(ids_b),
            "common_cells": common,
            "union_cells": union,
            "jaccard_percent": 100 * common / union if union else float("nan"),
            "spatial_buffer_m": SPATIAL_BUFFER_M,
            "spatial_intersection_m2": spatial_intersection,
            "spatial_union_m2": spatial_union,
            "spatial_jaccard_percent": (
                100 * spatial_intersection / spatial_union
                if spatial_union > 0
                else float("nan")
            ),
        }
    )

jaccard_comparison = pd.DataFrame(jaccard_rows)
if not jaccard_comparison.empty:
    print("\nJaccard celle esatte e spaziale (buffer sui poligoni):")
    print(jaccard_comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

jaccard_output = ROOT / "analysis/jaccard_comparison.csv"
jaccard_comparison.to_csv(jaccard_output, index=False)
print(f"Confronto Jaccard salvato in: {jaccard_output}")
