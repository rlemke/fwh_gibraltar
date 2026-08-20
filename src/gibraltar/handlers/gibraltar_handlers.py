# SPDX-License-Identifier: Apache-2.0
"""Handlers for the tunnel survey.

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

from ..tools._gibraltar_tools import places
from ..tools._gibraltar_tools.render import render, write_stats
from ..tools._gibraltar_tools.survey import SurveyError, survey

NAMESPACE = "gibraltar"

#: Where a locally hosted extract lives, colon-separated (same convention as
#: FW_OSM_LOCAL_EXTRACTS elsewhere in this fleet).
LOCAL_EXTRACTS = os.environ.get("FW_OSM_LOCAL_EXTRACTS", "")
#: Both places are Geofabrik sub-extracts of europe, and both are small — 1 MB
#: and 2 MB — so the survey never needs the network.
REL = {
    "gibraltar": "europe/gibraltar-latest.osm.pbf",
    "jersey": "europe/jersey-latest.osm.pbf",
}


def _log(params: dict[str, Any]):
    sl = params.get("_step_log")
    return (lambda m, level="info": sl(m, level=level)) if sl else (lambda m, level="info": None)


def _resolve(pbf: str, place_key: str) -> str:
    """This place's extract: an explicit path, else the local planet split."""
    if pbf:
        if not Path(pbf).exists():
            raise PermanentError(f"pbf does not exist: {pbf}")
        return pbf
    rel = REL.get(place_key)
    if rel is None:
        raise PermanentError(
            f"no extract path registered for place {place_key!r}; pass `pbf` explicitly")
    bare = rel.rsplit("/", 1)[-1]
    for root in (r for r in LOCAL_EXTRACTS.split(":") if r.strip()):
        for cand in (Path(root) / rel, Path(root) / bare):
            if cand.exists():
                return str(cand)
    raise PermanentError(
        f"no {place_key} extract. Pass `pbf`, or set FW_OSM_LOCAL_EXTRACTS to a tree "
        f"holding {rel}. It is a couple of MB — this survey never needs the network."
    )


def handle_survey(params: dict[str, Any]) -> dict[str, Any]:
    say = _log(params)
    key = (params.get("place") or "gibraltar").strip().lower()
    try:
        place = places.get(key)
    except KeyError as exc:
        # An unknown place is a request that can never succeed, not a transient
        # fault: fail it permanently rather than burning five retries.
        raise PermanentError(str(exc)) from exc
    pbf = _resolve((params.get("pbf") or "").strip(), place.key)
    say(f"surveying {place.name} from {pbf}")
    try:
        result = survey(pbf, place=place,
                        osmium_bin=os.environ.get("FW_OSMIUM_BIN", "osmium"))
    except SurveyError as exc:
        raise PermanentError(str(exc)) from exc
    stats = result.as_dict()
    out_dir = Path(params.get("out_dir") or "gibraltar-out")
    stats_path = write_stats(stats, str(out_dir / "statistics.json"))

    if place.has_denominator:
        summary = (f"{place.name}: {stats['tunnel_km']} km of tunnel mapped, "
                   f"{stats['mapped_pct']}% of the published "
                   f"{stats['published_tunnel_km']} km.")
    else:
        # Said in words rather than as a number, because there is no number.
        summary = (f"{place.name}: {stats['tunnel_km']} km of tunnel mapped "
                   f"({stats['tunnel_km_distinct']} km of distinct bore) against no "
                   f"published total — the records were destroyed, so the gap cannot "
                   f"be quantified.")
    say(summary)
    return {
        "stats_path": stats_path,
        "place_name": place.name,
        "tunnel_km": stats["tunnel_km"],
        "tunnel_km_distinct": stats["tunnel_km_distinct"],
        "has_denominator": place.has_denominator,
        "summary": summary,
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
    # Name the file after the place, so two runs into one out_dir do not
    # overwrite each other.
    slug = (stats.get("place") or "gibraltar")
    stem = {"gibraltar": "hollow-mountain"}.get(slug, slug)
    out = Path(params.get("out_dir") or "gibraltar-out") / f"{stem}.html"
    path = render(stats, features, str(out), title=(params.get("title") or "").strip() or None)
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
