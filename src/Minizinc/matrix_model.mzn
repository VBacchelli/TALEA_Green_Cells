include "globals.mzn";

% ----- Input ----- %
int: m;
int: n;
array[1..m, 1..n] of float: street_space;
array[1..m, 1..n] of float: ext_space;
array[1..m, 1..n] of float: green_space;
array[1..m, 1..n] of float: num_areas;
array[1..m, 1..n] of float: num_trees;
array[1..m, 1..n] of float: densities;

int: top_k = 50;
% int: dw = 2;
% float: window = (dw*2+1)*(dw*2+1);
float: beta_streets = 0.4;
float: alpha_yard = 0.8;
float: max_street = beta_streets * max(street_space);
float: max_yard = max(ext_space);
float: max_densities = max(densities);
float: max_areas = max(num_areas);
float: max_trees = max(num_trees);
float: max_green = max(green_space);
float: scale = (1+alpha_yard) * max_areas * max_green;

% ----- Decision Variables ----- %
array[1..m, 1..n] of var 0..max_street: street_cells;
array[1..m, 1..n] of var 0..max_yard: yard_cells;
array[1..m, 1..n] of var float: utility;
% array[1..m, 1..n] of var float: distribution;

% ----- Constraints ----- %
constraint forall(i in 1..m, j in 1..n)(
	if num_areas[i, j] == 0.0 then
		utility[i, j] = (alpha_yard * (yard_cells[i, j] / max_yard) + (street_cells[i, j] / max_street)) * (densities[i, j] / max_densities) / ((green_space[i, j] / max_green) * (num_trees[i, j] / max_trees))
	else
		utility[i, j] = (((alpha_yard * (yard_cells[i, j] / max_yard)) + (street_cells[i, j] / max_street)) / (num_areas[i, j] / max_areas)) * (densities[i, j] / max_densities) / ((green_space[i, j] / max_green) * (num_trees[i, j] / max_trees))
	endif
);

constraint forall(i in 1..m, j in 1..n)(
	street_cells[i, j] <= beta_streets * street_space[i, j]
);

constraint forall(i in 1..m, j in 1..n)(
	yard_cells[i, j] <= ext_space[i, j]
);

% constraint forall(i in 1..m, j in 1..n)(
% 	if i<=dw /\ j<=dw then distribution[i, j] = sum(k in 1..i+dw, z in 1..j+dw where street_cells[k, z] + yard_cells[k, z] > 0.0)(1) else
% 	if i<=dw /\ j>n-dw then distribution[i, j] = sum(k in 1..i+dw, z in j-dw..n where street_cells[k, z] + yard_cells[k, z] > 0.0)(1) else
% 	if i>m-dw /\ j<=dw then distribution[i, j] = sum(k in i-dw..m, z in 1..j+dw where street_cells[k, z] + yard_cells[k, z] > 0.0)(1) else
% 	if i>m-dw /\ j>n-dw then distribution[i, j] = sum(k in i-dw..m, z in j-dw..n where street_cells[k, z] + yard_cells[k, z] > 0.0)(1) else

% 	if i<=dw then distribution[i, j] = sum(k in 1..i+dw, z in j-dw..j+dw where street_cells[k, z] + yard_cells[k, z] > 0.0)(1) else 
% 	if i>m-dw then distribution[i, j] = sum(k in i-dw..m, z in j-dw..j+dw where street_cells[k, z] + yard_cells[k, z] > 0.0)(1) else 
% 	if j<=dw then distribution[i, j] = sum(k in i-dw..i+dw, z in 1..j+dw where street_cells[k, z] + yard_cells[k, z] > 0.0)(1) else 
% 	if j>n-dw then distribution[i, j] = sum(k in i-dw..i+dw, z in j-dw..n where street_cells[k, z] + yard_cells[k, z] > 0.0)(1) else 
% 	distribution[i, j] = sum(k in i-dw..i+dw, z in j-dw..j+dw where street_cells[k, z] + yard_cells[k, z] > 0.0)(1) 
% 	endif endif endif endif endif endif endif endif
% );

constraint forall(i in 1..m, j in 1..n)(
	street_cells[i, j] + yard_cells[i, j] + green_space[i, j] <= 10000
);

constraint sum(i in 1..m, j in 1..n where street_cells[i, j] != 0.0 \/ yard_cells[i, j] != 0.0)(1) <= top_k;

% ----- Objective Variable ----- %
var float: utility_mean = sum(i in 1..m, j in 1..n)(utility[i, j]) / top_k;

solve maximize utility_mean;