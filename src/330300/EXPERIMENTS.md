# 3-30-300 extension: experiments and evaluation

[Methodology and assumptions](README.md) · [Back to the project README](../../README.md)

This document describes the full-city optimization experiments performed on the `3-30-300` branch. All three models are compared with the same independent post-hoc evaluation, rather than treating their different MiniZinc objective values as directly comparable.

## Models and scenarios

- **STD** (`std`): original TALEA Standard baseline, from the `default` scenario.
- **Counterfactual** (`std_330300`): original local utility augmented with a weighted, locally estimated 3-30-300 benefit.
- **MaxCoverage** (`std_330300_maxcoverage`): original utility augmented with normalized city-wide deficit recovery.

All experiments discussed here use the **full** grid, **100 maximum selected cells**, and the original macro weights (population density **0.33**, existing green **0.33**, UHEI **0.34**). The baseline extension configuration is [`config/full/default.yaml`](../../config/full/default.yaml):

| Parameter | Default |
| --- | ---: |
| `gamma_330300` | 1.0 |
| `delta` | 1 m² |
| `tree_density_street`, `tree_density_yard` | 0.01 trees/m² |
| `canopy_density_street`, `canopy_density_yard` | 0.20 m²/m² |
| `beta_streets` | 0.2 |
| `alpha_yards` | 0.8 |

The versioned YAML files in [`config/full/`](../../config/full/) provide two sensitivity sweeps:

| Sweep | YAML profiles | Changed parameters |
| --- | --- | --- |
| Contribution weight | `gamma_0`, `gamma_low`, `gamma_medium`, `gamma_high` | `gamma_330300` = **0, 0.5, 1, 2**, while physical densities remain at the default |
| Assumed tree and canopy densities | `tree_density_low`, `tree_density_medium`, `tree_density_high` | **Low:** 0.005 trees/m² and 0.10 canopy; **medium:** 0.010 and 0.20; **high:** 0.015 and 0.30; `gamma_330300 = 1` |

Street and yard parameters are varied together in the density sweep, so it is not a factorial experiment and cannot isolate their individual effects.

## Reproducing optimization results

Run these commands from the repository root **inside the project's Docker environment**. The processed data in [`dataset/processed_data/330300/`](../../dataset/processed_data/330300/) should be retained for reproducibility: rebuilding the OSM-derived input can change it.

Run the STD baseline first (unless the committed result already suffices):

```bash
run_model --config config/full/default.yaml --model std
```

Then run the two extension models for a given scenario, e.g. the default:

```bash
run_model --config config/full/default.yaml --model std_330300
run_model --config config/full/default.yaml --model std_330300_maxcoverage
```

To regenerate sensitivity runs, substitute a versioned YAML file, such as `config/full/gamma_high.yaml` or `config/full/tree_density_low.yaml`, for `default.yaml`. The scenario profile's `res_name` determines the result filename. Execute both extension models for each scenario before evaluating it.

Model outputs are stored in:

- [`results/full/std/`](../../results/full/std/)
- [`results/full/std_330300/`](../../results/full/std_330300/)
- [`results/full/std_330300_maxcoverage/`](../../results/full/std_330300_maxcoverage/)

**Important:** The complete upstream geospatial pipeline need not be rerun for every YAML parameter change. Optimization results depend on the processed grid and the three prepared coverage datasets. To reproduce published results, keep these input versions fixed.

## Post-hoc evaluation and KPIs

[`analysis/evaluate_kpis.py`](../../analysis/evaluate_kpis.py) evaluates the final placements of STD, Counterfactual and MaxCoverage under **identical** physical assumptions for each scenario. The STD baseline placement remains fixed in the sensitivity comparisons.

The main measures are:

| Output metric | Interpretation |
| --- | --- |
| `P3_percent` | Percentage of the initial *missing-tree count* recovered, capped at each affected building's initial deficit |
| `P30_percent` | Percentage of the initial *missing canopy area* recovered, capped at each affected statistical area's initial deficit |
| `P300_percent` | Percentage of initially uncovered buildings that gain modeled access within 300 m |
| `KPI_330300_percent` | Arithmetic mean of `P3_percent`, `P30_percent` and `P300_percent` |
| `TALEA_original_utility` | Original TALEA objective evaluated for each final placement using the same baseline inputs |
| `TALEA_utility_change_percent` | Change in original TALEA utility relative to the STD baseline |

These are **estimated recovery indicators**, not direct measurements of realized improvements, planted trees or actual access to a newly built park. In particular, `P3_percent` and `P30_percent` measure recovered deficits, which is distinct from the proportion of fully compliant buildings/statistical areas. The post-hoc evaluation also exports complementary compliance counts (`new_buildings_meeting_3`, `new_areas_meeting_30`) and spatial-placement comparisons where available.

To generate the default comparison from committed results:

```bash
python3 analysis/evaluate_kpis.py --scenario default
python3 analysis/plot_kpis.py --scenario default
```

To evaluate another saved scenario, replace `default` with its name (e.g. `gamma_high` or `tree_density_low`). Plotting also uses the saved sensitivity comparisons to produce cross-scenario figures.

The saved artifacts are available in:

- [`analysis/results/`](../../analysis/results/): `kpi_comparison*.csv` and `jaccard_comparison*.csv`
- [`analysis/plots/`](../../analysis/plots/): PNG and SVG figures

Jaccard metrics compare the overlap in selected grid-cell IDs and, separately, a **buffered polygon** measure of spatial overlap. A high spatial Jaccard is not the same as choosing the same cell IDs.

## How to interpret comparisons

1. Compare the post-hoc `KPI_330300_percent` across all three models to assess modeled recovery of 3-30-300 deficits.
2. Compare `TALEA_original_utility` to quantify the trade-off against the original TALEA objective.
3. Use sensitivity scenarios to inspect the influence of the contribution weight and physical conversion assumptions.
4. Do **not** compare raw MiniZinc objective values from Counterfactual and MaxCoverage as if they were identical scales.

The assumptions that particularly affect interpretation—the treatment of a selected Green Cell as potential 300-m access even with a 1 m² minimum intervention, and the cell-level proxy for newly planted trees—are explained in the [methodology README](README.md).
