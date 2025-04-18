include "globals.mzn";

% ----- Input ----- #
int: m;
int: n;
array[1..m, 1..n] of int: FS;
array[1..m, 1..n] of int: GS;
int: threshold = 1000;

% ----- Decision Variables ----- #
array[1..m, 1..n] of var 0..10000: green_cells;
array[1..m-4, 1..n-4] of var 0..250000: distribution;
array[1..m-4, 1..n-4] of var 0..250000: fake_distribution;
var int: cost = sum(i in 1..m, j in 1..n where GS[i, j] <= threshold)(green_cells[i, j]);
var float: distr_mean;

% ----- Constraints ----- #

%%% TODO: aggiungi verde esistente anche alle nuove green cells %%%

constraint forall(i in 1..m, j in 1..n)(
    if FS[i, j] < threshold then green_cells[i, j] = 0 endif /\
    %if FS[i, j] >= 2000 then green_cells[i, j] != 0 endif /\
    if GS[i, j] > threshold then green_cells[i, j] = GS[i, j] endif
);

%constraint forall(i in 1..m, j in 1..n)(
%	 green_cells[i, j] >= 100
%);

%constraint forall(i in 1..m, j in 1..n)(
%	 green_cells[i, j] <= FS[i, j]
%);

constraint cost <= 10000000;

constraint forall(i in 1..m-4, j in 1..n-4)(
	 distribution[i, j] = sum(k in i..i+4, z in j..j+4)(green_cells[k, z])
);

constraint forall(i in 1..m-4, j in 1..n-4 where GS[i, j] <= threshold)(
	 fake_distribution[i, j] = sum(k in i..i+4, z in j..j+4)(green_cells[k, z])
);

constraint distr_mean = sum(i in 1..m-4, j in 1..n-4)(distribution[i, j]) / ((m-4)*(n-4));

constraint forall(i in 1..m-4, j in 1..n-4)(
    fake_distribution[i, j] >= distr_mean - distr_mean*0.2 /\
    fake_distribution[i, j] <= distr_mean + distr_mean*0.2
);

% ------ Objective Variables ----- #
var 0..m*n: num_cells = sum(i in 1..m, j in 1..n where green_cells[i, j] != 0)(1);

solve
	::int_search(green_cells, dom_w_deg, indomain_random)
maximize num_cells;

