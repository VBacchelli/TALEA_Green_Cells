import argparse
from collections import Counter
import pandas as pd
from pathlib import Path

import geopandas as gpd

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

STAT_AREAS = "dataset/processed_data/aree_statistiche_stat.geojson"

GRID_AREAS = "dataset/processed_data/full/aree_statistiche_grid.geojson"

INDEX_330300 = "dataset/processed_data/330300/bologna_3_30_300_stat_areas.csv"


def predominant_area(cell_id, grid_areas):
    parts = grid_areas[grid_areas["id"] == cell_id]

    if parts.empty:
        return None

    return (
        parts.sort_values(
            "intersect_area_statistica",
            ascending=False
        )
        .iloc[0]["codice_area_statistica"]
    )


def cell_330300(cell_id, grid_areas, components):
    parts = grid_areas[grid_areas["id"] == cell_id]

    d3 = 0.0
    d30 = 0.0
    d300 = 0.0

    for row in parts.itertuples():
        c3, c30, c300 = components[row.codice_area_statistica]
        weight = row.intersect_area_statistica / 10000.0

        d3 += c3 * weight
        d30 += c30 * weight
        d300 += c300 * weight

    return d3, d30, d300


def main():
    parser = argparse.ArgumentParser(
        description="Confronta due risultati TALEA."
    )

    parser.add_argument("--a", required=True, help="GeoJSON della run A")
    parser.add_argument("--b", required=True, help="GeoJSON della run B")
    parser.add_argument(
        "--maps",
        action="store_true",
        help="Genera anche le mappe di confronto."
    )
    parser.add_argument(
        "--outdir",
        default="analysis/compare_scenario",
        help="Cartella di output per tabelle e mappe."
    )

    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    a = gpd.read_file(args.a)
    b = gpd.read_file(args.b)

    ids_a = set(a["id"])
    ids_b = set(b["id"])

    common = ids_a & ids_b
    only_a = ids_a - ids_b
    only_b = ids_b - ids_a
    union = ids_a | ids_b

    jaccard = len(common) / len(union) if union else 1.0

    # --------------------------------------------------
    # GLOBAL
    # --------------------------------------------------

    print("\nGLOBAL")
    print("=" * 60)
    print(f"Celle selezionate A: {len(ids_a)}")
    print(f"Celle selezionate B: {len(ids_b)}")
    print(f"Celle comuni:        {len(common)}")
    print(f"Celle che escono:    {len(only_a)}")
    print(f"Celle che entrano:   {len(only_b)}")
    print(f"Jaccard:              {jaccard:.4f}")

    print("\nEscono:")
    print(sorted(only_a))

    print("\nEntrano:")
    print(sorted(only_b))

    # --------------------------------------------------
    # AREE STATISTICHE
    # --------------------------------------------------

    grid_areas = gpd.read_file(GRID_AREAS)

    areas_a = [
        predominant_area(cell_id, grid_areas)
        for cell_id in ids_a
    ]

    areas_b = [
        predominant_area(cell_id, grid_areas)
        for cell_id in ids_b
    ]

    counts_a = Counter(areas_a)
    counts_b = Counter(areas_b)

    all_areas = sorted(set(counts_a) | set(counts_b))

    print("\n\nAREE STATISTICHE")
    print("=" * 60)
    print(
        f"{'Area':>6} "
        f"{'A':>5} "
        f"{'B':>5} "
        f"{'Delta':>7} "
        f"{'Variazione':>12}"
    )

    for area in all_areas:
        before = counts_a[area]
        after = counts_b[area]
        delta = after - before

        # Mostriamo solo le aree che cambiano
        if delta == 0:
            continue

        if before == 0:
            variation = "nuova area"
        else:
            variation = f"{100 * delta / before:+.1f}%"

        print(
            f"{int(area):>6} "
            f"{before:>5} "
            f"{after:>5} "
            f"{delta:>+7} "
            f"{variation:>12}"
        )

    # --------------------------------------------------
    # MAPPA AREE STATISTICHE
    # --------------------------------------------------

    if args.maps:
        stat_areas = gpd.read_file(STAT_AREAS)

        map_rows = []

        only_a_areas = Counter(
            predominant_area(cell_id, grid_areas)
            for cell_id in only_a
        )
        only_b_areas = Counter(
            predominant_area(cell_id, grid_areas)
            for cell_id in only_b
        )

        touched_areas = sorted(set(only_a_areas) | set(only_b_areas))

        for area in touched_areas:
            before = counts_a[area]
            after = counts_b[area]
            out_count = only_a_areas[area]
            in_count = only_b_areas[area]
            delta = after - before

            if delta > 0:
                category = "gain"
            elif delta < 0:
                category = "loss"
            else:
                category = "turnover"

            map_rows.append({
                "codice_area_statistica": area,
                "A": before,
                "B": after,
                "delta": delta,
                "in_count": in_count,
                "out_count": out_count,
                "category": category,
            })

        map_df = pd.DataFrame(map_rows)

        mappa = stat_areas.merge(
            map_df,
            on="codice_area_statistica",
            how="left"
        )

        fig, ax = plt.subplots(figsize=(11, 11))

        # sfondo
        mappa.plot(
            ax=ax,
            facecolor="#f2f2f2",
            edgecolor="#bdbdbd",
            linewidth=0.6
        )

        positive = mappa[mappa["category"] == "gain"]
        negative = mappa[mappa["category"] == "loss"]
        turnover = mappa[mappa["category"] == "turnover"]

        if not positive.empty:
            positive.plot(
                ax=ax,
                color="#2ca25f",
                edgecolor="#006d2c",
                linewidth=1
            )

        if not negative.empty:
            negative.plot(
                ax=ax,
                color="#de2d26",
                edgecolor="#a50f15",
                linewidth=1
            )

        if not turnover.empty:
            turnover.plot(
                ax=ax,
                color="#fdd835",
                edgecolor="#b8860b",
                linewidth=1
            )

        # Etichette: area + numero di celle prima e dopo
        changed_areas = mappa[mappa["delta"].notna()]

        for _, row in changed_areas.iterrows():
            p = row.geometry.representative_point()

            if row["category"] == "turnover":
                label = (
                    f"{int(row['codice_area_statistica'])}\n"
                    f"↔ {int(row['in_count'])}"
                )
            else:
                label = (
                    f"{int(row['codice_area_statistica'])}\n"
                    f"{int(row['A'])}→{int(row['B'])}"
                )

            ax.text(
                p.x,
                p.y,
                label,
                ha="center",
                va="center",
                fontsize=7,
                fontweight="bold"
            )

        legend = [
            Patch(
                facecolor="#2ca25f",
                edgecolor="#006d2c",
                label="Aumento Green Cells"
            ),
            Patch(
                facecolor="#de2d26",
                edgecolor="#a50f15",
                label="Diminuzione Green Cells"
            ),
            Patch(
                facecolor="#fdd835",
                edgecolor="#b8860b",
                label="Stesso numero, celle diverse"
            ),
        ]

        ax.legend(handles=legend, loc="lower left")

        ax.set_title(
            "Redistribuzione delle Green Cells\n"
            "baseline → 3-30-300"
        )

        ax.set_axis_off()

        model_name = Path(args.b).parent.name
        scenario_name = Path(args.b).stem

        scenario_outdir = outdir / scenario_name
        scenario_outdir.mkdir(parents=True, exist_ok=True)

        output_map = scenario_outdir / f"{model_name}_statistical_areas_changes.png"

        plt.tight_layout()
        plt.savefig(
            output_map,
            dpi=250,
            bbox_inches="tight"
        )
        plt.close()

        print(f"\nMappa salvata in: {output_map}")

    # --------------------------------------------------
    # 3-30-300
    # --------------------------------------------------

    idx = pd.read_csv(INDEX_330300)

    components = {}

    for row in idx.itertuples():
        d3 = (100.0 - row.perc_buildings_near_3_trees) / 100.0
        d30 = max(
            0.0,
            (30.0 - row.perc_canopy_cover_30) / 30.0
        )
        d300 = (
            100.0 - row.perc_buildings_within_300m_park
        ) / 100.0

        components[row.stat_area_id] = (d3, d30, d300)

    rows = []

    for status, ids in [
        ("escono", only_a),
        ("entrano", only_b),
    ]:
        for cell_id in ids:
            d3, d30, d300 = cell_330300(
                cell_id,
                grid_areas,
                components
            )

            rows.append({
                "status": status,
                "d3": d3,
                "d30": d30,
                "d300": d300,
                "f330300": (d3 + d30 + d300) / 3.0,
            })

    df_330300 = pd.DataFrame(rows)

    print("\n\n3-30-300")
    print("=" * 60)

    print(
        df_330300
        .groupby("status")[["d3", "d30", "d300", "f330300"]]
        .mean()
        .round(4)
        .to_string()
    )


if __name__ == "__main__":
    main()
