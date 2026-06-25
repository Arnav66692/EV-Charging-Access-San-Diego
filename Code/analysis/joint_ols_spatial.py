"""Joint OLS and spatial-error regression of fast-charging access on equity axes.

Reproduces the regression results the paper reports in Results 3.2 and the
spatial-error robustness in the same section. These numbers were originally
produced by throwaway /tmp scripts and never committed, which contradicted the
Methods 2.7 claim that the full pipeline is committed. This script closes that
gap and asserts the headline numbers reproduce from the committed code.

Model: access_dcfc regressed on four predictors:
    is_dac, median_hhi, renter_percent, multifamily_housing_percent
fit on complete cases (rows with no missing predictor). The outcome
access_dcfc has no missing values. The continuous predictors (median_hhi,
renter_percent, multifamily_housing_percent) and the outcome are z-standardized,
so those coefficients are standardized betas. Disadvantaged-community status
(is_dac) is entered as a raw 0/1 indicator -- the conventional treatment for a
binary variable, and the specification the paper reports. Standardizing a 0/1
dummy would only rescale its coefficient and standard error by sd(is_dac); the
t-statistic, p-value, partial R-squared, model R-squared, and the other
coefficients are identical either way.

The access surface is operational-only (status_code == "E"), the committed default
in build_access_g2sfca, so these are the E-only regression values the paper reports.

Paper targets (Results 3.2, E-only):
    nobs                       == 2048
    is_dac coefficient         == -0.467  (SE 0.09)
    is_dac partial R-squared   ==  0.0130
    median_hhi coefficient     == +0.087
    model R-squared            ==  0.035
    spatial-error model        :  is_dac attenuates and loses significance

Data note: the inputs live under Data/processed/ and Data/raw/, which are
gitignored. This script is committed, but its inputs are not. Run it after the
processed CSVs and the TIGER block-group shapefile have been generated locally.

Run:
    .venv/bin/python Code/analysis/joint_ols_spatial.py

Deterministic. Writes nothing. No CSV, no commit.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import geopandas as gpd  # noqa: E402
import statsmodels.api as sm  # noqa: E402
import spreg  # noqa: E402
from libpysal.weights import Queen  # noqa: E402

# --------------------------------------------------------------------------- #
# Paths and constants
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "Data" / "processed"
RAW = ROOT / "Data" / "raw"
G2_CSV = PROC / "blockgroup_g2sfca.csv"
ACCESS_CSV = PROC / "blockgroup_access.csv"
BG_ZIP = RAW / "tl_2024_06_bg.zip"

SD_STATE = "06"
SD_CTY = "073"

OUTCOME = "access_dcfc"
PREDICTORS = ["is_dac", "median_hhi", "renter_percent", "multifamily_housing_percent"]

EXPECTED_NOBS = 2048

# Paper-reported targets and assertion tolerances (E-only operational surface).
TARGETS = {
    "is_dac_coef": (-0.467, 0.01),
    "is_dac_se": (0.09, 0.01),
    "is_dac_partial_r2": (0.0130, 0.002),
    "median_hhi_coef": (0.087, 0.01),
    "model_r2": (0.035, 0.002),
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def zscore(s: pd.Series) -> pd.Series:
    """Standardize to mean 0, unit variance. ddof=0 applied consistently to all
    columns, so the standardized beta is invariant to the ddof choice."""
    x = pd.to_numeric(s, errors="coerce").astype(float)
    return (x - x.mean()) / x.std(ddof=0)


def coerce_is_dac(s: pd.Series) -> pd.Series:
    """Map the boolean-ish is_dac column to 0.0/1.0. Handles both real Python
    booleans and the string spellings 'True'/'False'. NaN stays NaN so that
    complete-case dropping has already removed it upstream."""
    return s.map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})


def load_complete_case() -> pd.DataFrame:
    """Join the two committed-pipeline CSVs on the 12-char string GEOID and
    return the complete-case sample (no missing predictor)."""
    g2 = pd.read_csv(G2_CSV, dtype={"geoid": str})
    acc = pd.read_csv(ACCESS_CSV, dtype={"geoid": str})
    df = acc.merge(g2, on="geoid", how="inner")
    assert df[OUTCOME].isna().sum() == 0, "outcome access_dcfc has unexpected NA"
    cc = df.dropna(subset=PREDICTORS).copy()
    cc["is_dac"] = coerce_is_dac(cc["is_dac"])
    return cc


def partial_r2(y: pd.Series, Z: pd.DataFrame, target: str) -> float:
    """Partial R-squared of `target`: the proportional reduction in residual
    sum of squares from adding `target` to a model that already contains the
    other predictors. Algebraically equal to t^2 / (t^2 + df_resid)."""
    full = sm.OLS(y, sm.add_constant(Z[PREDICTORS])).fit()
    others = [p for p in PREDICTORS if p != target]
    reduced = sm.OLS(y, sm.add_constant(Z[others])).fit()
    return float((reduced.ssr - full.ssr) / reduced.ssr)


def build_queen_weights(cc: pd.DataFrame):
    """Queen contiguity weights on the block-group geometries, aligned to the
    exact complete-case sample and row order, row-standardized."""
    bg = gpd.read_file(f"zip://{BG_ZIP}")
    bg = bg[(bg["STATEFP"] == SD_STATE) & (bg["COUNTYFP"] == SD_CTY)].copy()
    bg["GEOID"] = bg["GEOID"].astype(str)
    bg = bg.set_index("GEOID")
    bg = bg.loc[cc["geoid"].tolist()]  # reindex to cc order; KeyError if any missing
    w = Queen.from_dataframe(bg, use_index=True)
    w.transform = "r"
    return w


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    print("=" * 78)
    print("JOINT OLS + SPATIAL-ERROR — fast-charging access on equity axes")
    print("=" * 78)

    cc = load_complete_case()
    nobs = len(cc)
    print(f"\nComplete-case block groups: {nobs}")

    # Standardize the outcome and the continuous predictors. is_dac stays a raw
    # 0/1 indicator (Spec B), the specification the paper reports. Column order
    # follows PREDICTORS so the spatial-error name alignment below holds.
    yz = zscore(cc[OUTCOME])
    Z = pd.DataFrame(index=cc.index)
    Z["is_dac"] = cc["is_dac"].astype(float)
    for p in PREDICTORS[1:]:
        Z[p] = zscore(cc[p])

    # ----- OLS ----------------------------------------------------------- #
    ols = sm.OLS(yz, sm.add_constant(Z[PREDICTORS])).fit()
    print("\n" + "-" * 78)
    print("OLS (continuous predictors and outcome standardized; is_dac as 0/1 indicator)")
    print("-" * 78)
    print(f"  {'predictor':32s} {'coef':>9s} {'std err':>9s} {'p-value':>9s} {'partial R2':>11s}")
    print(f"  {'const':32s} {ols.params['const']:9.4f} {ols.bse['const']:9.4f} "
          f"{ols.pvalues['const']:9.3g} {'-':>11s}")
    pr2 = {}
    for p in PREDICTORS:
        pr2[p] = partial_r2(yz, Z, p)
        print(f"  {p:32s} {ols.params[p]:9.4f} {ols.bse[p]:9.4f} "
              f"{ols.pvalues[p]:9.3g} {pr2[p]:11.4f}")
    print(f"\n  model R-squared : {ols.rsquared:.4f}")
    print(f"  nobs            : {int(ols.nobs)}   df_resid : {int(ols.df_resid)}")

    # ----- Spatial error model ------------------------------------------ #
    print("\n" + "-" * 78)
    print("SPATIAL ERROR MODEL (spreg.ML_Error, queen contiguity, row-standardized)")
    print("-" * 78)
    w = build_queen_weights(cc)
    print(f"  weights: n={w.n}  islands={len(w.islands)}  "
          f"avg neighbors={w.mean_neighbors:.2f}")
    err = spreg.ML_Error(
        yz.to_numpy().reshape(-1, 1),
        Z[PREDICTORS].to_numpy(),
        w=w,
        name_y="z_access_dcfc",
        name_x=PREDICTORS,
    )
    # betas: [const, is_dac, median_hhi, renter, multifamily, lambda]
    # z_stat: [(z, p)] aligned to [const, is_dac, median_hhi, renter, multifamily]
    names = ["const", *PREDICTORS]
    print(f"  {'param':32s} {'coef':>9s} {'z':>9s} {'p-value':>9s}")
    for i, nm in enumerate(names):
        z_val, p_val = err.z_stat[i]
        print(f"  {nm:32s} {float(err.betas[i][0]):9.4f} {z_val:9.3f} {p_val:9.3g}")
    print(f"  {'lambda (spatial)':32s} {float(err.betas[-1][0]):9.4f}")
    sp_is_dac_coef = float(err.betas[1][0])
    sp_is_dac_p = float(err.z_stat[1][1])
    print(f"\n  >>> spatial-error is_dac coef = {sp_is_dac_coef:.4f}   "
          f"p = {sp_is_dac_p:.4f} <<<")
    ols_is_dac_p = float(ols.pvalues["is_dac"])
    print(f"      (OLS is_dac p = {ols_is_dac_p:.3g} -> spatial-error p = {sp_is_dac_p:.3g}: "
          f"{'attenuated, loses significance' if sp_is_dac_p > 0.05 else 'still significant'})")

    # ----- Assertions ---------------------------------------------------- #
    print("\n" + "=" * 78)
    print("ASSERTIONS vs paper (Results 3.2)")
    print("=" * 78)
    checks = [
        ("nobs == 2048", nobs == EXPECTED_NOBS, nobs, EXPECTED_NOBS, None),
        ("is_dac coef -0.467 +/- 0.01", *_within(ols.params["is_dac"], *TARGETS["is_dac_coef"])),
        ("is_dac SE 0.09 +/- 0.01", *_within(ols.bse["is_dac"], *TARGETS["is_dac_se"])),
        ("is_dac partial R2 0.0130 +/- 0.002",
         *_within(pr2["is_dac"], *TARGETS["is_dac_partial_r2"])),
        ("median_hhi coef +0.087 +/- 0.01",
         *_within(ols.params["median_hhi"], *TARGETS["median_hhi_coef"])),
        ("model R2 0.035 +/- 0.002", *_within(ols.rsquared, *TARGETS["model_r2"])),
        ("spatial-error is_dac loses significance (p > 0.05)",
         sp_is_dac_p > 0.05, sp_is_dac_p, "> 0.05", None),
    ]
    all_pass = True
    for label, ok, got, want, _ in checks:
        all_pass &= ok
        got_s = f"{got:.4f}" if isinstance(got, float) else str(got)
        want_s = f"{want}" if not isinstance(want, float) else f"{want:.4f}"
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:48s} got={got_s:>10s} target={want_s}")
    print("\n" + ("ALL ASSERTIONS PASSED" if all_pass else "ONE OR MORE ASSERTIONS FAILED"))
    return 0 if all_pass else 1


def _within(value: float, target: float, tol: float):
    """Return (ok, value, target, tol) for a tolerance check."""
    return (abs(float(value) - target) <= tol, float(value), target, tol)


if __name__ == "__main__":
    raise SystemExit(main())
