Model
============

The model is built on the objective of finding the :math:`n` "best" cells to place a TGC, that maximize a **utility function**.
It is the composition of a **macro factor** and a **micro factor**, where only the last one is effectively influenced by the placement. For each cell :math:`i_{th}` the function is defined as:

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

- :math:`macro\_factor` :math:`\rightarrow` acts as a simple multiplicative factor. It is computed with the green space and the population density of the whole "area statistica" where the actual cell is. In particular, it increases proportionally with respect to the population density (:math:`density\_factor`) and inversely with respect to the green space (:math:`green\_factor`). The impact of these two factors is weghted through a :math:`density\_param` and a :math:`green\_param`, which span in the range [0, 1];

.. math::

    \mathrm{macro\_factor}_i = \mathrm{density\_param} * \mathrm{density\_factor}_i + 
    \mathrm{green\_param} * \mathrm{green\_factor}_i
    
- :math:`street\_cells` :math:`\rightarrow` streets area inside the cell. With the parameter :math:`\beta_{streets}`, we can regulate which pecentage of the street is available for the placement of a TGC;

.. math::

    \mathrm{street\_cells}_i \leq \beta_{\mathrm{streets}} \cdot \mathrm{street\_area}_i

- :math:`yard\_cells` :math:`\rightarrow` yard area inside the cell. The placement of a TGC here is limited by the free space (:math:`ext\_space` in the model) and its impact of the utility function is regulated by the parameter :math:`\alpha_{yard}`;

.. math::

    \mathrm{yard\_cells}_i \leq \mathrm{ext\_space}_i

- :math:`num\_areas` :math:`\rightarrow` number of yard_cells inside a cell. The higher it is, the more the yard area is fragmented and the lower is the utility;
- :math:`green\_space` :math:`\rightarrow` amount of green area already present in the cell. The utility grows inversely to this value;
- :math:`num\_trees` :math:`\rightarrow` number of trees in the cell (same behavior as the green space).

All the elements in the utility function are normalized on the basis of their maximum value, in a way that each factor influces the utility equally.

[NOTE -- TO BE TESTED WITHOUT]
Anyways, while developing the model, we noticed that some cells lack of data information regarding the land usage. 
To address this problem, we introduced a constraint that serves as an approximation, preventing the model from placing green areas 
if the cell's space exceeds half of the total available space. 
This approximation was necessary due to the lack of data, 
helping to avoid situations where the model assigns green space to areas that may actually contain features we have no information about.