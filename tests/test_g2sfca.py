"""Hand-computed unit test for the G2SFCA two-step core (build_access_g2sfca.g2sfca).

Setup: 2 block groups (pop 100 and 200), 1 DCFC station with 1 port, catchment d0 = 6 mi.
The expected R_j (step 1) and access_i (step 2) are derived independently here from the
explicit Gaussian decay formula (not by importing the module's gaussian()), so both the
decay and the two-step orchestration are checked.

Worked example (d0=6, d1=3 mi, d2=4.5 mi), approximate values for a human to sanity-check:
  G(3.0)  ~= 0.7013657      G(4.5)  ~= 0.3769540
  demand  = 100*G(3) + 200*G(4.5) ~= 145.5272
  R       = 1 / demand            ~= 0.00687158
  access1 = R*G(3)                ~= 0.00482010
  access2 = R*G(4.5)              ~= 0.00259047
"""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Code" / "features"))

from build_access_g2sfca import g2sfca  # noqa: E402


def _gauss(d: float, d0: float) -> float:
    """Dai (2010) normalized Gaussian decay, scalar — independent of the module's impl."""
    a = math.exp(-0.5)
    return (math.exp(-0.5 * (d / d0) ** 2) - a) / (1 - a)


def test_g2sfca_two_bg_one_station_hand_computed():
    d0 = 6.0
    d1, d2 = 3.0, 4.5                 # both strictly within the 6-mile catchment
    pop = np.array([100.0, 200.0])
    supply = np.array([1.0])          # one DCFC station, 1 port
    dist = np.array([[d1], [d2]])     # (2 block groups, 1 station), miles

    g1, g2 = _gauss(d1, d0), _gauss(d2, d0)
    demand = 100.0 * g1 + 200.0 * g2          # step 1 denominator
    r = 1.0 / demand                           # step 1: R_j = supply / demand
    expected = np.array([r * g1, r * g2])      # step 2: access_i = R_j * G(d_ij)

    got = g2sfca(dist, pop, supply, d0)
    assert got.shape == (2,)
    assert abs(got[0] - expected[0]) < 1e-9
    assert abs(got[1] - expected[1]) < 1e-9


def test_g2sfca_station_beyond_catchment_contributes_zero():
    """A block group beyond d0 gets zero access and is excluded from step-1 demand."""
    d0 = 6.0
    pop = np.array([100.0, 200.0])
    supply = np.array([1.0])
    dist = np.array([[3.0], [10.0]])           # BG2 is 10 mi out, beyond the catchment

    g1 = _gauss(3.0, d0)
    demand = 100.0 * g1                          # BG2 weight is 0, not in denominator
    expected0 = (1.0 / demand) * g1
    got = g2sfca(dist, pop, supply, d0)
    assert abs(got[0] - expected0) < 1e-9
    assert got[1] == 0.0
