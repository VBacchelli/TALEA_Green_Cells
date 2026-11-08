# 3-30-300 extension: experiments and results

[Methodology and assumptions](README.md) · [Project README](../../README.md)

We compare **STD**, **Counterfactual** and **MaxCoverage** on the same full-city grid. All results use the same post-hoc evaluation; the models' own objective values are not directly comparable.

## Scenarios

The [default configuration](../../config/full/default.yaml) uses **100 cells**, `gamma_330300 = 1`, `delta = 1 m²`, **0.01 trees/m²** and **0.20 m²/m²** additional canopy (both street and yard). The original TALEA macro weights and street/yard weights are unchanged.

| Sensitivity | Values tested | Notes |
| --- | --- | --- |
| **3-30-300 weight** | `gamma_330300`: **0, 0.5, 1, 2** | Same 100-cell STD baseline |
| **Tree and canopy density** | **0.005 / 0.10**, **0.010 / 0.20**, **0.015 / 0.30** | Tree and canopy densities vary **together**, not independently |
| **Maximum cells** | **50, 75, 100, 150** | STD, Counterfactual and MaxCoverage use the **same cell limit** |

The scenario YAML files are in [`config/full/`](../../config/full/). The earlier 25-cell test is not included in the comparison.

## Evaluation

[`analysis/evaluate_kpis.py`](../../analysis/evaluate_kpis.py) measures:

| KPI | Meaning |
| --- | --- |
| `P3_percent` | Percentage of the initial missing-tree deficit recovered |
| `P30_percent` | Percentage of the initial canopy deficit recovered |
| `P300_percent` | Percentage of initially uncovered buildings newly reached within 300 m |
| `KPI_330300_percent` | Average of **P3, P30 and P300** |
| `TALEA_original_utility` | Original TALEA utility recalculated for every model |
| `TALEA_utility_change_percent` | Utility change compared with STD **at the same budget** |

The CSVs also include raw counts: `new_buildings_meeting_3`, `new_areas_meeting_30` and `new_buildings_covered`, plus **Jaccard** overlap (exact and spatial). Recovered deficits are not the same as full compliance. All improvements are modeled estimates, not measured planting, canopy growth or public park access.

## Results

**Cell-budget sensitivity:** KPI and utility changes are percentages; utility is compared with STD at the same budget.

| Cells | STD KPI | Counterfactual KPI | MaxCoverage KPI | Counterfactual Δ utility | MaxCoverage Δ utility |
| ---: | ---: | ---: | ---: | ---: | ---: |
| **50** | 10.71 | 11.72 | **12.34** | −7.38 | **−0.14** |
| **75** | 14.42 | 15.69 | **17.71** | −6.89 | **−0.42** |
| **100** | 17.52 | 17.53 | **19.71** | −5.05 | **−0.22** |
| **150** | 20.62 | 22.36 | **26.14** | −5.40 | **−0.76** |

**MaxCoverage has the highest composite KPI at every budget**, while losing less than 1% of the original TALEA utility. At 150 cells it gains **5.52 percentage points** over STD. It also selects locations close to STD (only **2–5 cells replaced** across the four budgets), whereas Counterfactual replaces **15–32**.

## Figures

**Utility trade-off (100 cells)**

![3-30-300 improvement versus original TALEA utility](../../analysis/plots/tradeoff_default.png)

**Sensitivity to the number of selected cells**

![KPI, utility and placement by cell budget](../../analysis/plots/max_cells_sensitivity.png)

**Tree/canopy assumptions and placement overlap with STD**

![Density sensitivity and Jaccard versus STD](../../analysis/plots/density_sensitivity.png)

See also [gamma sensitivity](../../analysis/plots/gamma_sensitivity.png), [individual KPI components](../../analysis/plots/kpi_components_default.png) and [placement Jaccard](../../analysis/plots/jaccard_heatmap_default.png). SVG versions are in [`analysis/plots/`](../../analysis/plots/).

## Reproduce

Inside the project's Docker environment, use the versioned processed data and run all three models with the same YAML for a cell-budget comparison:

```bash
run_model --config config/full/max_cells_150.yaml --model std
run_model --config config/full/max_cells_150.yaml --model std_330300
run_model --config config/full/max_cells_150.yaml --model std_330300_maxcoverage
python3 analysis/evaluate_kpis.py --scenario max_cells_150
```

For gamma and density scenarios, reuse STD's `default` placement and rerun the two extension models. Once all scenario CSVs are available, regenerate the figures with:

```bash
python3 analysis/plot_kpis.py --scenario default
```

Placements are in [`results/full/`](../../results/full/), comparison CSVs in [`analysis/results/`](../../analysis/results/) and figures in [`analysis/plots/`](../../analysis/plots/). Avoid rebuilding the live OpenStreetMap input when reproducing these results.
