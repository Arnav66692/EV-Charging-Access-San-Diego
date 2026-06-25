"""Download the TIGER/Line geometry inputs the pipeline needs.

The committed regression and feature builds need two large Census geometry files
that are too big to commit (Data/raw/ is gitignored):

  1. tl_2024_06_bg.zip          — TIGER/Line 2024 California block-group polygons.
                                   Used for the point-in-polygon station clip, the
                                   G2SFCA centroids, and the queen-contiguity weights
                                   in Code/analysis/joint_ols_spatial.py. ~52 MB
                                   zipped (the unzipped .shp is ~126 MB).
  2. tab20_tract20_tract10_st06.txt — 2020-to-2010 census-tract relationship file
                                   for California, used by build_access_features.py
                                   to crosswalk CalEnviroScreen 4.0 (2010 tracts)
                                   onto 2020 tracts. ~1.9 MB.

Both come from the public Census static file server (no API key required). This
script makes the geometry fetchable so a cloner of the public repo can regenerate
the processed data and rerun the spatial-error model. It writes only into
Data/raw/ and skips files that already exist unless --force is given.

Run:
    .venv/bin/python Code/pull_tiger.py            # download if missing
    .venv/bin/python Code/pull_tiger.py --force    # re-download even if present
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "Data" / "raw"

# (url, destination filename). Both are public Census static files, no key needed.
DOWNLOADS = [
    (
        "https://www2.census.gov/geo/tiger/TIGER2024/BG/tl_2024_06_bg.zip",
        "tl_2024_06_bg.zip",
    ),
    (
        "https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/"
        "tab20_tract20_tract10_st06.txt",
        "tab20_tract20_tract10_st06.txt",
    ),
]

CHUNK = 1 << 20  # 1 MiB


def download(url: str, dest: Path, force: bool) -> None:
    if dest.exists() and not force:
        print(f"  skip (exists): {dest.name}  ({dest.stat().st_size / 1e6:.1f} MB)")
        return
    print(f"  GET {url}")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        written = 0
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=CHUNK):
                fh.write(chunk)
                written += len(chunk)
        tmp.replace(dest)
    print(f"  wrote {dest.name}  ({written / 1e6:.1f} MB)")


def main() -> int:
    force = "--force" in sys.argv[1:]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading TIGER geometry into {RAW_DIR}")
    for url, name in DOWNLOADS:
        download(url, RAW_DIR / name, force)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
