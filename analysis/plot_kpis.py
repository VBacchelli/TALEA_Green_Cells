"""Plot TALEA utility trade-off and disaggregated 3-30-300 KPIs.

Reads results produced by evaluate_kpis.py.
Does not recompute KPIs or run optimization models.

Usage:
    python3 analysis/plot_kpis.py --scenario default
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SCENARIOS = (
    "default",
    "gamma_0",
    "gamma_low",
    "gamma_medium",
    "gamma_high",
    "tree_density_low",
    "tree_density_medium",
    "tree_density_high",
)

MODELS = ("STD", "Counterfactual", "MaxCoverage")

COLORS = {
    "STD": "#526276",
    "Counterfactual": "#D98234",
    "MaxCoverage": "#167F82",
}


def load_kpis(csv_path):
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Missing KPI comparison: {csv_path}. " "Run evaluate_kpis.py first."
        )

    data = pd.read_csv(csv_path)

    required = {
        "model",
        "P3_percent",
        "P30_percent",
        "P300_percent",
        "KPI_330300_percent",
        "TALEA_utility_change_percent",
    }

    missing = required - set(data.columns)

    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")

    if data["model"].isna().any() or data["model"].duplicated().any():
        raise ValueError("Model labels must be present and unique.")

    if set(data["model"]) != set(MODELS):
        raise ValueError(f"Expected models: {MODELS}; got {data['model'].tolist()}")

    numeric_columns = required - {"model"}

    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="raise")

        if not np.isfinite(data[column].to_numpy()).all():
            raise ValueError(f"Non-finite values in {column}")

    return data.set_index("model").loc[list(MODELS)].reset_index()


def save_figure(fig, output_dir, stem):
    output_dir.mkdir(parents=True, exist_ok=True)

    png_path = output_dir / f"{stem}.png"
    svg_path = output_dir / f"{stem}.svg"

    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")

    plt.close(fig)

    print(f"PNG saved to: {png_path}")
    print(f"SVG saved to: {svg_path}")


def plot_tradeoff(data, output_dir, scenario):
    std_kpi = float(
        data.loc[
            data["model"] == "STD",
            "KPI_330300_percent",
        ].iloc[0]
    )

    data = data.copy()

    data["delta_kpi_pp"] = data["KPI_330300_percent"] - std_kpi

    std_change = float(
        data.loc[
            data["model"] == "STD",
            "TALEA_utility_change_percent",
        ].iloc[0]
    )

    if not np.isclose(std_change, 0.0, atol=1e-6, rtol=0):
        raise ValueError("STD utility change must be zero.")

    # Merge coincident points, e.g. gamma_0.
    groups = []

    for row in data.itertuples(index=False):
        x = float(row.TALEA_utility_change_percent)
        y = float(row.delta_kpi_pp)

        match = next(
            (
                group
                for group in groups
                if np.isclose(group["x"], x, atol=1e-5, rtol=0)
                and np.isclose(group["y"], y, atol=1e-5, rtol=0)
            ),
            None,
        )

        if match is None:
            groups.append(
                {
                    "x": x,
                    "y": y,
                    "models": [row.model],
                }
            )
        else:
            match["models"].append(row.model)

    fig, ax = plt.subplots(
        figsize=(10.5, 6.2),
        constrained_layout=True,
    )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.axvline(
        0,
        color="#8F9BA7",
        linestyle="--",
        linewidth=1,
    )

    ax.axhline(
        0,
        color="#8F9BA7",
        linestyle="--",
        linewidth=1,
    )

    ax.grid(color="#E8ECEF", linewidth=0.8)
    ax.set_axisbelow(True)

    for group in groups:
        models = group["models"]

        color = COLORS.get(models[0], "#364153") if len(models) == 1 else "#364153"

        ax.scatter(
            group["x"],
            group["y"],
            s=115,
            color=color,
            edgecolors="white",
            linewidths=1.5,
            zorder=3,
        )

        ax.annotate(
            " / ".join(models),
            xy=(group["x"], group["y"]),
            xytext=(9, 10),
            textcoords="offset points",
            fontsize=10,
            color="#253344",
            weight="medium",
        )

    x = data["TALEA_utility_change_percent"].to_numpy()
    y = data["delta_kpi_pp"].to_numpy()

    x_min, x_max = float(min(x.min(), 0)), float(max(x.max(), 0))
    y_min, y_max = float(min(y.min(), 0)), float(max(y.max(), 0))

    x_span = max(x_max - x_min, 1.0)
    y_span = max(y_max - y_min, 0.5)

    ax.set_xlim(
        x_min - 0.12 * x_span,
        x_max + 0.34 * x_span,
    )

    ax.set_ylim(
        y_min - 0.19 * y_span,
        y_max + 0.32 * y_span,
    )

    ax.set_title(
        "3-30-300 improvement vs. original TALEA utility",
        fontsize=15,
        fontweight="semibold",
        loc="left",
        pad=18,
    )

    ax.set_xlabel(
        "Change in original TALEA utility vs. STD (%)",
        fontsize=11,
    )

    ax.set_ylabel(
        "Change in composite 3-30-300 KPI (percentage points)",
        fontsize=11,
    )

    ax.text(
        0.0,
        -0.15,
        (
            f"Scenario: {scenario}   |   "
            "Composite KPI = mean(P3, P30, P300)   |   "
            f"STD baseline = {std_kpi:.3f}%"
        ),
        transform=ax.transAxes,
        fontsize=9,
        color="#596575",
    )

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    save_figure(
        fig,
        output_dir,
        f"tradeoff_{scenario}",
    )


def plot_kpi_components(data, output_dir, scenario):
    """Grouped bar chart for P3, P30 and P300."""

    metrics = [
        ("P3_percent", "P3"),
        ("P30_percent", "P30"),
        ("P300_percent", "P300"),
    ]

    x = np.arange(len(metrics))
    bar_width = 0.24

    fig, ax = plt.subplots(
        figsize=(10.5, 6.2),
        constrained_layout=True,
    )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    for model_index, model in enumerate(MODELS):
        model_data = data.loc[data["model"] == model].iloc[0]

        values = [float(model_data[column]) for column, _ in metrics]

        positions = x + (model_index - 1) * bar_width

        bars = ax.bar(
            positions,
            values,
            width=bar_width,
            label=model,
            color=COLORS[model],
            edgecolor="white",
            linewidth=0.7,
            zorder=3,
        )

        ax.bar_label(
            bars,
            labels=[f"{value:.2f}%" for value in values],
            padding=4,
            fontsize=8.5,
            color="#253344",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [label for _, label in metrics],
        fontsize=11,
    )

    ax.set_ylabel(
        "Recovered initial deficit (%)",
        fontsize=11,
    )

    ax.set_title(
        "3-30-300 KPI components by optimization model",
        fontsize=15,
        fontweight="semibold",
        loc="left",
        pad=18,
    )

    max_value = max(float(data[column].max()) for column, _ in metrics)

    ax.set_ylim(0, max_value * 1.18)

    ax.yaxis.grid(
        True,
        color="#E8ECEF",
        linewidth=0.8,
    )

    ax.set_axisbelow(True)

    ax.legend(
        loc="upper left",
        frameon=False,
        ncol=3,
        fontsize=10,
    )

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax.text(
        0.0,
        -0.15,
        (
            f"Scenario: {scenario}   |   "
            "P3: trees   |   "
            "P30: canopy   |   "
            "P300: park accessibility"
        ),
        transform=ax.transAxes,
        fontsize=9,
        color="#596575",
    )

    save_figure(
        fig,
        output_dir,
        f"kpi_components_{scenario}",
    )



def plot_kpi_relative_changes(data, output_dir, scenario):
    """Relative percentage changes from STD for each 3-30-300 KPI."""

    metrics = [
        ("P3_percent", "P3"),
        ("P30_percent", "P30"),
        ("P300_percent", "P300"),
    ]

    baseline = data.set_index("model").loc["STD"]
    y = np.arange(len(metrics))
    bar_height = 0.32

    fig, ax = plt.subplots(
        figsize=(10.5, 5.8),
        constrained_layout=True,
    )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    changes = {}

    for model in ("Counterfactual", "MaxCoverage"):
        model_data = data.set_index("model").loc[model]

        values = []

        for column, _ in metrics:
            std_value = float(baseline[column])

            if std_value <= 0:
                raise ValueError(
                    f"Cannot calculate relative change for {column}: "
                    "STD baseline must be positive."
                )

            model_value = float(model_data[column])

            change = 100 * (
                model_value - std_value
            ) / std_value

            values.append(change)

        changes[model] = values

    all_values = np.array(list(changes.values())).flatten()

    x_min = min(0, all_values.min())
    x_max = max(0, all_values.max())
    x_span = max(x_max - x_min, 1.0)

    ax.set_xlim(
        x_min - 0.15 * x_span,
        x_max + 0.18 * x_span,
    )

    for index, model in enumerate(
        ("Counterfactual", "MaxCoverage")
    ):
        values = changes[model]

        positions = y + (
            -bar_height / 2
            if index == 0
            else bar_height / 2
        )

        ax.barh(
            positions,
            values,
            height=bar_height,
            color=COLORS[model],
            label=model,
            zorder=3,
        )

        for position, value in zip(positions, values):
            if value >= 0:
                text_x = value + 0.025 * x_span
                alignment = "left"
            else:
                text_x = value - 0.025 * x_span
                alignment = "right"

            ax.text(
                text_x,
                position,
                f"{value:+.2f}%",
                va="center",
                ha=alignment,
                fontsize=10,
                color="#253344",
            )

    ax.axvline(
        0,
        color="#526276",
        linewidth=1.3,
        zorder=2,
    )

    ax.xaxis.grid(
        True,
        color="#E8ECEF",
        linewidth=0.8,
    )

    ax.set_axisbelow(True)

    ax.set_yticks(y)
    ax.set_yticklabels(
        [label for _, label in metrics],
        fontsize=11,
    )

    ax.invert_yaxis()

    ax.set_xlabel(
        "Relative change vs. STD (%)",
        fontsize=11,
    )

    ax.set_title(
        "Relative change in 3-30-300 KPIs vs. STD",
        fontsize=15,
        fontweight="semibold",
        loc="left",
        pad=18,
    )

    ax.legend(
        loc="upper right",
        frameon=False,
        fontsize=10,
    )

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)

    ax.tick_params(axis="y", length=0)

    ax.text(
        0.0,
        -0.17,
        (
            f"Scenario: {scenario}   |   "
            "STD = 0% for each KPI   |   "
            "Negative values indicate deterioration"
        ),
        transform=ax.transAxes,
        fontsize=9,
        color="#596575",
    )

    save_figure(
        fig,
        output_dir,
        f"kpi_relative_changes_{scenario}",
    )



def plot_jaccard_heatmap(csv_path, output_dir, scenario):
    """Compare exact and spatial Jaccard with a shared color scale."""

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Missing Jaccard comparison: {csv_path}. "
            "Run evaluate_kpis.py first."
        )

    data = pd.read_csv(csv_path)

    required = {
        "model_a",
        "model_b",
        "jaccard_percent",
        "spatial_jaccard_percent",
        "spatial_buffer_m",
    }

    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")

    models = list(MODELS)
    expected_pairs = {
        frozenset((a, b))
        for i, a in enumerate(models)
        for b in models[i + 1:]
    }

    seen_pairs = set()
    exact = np.eye(len(models)) * 100
    spatial = np.eye(len(models)) * 100

    for row in data.itertuples(index=False):
        pair = frozenset((row.model_a, row.model_b))

        if pair not in expected_pairs or pair in seen_pairs:
            raise ValueError(
                f"Invalid or duplicate Jaccard pair: {pair}"
            )

        seen_pairs.add(pair)

        i = models.index(row.model_a)
        j = models.index(row.model_b)

        for matrix, value in (
            (exact, row.jaccard_percent),
            (spatial, row.spatial_jaccard_percent),
        ):
            value = float(value)

            if not np.isfinite(value) or not 0 <= value <= 100:
                raise ValueError("Invalid Jaccard percentage")

            matrix[i, j] = value
            matrix[j, i] = value

    if seen_pairs != expected_pairs:
        raise ValueError("Missing Jaccard model comparisons")

    buffer_values = pd.to_numeric(
        data["spatial_buffer_m"],
        errors="raise",
    )

    if (
        not np.isfinite(buffer_values).all()
        or not (buffer_values > 0).all()
        or not np.allclose(buffer_values, buffer_values.iloc[0])
    ):
        raise ValueError("Inconsistent spatial buffer distances")

    buffer_m = float(buffer_values.iloc[0])

    fig, axes = plt.subplots(
        1, 2,
        figsize=(12.5, 5.8),
        constrained_layout=True,
    )

    fig.patch.set_facecolor("white")

    fig.suptitle(
        "Similarity between selected green-cell solutions",
        fontsize=15,
        fontweight="semibold",
        y=1.05,
    )

    matrices = [
        (exact, "Exact Jaccard — selected cell IDs"),
        (spatial, f"Spatial Jaccard — {buffer_m:g} m buffer"),
    ]

    for ax, (matrix, title) in zip(axes, matrices):

        image = ax.imshow(
            matrix,
            cmap="Blues",
            vmin=0,
            vmax=100,
            interpolation="nearest",
        )

        ax.set_title(
            title,
            fontsize=12,
            fontweight="semibold",
            pad=15,
        )

        ax.set_xticks(range(len(models)))
        ax.set_yticks(range(len(models)))

        ax.set_xticklabels(
            models,
            rotation=30,
            ha="right",
            fontsize=9,
        )

        ax.set_yticklabels(models, fontsize=9)

        ax.tick_params(length=0)

        for i in range(len(models)):
            for j in range(len(models)):
                value = matrix[i, j]

                ax.text(
                    j,
                    i,
                    f"{value:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=10,
                    fontweight="semibold",
                    color=(
                        "white"
                        if value >= 50
                        else "#253344"
                    ),
                )

        for spine in ax.spines.values():
            spine.set_visible(False)

    colorbar = fig.colorbar(
        image,
        ax=axes,
        shrink=0.8,
        pad=0.02,
    )

    colorbar.set_label(
        "Jaccard similarity (%)",
        fontsize=10,
    )

    fig.text(
        0.5,
        -0.04,
        (
            f"Scenario: {scenario}   |   "
            "Diagonal = 100% (same model)   |   "
            "Higher values indicate greater similarity"
        ),
        ha="center",
        fontsize=9,
        color="#596575",
    )

    save_figure(
        fig,
        output_dir,
        f"jaccard_heatmap_{scenario}",
    )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="default",
    )

    args = parser.parse_args()

    suffix = "" if args.scenario == "default" else f"_{args.scenario}"

    csv_path = ROOT / "analysis" / f"kpi_comparison{suffix}.csv"

    output_dir = ROOT / "analysis" / "plots"

    data = load_kpis(csv_path)

    plot_tradeoff(
        data,
        output_dir,
        args.scenario,
    )

    plot_kpi_components(
        data,
        output_dir,
        args.scenario,
    )

    plot_kpi_relative_changes(
        data,
        output_dir,
        args.scenario,
    )

    jaccard_csv = (
        ROOT / "analysis" / (
            "jaccard_comparison.csv"
            if args.scenario == "default"
            else f"jaccard_comparison_{args.scenario}.csv"
        )
    )

    plot_jaccard_heatmap(
        jaccard_csv,
        output_dir,
        args.scenario,
    )

if __name__ == "__main__":
    main()
