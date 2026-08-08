include "globals.mzn";

% ----- Input ----- %
int: len;
int: top_k;
float: beta_streets;
float: alpha_yard;
array[1..len] of float: street_space;
array[1..len] of float: ext_space;
array[1..len] of float: green_space;
array[1..len] of float: num_areas;
array[1..len] of float: num_trees;
array[1..len] of float: macro_factors;
array[1..len] of float: full_space;

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

% ----- Constraints ----- %
constraint forall(i in 1..len)(
	if num_areas[i] == 0.0 then
		utility[i] = macro_factors[i] * ((alpha_yard * (yard_cells[i] / max_yard) + (street_cells[i] / max_street)) / ((green_space[i] / max_green) + (num_trees[i] / max_trees) + 0.00000001))
	else
		utility[i] = macro_factors[i] * ((alpha_yard * (yard_cells[i] / max_yard) + (street_cells[i] / max_street)) / ((num_areas[i] / max_areas) + (green_space[i] / max_green) + (num_trees[i] / max_trees) + 0.00000001))
	endif
);

constraint forall(i in 1..len)(
    street_cells[i] <= beta * street_space[i] * z[i]
);

constraint forall(i in 1..len)(
    yard_cells[i] <= ext_space[i] * z[i]
);

constraint forall(i in 1..len)(
	street_cells[i] + yard_cells[i] + green_space[i] <= full_space[i]
);

constraint sum(i in 1..len)(z[i]) <= top_k;

% ----- Objective Variable ----- %
var float: utility_mean = sum(i in 1..len)(utility[i]) / top_k;

solve maximize utility_mean;