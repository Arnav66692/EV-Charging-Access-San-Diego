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
