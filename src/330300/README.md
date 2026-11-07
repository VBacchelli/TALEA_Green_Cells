# 3-30-300 extension: data, methods and models

[Back to the project README](../../README.md) · [Experiments, evaluation and reproducibility](EXPERIMENTS.md)

This directory contains the geospatial preparation code for the **3-30-300 urban greenness extension** to TALEA Green Cells. The original TALEA models remain the reference baseline; the two additional MiniZinc formulations, preprocessing steps and post-hoc comparisons described here belong to this extension.

## Operational definition of the three criteria

| Criterion | Initial condition | Estimated impact of new Green Cells |
| --- | --- | --- |
| **3 trees** | A residential building has at least three mapped trees within **50 m of its centroid**, **or** lies within **300 m of an existing park/garden** (an additional convention adopted here). | New trees are estimated from allocated street/yard green area. A building can benefit from new trees attributed to a Green Cell whose geometry lies within 50 m of its centroid. |
| **30% canopy** | Tree-canopy coverage of each statistical area is at least **30%**, estimated from the raster. | Added canopy is proportional to new green area and apportioned to statistical areas using each cell's intersection shares. |
| **300 m access** | A residential building lies within **300 m of an existing park/garden**. | A selected Green Cell is treated as *potential* new accessible green space; buildings within 300 m of its geometry gain coverage. |

Distances are **straight-line (Euclidean)**, evaluated in a metric projected coordinate reference system (EPSG:32632), not pedestrian-network distances. Buildings are assigned to statistical areas by the location of their centroid; trees and parks on the other side of an administrative boundary may still contribute.

The **baseline** calculation uses mapped municipal trees for criterion 3; the canopy raster is used for criterion 30. They are different input datasets and should not be treated as interchangeable.

## Geospatial processing

- [`prepare_data.py`](prepare_data.py) prepares statistical-area polygons, derives canopy percentages from the raster and extracts/clips parks and gardens.
- [`compute_index.py`](compute_index.py) obtains residential building geometries from OpenStreetMap, assigns them to statistical areas, computes baseline conditions and produces the three cell-to-building or cell-to-area coverage relations.
- [Prepared data and coverage CSVs](../../dataset/processed_data/330300/) are the inputs used by [`data_parser.py`](../data_parser.py) to construct MiniZinc instances.

The three coverage files are `cell_3_coverage.csv`, `cell_30_coverage.csv` and `cell_300_coverage.csv`. They describe which building or statistical area could benefit from an intervention in each grid cell.

**Reproducibility:** `compute_index.py` downloads current OpenStreetMap buildings when rerun; those records may change over time. To reproduce the published optimization experiments, retain the committed processed data (including `buildings_330300.gpkg`) rather than rebuilding the baseline from a new OSM query.

## Optimization models

The extension introduces two models alongside the original TALEA Standard (**STD**) baseline.

### Counterfactual: `std_330300`

[MiniZinc model](../Minizinc/models/std_330300_model.mzn)

Adds a locally estimated 3-30-300 benefit to the original cell-level TALEA utility. A weight `gamma_330300` controls the contribution of this estimated benefit. Each cell's gain is calculated locally from the covered buildings and overlapping statistical areas, and then included in the utility of that cell.

The objective is **not the same quantity** as the recovered city-wide 3-30-300 deficit calculated after optimization. Improving this objective does not necessarily imply the largest possible improvement in the global KPI.

### MaxCoverage: `std_330300_maxcoverage`

[MiniZinc model](../Minizinc/models/std_330300_maxcoverage_model.mzn)

Adds to the original STD utility the weighted average recovery of the **initial city-wide deficits** for the three criteria:

- **3:** useful additional trees, capped by each building's initial deficit;
- **30:** useful additional canopy area, capped by the canopy deficit of each statistical area;
- **300:** initially uncovered buildings that become covered by at least one selected cell (counted once).

Each recovery is normalized by the corresponding full initial deficit, including locations for which no candidate cell can provide a benefit. The three normalized terms are averaged, then weighted by `gamma_330300`.

Both models retain the underlying TALEA feasibility constraints, a maximum number of selected cells and the minimum allocated area per selected cell (`delta`).

### Exploratory test: 3-30-300 as a macro factor

A separate **test configuration** also incorporates the initial 3-30-300 conditions into the **macro-level utility factor** of the original TALEA models, rather than adding an intervention-dependent benefit to their objective functions.

In [`config/full/default+330300.yaml`](../../config/full/default+330300.yaml), the macro-factor weights are set to **0.25 each** for population density, existing green deficit, UHEI and a new 3-30-300 deficit indicator (`factor_330300_param`). As implemented in [`src/preprocessing.py`](../preprocessing.py), the new indicator is the arithmetic mean of the area's baseline deficits: the fraction of residential buildings failing criterion 3; the remaining canopy shortfall relative to the 30% target, truncated at zero; and the fraction of buildings failing criterion 300.

This is **not a third MiniZinc model**. The YAML file provides profiles for the original `std`, `diff`, `inverse_uhei` and `ndvi` models, which keep their existing optimization formulations but receive modified macro factors. Unlike **Counterfactual** and **MaxCoverage**, the 3-30-300 component here is a **static, area-level priority signal**, not a forecast of gains caused by newly selected Green Cells.

It is kept as an exploratory alternative rather than part of the main three-model evaluation. The usual experiments set `factor_330300_param = 0`; preprocessing regenerates the shared macro-factor data according to the active configuration.


## Modeling assumptions and limits

These assumptions are deliberate approximations; they do not claim to model the complete ecological or urban-planning process.

1. **Selected cell ≠ realized public park.** For criterion 300, any selected Green Cell satisfying the intervention constraints can provide potential access. With the default `delta = 1 m²`, even a 1 m² allocation may count as accessible green space. The model imposes **no minimum park area**, does not verify public access and does not simulate the construction of a public park. Thus the 300-m criterion is a **proxy for potential coverage**, not a guarantee of practical park access.
2. **Tree counts are estimated**, not individually planted in the geographic model. For each selected cell, new trees equal `floor(tree_density_street × street_cells + tree_density_yard × yard_cells)`. All estimated trees of a cell may contribute to buildings near that cell; their exact planting positions inside the polygon are not optimized.
3. **Canopy is a scenario assumption.** Additional canopy is estimated as `canopy_density_street × street_cells + canopy_density_yard × yard_cells`. Canopy maturity, growth and survival are not simulated.
4. **Straight-line proximity and geometric approximation.** The 50-m and 300-m checks use metric distances to centroids, building footprints and cell polygons as described above, not a walking network or actual site entrance.
5. **Different optimization targets.** Counterfactual and MaxCoverage should be compared using the same post-hoc evaluation, not by comparing their raw objective values as if they were the same metric.

See [EXPERIMENTS.md](EXPERIMENTS.md) for the versioned YAML configurations, sensitivity studies and evaluation outputs.
