#!/usr/bin/env python3
"""Generate config/lat_longs.tsv from the metadata's own coordinates.

Every isolate in toxo_meta3.tsv carries a Latitude/Longitude, so the location
of each country, region, and city is just the mean of its isolates' recorded
positions. Deriving the file this way means the map can never fall out of sync
with the data: any location present in the metadata is guaranteed an entry.

That matters here because augur silently falls back to its built-in country
list for anything it cannot resolve. Five locations in this dataset are not in
that list -- Burkina Faso, Congo, Plateau, St. Kitts, and Svalbard -- and their
46 isolates were simply absent from the map before this file existed.

Output format is augur's:  <column>\t<value>\t<latitude>\t<longitude>

Usage (from the repository root):
    python3 toxo-analysis/scripts/build_lat_longs.py
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
METADATA = REPO / "toxo-analysis" / "data" / "toxo_meta3.tsv"
OUTPUT = REPO / "toxo-analysis" / "config" / "lat_longs.tsv"

# Metadata columns to emit coordinates for. These are exactly the
# geo_resolutions declared in config/auspice_config.json.
COLUMNS = ["country", "region", "city"]


def main():
    with METADATA.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    # column -> value -> [(lat, long), ...]
    coords = {col: defaultdict(list) for col in COLUMNS}

    for row in rows:
        try:
            lat = float(row["Latitude"].strip())
            lon = float(row["Longitude"].strip())
        except (AttributeError, KeyError, ValueError):
            continue
        for col in COLUMNS:
            value = (row.get(col) or "").strip()
            if value:
                coords[col][value].append((lat, lon))

    lines = []
    for col in COLUMNS:
        for value in sorted(coords[col]):
            points = coords[col][value]
            lat = sum(p[0] for p in points) / len(points)
            lon = sum(p[1] for p in points) / len(points)
            lines.append(f"{col}\t{value}\t{lat:.6f}\t{lon:.6f}")
        print(f"{col}: {len(coords[col])} values", file=sys.stderr)

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} rows to {OUTPUT.relative_to(REPO)}", file=sys.stderr)


if __name__ == "__main__":
    main()
