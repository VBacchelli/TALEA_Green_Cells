include "globals.mzn";

% ==================================================================
% INPUT: BASELINE CELL DATA
% ==================================================================

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

array [1..len] of float: street_space;
array [1..len] of float: ext_space;
array [1..len] of float: green_space;
array [1..len] of float: num_areas;
array [1..len] of float: num_trees;
array [1..len] of float: macro_factors;
array [1..len] of float: full_space;

% ==================================================================
% INPUT: CRITERION 3 - MAXIMUM COVERAGE
%
% Each relation r represents a (cell, deficit building) pair.
% Each building has an individual deficit of 1, 2 or 3 trees.
% ==================================================================

int: n_buildings_3;
int: total_deficit_3;
int: n_rel_3;

array [1..n_rel_3] of int: rel3_cell;
array [1..n_rel_3] of int: rel3_building;
array [1..n_buildings_3 + 1] of int: rel3_offset;

array [1..n_buildings_3] of int: required_trees_3;

% ==================================================================
% INPUT: CRITERION 30
%    Legacy counterfactual representation for now
% ==================================================================

int: n_rel_30;

array [1..n_rel_30] of int: rel30_cell;
array [1..n_rel_30] of int: rel30_area;

array [1..n_rel_30] of float: rel30_cell_share;
array [1..n_rel_30] of float: rel30_required_canopy;

% ==================================================================
% INPUT: CRITERION 300 - MAXIMUM COVERAGE
%
%    One relation r corresponds to one:
%        (cell i, deficit building b)
% ==================================================================

int: n_buildings_300;
int: total_deficit_300;

int: n_rel_300;

array [1..n_rel_300] of int: rel300_cell;
array [1..n_rel_300] of int: rel300_building;
array [1..n_buildings_300 + 1] of int: rel300_offset;

% ==================================================================
% SCALE REFERENCES
% ==================================================================

float: max_street = max(street_space);
float: max_yard = max(ext_space);
float: max_areas = max(num_areas);
float: max_trees = max(num_trees);
float: max_green = max(green_space);

% ==================================================================
% DECISION VARIABLES: GREEN CELL PLACEMENT
% ==================================================================

array [1..len] of var 0..max_street: street_cells;
array [1..len] of var 0..max_yard: yard_cells;

array [1..len] of var 0..1: z;

array [1..len] of var float: utility;

% ==================================================================
% PHYSICAL EFFECT OF SELECTED GREEN CELLS
% ==================================================================

array [1..len] of var int: added_trees = [
    floor(tree_density_street * street_cells[i] + tree_density_yard * yard_cells[i]) |
        i in 1..len,
];

array [1..len] of var float: added_canopy = [
    canopy_density_street * street_cells[i] + canopy_density_yard * yard_cells[i] |
        i in 1..len,
];

% ==================================================================
% MAXIMUM COVERAGE - CRITERION 300
%
% y_300[b] = 1 if deficit building b is covered by at least
% one selected Green Cell.
% ==================================================================

array [1..n_buildings_300] of var 0..1: y_300;
var 0.0..1.0: benefit_300_global;


constraint
    forall (b in 1..n_buildings_300) (
        y_300[b] <=
            sum (r in rel300_offset[b]..(rel300_offset[b + 1] - 1)) (
                z[rel300_cell[r]]
            )
    );


constraint
    benefit_300_global =
        if total_deficit_300 > 0 then
            sum (b in 1..n_buildings_300) (y_300[b]) / total_deficit_300
        else
            0.0
        endif;

% ==================================================================
% MAXIMUM COVERAGE - CRITERION 3
%
% Trees added by a Green Cell can benefit every building in range.
% Each building's gain is capped at its individual tree deficit.
% ==================================================================

array [1..n_buildings_3] of var 0..3: gain_3_building;

var 0.0..1.0: benefit_3_global;

constraint
    forall (b in 1..n_buildings_3) (
        gain_3_building[b] =
            min(
                required_trees_3[b],
                sum (r in rel3_offset[b]..(rel3_offset[b + 1] - 1)) (added_trees[rel3_cell[r]]),
            )
    );

constraint
    benefit_3_global =
        if total_deficit_3 > 0 then
            sum (b in 1..n_buildings_3) (gain_3_building[b]) / total_deficit_3
        else
            0.0
        endif;


% ============================================================
% MAXIMUM COVERAGE - CRITERION 30
% ============================================================

int: n_areas_30 = max(rel30_area);

array[1..n_areas_30] of float: required_canopy_30 = [
    max([rel30_required_canopy[r] |
        r in 1..n_rel_30 where rel30_area[r] = a] ++ [0.0])
    | a in 1..n_areas_30
];

array[1..n_areas_30] of var float: gain_30_area;

constraint forall(a in 1..n_areas_30)(
    gain_30_area[a] =
        min(
            required_canopy_30[a],
            sum(r in 1..n_rel_30 where rel30_area[r] = a)(
                added_canopy[rel30_cell[r]]
                * rel30_cell_share[r]
            )
        )
);

var 0.0..1.0: benefit_30_global;

constraint
    benefit_30_global =
        if sum(required_canopy_30) > 0.0 then
            sum(gain_30_area) / sum(required_canopy_30)
        else
            0.0
        endif;


% ==================================================================
% BASE BENEFIT
% ==================================================================

array [1..len] of var float: base_benefit :: output_array([1..len]);

constraint
    forall (i in 1..len) (
        base_benefit[i] = alpha_yard * (yard_cells[i] / max_yard) + (street_cells[i] / max_street)
    );


% ==================================================================
% UTILITY: LOCAL BASELINE COMPONENT
% ==================================================================

constraint
    forall (i in 1..len) (
        if num_areas[i] == 0.0 then
            utility[i] =
                macro_factors[i] * base_benefit[i] /
                (
                    green_space[i] / max_green +
                    num_trees[i] / max_trees +
                    0.00000001
                )
        else
            utility[i] =
                macro_factors[i] * base_benefit[i] /
                (
                    num_areas[i] / max_areas +
                    green_space[i] / max_green +
                    num_trees[i] / max_trees +
                    0.00000001
                )
        endif
    );

var 0.0..1.0: benefit_330300_global =
    (benefit_3_global + benefit_30_global + benefit_300_global) / 3.0;


% ==================================================================
% GREEN CELL FEASIBILITY / LINKING CONSTRAINTS
% ==================================================================

constraint forall (i in 1..len) (street_cells[i] <= beta_streets * street_space[i] * z[i]);

constraint forall (i in 1..len) (yard_cells[i] <= ext_space[i] * z[i]);

constraint forall (i in 1..len) (street_cells[i] + yard_cells[i] + green_space[i] <= full_space[i]);

constraint forall (i in 1..len) (street_cells[i] + yard_cells[i] >= delta * z[i]);

% ==================================================================
% CARDINALITY
% ==================================================================

constraint sum (i in 1..len) (z[i]) <= top_k;

% ==================================================================
% OBJECTIVE
% ==================================================================

var float: utility_local_mean =
    sum(i in 1..len)(utility[i]) / top_k;

var float: utility_mean =
    utility_local_mean +
    gamma_330300 * benefit_330300_global;

solve maximize utility_mean;
