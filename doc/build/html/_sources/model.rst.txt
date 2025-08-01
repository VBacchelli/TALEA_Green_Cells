Model
============

The model objective is to find the n "best" cells where place a green cell.
The best n cells are chosen as those with the highest utility function.
The utility function for the cell :math:`i_{th}` is defined as:

.. math::

   \text{utility}_i = \text{macro\_factor}_i \times 
   \frac{
      \left( \alpha_{\text{yard}} \frac{\text{yard\_cells}_i}{\text{max\_yard}} 
      + \frac{\text{street\_cells}_i}{\text{max\_street}} \right) 
      \Big/ \frac{\text{num\_areas}_i}{\text{max\_areas}}
   }{
      \frac{\text{green\_space}_i}{\text{max\_green}} 
      \times \frac{\text{num\_trees}_i}{\text{max\_trees}}
   }

- macro_factor, which acts as a multiplicative factor to the "real" utility function. It is composed by the green space and the population density of the whole "area statistica", where the actual cell is. The macro factor increases proportionally with respect to the population density and inversely with respect to the green space. The impact of population density and green space can be regulated by density_param and green_param, which spans in a range [0, 1];
.. math::

    \text{macro\_factor}_i = (density\_param * density\_factor_i) + (green\_param * green\_factor_i)
    
- street_cells: streets area inside the cell, using the parameter beta_street we can regulate which pecentage of street we are considering during the green placement;
- yard_cells: yard area inside the cell, using the parameter alpha_yard we can regulate which pecentage of yards we are considering during the green placement;
- num_areas: the number of yard_cells inside a cell. The higher it is this number the more the yard area is fragmented;
- green_space: the amount of green area already present in the cell;
- num_trees: the number of trees in the cell.