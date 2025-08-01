Results 
==========
The optimization model developed was applied to two different spatial scales: the city center of Bologna and 
the entire municipal area. For both case studies, five distinct configurations were tested to explore how different priorities and 
constraints affect the placement of new green areas.

Bologna city center
-----------------------
In the city center scenario (20 cells), the default configuration balanced population density and green distribution equally, 
resulting in a fairly even allocation of new green areas across statistical zones. 
When the green-enhanced configuration was applied, giving green availability 100 times more importance than population density, 
the model concentrated interventions in areas already characterized by a greener profile, reinforcing existing green corridors. 
Conversely, the density-enhanced configuration, which prioritized population density over green coverage, led to a markedly different 
pattern: new green spaces were shifted toward highly populated but underserved areas, reflecting the model's ability to target areas of 
greatest need when the objective function is adjusted.

The no-streets configuration, which prevented streets from being buildable, encouraged the algorithm to use external spaces more intensively. 
This led to more dispersed but spatially efficient solutions, favoring residual areas over linear corridors. In contrast, the no-yards 
configuration, which removed the contribution of external spaces from the utility function, pushed the model to prioritize street-based 
interventions, leading to a denser but less organically distributed placement pattern.

Bologna entire city
-----------------------

Scaling up to the entire city (50 cells) showed both similarities and divergences compared to the city center. 
The default configuration again produced a balanced distribution, but the larger grid size allowed for more nuanced spatial differentiation. 
The green-enhanced scenario amplified existing ecological networks, reinforcing peri-urban green belts and emphasizing environmental continuity. 
The density-enhanced scenario, on the other hand, shifted the focus to dense neighborhoods, 
including peripheral districts where population pressure is high.

The no-streets and no-yards configurations had more pronounced effects at the citywide scale. 
Forbidding street conversions increased reliance on open land parcels, often at the edge of the urban fabric, 
while ignoring yards led to concentrated interventions along major thoroughfares. These contrasting results highlight the model's 
sensitivity to land-use assumptions and its potential to support policy decisions by illustrating trade-offs between preserving mobility 
infrastructure and expanding green space.

Discussion
-----------------
Overall, the results demonstrate that the optimization framework is highly adaptable and responsive to policy priorities. 
The contrasting outcomes between configurations illustrate how decision-makers can steer urban greening strategies: 
emphasizing ecological value yields a greener but less socially targeted pattern, while prioritizing population density directs green 
spaces toward areas with the highest human benefit. The city center experiments showed the model's potential to manage tight urban 
constraints, while the citywide application confirmed scalability and the ability to accommodate diverse urban morphologies.

These findings suggest that the model can serve as a decision-support tool for Bologna's urban planning, 
enabling evidence-based discussions about the trade-offs between green equity, ecological connectivity, and land-use constraints.