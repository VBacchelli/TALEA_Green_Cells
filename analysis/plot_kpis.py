"""Plot the trade-off between TALEA utility and post-hoc 3-30-300 KPIs.

Consumes the CSV produced by evaluate_kpis.py; never recomputes or changes KPIs.
Usage:
    python3 analysis/plot_kpis.py --scenario default
    python3 analysis/plot_kpis.py --scenario gamma_0
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Headless Docker runs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    "default",
    "gamma_0", "gamma_low", "gamma_medium", "gamma_high",
    "tree_density_low", "tree_density_medium", "tree_density_high",
)
COLORS = {
    "STD": "#526276",
    "Counterfactual": "#D98234",
    "MaxCoverage": "#167F82",
}


def plot_tradeoff(csv_path: Path, output_dir: Path, scenario: str) -> tuple[Path, Path]:
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Missing KPI comparison: {csv_path}. "
            f"Run evaluate_kpis.py --scenario {scenario} first."
        )

    data = pd.read_csv(csv_path)
    required = {
        "model", "KPI_330300_percent", "TALEA_utility_change_percent",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")
    if data.empty or data["model"].isna().any() or data["model"].duplicated().any():
        raise ValueError("Model labels must be present and unique.")

    for column in ("KPI_330300_percent", "TALEA_utility_change_percent"):
        data[column] = pd.to_numeric(data[column], errors="raise")
        if not np.isfinite(data[column].to_numpy()).all():
            raise ValueError(f"Non-finite values in {column}.")

    baseline = data.loc[data["model"] == "STD"]
    if len(baseline) != 1:
        raise ValueError("The comparison must contain exactly one STD baseline.")

    std_kpi = float(baseline["KPI_330300_percent"].iloc[0])
    data["delta_kpi_pp"] = data["KPI_330300_percent"] - std_kpi

    std_change = float(baseline["TALEA_utility_change_percent"].iloc[0])
    if not np.isclose(std_change, 0.0, atol=1e-6, rtol=0):
        raise ValueError("STD utility change must be zero.")

    # Merge coincident points (all three models coincide in gamma_0).
    groups = []
    for row in data.itertuples(index=False):
        x = float(row.TALEA_utility_change_percent)
        y = float(row.delta_kpi_pp)
        match = next(
            (g for g in groups
             if np.isclose(g["x"], x, atol=1e-5, rtol=0)
             and np.isclose(g["y"], y, atol=1e-5, rtol=0)),
            None,
        )
        if match is None:
            groups.append({"x": x, "y": y, "models": [row.model]})
        else:
            match["models"].append(row.model)

    fig, ax = plt.subplots(figsize=(10.5, 6.2), constrained_layout=True)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.axvline(0, color="#8F9BA7", linestyle="--", linewidth=1)
    ax.axhline(0, color="#8F9BA7", linestyle="--", linewidth=1)
    ax.grid(color="#E8ECEF", linewidth=0.8)
    ax.set_axisbelow(True)

    for group in groups:
        models = group["models"]
        color = COLORS.get(models[0], "#364153") if len(models) == 1 else "#364153"
        ax.scatter(
            group["x"], group["y"], s=115, color=color,
            edgecolors="white", linewidths=1.5, zorder=3,
        )
        label = " / ".join(models)
        ax.annotate(
            label,
            xy=(group["x"], group["y"]),
            xytext=(9, 10), textcoords="offset points",
            fontsize=10, color="#253344", weight="medium",
        )

    x = data["TALEA_utility_change_percent"].to_numpy(dtype=float)
    y = data["delta_kpi_pp"].to_numpy(dtype=float)
    x_min, x_max = float(min(x.min(), 0)), float(max(x.max(), 0))
    y_min, y_max = float(min(y.min(), 0)), float(max(y.max(), 0))
    x_span = max(x_max - x_min, 1.0)
    y_span = max(y_max - y_min, 0.5)
    ax.set_xlim(x_min - 0.12 * x_span, x_max + 0.34 * x_span)
    ax.set_ylim(y_min - 0.19 * y_span, y_max + 0.32 * y_span)

    ax.set_title(
        "3-30-300 improvement vs. original TALEA utility",
        fontsize=15, fontweight="semibold", loc="left", pad=18,
    )
    ax.set_xlabel("Change in original TALEA utility vs. STD (%)", fontsize=11)
    ax.set_ylabel("Change in composite 3-30-300 KPI (percentage points)", fontsize=11)
    ax.text(
        0.0, -0.15,
        f"Scenario: {scenario}   |   Composite KPI = mean(P3, P30, P300)   |   STD is the reference",
        transform=ax.transAxes, fontsize=9, color="#596575",
    )
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_dir / f"tradeoff_{scenario}"
    png_path = stem.with_suffix(".png")
    svg_path = stem.with_suffix(".svg")
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)
    return png_path, svg_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="default")
    args = parser.parse_args()

    suffix = "" if args.scenario == "default" else f"_{args.scenario}"
    csv_path = ROOT / "analysis" / f"kpi_comparison{suffix}.csv"
    output_dir = ROOT / "analysis" / "plots"

    png_path, svg_path = plot_tradeoff(csv_path, output_dir, args.scenario)
    print(f"PNG saved to: {png_path}")
    print(f"SVG saved to: {svg_path}")


if __name__ == "__main__":
    main()
