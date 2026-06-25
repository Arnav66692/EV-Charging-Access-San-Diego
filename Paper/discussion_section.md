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
