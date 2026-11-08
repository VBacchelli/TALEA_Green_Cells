# 3-30-300 extension: methodology

[Project README](../../README.md) · [Experiments and results](EXPERIMENTS.md)

This extension evaluates how TALEA Green Cells could contribute to the **3-30-300 urban greenness rule**. It adds two optimization models to the original **TALEA Standard (STD)** baseline. All reported gains are modeled estimates, not observed interventions.

## Criteria and data

| Rule | Baseline condition | Effect attributed to a selected Green Cell |
| --- | --- | --- |
| **3 trees** | A residential building has at least 3 mapped trees within 50 m of its centroid **or** is within 300 m of an existing park/garden (a project-specific convention). | Estimated newly planted trees can reduce deficits for buildings within 50 m of the cell geometry. |
| **30% canopy** | A statistical area has at least 30% canopy cover, measured from a raster. | Additional canopy is distributed among statistical areas according to the cell's area shares. |
| **300 m access** | A residential building is within 300 m of an existing park/garden. | A selected cell is treated as *potential* accessible green space for nearby buildings. |

Distances are **Euclidean**, using EPSG:32632 rather than walking-network routes. Tree counts and canopy cover come from different baseline datasets.

[`prepare_data.py`](prepare_data.py) processes statistical areas, canopy and green spaces; [`compute_index.py`](compute_index.py) processes OpenStreetMap residential buildings and computes the initial deficits and cell-to-building/area relations. The prepared inputs, including `buildings_330300.gpkg` and `cell_3_coverage.csv`, `cell_30_coverage.csv`, `cell_300_coverage.csv`, are kept in [`dataset/processed_data/330300/`](../../dataset/processed_data/330300/).

**Reproducibility:** rerunning the OpenStreetMap download may change the input buildings. Use the versioned processed data to reproduce the experiments.

## Optimization models

All models share the original TALEA feasibility constraints, a maximum number of selected cells (`max_cells`) and a minimum intervention area per selected cell (`delta`).

- **STD** (`std`): the unchanged original TALEA Standard model, used as the baseline.
- **Counterfactual** ([`std_330300`](../Minizinc/models/std_330300_model.mzn)): adds a locally estimated 3-30-300 benefit to each cell's original TALEA utility, scaled by `gamma_330300`. Local gains may overlap, so this objective is **not** equal to the total recovered city-wide deficit.
- **MaxCoverage** ([`std_330300_maxcoverage`](../Minizinc/models/std_330300_maxcoverage_model.mzn)): augments the original utility with `gamma_330300` times the mean of three normalized **city-wide deficit recoveries**: missing trees supplied to buildings, canopy deficit recovered in statistical areas and initially uncovered buildings newly reached within 300 m. Benefits are capped at initial deficits; covered buildings are counted only once. The normalization includes deficits that no candidate cell can reach.

The raw MiniZinc objective values differ across models and must **not** be compared directly. Their placements are evaluated using the same independent post-hoc KPIs described in [EXPERIMENTS.md](EXPERIMENTS.md).

**Comparison protocol:** gamma and density sensitivity runs use the fixed 100-cell STD baseline. For `max_cells` sensitivity (**50, 75, 100, 150**), STD and both extension models are optimized at each budget, with the other parameters held fixed. This avoids comparing solutions subject to different cell limits.

## Assumptions and limitations

- **Potential access is not a park.** For the 300 m rule, any selected cell may count as newly accessible green space, even with the default `delta = 1 m²`. Public access, minimum park size and actual pedestrian routes are not verified. This can overestimate practical 300 m access.
- **Trees are estimated per cell:** `floor(tree_density_street × street_cells + tree_density_yard × yard_cells)`. Exact planting locations within the cell are not optimized.
- **Canopy is estimated per cell:** `canopy_density_street × street_cells + canopy_density_yard × yard_cells`. Tree growth, maturity and survival are not simulated.
- **Spatial relationships are approximate:** proximity uses building centroids and cell geometries, not the detailed street network or site entrances.

## Separate exploratory macro-factor test

[`config/full/default+330300.yaml`](../../config/full/default+330300.yaml) tests **static 3-30-300 deficits as a fourth macro factor** alongside population density, existing green deficit and UHEI, assigning weight **0.25** to each. The new factor, implemented in [`preprocessing.py`](../preprocessing.py), combines baseline deficits in the 3, 30 and 300 criteria at statistical-area level.

This changes the priority weights used by the original `std`, `diff`, `inverse_uhei` and `ndvi` models; it is **not a third 3-30-300 optimization model** and is not included in the main three-model comparison. The main experiments set `factor_330300_param = 0`.
