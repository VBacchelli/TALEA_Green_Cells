include "globals.mzn";

% ----- Input ----- %
int: len;
int: top_k;
float: alpha_yard;
float: beta_streets;
float: gamma_330300;
float: delta; 
float: tree_density;
float: canopy_density;
array[1..len] of float: street_space;
array[1..len] of float: ext_space;
array[1..len] of float: green_space;
array[1..len] of float: num_areas;
array[1..len] of float: num_trees;
array[1..len] of float: macro_factors;
array[1..len] of float: full_space;
array[1..len] of float: benefit_300;
array[1..len, 1..3] of float: benefit_3_counts;
array[1..len] of float: benefit_30_factor;

float: max_street = max(street_space);
float: max_yard = max(ext_space);
float: max_areas = max(num_areas);
float: max_trees = max(num_trees);
float: max_green = max(green_space);

% ----- Decision Variables ----- %
array[1..len] of var 0..max_street: street_cells;
array[1..len] of var 0..max_yard: yard_cells;
array[1..len] of var float: utility;
array[1..len] of var 0..1: z;

array[1..len] of var int: added_trees = [floor(tree_density * (street_cells[i] + yard_cells[i])) | i in 1..len];
array[1..len] of var float: benefit_3 = [sum(k in 1..3)(benefit_3_counts[i, k] * bool2int(added_trees[i] >= k)) | i in 1..len];

array[1..len] of var float: added_canopy = [canopy_density * (street_cells[i] + yard_cells[i]) | i in 1..len];
array[1..len] of var float: benefit_30 = [added_canopy[i] * benefit_30_factor[i] | i in 1..len];

array[1..len] of var float: benefit_330300 = [benefit_3[i] + benefit_30[i] + benefit_300[i] * z[i] | i in 1..len];

% ----- Constraints ----- %
constraint forall(i in 1..len)(
	if num_areas[i] == 0.0 then
		utility[i] = macro_factors[i] * ((alpha_yard * (yard_cells[i] / max_yard) + (street_cells[i] / max_street) + (gamma_330300 * benefit_330300[i])) / ((green_space[i] / max_green) + (num_trees[i] / max_trees) + 0.00000001))
	else
		utility[i] = macro_factors[i] * ((alpha_yard * (yard_cells[i] / max_yard) + (street_cells[i] / max_street) + (gamma_330300 * benefit_330300[i])) / ((num_areas[i] / max_areas) + (green_space[i] / max_green) + (num_trees[i] / max_trees) + 0.00000001))
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

% Minimum intervention size for selected cells
constraint forall(i in 1..len)(
    street_cells[i] + yard_cells[i] >= delta * z[i]
);

constraint sum(i in 1..len)(z[i]) <= top_k;

% ----- Objective Variable ----- %
var float: utility_mean = sum(i in 1..len)(utility[i]) / top_k;

solve maximize utility_mean;