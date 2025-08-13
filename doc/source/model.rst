Model
============

The model objective is to find the n "best" cells where place a green cell.
The best n cells are chosen as those with the highest utility function.
The utility function for the cell :math:`i_{th}` is defined as:

.. math::

    \mathrm{utility}_i =
    \mathrm{macro\_factor}_i \times
    \frac{
        \alpha_{\mathrm{yard}} \cdot \mathrm{yard\_cells}_i
        + \mathrm{street\_cells}_i
    }{
        \mathrm{num\_areas}_i
        + \mathrm{green\_space}_i
        + \mathrm{num\_trees}_i
    }

- macro_factor, which acts as a multiplicative factor to the "real" utility function. It is composed by the green space and the population density of the whole "area statistica", where the actual cell is. The macro factor increases proportionally with respect to the population density and inversely with respect to the green space. The impact of population density and green space can be regulated by density_param and green_param, which spans in a range [0, 1];
.. math::

    \mathrm{macro\_factor}_i = \mathrm{density\_param} * \mathrm{density\_factor}_i + 
    \mathrm{green\_param} * \mathrm{green\_factor}_i
    
- street_cells: streets area inside the cell, using the parameter beta_street we can regulate which pecentage of street we are considering during the green placement;
- yard_cells: yard area inside the cell, using the parameter alpha_yard we can regulate which pecentage of yards we are considering during the green placement;
- num_areas: the number of yard_cells inside a cell. The higher it is this number the more the yard area is fragmented;
- green_space: the amount of green area already present in the cell;
- num_trees: the number of trees in the cell.

All the elements in the utility function are normalized on the basis of their maximum value.

While developing the model, we noticed that some cells miss data information. 
To address this, we introduced a constraint that serves as an approximation, preventing the model from placing green areas 
if the cell's space exceeds half of the total available space. 
This approximation was necessary due to the lack of data, 
helping to avoid situations where the model assigns green space to areas that may actually contain features we have no information about.