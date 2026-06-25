<!-- Assembled from Paper/*_section.md. Build (PDF):
     cd Paper && pandoc main.md --citeproc --bibliography=../references.bib \
       --pdf-engine=xelatex -V fontsize=11pt -V geometry:margin=1in -N -o main.pdf
     Regenerate figures first: .venv/bin/python Code/figures/make_figures.py
     All six figures live in the Results section, in order F1..F6. -->

---
title: "Beyond charger counts: competition- and equity-aware electric-vehicle charging access in San Diego County"
author:
  - Arnav Singh
date: 2026
bibliography: ../references.bib
link-citations: true
header-includes:
  - \usepackage{float}
  - \floatplacement{figure}{H}
abstract: |
  Public charging is the main option for residents who cannot charge at home, yet charging
  decisions usually rest on charger counts and proximity, which ignore how many people compete for
  each charger and whether chargers work. This study measured electric-vehicle charging access
  across 2,058 census block groups in San Diego County using a Gaussian two-step floating catchment
  area method, then extended it to discount each charger's supply by its network's assumed
  reliability. Three findings emerged. First, the expectation that renters and apartment residents are most underserved did not hold. Renter-heavy and multifamily-heavy areas had more charging access, not less, concentrated in Level 2 charging that does not substitute for the overnight home charging renters lack, and the access deficit fell on disadvantaged-community status, not housing tenure. This was the sharpest equity axis and it survived every individual sensitivity tested, though not the single joint extreme of a 10-mile catchment combined with linear income-weighted demand. Second, accounting for the population competing for each charger reversed the proximity picture for disadvantaged communities. They looked closer to fast charging by straight-line distance but were worse served once competition was counted, which quantifies for San Diego the correction that accessibility methods were designed to make. The direction of this deficit was stable across every reasonable choice of catchment radius and demand measure, but its magnitude was not. The shortfall ran from roughly 2 to 34 percent, with the population-weighted access ratio at 0.6845 in the primary specification, and that magnitude rests on a thin base of 33 fast-charging ports, with a station-level bootstrap placing the ratio between 0.41 and 1.02 and about 3.4 percent of resamples reaching parity. This finding is descriptive, not causal. The direction is stable across specifications, but the gap is not separable from spatial structure: it attenuates to non-significance under a spatial-error model, and the station-level bootstrap interval includes parity. We therefore report it as a population-weighted contrast, not as an identified or statistically separable effect. Weighting demand toward likely electric-vehicle owners, a normative choice rather than a measurement, narrowed the gap to 0.818 under linear income weighting, still below parity. Third, because disadvantaged communities draw more of their fast-charging supply from lower-reliability networks, discounting supply by assumed network reliability widened the gap rather than narrowing it. This network-composition disparity is measured, the discount on top of it is an illustrative consequence of assumed national priors, and we report it as a sensitivity, not the study's main finding. A greedy optimization identified in-corridor south-county candidate locations that directed nearly
  all gains to disadvantaged communities, closing an estimated 31.0 percent of the gap at the mean and 48.4 percent at the median. These closures are model upper bounds, because the chosen sites cluster, and the model does not address whether the identified candidate locations are buildable, permitted, or grid-connected. The siting is illustrative rather than a claim of optimal or deliverable placement. The reliability values are assumed national priors, not measured uptime, and the
  framework is built to ingest measured data when it publishes.
---

# Introduction

Electric vehicle adoption in California is rising faster than the public charging network that
supports it. People who can charge at home rarely depend on public infrastructure. Renters and
residents of multifamily buildings often cannot install a home charger, so for them public
charging is the primary way to keep a vehicle usable. San Diego County has aggressive vehicle
electrification goals, but the value of those goals depends on whether public charging is
actually reachable for the households that lack private alternatives. Where reliable public
charging is missing, electrification stalls for the residents who have the fewest options.
Identifying those neighborhoods is a prerequisite for spending limited public charging dollars
well.

Infrastructure decisions commonly rest on charger counts and proximity maps. Both are easy to
compute and both can mislead. A charger count says nothing about how many people compete for
each port. A proximity map can make a dense neighborhood look well served precisely because
chargers cluster where people cluster, even when each charger is shared by far more residents.
Spatial accessibility methods were developed to correct this. The two-step floating catchment
area method and its Gaussian-decay extension, drawn from the health care access literature,
measure access as the ratio of supply to the population that competes for it within a travel
radius [@luo_wang_2003_2sfca; @dai_2010_gaussian2sfca]. Accessibility and equity of charging have
become an active area of study [@khan_2021_inequitable; @ju_2025_trajectory; @kinchen_2025_unified; @yu_2025_equity_reliability].

Two gaps remain. First, accessibility studies of charging assume that every charger works.
They count a station as available supply whether or not it is in service. Charger reliability
is a documented and network-correlated problem, yet to our knowledge prior accessibility
studies rarely discount a charger's supply by its expected uptime [@chen_2025_equity_review].
Second, the common intuition that renters and apartment residents are the most underserved
group has not been tested against an accessibility measure that distinguishes charger types.
Renters lack overnight home charging, but workplace and commercial Level 2 charging is
concentrated in the same dense areas where renters live, and the two are not interchangeable.
Whether the renter deficit survives a type-aware accessibility measure is an open question.

This study measured EV charging access in San Diego County and then extended the measure to
account for reliability. We computed Gaussian two-step floating catchment access for 2,058
census block groups, using public charging station locations [@afdc_stations], block-group
demographics from the American Community Survey [@acs_2023], and disadvantaged-community status
from CalEnviroScreen 4.0 [@calenviroscreen_4]. We then discounted each station's supply by its
network's expected reliability before computing access, using assumed national reliability
averages by network [@jdpower_evx_2025]. These reliability values are
assumed priors, not measured San Diego uptime. Station-level uptime data for publicly funded DC fast chargers in California will
become available beginning in 2027 under state reporting requirements [@ab2061_2022], and the
method was built to ingest that data when it exists. A greedy optimization then used the
reliability-weighted measure to identify where added fast charging would most reduce the
disadvantaged-community access gap.

Three findings followed, and together they revise a common assumption about who lacks charging access. First, the renter assumption did not hold. We expected renter-heavy and multifamily-heavy areas to be worst served, and they were not. They had more access, not less, concentrated in Level 2 charging that does not substitute for the overnight home charging renters lack, and the sharpest equity gap fell on disadvantaged-community status, not housing tenure. This is the study's central empirical result. Second, accounting for competition reversed the proximity picture. By straight-line distance, disadvantaged communities appeared better served, but once the competing population was counted they were worse served for fast charging, by roughly 2 to 34 percent across reasonable choices of catchment radius and demand measure. This quantifies for San Diego the correction that accessibility methods were built to make, rather than a surprise about the method itself. Third, because the chargers disadvantaged communities depend on are disproportionately on lower-reliability networks, discounting supply by assumed reliability widened the gap rather than narrowing it. The measured content of this finding is the network-composition disparity itself, and the discount is one illustrative consequence of assumed priors. The unifying point is that charging equity is mischaracterized when access is measured by proximity or charger counts, and that the group conventionally assumed to be worst served is not the one carrying the deficit here.

Recent work documents equity and reliability of public charging together
[@yu_2025_equity_reliability], but treats them as separate descriptive measures rather than
folding reliability into the accessibility metric itself. The primary findings are the proximity reversal and the failure of the renter hypothesis, both of which revise how charging equity is usually measured. The study also reports an illustrative reliability discounting exercise. Its measured content is a network-composition disparity, that disadvantaged communities depend more on lower-reliability networks, and the discounting itself rests on assumed national priors rather than measured uptime, so we report it as a sensitivity rather than a contribution and are explicit about what those priors can and cannot support. The framework is transferable to any region with public charger
locations and demographic data, and it is built to use measured uptime as soon as that data
publishes. The remainder of the paper describes the data and methods, reports the three
findings and the siting result, and discusses limitations and policy implications.

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
each metric unit-tested or checked against a hand-computed reference before use. The full pipeline is available at https://github.com/Arnav66692/EV-Charging-Access-San-Diego. Because census
block groups are spatially autocorrelated, neighboring units are not independent observations.
Effect sizes were therefore reported as the primary evidence, and p-values were treated as
optimistic and not reported.

We measured this autocorrelation directly. Global Moran's I was 0.46 on the fast-charging access surface and 0.80 on the Level 2 surface, both with permutation p of 0.001 under queen contiguity, confirming strong positive spatial autocorrelation.

# Results

## Distance baselines and the accessibility reversal

By straight-line distance, disadvantaged communities were closer to fast charging than the rest
of the county. The population-weighted median distance to the nearest DC fast charger was 0.736
miles in disadvantaged-community block groups and 1.11 miles elsewhere. Proximity alone would
suggest disadvantaged communities were better served.

The accessibility metric reversed that picture. Once the population competing for each charger was
counted, the population-weighted median fast-charging access score was lower in disadvantaged
communities than elsewhere, 0.000233 versus 0.000341 (both rounded to three significant figures, with the ratio below computed from the unrounded medians). The ratio of disadvantaged to non-disadvantaged access was 0.6845 at the primary specification, about 32 percent worse served, and roughly 2 to 34 percent worse across the range of specifications reported below (Figure 1). The direction of the reversal was stable across single changes of assumption, but its size was not, and we report both. The reversal held across the catchment-radius check, with ratios of 0.6575, 0.6845, and 0.9752 at 4, 6, and 10 miles, never crossing parity, so the gap was widest at the shorter radii and narrowed to about 2 percent at 10 miles. It held when crosswalked disadvantaged-community values were excluded, at a ratio of 0.700. It held under a demand reweight that scaled effective demand toward higher-income block groups as a proxy for electric-vehicle ownership: the ratio rose from 0.6845 at residential population to 0.818 when demand scaled linearly with income, about 18 percent worse, and stayed below parity at every weighting up to a quadratic one (0.941). We weight demand by residential population rather than current electric-vehicle ownership for a specific reason. Population weighting answers a latent-demand question, who would be underserved if every household here owned an electric vehicle, which is the relevant question for an equity study about residents who lack private charging today. Weighting by current registrations instead answers a realized-demand question, and current adoption is itself shaped by the access gap this study measures, so registration weighting partly builds the outcome into the demand term. We therefore treat population as the primary measure and report the 0.818 linear and 0.941 quadratic income weightings as sensitivities. The reading we take is that disadvantaged communities were worse served for fast charging by roughly 2 to 34 percent depending on the catchment radius and demand measure, and that the direction did not depend on either choice taken alone.

One combination did cross parity. Imposing the 10-mile catchment and the linear income reweight together gave a ratio of 1.19, the only specification tested in which disadvantaged communities were not worse served. The 6-mile catchment is the primary specification, supported by the observed distance distribution in the county, where the median block group is within roughly one mile of a fast charger, and linear income weighting is an aggressive proxy for electric-vehicle ownership rather than a measurement of it. Stacking the conservative radius tail with the aggressive demand tail is therefore the least likely of the configurations tested. We report it because the deficit is not invariant to that joint extreme, and a reader should weigh the result against it.

The supply base behind this gap is thin, which we state plainly. Disadvantaged-community fast charging rests on 33 DCFC ports against 1,312 elsewhere. To bound the uncertainty this introduces, we resampled the result two ways at the primary specification. A spatial block bootstrap that resampled whole census tracts placed the access ratio between 0.599 and 0.808, with no resample of 2,000 reaching parity. A station-level bootstrap that resampled the DCFC stations placed it between 0.412 and 1.024, wider because of the small port count, with about 3.4 percent of resamples reaching parity. Under both schemes the gap pointed the same direction in at least 96 percent of resamples. The magnitude of the fast-charging deficit is uncertain, but at the primary specification its sign is not. Because straight-line distance can cross San Diego Bay, we also tested whether the bayfront geography inflates the gap. Excluding the 14 block groups whose nearest fast charger is reached only by a straight-line path across bay water moved the ratio from 0.6845 to 0.6842, so the deficit is not an artifact of measuring distance across water.

![Disadvantaged communities are closer to the nearest DC fast charger by straight-line distance, yet have lower G2SFCA fast-charging access once competing population is counted.](../Figures/F1_reversal_distance_vs_access.png){#fig:f1 width=85%}

The spatial pattern of fast-charging access is shown in Figure 2. Access concentrated in the urban
core and the South Bay. Low-density rural block groups, where the accessibility method overstates
access, are shown separately and were excluded from the siting analysis.

![DC fast-charging G2SFCA accessibility across San Diego County block groups (access percentile; low-density rural block groups greyed, where the metric overstates access).](../Figures/F2_access_choropleth.png){#fig:f2 width=85%}

## Equity contrasts across housing and environmental-justice axes

Access was contrasted across four axes (Figure 3). For income, renter share, and multifamily
share, the contrast is the ratio of the top quartile to the bottom quartile. For
disadvantaged-community status, it is the ratio of disadvantaged to non-disadvantaged areas. For income, renter share, and multifamily share, a value above one
means the top quartile is better served. For disadvantaged-community status the ratio is
disadvantaged to non-disadvantaged, so a value below one means disadvantaged communities are
worse served.

Renter-heavy and multifamily-heavy areas were better served, not worse. The renter ratio was 2.2250
for Level 2 and 1.2646 for fast charging. The multifamily ratio was 2.9771 for Level 2 and 1.4268 for
fast charging. The surplus was largest for Level 2 charging in both cases, which is the workplace
and commercial charging concentrated in dense areas, and much smaller for fast charging. Income
showed only a weak gradient, with a fast-charging ratio of 1.2517 and a Level 2 ratio of 0.9319.

Disadvantaged-community status was the sharpest axis. Disadvantaged communities had a fast-charging access ratio of 0.6845, well under one. Their Level 2 ratio fell below one only at the shorter Level 2 catchment, and at the matched 6-mile radius it rose above one, so the deficit that holds across specifications is the fast-charging one. The equity deficit in this county therefore tracked environmental-justice burden, not housing tenure. It was not an artifact of where the disadvantaged-community threshold was set. Recomputed at the 70th and 80th percentiles of the screening score, the fast-charging ratio was 0.76 and 0.73, against 0.68 at the 75th-percentile primary cutoff, and stayed below parity at every cut. The gap also held inside both tenure halves. Splitting block groups at the median renter share, disadvantaged renter-heavy and disadvantaged owner-heavy groups each had lower median fast-charging access than either non-disadvantaged group, so disadvantaged-community status dominated renter share rather than the reverse.

![Q4/Q1 access ratios by equity axis for Level 2 versus DC fast charging. Renter- and multifamily-heavy areas are better served, especially on Level 2, while disadvantaged-community status shows the sharpest gap.](../Figures/F3_equity_ratios_L2_vs_DCFC.png){#fig:f3 width=85%}

These four axes are correlated, so we tested whether the disadvantaged-community gap was a restatement of income with a single model. A linear regression of fast-charging access on disadvantaged-community status, income, renter share, and multifamily share, with the continuous predictors and the outcome standardized and disadvantaged-community status entered as a 0/1 indicator, gave disadvantaged-community status the largest and most negative coefficient, -0.47 with a standard error of 0.09, and the largest partial R-squared, 0.0130. Income carried a small positive coefficient of 0.09. The model explained little variance overall, with an R-squared of 0.035 across 2,048 block groups, so we read it as a ranking of weak predictors rather than a strong fit, in which disadvantaged-community status is distinguishable from zero even as the full model leaves most variation unexplained. The regression is fit on complete cases across all four predictors, ten block groups fewer than the county total of 2,058, because ten are missing at least one predictor input. One lacks disadvantaged-community status, eight lack income, and seven lack renter or multifamily share, overlapping to ten unique block groups. Within that ranking disadvantaged-community status was not absorbed by income, which matches the ratio contrasts. The association is not separable from spatial structure. When access was modeled with a spatial error term that absorbs geographically structured variation, the disadvantaged-community coefficient attenuated and lost significance, because disadvantaged communities and low-access areas cluster in the same part of the county. For this reason the equity claim is descriptive, that people in disadvantaged communities receive worse service, and rests on the population-weighted effect sizes rather than on regression inference that holds location constant. We treated the robustness checks as attempts to make the gap disappear, and report them in the order we ran them. It was not a restatement of income, since disadvantaged-community status kept the largest negative coefficient with income held in the same model. It was not an artifact of where the disadvantaged-community threshold was set, since it held at the 70th and 80th percentiles as well as the 75th. It was not produced by the catchment radius, since it held from 4 to 10 miles. It was not an artifact of measuring distance across water, since excluding the bayfront block groups left it unchanged (Section 3.1). And it reproduced on a random split of the county's census tracts into two halves, with ratios of 0.641 and 0.616, though this internal check is coarse because each half holds only a handful of fast-charging ports. Each attempt to explain the gap away failed.

## Reliability-weighted access

The supply disadvantaged communities depend on is drawn from different and lower-reliability networks than the rest of the county, a measured composition disparity. Discounting supply by assumed network reliability widens the fast-charging gap as a consequence, but that discount rests on assumed priors, so we report the composition disparity as the finding and the discount as an illustrative sensitivity rather than a central result.

The fast-charging ports located in disadvantaged communities came from a different network mix than
elsewhere (Figure 4). Among DCFC ports in disadvantaged-community block groups, 24 percent were
Tesla and 30 percent were EVgo. Among non-disadvantaged ports, 58 percent were Tesla and 15
percent were EVgo. Because Tesla carried the highest assumed reliability prior and EVgo a lower
one, the ports-weighted mean assumed reliability was 0.815 in disadvantaged communities and 0.875
elsewhere. The disadvantaged-community fast-charging mechanism rests on a small base of 33 DCFC
ports, against 1,312 elsewhere.

![Network composition of DC fast-charging ports in disadvantaged versus non-disadvantaged areas. Disadvantaged-community supply is EVgo-heavy while non-disadvantaged supply is Tesla-heavy.](../Figures/F4_network_mix_by_dac.png){#fig:f4 width=80%}

Weighting each station's supply by its network's expected reliability widened the gap rather than narrowing it. The measured driver is composition. Disadvantaged communities draw more of their fast-charging supply from lower-reliability networks (Figure 4). The disadvantaged-to-non-disadvantaged ratio moved from 0.6845 unweighted to 0.6533
weighted (Figure 5). The result behaved as the composition mechanism predicts under every perturbation tested. Uniform reliability applied to all chargers reproduced the unweighted ratio of 0.6845 exactly, at every uptime level from 60 to 100 percent, because uniform scaling cancels in a ratio, so the effect depends only on differences between networks. Compressing the assumed spread between networks gave 0.667 and widening it gave 0.649, both still widened relative to the unweighted baseline. The decisive test is inverting the ranking. When the network reliability values were inverted so that the network disadvantaged communities rely on most, EVgo, received the highest reliability and Tesla the lowest, the gap narrowed to 0.711, crossing above the unweighted 0.6845 but not reaching parity. This is the signature of the composition mechanism. Making the disadvantaged-community network the most reliable improves their relative access, confirming that network composition drives the effect, while the underlying supply disparity is deep enough that even a maximally favorable reliability assumption leaves disadvantaged communities worse served.

![Disadvantaged-to-non-disadvantaged DCFC access ratio before and after reliability weighting (0.6845 to 0.6533; figure labels rounded to three significant figures). Reliability weighting widens the gap.](../Figures/F5_reliability_ratio_base_vs_weighted.png){#fig:f5 width=70%}

## Greedy DCFC siting

The siting analysis optimizes the reliability-weighted fast-charging score, so its gap closures are reported against the reliability-weighted disadvantaged-community access gap, not against the unweighted headline gap of 0.6845. On the reliability-weighted surface the population-weighted mean disadvantaged-to-non-disadvantaged ratio was 0.6420 and the median was 0.6533, and each closure below is computed against the matching aggregate, the mean closures against 0.6420 and the median closures against 0.6533. We state this because the optimization targets the reliability-weighted surface, and the closure percentages should be read against the metric it actually maximizes.

A greedy procedure selected ten block-group locations for added DC fast charging, maximizing the
population-weighted mean reliability-weighted DCFC access of disadvantaged-community block groups
(Figure 6). All ten selected centroids lie in the South Bay corridor of southern San Diego County.
By incorporated place, reverse-geocoded against the U.S. Census geocoder, they fall in National
City (6 sites), Coronado (3), and the City of San Diego (1). Seven of the ten chosen block groups
are themselves disadvantaged communities. The three Coronado sites are non-disadvantaged bayfront
block-group centroids.

Excluding the three non-buildable Coronado bayfront centroids, the seven in-corridor sites raised the disadvantaged-community population-weighted mean access from 0.000236 to 0.000279, a gain of 18.6 percent, and the median from 0.000196 to 0.000247, a gain of 26.0 percent. This closed 31.0
percent of the disadvantaged-to-non-disadvantaged gap on the mean and 48.4 percent on the median.
These are the headline figures for the in-corridor candidate sites.

Including the three Coronado centroids, the full set of ten raised the disadvantaged-community mean to 0.000299, a gain of 27.0 percent, and the median to 0.000271, a gain of 38.5 percent, closing
45.0 percent of the gap on the mean and 71.5 percent on the median. These ten-site figures are an
upper bound, because the three Coronado centroids are non-buildable artifacts of using block-group
centroids and Euclidean distance, and because the additive model captures competition between new
and existing chargers but not among the newly selected sites. In both cases the modeled gains
accrued almost entirely to disadvantaged communities, with non-disadvantaged mean access rising
only 1.5 percent.

![Greedy DCFC siting. The ten selected block-group locations over disadvantaged-community block groups, concentrated in the South Bay corridor. Seven sites are in-corridor; three are non-buildable Coronado bayfront centroids, included only as an upper bound.](../Figures/F6_greedy_siting_map.png){#fig:f6 width=95%}

# Discussion

This study measured electric-vehicle charging access in San Diego County with a method that
accounts for how many people compete for each charger, then extended it to account for charger
reliability. Three findings emerged, and together they revise a common assumption about who
lacks charging access.

The first finding is the one that ran against the premise the study began with. We expected renters and apartment residents to have the worst access, since they cannot install home chargers. The data showed the opposite. Renter-heavy and multifamily-heavy areas had more charging access, not less. Splitting by charger type explained why. The renter surplus was large for Level 2 charging and much smaller for fast charging. Dense urban areas are rich in Level 2 chargers at workplaces and commercial sites, but that charging is not a substitute for the overnight home charging that renters without driveways lack. So the apparent renter advantage is real in the data but does not mean renters are well served in the way that matters for daily charging. The access deficit instead fell on disadvantaged-community status, which was the sharpest of the four equity axes tested, with income a weak secondary gradient. The honest reading is that the equity gap in this county is defined by environmental-justice burden, not by housing tenure. A study that stopped at the renter hypothesis would have reached the wrong conclusion. We measure public charging access here, not home charging. The claim that Level 2 access does not substitute for the overnight charging renters lack is drawn from the literature on home-charging dependence, not demonstrated by our own metric, which finds renters better served on every public axis we report.

The second finding is that proximity is a misleading measure of charging access. By straight-line distance, disadvantaged communities appeared better served, because they concentrate in dense areas where chargers cluster. The accessibility metric reversed this. Once the population competing for each charger was counted, disadvantaged communities were worse served for fast charging, with a population-weighted access ratio of 0.6845. The reversal is not a quirk of one parameter choice. It held when the catchment radius was varied from 4 to 10 miles and when crosswalked disadvantaged-community values were excluded. Because accessibility methods were designed to correct proximity for competition, this is less a surprise about the method than a quantification of how large that correction is for disadvantaged communities in this county. It matters for policy because charger counts and proximity maps, which are the common basis for infrastructure decisions, can understate the access gap in exactly the dense communities that most depend on public charging. This claim is descriptive rather than causal. The disadvantaged-community gap is not separable from spatial structure, and it rests on a thin base of 33 fast-charging ports, so it is reported as a population-weighted contrast, not as an identified effect.

The third finding is a measured network-composition disparity, with a reliability discount reported as an illustrative sensitivity on top of it. The composition fact is direct. Fast-charging supply in non-disadvantaged areas is predominantly Tesla, while disadvantaged-community supply leans more on networks such as EVgo. Under the assumed reliability priors used here, that composition difference means disadvantaged communities not only have fewer fast chargers per person but draw them from networks with lower assumed uptime, so discounting supply by reliability widens the gap, from 0.6845 to 0.6533. The discount itself rests on assumed national priors, not measured San Diego uptime, so we treat it as illustrative.

What makes the composition story defensible is not the size of the discount but how it behaves when the priors are perturbed. A uniform reliability applied to all chargers reproduced the unweighted ratio exactly, because uniform scaling cancels in a ratio, so the effect depends only on differences between networks. Compressing the assumed spread gave 0.667 and widening it gave 0.649, both still widened. The decisive test inverts the ranking: assigning the highest reliability to EVgo and the lowest to Tesla narrowed the gap to 0.711, lifting it just above the unweighted 0.6845 without reaching parity. That is the signature of a composition effect. Making the disadvantaged-community network the most reliable improves their relative position, which confirms composition drives the result, while the underlying supply disparity is deep enough that even a maximally favorable reliability assumption leaves disadvantaged communities worse served.

Together, these findings motivate a concrete siting recommendation. A greedy optimization
identified ten block-group locations where added fast charging would most raise reliability-weighted access among disadvantaged communities. The selected sites sit around San Diego Bay in
the south of the county and are concentrated in National City, where disadvantaged-community
clusters are densest and current fast-charging access is lowest. As reported in the Results, the
modeled gains accrued almost entirely to disadvantaged communities, with little spillover to
non-disadvantaged areas, so the benefit was directed where the gap is worst. Three of the ten
candidates were non-disadvantaged bayfront centroids whose modeled benefit to disadvantaged
communities depends on straight-line distance across the bay. They are an artifact of using
block-group centroids as candidate locations and Euclidean distance, not buildable
recommendations, and they are one reason the combined gain is an upper bound. This suggests that
a small, targeted set of new fast-charging locations could reduce a meaningful share of the
access gap, and that equity-aware siting differs sharply from siting that chases population or
existing demand.

## Limitations

The study has several limitations, and they bound the claims above.

Reliability is the most important. Every reliability value used is an assumed national network
average drawn from published reliability reports, not measured San Diego uptime. Real station-
level uptime data for California is scheduled to become available beginning in 2027 under state
reporting requirements, and the method is built to accept that data when it exists. Until then,
the reliability findings should be read as the consequence of plausible assumed priors,
consistent in direction but not validated against measured uptime. The disadvantaged-community
reliability mechanism also rests on a small number of fast-charging ports in disadvantaged block
groups, which makes the specific network mix sensitive to a few stations.

Distance was measured as straight-line Euclidean distance in a projected coordinate system, not
road-network or drive-time distance. In a county with canyons and uneven road coverage, this
understates real travel, especially in the rural east. Network distance is the clearest
methodological improvement for future work.

Ports were treated as linear supply, so queueing and congestion at individual stations were not modeled. The assumed reliability for non-networked and other stations, 0.75, applies to 18 percent of disadvantaged-community fast-charging ports and was not separately sensitivity-tested, so the disadvantaged-community reliability mechanism rests partly on an untested prior. Euclidean distance measured across water contaminates baseline access scores for coastal block groups generally, not only the three Coronado siting candidates excluded later.

Access was computed from block-group centroids, not population-weighted centroids or parcel-
level locations, which is standard for this method but coarsens the within-block-group
geography. The accessibility method is also known to overstate access in low-density areas where
almost no population competes for a charger, so the rural east county results were treated
separately and excluded from the siting candidates.

Demand was proxied by residential population, not by measured charging sessions or electric-
vehicle registrations, so the analysis captures where people live rather than where charging
demand is observed. The siting optimization used existing block-group centroids as candidate
locations, which identifies where added access would help most, not which specific parcels are
available or buildable. Its additive access model captures competition between new and existing
chargers but not among the newly sited chargers, so because the selected sites cluster, the
reported combined gain is a modest upper bound.

The magnitude of the fast-charging deficit is specification-dependent. It held under each perturbation taken alone but reached parity, at a ratio of 1.19, under the single combination of a 10-mile catchment and demand weighted linearly by income. Because the 6-mile catchment is the primary specification and linear income weighting is an aggressive ownership proxy, this corner is the least likely of those tested, but the result is not invariant to it.

Finally, because census block groups are spatially autocorrelated, neighboring units are not
independent observations. Effect sizes were therefore reported as the primary evidence and
p-values were treated as optimistic and not reported. A significance test that accounts for
spatial autocorrelation is a direction for future work, alongside measured reliability data, a
budget-constrained siting optimization, and network-distance accessibility.

As reported in the results, the disadvantaged-community gap is a cross-sectional association that is not separable from spatial structure, which is why the equity claim here is descriptive rather than causal.

# Conclusion

This study showed that EV charging equity in San Diego County is mischaracterized by the
measures that usually drive infrastructure decisions. The group conventionally assumed to be worst served, renters, was not, once charger type was separated, which located the real deficit on disadvantaged-community status rather than housing tenure. Charger counts and proximity made disadvantaged communities look adequately served, but a population-competition-aware accessibility measure found them worse served for fast charging by roughly 2 to 34 percent across reasonable specifications, a descriptive contrast that is not separable from spatial structure and rests on a thin fast-charging base. The supply those communities depend on also draws more on lower-reliability networks, a measured composition disparity, and discounting supply by assumed reliability widened the gap as an illustrative consequence of those priors. A small set of in-corridor sites in the south county would direct nearly all of its modeled benefit to those communities, closing an estimated 31.0 percent of the gap at the mean, a model upper bound because the chosen sites cluster and the sites are not yet checked for buildability. The central empirical findings are the relocation of the deficit from housing tenure to disadvantaged-community status and the competition-aware proximity reversal. The reliability-weighted accessibility measure is offered as a transferable but illustrative extension, resting on assumed national priors, and is built to use measured station uptime as soon as that data publishes in 2027. The framework transfers to any region with public charger locations and demographic data.

# References
