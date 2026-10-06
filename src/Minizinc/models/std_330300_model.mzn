include "globals.mzn";

% ------------------------------------------------------------------
% Input: baseline cell data
% ------------------------------------------------------------------
int: len;
int: top_k;
float: alpha_yard;
float: beta_streets;
float: gamma_330300;
float: delta;
float: tree_density_street;
float: tree_density_yard;
float: canopy_density_street;
float: canopy_density_yard;

array[1..len] of float: street_space;
array[1..len] of float: ext_space;
array[1..len] of float: green_space;
array[1..len] of float: num_areas;
array[1..len] of float: num_trees;
array[1..len] of float: macro_factors;
array[1..len] of float: full_space;

% ------------------------------------------------------------------
% Sparse cell-statistical-area relations for criterion 3
% One relation r corresponds to one (cell i, statistical area a).
% ------------------------------------------------------------------
int: n_rel_3;
array[1..n_rel_3] of int: rel3_cell;
array[1..n_rel_3] of int: rel3_area; % diagnostic label; not used in objective
array[1..n_rel_3] of int: rel3_count_req1;
array[1..n_rel_3] of int: rel3_count_req2;
array[1..n_rel_3] of int: rel3_count_req3;
array[1..n_rel_3] of float: rel3_deficit_area;

% ------------------------------------------------------------------
% Sparse cell-statistical-area relations for criterion 30
% ------------------------------------------------------------------
int: n_rel_30;
array[1..n_rel_30] of int: rel30_cell;
array[1..n_rel_30] of int: rel30_area; % diagnostic label; not used in objective
array[1..n_rel_30] of float: rel30_cell_share;
array[1..n_rel_30] of float: rel30_required_canopy;

% ------------------------------------------------------------------
% Sparse cell-statistical-area relations for criterion 300
% ------------------------------------------------------------------
int: n_rel_300;
array[1..n_rel_300] of int: rel300_cell;
array[1..n_rel_300] of int: rel300_area; % diagnostic label; not used in objective
array[1..n_rel_300] of int: rel300_gain_count;
array[1..n_rel_300] of float: rel300_deficit_area;

float: max_street = max(street_space);
float: max_yard = max(ext_space);
float: max_areas = max(num_areas);
float: max_trees = max(num_trees);
float: max_green = max(green_space);

% ------------------------------------------------------------------
% Decision variables
% ------------------------------------------------------------------
array[1..len] of var 0..max_street: street_cells;
array[1..len] of var 0..max_yard: yard_cells;
array[1..len] of var float: utility;
array[1..len] of var 0..1: z;

array[1..len] of var int: added_trees =
    [floor(tree_density_street * street_cells[i]
            + tree_density_yard * yard_cells[i]) | i in 1..len];

array[1..len] of var float: added_canopy =
    [canopy_density_street * street_cells[i]
     + canopy_density_yard * yard_cells[i] | i in 1..len];

% ------------------------------------------------------------------
% Criterion 3: benefit_3_ia = gain_3_ia / deficit_3_a
% Each row below is one cell-area relation, not a city-wide normalization.
% ------------------------------------------------------------------
array[1..n_rel_3] of var float: gain_3_ia =
    [
        (
            rel3_count_req1[r] * min(added_trees[rel3_cell[r]], 1) +
            rel3_count_req2[r] * min(added_trees[rel3_cell[r]], 2) +
            rel3_count_req3[r] * min(added_trees[rel3_cell[r]], 3)
        ) / 3.0
        | r in 1..n_rel_3
    ];

array[1..n_rel_3] of var float: benefit_3_ia =
    [min(1.0, gain_3_ia[r] / rel3_deficit_area[r]) | r in 1..n_rel_3];

% ------------------------------------------------------------------
% Criterion 30: cell_share is applied exactly once.
% ------------------------------------------------------------------
array[1..n_rel_30] of var float: added_canopy_ia =
    [added_canopy[rel30_cell[r]] * rel30_cell_share[r] | r in 1..n_rel_30];

array[1..n_rel_30] of var float: useful_canopy_ia =
    [min(added_canopy_ia[r], rel30_required_canopy[r]) | r in 1..n_rel_30];

array[1..n_rel_30] of var float: benefit_30_ia =
    [min(1.0, useful_canopy_ia[r] / rel30_required_canopy[r]) | r in 1..n_rel_30];

% ------------------------------------------------------------------
% Criterion 300: z activates the accessibility benefit.
% ------------------------------------------------------------------
array[1..n_rel_300] of var float: benefit_300_ia =
    [
        min(
            1.0,
            z[rel300_cell[r]] * rel300_gain_count[r] / rel300_deficit_area[r]
        )
        | r in 1..n_rel_300
    ];

% ------------------------------------------------------------------
% Cell-level aggregation used by the objective.
%
% IMPORTANT: the following diagnostics are declared as explicit variables and
% then linked by constraints. This prevents MiniZinc from treating them only as
% aliases/expressions and dropping them from the Python solution object.
%
% We preserve all i-a relations above. To obtain one value per cell for the
% current objective, relations are aggregated with a deficit-weighted mean:
%     sum_a(deficit_a * benefit_ia) / sum_a(deficit_a)
% This keeps each criterion in [0,1] and introduces no observed-max scaling.
% ------------------------------------------------------------------
array[1..len] of var 0.0..1.0: benefit_3 :: output_array([1..len]);
array[1..len] of var 0.0..1.0: benefit_30 :: output_array([1..len]);
array[1..len] of var 0.0..1.0: benefit_300 :: output_array([1..len]);
array[1..len] of var 0.0..1.0: benefit_330300 :: output_array([1..len]);

% base_benefit is not necessarily <= 1 because it is the sum of two normalized
% allocation terms weighted as in the original utility.
array[1..len] of var float: base_benefit :: output_array([1..len]);
array[1..len] of var float: contribution_330300 :: output_array([1..len]);

constraint forall(i in 1..len)(
    benefit_3[i] =
        if sum(r in 1..n_rel_3 where rel3_cell[r] = i)(rel3_deficit_area[r]) > 0.0 then
            sum(r in 1..n_rel_3 where rel3_cell[r] = i)(
                rel3_deficit_area[r] * benefit_3_ia[r]
            ) /
            sum(r in 1..n_rel_3 where rel3_cell[r] = i)(rel3_deficit_area[r])
        else
            0.0
        endif
);

constraint forall(i in 1..len)(
    benefit_30[i] =
        if sum(r in 1..n_rel_30 where rel30_cell[r] = i)(rel30_required_canopy[r]) > 0.0 then
            sum(r in 1..n_rel_30 where rel30_cell[r] = i)(
                rel30_required_canopy[r] * benefit_30_ia[r]
            ) /
            sum(r in 1..n_rel_30 where rel30_cell[r] = i)(rel30_required_canopy[r])
        else
            0.0
        endif
);

constraint forall(i in 1..len)(
    benefit_300[i] =
        if sum(r in 1..n_rel_300 where rel300_cell[r] = i)(rel300_deficit_area[r]) > 0.0 then
            sum(r in 1..n_rel_300 where rel300_cell[r] = i)(
                rel300_deficit_area[r] * benefit_300_ia[r]
            ) /
            sum(r in 1..n_rel_300 where rel300_cell[r] = i)(rel300_deficit_area[r])
        else
            0.0
        endif
);

constraint forall(i in 1..len)(
    benefit_330300[i] =
        (benefit_3[i] + benefit_30[i] + benefit_300[i]) / 3.0
);

constraint forall(i in 1..len)(
    base_benefit[i] =
        alpha_yard * (yard_cells[i] / max_yard) +
        (street_cells[i] / max_street)
);

constraint forall(i in 1..len)(
    contribution_330300[i] = gamma_330300 * benefit_330300[i]
);

% ------------------------------------------------------------------
% Utility and constraints
% ------------------------------------------------------------------
constraint forall(i in 1..len)(
    if num_areas[i] == 0.0 then
        utility[i] = macro_factors[i] * (
            (base_benefit[i] + contribution_330300[i]) /
            ((green_space[i] / max_green) + (num_trees[i] / max_trees) + 0.00000001)
        )
    else
        utility[i] = macro_factors[i] * (
            (base_benefit[i] + contribution_330300[i]) /
            ((num_areas[i] / max_areas) + (green_space[i] / max_green) +
             (num_trees[i] / max_trees) + 0.00000001)
        )
    endif
);

constraint forall(i in 1..len)(
    street_cells[i] <= beta_streets * street_space[i] * z[i]
);

constraint forall(i in 1..len)(
    yard_cells[i] <= ext_space[i] * z[i]
);

constraint forall(i in 1..len)(
    street_cells[i] + yard_cells[i] + green_space[i] <= full_space[i]
);

constraint forall(i in 1..len)(
    street_cells[i] + yard_cells[i] >= delta * z[i]
);

constraint sum(i in 1..len)(z[i]) <= top_k;

var float: utility_mean = sum(i in 1..len)(utility[i]) / top_k;

solve maximize utility_mean;
