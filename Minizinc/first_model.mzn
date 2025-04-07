include "globals.mzn";

% ----- Input ----- #
int: m;
int: n;
array[1..m*n] of int: FS;
array[1..m*n] of int: GS;

% ----- Decision Variables ----- #
array[1..m, 1..n] of var int: green_cells;
array[1..m-4, 1..n-4] of var int: distribution;
var int: cost = sum(i in 1..m, j in 1..n)(green_cells[i, j]);

% ----- Constraints ----- #
constraint forall(i in 1..m*n)(
    if FS[i] < 2500 then green_cells[i] = 0 endif
)

constraint forall(i in 1..n)(
    if GS[i] > 1100 then green_cells[i] = GS[i] endif
)

constraint cost <= 10000;

constraint forall(i in 1..m-4, j in 1..n-4)(
    distribution[i, j] = sum(k in i..i+4, z in j..j+4)(green_cells[(k-1)*m + z])
)

% ------ Objective Variables ----- #
var int: num_cells = sum(i in 1..n where green_cells[i] != 0)(1);

solve maximize num_cells;