#!/usr/bin/env python3
"""Generate config/colors.tsv covering every categorical value in the metadata.

The hand-maintained predecessor keyed on "Country" with a capital C while the
metadata column is "country", so augur matched nothing and Auspice fell back to
auto-assigned colors for every panel. Generating the file guarantees the key
casing is right and that no value is ever missing an entry.

Small vocabularies get hand-picked palettes so the map and legend stay readable.
Large ones (genotype: 212 values, city: 282) get a deterministic ramp ordered by
isolate count, which at least makes the common categories far apart in hue and
keeps the output stable across runs.

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

    # Generated ramps, tuned so the three large vocabularies stay
    # distinguishable from one another at a glance.
    palettes["country"] = ramp(by_frequency(rows, "country"), 0.62, 0.48)
    palettes["host"] = ramp(by_frequency(rows, "host"), 0.45, 0.55, hue_offset=0.33)
    palettes["genotype"] = ramp(by_frequency(rows, "genotype"), 0.70, 0.50, hue_offset=0.10)
    palettes["city"] = ramp(by_frequency(rows, "city"), 0.35, 0.62, hue_offset=0.5)

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
