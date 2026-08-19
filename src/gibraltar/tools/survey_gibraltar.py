"""Survey Gibraltar from a local OSM extract, and draw the result.

Thin CLI over ``_gibraltar_tools``; the same library backs the FFL facets, so
the tool and the workflow produce identical numbers.

    python survey_gibraltar.py --pbf /path/europe/gibraltar-latest.osm.pbf -o out/
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

from _gibraltar_tools.render import render, write_stats  # noqa: E402
from _gibraltar_tools.survey import SurveyError, survey  # noqa: E402

REL = "europe/gibraltar-latest.osm.pbf"


def _resolve(pbf: str | None) -> str:
    if pbf:
        return pbf
    for root in (r for r in os.environ.get("FW_OSM_LOCAL_EXTRACTS", "").split(":") if r.strip()):
        for cand in (Path(root) / REL, Path(root) / "gibraltar-latest.osm.pbf"):
            if cand.exists():
                return str(cand)
    raise SystemExit("no extract: pass --pbf or set FW_OSM_LOCAL_EXTRACTS")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="survey_gibraltar", description=__doc__)
    p.add_argument("--pbf", help="Gibraltar extract (default: from FW_OSM_LOCAL_EXTRACTS)")
    p.add_argument("-o", "--out-dir", default="gibraltar-out")
    p.add_argument("--json", action="store_true", help="statistics to stdout")
    p.add_argument("--no-map", action="store_true", help="statistics only")
    a = p.parse_args(argv)

    try:
        result = survey(_resolve(a.pbf))
    except SurveyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    stats = result.as_dict()

    if a.json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"  tunnels mapped   {stats['tunnel_km']:>7.2f} km   "
              f"({stats['mapped_pct']}% of {stats['published_tunnel_km']} km published)",
              file=sys.stderr)
        print(f"  not in OSM       {stats['unmapped_km']:>7.2f} km", file=sys.stderr)
        print(f"  public road      {stats['public_road_km']:>7.2f} km   "
              f"({stats['osm_vs_official_roads']}x the official "
              f"{stats['official_road_km']} km)", file=sys.stderr)

    write_stats(stats, str(Path(a.out_dir) / "statistics.json"))
    if not a.no_map:
        path = render(stats, result.features, str(Path(a.out_dir) / "hollow-mountain.html"))
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
