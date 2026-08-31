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

Two mechanisms keep the averaging honest, because a single bad row can drag a
whole country off the map without any warning:

  Anchors.  config/place_anchors.tsv gives authoritative coordinates for the
  handful of localities whose recorded coordinates contradict their label. An
  anchored isolate contributes the anchor position instead of its own, so
  fixing a city fixes its country and region rollups too. The metadata's
  Latitude/Longitude columns are never modified -- augur does not read them
  anyway, it positions demes purely from this file, keyed on the label.

  Validation.  Three checks abort the run. Out-of-range centroids; unanchored
  cities whose isolates are scattered across more than MAX_CITY_SPREAD degrees;
  and unanchored cities that would land more than MAX_SIGN_GAIN degrees closer
  to their own country if a coordinate sign were flipped or the pair swapped,
  which is what a dropped minus sign looks like. The spread check needs at least
  two isolates to have anything to compare, so the sign check is what catches a
  single-isolate city -- both coordinates found this way were marked GIS-exact.
  Countries and regions are exempt from the spread check: Canada legitimately
  spans 223 degrees and Portugal 20 (the mainland plus the Azores).

Output format is augur's:  <column>\t<value>\t<latitude>\t<longitude>

Usage (from the repository root):
    python3 toxo-analysis/scripts/build_lat_longs.py
"""
import csv
import statistics
import sys
from collections import Counter, defaultdict
from math import dist
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
METADATA = REPO / "toxo-analysis" / "data" / "toxo_meta3.tsv"
ANCHORS = REPO / "toxo-analysis" / "config" / "place_anchors.tsv"
OUTPUT = REPO / "toxo-analysis" / "config" / "lat_longs.tsv"

# Metadata columns to emit coordinates for. These are exactly the
# geo_resolutions declared in config/auspice_config.json.
COLUMNS = ["country", "region", "city"]

# A city is meant to be a point. Isolates spread wider than this around their
# own median mean the label and the coordinates disagree about where they are.
MAX_CITY_SPREAD = 2.0

# A correct coordinate is not dramatically improved by flipping one of its
# signs. Anything that moves this many degrees closer to its own country under
# a flip or a swap is a data-entry error, not a place.
MAX_SIGN_GAIN = 10.0


def load_anchors():
    """column -> value -> (lat, long), from config/place_anchors.tsv."""
    anchors = defaultdict(dict)
    with ANCHORS.open(encoding="utf-8") as fh:
        rows = csv.DictReader(
            (line for line in fh if not line.startswith("#")), delimiter="\t"
        )
        for row in rows:
            anchors[row["column"].strip()][row["value"].strip()] = (
                float(row["latitude"]),
                float(row["longitude"]),
            )
    return anchors


def main():
    anchors = load_anchors()

    with METADATA.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    # column -> value -> [(lat, long, strain), ...]
    coords = {col: defaultdict(list) for col in COLUMNS}
    anchored = {col: set() for col in COLUMNS}

    for row in rows:
        try:
            recorded = (float(row["Latitude"].strip()), float(row["Longitude"].strip()))
        except (AttributeError, KeyError, ValueError):
            continue

        # An anchored city overrides the recorded position everywhere, so the
        # correction propagates into the country and region centroids too.
        city = (row.get("city") or "").strip()
        anchor = anchors["city"].get(city)
        lat, lon = anchor if anchor else recorded

        for col in COLUMNS:
            value = (row.get(col) or "").strip()
            if not value:
                continue
            direct = anchors[col].get(value)
            if direct:
                coords[col][value].append((*direct, row.get("strain", "")))
                anchored[col].add(value)
            else:
                coords[col][value].append((lat, lon, row.get("strain", "")))
                if anchor:
                    anchored[col].add(value)

    def centroid(points):
        return (sum(p[0] for p in points) / len(points),
                sum(p[1] for p in points) / len(points))

    # Country centroids first, so each city can be sanity-checked against the
    # country it belongs to.
    country_centre = {v: centroid(p) for v, p in coords["country"].items()}
    city_country = defaultdict(Counter)
    for row in rows:
        city = (row.get("city") or "").strip()
        country = (row.get("country") or "").strip()
        if city and country:
            city_country[city][country] += 1

    problems = []
    lines = []
    for col in COLUMNS:
        for value in sorted(coords[col]):
            points = coords[col][value]
            lat = sum(p[0] for p in points) / len(points)
            lon = sum(p[1] for p in points) / len(points)

            if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                problems.append(
                    f"{col} {value!r}: centroid ({lat:.6f}, {lon:.6f}) is out of range. "
                    f"Strains: {', '.join(p[2] for p in points[:8])}"
                )

            if col == "city" and len(points) > 1 and value not in anchored[col]:
                mlat = statistics.median(p[0] for p in points)
                mlon = statistics.median(p[1] for p in points)
                outliers = [p for p in points if dist((p[0], p[1]), (mlat, mlon)) > MAX_CITY_SPREAD]
                if outliers:
                    problems.append(
                        f"city {value!r}: {len(outliers)} of {len(points)} isolates sit more "
                        f"than {MAX_CITY_SPREAD} degrees from the median ({mlat:.4f}, {mlon:.4f}). "
                        f"Add an entry to {ANCHORS.relative_to(REPO)}. "
                        f"Strains: {', '.join(p[2] for p in outliers[:8])}"
                    )

            if col == "city" and value not in anchored[col] and city_country[value]:
                country = city_country[value].most_common(1)[0][0]
                centre = country_centre.get(country)
                if centre:
                    here = dist((lat, lon), centre)
                    for label, cand in (
                        ("its longitude sign flipped", (lat, -lon)),
                        ("its latitude sign flipped", (-lat, lon)),
                        ("its coordinates swapped", (lon, lat)),
                    ):
                        if here - dist(cand, centre) > MAX_SIGN_GAIN:
                            problems.append(
                                f"city {value!r}: sits {here:.1f} degrees from {country}, but only "
                                f"{dist(cand, centre):.1f} with {label} -- a dropped sign, most likely. "
                                f"Add an entry to {ANCHORS.relative_to(REPO)}. "
                                f"Strains: {', '.join(p[2] for p in points[:8])}"
                            )
                            break

            lines.append(f"{col}\t{value}\t{lat:.6f}\t{lon:.6f}")
        print(f"{col}: {len(coords[col])} values", file=sys.stderr)

    if problems:
        print("\nlat_longs validation failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        raise SystemExit(1)

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    total = sum(len(anchored[col]) for col in COLUMNS)
    print(f"wrote {len(lines)} rows to {OUTPUT.relative_to(REPO)} "
          f"({total} anchored)", file=sys.stderr)


if __name__ == "__main__":
    main()
