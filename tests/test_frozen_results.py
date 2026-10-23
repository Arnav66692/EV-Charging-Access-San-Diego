"""Published headline must agree with the committed, key-free input tables."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def weighted_median(values, weights):
    order = np.argsort(values)
    values, weights = np.asarray(values)[order], np.asarray(weights)[order]
    return values[np.searchsorted(np.cumsum(weights), weights.sum() / 2)]


def test_published_dcfc_ratio_matches_frozen_tables():
    access = pd.read_csv(ROOT / 'Data/processed/blockgroup_access.csv', dtype={'geoid': str})
    sfca = pd.read_csv(ROOT / 'Data/processed/blockgroup_g2sfca.csv', dtype={'geoid': str})
    data = access.merge(sfca, on='geoid', validate='one_to_one')
    assert len(data) == 2058
    data = data.dropna(subset=['is_dac', 'population', 'access_dcfc'])
    dac = data[data.is_dac == True]
    other = data[data.is_dac == False]
    ratio = weighted_median(dac.access_dcfc, dac.population) / weighted_median(other.access_dcfc, other.population)
    assert ratio == pytest.approx(0.6845231553, abs=1e-9)
