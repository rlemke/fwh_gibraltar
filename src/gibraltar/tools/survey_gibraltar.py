"""Survey a place's tunnels from a local OSM extract, and draw the result.

Thin CLI over ``_gibraltar_tools``; the same library backs the FFL facets, so
the tool and the workflow produce identical numbers.

    python survey_gibraltar.py --place gibraltar -o out/
    python survey_gibraltar.py --place jersey -o out/
    python survey_gibraltar.py --json          # statistics on stdout, nothing else

No network: the extract comes from the local planet split.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gibraltar_tools import places  # noqa: E402
from _gibraltar_tools.render import render, write_stats  # noqa: E402
from _gibraltar_tools.survey import SurveyError, survey  # noqa: E402

REL = {
    "gibraltar": "europe/gibraltar-latest.osm.pbf",
    "jersey": "europe/jersey-latest.osm.pbf",
}


def _resolve(pbf: str | None, place_key: str) -> str:
    if pbf:
        return pbf
    rel = REL[place_key]
    bare = rel.rsplit("/", 1)[-1]
    for root in (r for r in os.environ.get("FW_OSM_LOCAL_EXTRACTS", "").split(":") if r.strip()):
        for cand in (Path(root) / rel, Path(root) / bare):
            if cand.exists():
                return str(cand)
    raise SystemExit(f"no {place_key} extract: pass --pbf or set FW_OSM_LOCAL_EXTRACTS")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="survey_gibraltar", description=__doc__)
    p.add_argument("--place", default="gibraltar", choices=sorted(places.PLACES),
                   help="which place's published ground truth to compare against")
    p.add_argument("--pbf", help="extract to read (default: from FW_OSM_LOCAL_EXTRACTS)")
    p.add_argument("-o", "--out-dir", default="gibraltar-out")
    p.add_argument("--json", action="store_true", help="statistics to stdout")
    p.add_argument("--no-map", action="store_true", help="statistics only")
    a = p.parse_args(argv)

    place = places.get(a.place)
    try:
        result = survey(_resolve(a.pbf, place.key), place=place)
    except SurveyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    stats = result.as_dict()

    if a.json:
        print(json.dumps(stats, indent=2))
    elif place.has_denominator:
        print(f"  tunnels mapped   {stats['tunnel_km']:>7.2f} km   "
              f"({stats['mapped_pct']}% of {stats['published_tunnel_km']} km published)",
              file=sys.stderr)
        print(f"  not in OSM       {stats['unmapped_km']:>7.2f} km", file=sys.stderr)
        print(f"  public road      {stats['public_road_km']:>7.2f} km   "
              f"({stats['osm_vs_official_roads']}x the official "
              f"{stats['official_road_km']} km)", file=sys.stderr)
    else:
        # No published total: report what was measured and say why there is no
        # percentage, rather than printing one against a made-up denominator.
        print(f"  tunnels mapped   {stats['tunnel_km']:>7.2f} km   "
              f"({stats['tunnel_km_distinct']:.2f} km of distinct bore)", file=sys.stderr)
        print(f"  published total    unknown     — records destroyed before the "
              f"1945 surrender; no percentage can be given", file=sys.stderr)
        print(f"  road             {stats['road_km']:>7.2f} km", file=sys.stderr)

    write_stats(stats, str(Path(a.out_dir) / "statistics.json"))
    if not a.no_map:
        stem = "hollow-mountain" if place.key == "gibraltar" else place.key
        path = render(stats, result.features, str(Path(a.out_dir) / f"{stem}.html"))
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
