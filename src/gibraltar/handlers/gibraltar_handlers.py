# SPDX-License-Identifier: Apache-2.0
"""Handlers for the Hollow Mountain survey.

Thin wrappers over ``tools/_gibraltar_tools`` so the CLI and the FFL share one
implementation. The work is a couple of osmium passes over a 1 MB extract, so it
is fast, offline, and needs no per-handler timeout heroics — but the source PBF
is resolved from the local planet split rather than downloaded, which is the
point: the survey never depends on a service that could rate-limit it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from facetwork.runtime.errors import PermanentError

from ..tools._gibraltar_tools.render import render, write_stats
from ..tools._gibraltar_tools.survey import SurveyError, survey

NAMESPACE = "gibraltar"

#: Where a locally hosted extract lives, colon-separated (same convention as
#: FW_OSM_LOCAL_EXTRACTS elsewhere in this fleet).
LOCAL_EXTRACTS = os.environ.get("FW_OSM_LOCAL_EXTRACTS", "")
REL = "europe/gibraltar-latest.osm.pbf"


def _log(params: dict[str, Any]):
    sl = params.get("_step_log")
    return (lambda m, level="info": sl(m, level=level)) if sl else (lambda m, level="info": None)


def _resolve(pbf: str) -> str:
    """The Gibraltar extract: an explicit path, else the local planet split."""
    if pbf:
        if not Path(pbf).exists():
            raise PermanentError(f"pbf does not exist: {pbf}")
        return pbf
    for root in (r for r in LOCAL_EXTRACTS.split(":") if r.strip()):
        for cand in (Path(root) / REL, Path(root) / "gibraltar-latest.osm.pbf"):
            if cand.exists():
                return str(cand)
    raise PermanentError(
        "no Gibraltar extract. Pass `pbf`, or set FW_OSM_LOCAL_EXTRACTS to a tree "
        f"holding {REL}. It is ~1 MB — this survey never needs the network."
    )


def handle_survey(params: dict[str, Any]) -> dict[str, Any]:
    say = _log(params)
    pbf = _resolve((params.get("pbf") or "").strip())
    say(f"surveying {pbf}")
    try:
        result = survey(pbf, osmium_bin=os.environ.get("FW_OSMIUM_BIN", "osmium"))
    except SurveyError as exc:
        raise PermanentError(str(exc)) from exc
    stats = result.as_dict()
    out_dir = Path(params.get("out_dir") or "gibraltar-out")
    stats_path = write_stats(stats, str(out_dir / "statistics.json"))
    say(f"{stats['tunnel_km']} km of tunnel mapped — {stats['mapped_pct']}% of the "
        f"published {stats['published_tunnel_km']} km")
    return {
        "stats_path": stats_path,
        "tunnel_km": stats["tunnel_km"],
        "mapped_pct": stats["mapped_pct"],
        "unmapped_km": stats["unmapped_km"],
        "public_road_km": stats["public_road_km"],
        "osm_vs_official_roads": stats["osm_vs_official_roads"],
        "feature_count": len(result.features),
        "stats": stats,
        "features": result.features,
    }


def handle_render(params: dict[str, Any]) -> dict[str, Any]:
    say = _log(params)
    stats = params.get("stats")
    features = params.get("features")
    if not stats or not features:
        raise PermanentError("stats and features are required — run Survey first")
    out = Path(params.get("out_dir") or "gibraltar-out") / "hollow-mountain.html"
    path = render(stats, features, str(out), title=params.get("title") or "The Hollow Mountain")
    say(f"rendered {path} ({len(features)} features, self-contained)")
    return {"map_path": path, "feature_count": len(features)}


_DISPATCH = {
    f"{NAMESPACE}.Survey": handle_survey,
    f"{NAMESPACE}.RenderMap": handle_render,
}


def handle(payload: dict) -> dict:
    facet = payload["_facet_name"]
    fn = _DISPATCH.get(facet)
    if fn is None:
        raise ValueError(f"Unknown facet: {facet}")
    return fn(payload)


def register_handlers(runner) -> None:
    for facet_name in _DISPATCH:
        runner.register_handler(
            facet_name=facet_name,
            module_uri=f"file://{os.path.abspath(__file__)}",
            entrypoint="handle",
            timeout_ms=0,
        )


def register_gibraltar_handlers(poller) -> None:
    for facet_name, fn in _DISPATCH.items():
        poller.register(facet_name, fn)
