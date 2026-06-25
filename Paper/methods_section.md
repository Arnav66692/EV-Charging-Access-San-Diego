# Methods

## Study area and unit of analysis

The study area was San Diego County, California (FIPS code 06073). The unit of analysis was the
census block group. The county contains 2,058 block groups in the 2020 census geography. Block
groups were chosen because the American Community Survey reports tenure, housing type, and income
at the block-group level with acceptable reliability. The census tract is coarser, and the census
block is too small for stable ACS estimates. CalEnviroScreen is published at the tract level and
was joined down to block groups by containment.

All distance computation was performed in a projected coordinate system, EPSG:3310 (California
Albers Equal Area), so that distances were measured in meters rather than degrees. Distances were
converted to miles for reporting. Input geometries were reprojected to this system before any
distance or area calculation.

## Data sources

Charging station locations were obtained from the Alternative Fuels Data Center (AFDC)
Alternative Fuel Stations dataset [@afdc_stations]. The dataset was queried for public electric
stations in California and clipped to San Diego County by a point-in-polygon test against the
U.S. Census TIGER/Line 2024 county boundary [@tiger_2024]. After clipping, 1,648 public stations were located in the county. The accessibility analysis used only stations the data marked operational, which left 1,607 public stations, of which 212 offered direct-current fast charging (DCFC). The station record includes the operating
network and the number of Level 2 and DCFC ports, which were used as the supply input to the
accessibility model. The dataset also includes a station-level operational status field, which is
a coarse daily availability indicator and not a measure of session-level uptime. This field was
not used as a reliability measure.

Demographic data were drawn from the American Community Survey (ACS) 5-year estimates [@acs_2023]
for San Diego County block groups. The following tables were used: tenure (renter versus owner),
units in structure (used to derive multifamily housing share), median household income, and total
population. Block-group identifiers were stored as twelve-character strings to preserve the
leading zero of the California state FIPS code.

The Census Bureau suppresses median household income for small-sample block groups and returns a
sentinel value rather than a null. These sentinel values were converted to missing, which
affected 89 of the 2,058 block groups. Rather than dropping these block groups, which would have
removed military installations and low-density areas non-randomly, their income was imputed from
the parent tract median. Imputed block groups were flagged so they could be included in access and
density calculations but excluded from direct income claims, and so a sensitivity analysis with
and without imputed values could be run.

Disadvantaged-community (DAC) status was defined using CalEnviroScreen 4.0 [@calenviroscreen_4]. A
block group was classified as a DAC when its CalEnviroScreen percentile was at or above 75, the
standard top-quartile threshold used as a proxy for the California SB 535 designation. This is a
first-order equity proxy and not a regulatory determination. After classification, 142 block
groups were DACs.

CalEnviroScreen 4.0 is built on 2010 census tracts, while the ACS and TIGER geographies use 2020
tracts. A direct join left 24 percent of block groups without a DAC value. To resolve this,
CalEnviroScreen percentiles were crosswalked from 2010 tracts to 2020 tracts using the Census
2020-to-2010 tract relationship file. Each 2020 tract received the land-area-weighted average of
the CalEnviroScreen percentiles of the 2010 tracts it overlapped, weighted by the overlapping land
area. DAC status was then recomputed by applying the 75th-percentile threshold to the crosswalked
percentile. This raised DAC coverage from 76 percent to 100 percent of block groups, with 491
block groups receiving crosswalked values. Crosswalked values were flagged so that directly
matched and crosswalked DAC values could be separated in a sensitivity analysis. One block group
had no overlapping scored tract and was left without a DAC value. It was excluded from all DAC and
non-DAC contrasts, which is why the non-disadvantaged group contains 1,915 block groups rather
than 1,916.

## Spatial accessibility metric

Charging accessibility was measured using the Gaussian two-step floating catchment area (G2SFCA)
method. The two-step floating catchment area method was introduced to measure spatial access to
primary care [@luo_wang_2003_2sfca], and the Gaussian distance-decay refinement was added by Dai
[@dai_2010_gaussian2sfca]. Accessibility and equity of electric-vehicle charging have been
studied with a range of spatial and network methods [@khan_2021_inequitable; @ju_2025_trajectory].

The method proceeds in two steps. In the first step, for each charging station, a supply-to-demand
ratio was computed as the station supply divided by the population within the catchment, with each
block group's population weighted by its distance from the station. In the second step, for each
block group, the accessibility score was computed as the sum of the supply-to-demand ratios of all
stations within the catchment, again weighted by distance. The distance weight used a normalized
Gaussian decay that equals one at the station and zero at the catchment edge, following the Dai
form:

For each station j, the supply-to-demand ratio is
$$R_j = \frac{S_j}{\sum_{k:\, d_{kj} \le d_0} P_k\, G(d_{kj})},$$
and for each block group i, the accessibility score is
$$A_i = \sum_{j:\, d_{ij} \le d_0} R_j\, G(d_{ij}),$$
where $S_j$ is station supply, $P_k$ is block-group population, and $G$ is the decay weight below.

$$G(d) = \frac{\exp\!\left(-\tfrac{1}{2}(d/d_0)^2\right) - \exp\!\left(-\tfrac{1}{2}\right)}{1 - \exp\!\left(-\tfrac{1}{2}\right)} \quad \text{for } d \le d_0, \quad \text{and } 0 \text{ otherwise,}$$

where $d$ is the distance from block group to station and $d_0$ is the catchment radius.

Accessibility was computed separately for the two charger types, because travel behavior differs
between them. Fast charging used a catchment radius of 6 miles and direct-current fast-charging
ports as supply. Level 2 charging used a catchment radius of 2 miles and Level 2 ports as supply.
These radii sit at the shorter end of the published range and are supported by the observed
distance distribution in the county, where the median block group was within roughly one mile of a
fast charger. Level 2 and fast-charging access were reported separately throughout, so no combined service weight was needed and none was used in any reported result. Population was the demand term throughout. The catchment radius was varied between 4 and 10 miles as a sensitivity check.

## Reliability-weighted accessibility

This study extended the G2SFCA metric by weighting each station's effective supply by its expected
reliability before the supply-to-demand ratio was computed. To our knowledge, prior
electric-vehicle accessibility studies have not weighted access by charger reliability, and
instead treat every charger as fully available.

We assigned each station an expected session success rate according to its operating network. We set these rates to Tesla and Tesla Destination 0.95, ChargePoint 0.85, Electrify America 0.80, EVgo 0.75, Blink 0.70, Shell Recharge 0.70, and all other or non-networked stations 0.75. These are values we assigned to preserve the relative network ranking reported by J.D. Power, used as a proxy for relative reliability, not measured uptime [@jdpower_evx_2025]. They are not point estimates drawn from that source. The rates are assumed national averages and not measured San Diego uptime. Measured
station-level uptime for publicly funded DC fast chargers in California is scheduled to become available beginning in 2027 under state
reporting requirements [@ab2061_2022], and the method is structured to accept that data when it is
published.

The effective supply of each station was computed as the number of ports multiplied by the
network's expected success rate. $$S_j^{\mathrm{rel}} = S_j \times r_j,$$ where $r_j$ is the
assumed reliability of station j's network. The reliability-weighted accessibility score was then computed
using the same two-step procedure, decay function, and catchments as the unweighted metric. The
effect was tested for sensitivity by narrowing the assumed reliability spread, by widening it, and
by reordering the network ranking, and the sign of the disparity was unchanged in each case, though reordering the network ranking narrowed the magnitude.

## Equity contrasts

Access was compared across four equity axes: disadvantaged-community status, median household
income quartile, renter share, and multifamily-housing share. For each axis, accessibility was
summarized as a population-weighted median, so that the comparison reflected people rather than
block groups. The disadvantaged-community contrast was reported as the ratio of disadvantaged to
non-disadvantaged population-weighted access, where a value below one indicates worse access. The
disadvantaged-community contrast was also recomputed with crosswalked values excluded, to confirm
the result held on directly matched block groups.

## Siting optimization

A greedy optimization identified locations where new DCFC capacity would most reduce the access
gap for disadvantaged communities. The objective was to maximize the population-weighted mean of
the reliability-weighted DCFC accessibility score among DAC block groups. The mean was used as the
objective because it updates consistently after each greedy step. The procedure is a heuristic
siting analysis, not a proof of globally optimal placement. The population-weighted median was retained as a reported outcome measure but was not optimized. Gap closure is reported as the fraction of the distance to parity that is closed in ratio space, computed as the post-siting ratio minus the pre-siting ratio, divided by one minus the pre-siting ratio, with non-disadvantaged access taken at its post-siting value. On the reliability-weighted siting surface the population-weighted mean disadvantaged-to-non-disadvantaged ratio was 0.6420 before siting, and the population-weighted median ratio was 0.6533.

Candidate locations were the existing block-group centroids. This is an explicit simplification.
The analysis asked where an added DCFC-serving location would most reduce the gap, not whether a
specific parcel was available or buildable. Block groups in the rural low-density tail, which the
G2SFCA method is known to overstate, were excluded from the candidate set. Each hypothetical site
was assigned a supply of 4 DCFC ports at an assumed reliability of 0.80. The procedure was
iterative. At each step, the single candidate that most increased the objective was added, the
accessibility scores were recomputed with that site in place, and the step was repeated until 10
sites had been selected. Because the additive model captures competition between new and existing
chargers but not among the newly selected sites, the combined gain from clustered sites is an
upper bound. The additive model does not represent queueing, driver substitution between stations, or congestion relief.

## Reproducibility and statistical treatment

The full pipeline was implemented in Python and committed to a version-controlled repository, with
each metric unit-tested or checked against a hand-computed reference before use. The full pipeline is available at REPO_URL_PENDING. Because census
block groups are spatially autocorrelated, neighboring units are not independent observations.
Effect sizes were therefore reported as the primary evidence, and p-values were treated as
optimistic and not reported.

We measured this autocorrelation directly. Global Moran's I was 0.46 on the fast-charging access surface and 0.80 on the Level 2 surface, both with permutation p of 0.001 under queen contiguity, confirming strong positive spatial autocorrelation.
