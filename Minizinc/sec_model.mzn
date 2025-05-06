include "globals.mzn";

QuadrFloat = true;

% ----- Input ----- %
int: m;
int: n;
array[1..m, 1..n] of float: street_space;
array[1..m, 1..n] of float: ext_space;
array[1..m, 1..n] of float: green_space;
array[1..m, 1..n] of float: num_areas;
array[1..m, 1..n] of float: densities;

int: dw = 2;
int: top_k = 50;
float: beta_streets = 0.1;
float: alpha_yard = 1.0;
float: max_street = beta_streets * max(street_space);
float: max_yard = max(ext_space);
float: max_densities = max(densities);
float: max_areas = max(num_areas);
float: max_green = max(green_space);


% ----- Decision Variables ----- %
array[1..m, 1..n] of var 0..max_street: street_cells;
array[1..m, 1..n] of var 0..max_yard: yard_cells;
array[1..m, 1..n] of var float: utility;
array[1..m, 1..n] of var float: distribution;


% ----- Constraints ----- %
constraint forall(i in 1..m, j in 1..n)(
	if num_areas[i, j] == 0.0 then
		utility[i, j] = (alpha_yard * (yard_cells[i, j] / max_yard) + (street_cells[i, j] / max_street)) * (densities[i, j] / max_densities) / (green_space[i, j] / max_green) / ((distribution[i, j] + 1.0) / ((2*dw+1)*(2*dw+1)))
	else
		utility[i, j] = (((alpha_yard * (yard_cells[i, j] / max_yard)) + (street_cells[i, j] / max_street)) / (num_areas[i, j] / max_areas)) * (densities[i, j] / max_densities) / (green_space[i, j] / max_green) / ((distribution[i, j] + 1.0) / ((2*dw+1)*(2*dw+1)))
	endif
);

constraint forall(i in 1..m, j in 1..n)(
	street_cells[i, j] <= beta_streets * street_space[i, j]
);

constraint forall(i in 1..m, j in 1..n)(
	yard_cells[i, j] <= ext_space[i, j]
);

constraint forall(i in 1..m, j in 1..n)(
	street_cells[i, j] + yard_cells[i, j] + green_space[i, j] <= 10000
);

constraint sum(i in 1..m, j in 1..n where street_cells[i, j] != 0.0 \/ yard_cells[i, j] != 0.0)(1) <= top_k;

constraint forall(i in 1..dw, j in 1..n-dw)(
	distribution[i, j] = sum(k in i..i+dw, z in j..j+dw where street_cells[k, z] + yard_cells[k, z] > 0.0)(1)
);

constraint forall(i in 1..m-dw, j in n-dw+1..n)(
	distribution[i, j] = sum(k in i..i+dw, z in j-dw..j where street_cells[k, z] + yard_cells[k, z] > 0.0)(1)
);

constraint forall(i in m-dw+1..m, j in dw+1..n)(
	distribution[i, j] = sum(k in i-dw..i, z in j-dw..j where street_cells[k, z] + yard_cells[k, z] > 0.0)(1)
);

constraint forall(i in dw+1..m, j in 1..dw)(
	distribution[i, j] = sum(k in i-dw..i, z in j..j+dw where street_cells[k, z] + yard_cells[k, z] > 0.0)(1)
);

constraint forall(i in dw+1..m-dw, j in dw+1..n-dw)(
	distribution[i, j] = sum(k in i-dw..i+dw, z in j-dw..j+dw where street_cells[k, z] + yard_cells[k, z] > 0.0)(1)
);


% ----- Objective Variables ----- %
var float: utility_mean = sum(i in 1..m, j in 1..n)(utility[i, j]) / top_k;
%var float: distribution_mean = sum(i in 1..m-dw, j in 1..n-dw)(distribution[i, j]) / (m*n);

solve maximize utility_mean;