include "globals.mzn";

% ----- Input ----- %
int: len;
int: top_k;
float: beta_streets;
float: alpha_yard;
float: ndvi_norm_max;
float: ndvi_norm_min;
array[1..len] of float: street_space;
array[1..len] of float: ext_space;
array[1..len] of float: green_space;
array[1..len] of float: num_areas;
array[1..len] of float: num_trees;
array[1..len] of float: macro_factors;
array[1..len] of float: full_space;
array[1..len] of float: ndvi;

float: max_street = max(street_space);
float: max_yard = max(ext_space);
float: max_areas = max(num_areas);

% ----- Decision Variables ----- %
array[1..len] of var 0..max_street: street_cells;
array[1..len] of var 0..max_yard: yard_cells;
array[1..len] of var float: utility;

% ----- Constraints ----- %
constraint forall(i in 1..len)(
	utility[i] = (macro_factors[i] / (ndvi[i] + (num_areas[i] / max_areas))) * (((0.5 + (0.5 * (street_cells[i] + yard_cells[i]) / full_space[i]))* (ndvi_norm_max - ndvi_norm_min)) + ndvi_norm_min)
);

constraint forall(i in 1..len)(
	street_cells[i] <= beta_streets * street_space[i]
);

constraint forall(i in 1..len)(
	yard_cells[i] <= alpha_yard * ext_space[i]
);

constraint forall(i in 1..len)(
	street_cells[i] + yard_cells[i] + green_space[i] <= full_space[i]
);

constraint sum(i in 1..len where street_cells[i] != 0.0 \/ yard_cells[i] != 0.0)(1) <= top_k;

% ----- Objective Variable ----- %
var float: utility_mean = sum(i in 1..len)(utility[i]) / top_k;

solve maximize utility_mean;