#!/usr/bin/env python3
"""Generate config/colors.tsv covering every categorical value in the metadata.

The hand-maintained predecessor keyed on "Country" with a capital C while the
metadata column is "country", so augur matched nothing and Auspice fell back to
auto-assigned colors for every panel. Generating the file guarantees the key
casing is right and that no value is ever missing an entry.

Small vocabularies get hand-picked palettes so the map and legend stay readable.
Mid-sized ones get an evenly-spaced hue ramp ordered by isolate count.

The two large vocabularies (city: 277 values, genotype: 212) cannot use an even
ramp at all: spreading 277 values over one hue rotation puts neighbours ~1.3
degrees apart, which is a CIELAB deltaE around 0.7 -- well under the ~2.3 needed
to tell two colours apart. Every city came out the same pale teal. They use
distinct_ramp() instead, which walks the hue circle by the golden angle and
cycles lightness and saturation, lifting the gap between neighbours to a deltaE
around 100. With this many categories no scheme can make all of them mutually
distinguishable; the goal is that adjacent legend rows and neighbouring map
demes never look alike.

All ramps are ordered by isolate count and are stable across runs.

Output format is augur's:  <column>\t<value>\t#RRGGBB

Usage (from the repository root):
    python3 toxo-analysis/scripts/build_colors.py
"""
import colorsys
import csv
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
METADATA = REPO / "toxo-analysis" / "data" / "toxo_meta3.tsv"
OUTPUT = REPO / "toxo-analysis" / "config" / "colors.tsv"

# Every categorical coloring declared in config/auspice_config.json.
COLUMNS = ["country", "region", "city", "host", "genotype", "GIS_Position"]

# Continents keep intuitive, well-separated hues.
REGION_COLORS = {
    "Africa": "#CEB541",
    "Arctic": "#8ACDEA",
    "Asia": "#447CCD",
    "Caribbean": "#63AC9A",
    "Central America": "#B4BD4C",
    "Europe": "#E39B39",
    "Hawaii": "#7EB876",
    "North America": "#DE752F",
    "South America": "#DB2823",
}

# Provenance of the coordinates: exact collection site vs. a regional centroid.
GIS_COLORS = {
    "GIS-exact": "#3F8F5B",
    "GIS-proxy": "#BDBDBD",
}


def ramp(values, saturation, lightness, hue_offset=0.0):
    """Assign evenly-spaced hues to values, in the order given."""
    out = {}
    n = max(len(values), 1)
    for i, value in enumerate(values):
        hue = (hue_offset + i / n) % 1.0
        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
        out[value] = "#{:02X}{:02X}{:02X}".format(
            round(r * 255), round(g * 255), round(b * 255)
        )
    return out


# Walking the hue circle by the golden angle keeps successive values far apart
# no matter how many there are, instead of inching around it. Cycling lightness
# and saturation on top separates values whose hues do happen to land close.
GOLDEN_ANGLE = 0.6180339887498949
LIGHTNESS_TIERS = (0.42, 0.58, 0.72)
SATURATION_TIERS = (0.75, 0.50)


def distinct_ramp(values, hue_offset=0.0):
    """Assign maximally-separated colours to values, in the order given."""
    out = {}
    for i, value in enumerate(values):
        hue = (hue_offset + i * GOLDEN_ANGLE) % 1.0
        lightness = LIGHTNESS_TIERS[i % len(LIGHTNESS_TIERS)]
        saturation = SATURATION_TIERS[(i // len(LIGHTNESS_TIERS)) % len(SATURATION_TIERS)]
        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
        out[value] = "#{:02X}{:02X}{:02X}".format(
            round(r * 255), round(g * 255), round(b * 255)
        )
    return out


def by_frequency(rows, column):
    """Distinct non-blank values, most common first, ties broken alphabetically."""
    counts = Counter((row.get(column) or "").strip() for row in rows)
    counts.pop("", None)
    return [v for v, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def main():
    with METADATA.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    palettes = {}

    # Curated palettes, with a generated fallback so a new value can never
    # slip through uncolored.
    for column, curated in (("region", REGION_COLORS), ("GIS_Position", GIS_COLORS)):
        values = by_frequency(rows, column)
        missing = [v for v in values if v not in curated]
        palettes[column] = {**ramp(missing, 0.55, 0.55), **curated}
        palettes[column] = {v: palettes[column][v] for v in values}

    # Even ramps for the vocabularies small enough to take one.
    palettes["country"] = ramp(by_frequency(rows, "country"), 0.62, 0.48)
    palettes["host"] = ramp(by_frequency(rows, "host"), 0.45, 0.55, hue_offset=0.33)

    # The two crowded ones. The hue offsets are kept from the even ramps so the
    # genotype and city palettes still look unlike each other.
    palettes["genotype"] = distinct_ramp(by_frequency(rows, "genotype"), hue_offset=0.10)
    palettes["city"] = distinct_ramp(by_frequency(rows, "city"), hue_offset=0.5)

    lines = []
    for column in COLUMNS:
        palette = palettes[column]
        for value in by_frequency(rows, column):
            lines.append(f"{column}\t{value}\t{palette[value]}")
        print(f"{column}: {len(palette)} values", file=sys.stderr)

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} rows to {OUTPUT.relative_to(REPO)}", file=sys.stderr)


if __name__ == "__main__":
    main()
