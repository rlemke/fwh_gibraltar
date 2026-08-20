# SPDX-License-Identifier: Apache-2.0
"""Measure Gibraltar's mapped network — and the part OSM cannot see.

Gibraltar holds roughly **55 km of tunnels inside a 6.7 km² rock**, cut between
1782 and 1967, "nearly twice the length of its entire road network"
(en.wikipedia.org/wiki/Tunnels_of_Gibraltar). Almost all of it is military,
sealed, and therefore unmappable. That makes this the rare place where OSM's
*omission* is bounded and quantifiable: the ground truth is published, so the
gap can be measured rather than guessed at.

This module measures three things from a local extract:

1. the surface network, **classified** — because `w/highway` is not "roads". On
   a rock climbed by the Mediterranean Steps, footways and steps dominate the
   way count, and comparing that total against a published *road* figure would
   overstate the network sevenfold. (Measured here first as a single 207.69 km
   number, which is why the split exists.)
2. the mapped tunnels, by length and name;
3. the surface evidence of the rest — cave entrances, bunkers, batteries — the
   seams where a hollow mountain reaches daylight.

Lengths are geodesic (pyproj `Geod`), not planar: Gibraltar spans ~4 km and a
Web-Mercator length at 36°N would be inflated by ~24%.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

#: Highway values that are a ROAD — what the published "road network" means.
ROAD_VALUES = {
    "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
    "secondary", "secondary_link", "tertiary", "tertiary_link",
    "unclassified", "residential", "living_street", "service", "road",
}
#: Ways people walk or climb, which are not roads and must not be added to them.
PATH_VALUES = {"footway", "path", "steps", "pedestrian", "track", "cycleway", "bridleway"}

#: Published figures, for the gap. Sources are listed in docs/sources.md; each
#: is quoted there rather than paraphrased, because the whole result is a
#: comparison against them.
TUNNEL_KM_PUBLISHED = 55.0
TUNNEL_MILES_PUBLISHED = 34.0
AREA_KM2 = 6.7
#: Gibraltar's official road network, 29 km (18 mi) — the figure the published
#: "tunnels are nearly twice the road network" claim is measured against. OSM
#: counts far more than this, which is the second gap this survey reports.
ROAD_KM_OFFICIAL = 29.0


class SurveyError(RuntimeError):
    """Raised when the survey cannot be produced."""


@dataclass
class Survey:
    place: Any = None
    road_km: float = 0.0
    path_km: float = 0.0
    other_km: float = 0.0
    tunnel_km: float = 0.0
    tunnel_road_km: float = 0.0
    ways: dict[str, int] = field(default_factory=dict)
    km_by_class: dict[str, float] = field(default_factory=dict)
    tunnels: list[dict] = field(default_factory=list)
    underground_evidence: dict[str, int] = field(default_factory=dict)
    features: list[dict] = field(default_factory=list)

    @property
    def public_road_km(self) -> float:
        """Public roads only — the like-for-like against the official 29 km.

        `service` is excluded: 75 km of it is car parks, estate access and
        military service ways, which no road statistic counts.
        """
        return sum(v for k, v in self.km_by_class.items()
                   if k in ROAD_VALUES and k != "service")

    @property
    def pavement_duplicate_km(self) -> float:
        """Footway tunnels that share a bore with a road tunnel of the same name.

        A road tunnel with a pavement each side is three OSM ways through one
        hole in the ground, so summing way length counts the same bore three
        times. Jersey's Route du Fort is exactly that: a 250.2 m trunk plus two
        250.4 m footways — 0.75 km of "mapped tunnel" for a 250 m tunnel.

        The test is deliberately narrow rather than a general overlap
        heuristic: same name, one road-class way, and a path-class way within
        15% of its length. Ho8's tunnels are eight footways with no road among
        them — a genuine branching network — and a bbox-overlap rule would have
        collapsed those into one passage, destroying real length. This rule
        leaves them alone.

        Reported alongside the headline, never subtracted from it silently: it
        is an estimate of double-counting, and the raw way total is the
        reproducible measurement.
        """
        by_name: dict[str, list[dict]] = {}
        for t in self.tunnels:
            if t["name"] != "(unnamed)":
                by_name.setdefault(t["name"], []).append(t)
        dup_m = 0
        for ways in by_name.values():
            roads = [w for w in ways if w["highway"] in ROAD_VALUES]
            if not roads:
                continue
            longest = max(w["metres"] for w in roads)
            for w in ways:
                if w["highway"] in PATH_VALUES and abs(w["metres"] - longest) <= 0.15 * longest:
                    dup_m += w["metres"]
        return dup_m / 1000.0

    @property
    def published_tunnel_km(self) -> float | None:
        p = getattr(self.place, "tunnel_km_published", None)
        return TUNNEL_KM_PUBLISHED if p is None and self.place is None else p

    @property
    def mapped_fraction(self) -> float | None:
        """Mapped tunnel length as a fraction of the published total.

        ``None`` where no total was ever published — Jersey's records were
        destroyed before the 1945 surrender. Returning 0.0, or picking a
        plausible denominator, would turn "unknown" into a number, and the
        difference between unknown and unmapped is the whole point.
        """
        total = self.published_tunnel_km
        return self.tunnel_km / total if total else None

    def as_dict(self) -> dict[str, Any]:
        frac = self.mapped_fraction
        official = getattr(self.place, "road_km_official", None) if self.place else ROAD_KM_OFFICIAL
        pub = self.published_tunnel_km
        return {
            "place": getattr(self.place, "key", "gibraltar"),
            "place_name": getattr(self.place, "name", "Gibraltar"),
            "title": getattr(self.place, "title", "The Hollow Mountain"),
            "blurb": getattr(self.place, "blurb", ""),
            "notes": list(getattr(self.place, "notes", [])),
            "road_km": round(self.road_km, 2),
            "path_km": round(self.path_km, 2),
            "other_km": round(self.other_km, 2),
            "tunnel_km": round(self.tunnel_km, 2),
            "tunnel_road_km": round(self.tunnel_road_km, 2),
            "pavement_duplicate_km": round(self.pavement_duplicate_km, 2),
            "tunnel_km_distinct": round(self.tunnel_km - self.pavement_duplicate_km, 2),
            "published_tunnel_km": pub,
            "mapped_pct": round(100 * frac, 1) if frac is not None else None,
            "unmapped_km": round(pub - self.tunnel_km, 1) if pub else None,
            "tunnel_vs_road_ratio_published": round(pub / self.road_km, 2)
            if (pub and self.road_km) else None,
            "ways": self.ways,
            "km_by_class": {k: round(v, 2) for k, v in self.km_by_class.items()},
            "public_road_km": round(self.public_road_km, 2),
            "official_road_km": official,
            "osm_vs_official_roads": round(self.public_road_km / official, 2) if official else None,
            "tunnel_vs_official_roads": round(pub / official, 2) if (pub and official) else None,
            "named_tunnels": self.tunnels,
            "underground_evidence": self.underground_evidence,
            "area_km2": getattr(self.place, "area_km2", AREA_KM2),
            "tunnel_per_km2": round(self.tunnel_km / getattr(self.place, "area_km2", AREA_KM2), 3),
        }


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SurveyError(f"osmium not found: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        raise SurveyError(f"{cmd[1]} failed: {(exc.stderr or '').strip() or exc}") from exc


def _geodesic_km(coords: list[list[float]]) -> float:
    from pyproj import Geod

    if len(coords) < 2:
        return 0.0
    geod = Geod(ellps="WGS84")
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return geod.line_length(lons, lats) / 1000.0


def survey(pbf: str, *, place: Any = None, osmium_bin: str = "osmium",
           keep_geometry: bool = True) -> Survey:
    """Measure one extract against a place's published ground truth."""
    src = Path(pbf)
    if not src.exists():
        raise SurveyError(f"no such extract: {src}")
    if not shutil.which(osmium_bin):
        raise SurveyError(f"osmium not found ({osmium_bin})")

    staging = Path(tempfile.mkdtemp(prefix="gib-survey-"))
    out = Survey(place=place)
    try:
        # Pass 1 — the network.
        hw_pbf = staging / "hw.osm.pbf"
        hw_seq = staging / "hw.geojsonseq"
        _run([osmium_bin, "tags-filter", "--overwrite", "-o", str(hw_pbf), str(src), "w/highway"])
        _run([osmium_bin, "export", "-f", "geojsonseq", "--geometry-types=linestring",
              "-o", str(hw_seq), "--overwrite", str(hw_pbf)])

        counts: dict[str, int] = {}
        for line in hw_seq.read_text(encoding="utf-8").splitlines():
            line = line.strip("\x1e \t\r\n")
            if not line:
                continue
            feat = json.loads(line)
            props = feat.get("properties") or {}
            geom = feat.get("geometry") or {}
            if geom.get("type") != "LineString":
                continue
            km = _geodesic_km(geom["coordinates"])
            hw = props.get("highway") or "?"
            counts[hw] = counts.get(hw, 0) + 1
            out.km_by_class[hw] = out.km_by_class.get(hw, 0.0) + km

            tunnel = props.get("tunnel")
            is_tunnel = bool(tunnel) and tunnel != "no"
            if hw in ROAD_VALUES:
                out.road_km += km
            elif hw in PATH_VALUES:
                out.path_km += km
            else:
                out.other_km += km
            if is_tunnel:
                out.tunnel_km += km
                if hw in ROAD_VALUES:
                    out.tunnel_road_km += km
                out.tunnels.append({
                    "name": props.get("name") or "(unnamed)",
                    "metres": round(km * 1000),
                    "highway": hw,
                    "tunnel": tunnel,
                    "layer": props.get("layer"),
                })
                if keep_geometry:
                    out.features.append({
                        "type": "Feature", "geometry": geom,
                        "properties": {"kind": "tunnel", "name": props.get("name"),
                                       "highway": hw, "metres": round(km * 1000)},
                    })
            elif keep_geometry and hw in ROAD_VALUES:
                out.features.append({
                    "type": "Feature", "geometry": geom,
                    "properties": {"kind": "road", "name": props.get("name"), "highway": hw},
                })
        out.ways = dict(sorted(counts.items(), key=lambda kv: -kv[1]))

        # Pass 2 — where the underground shows itself.
        ev_pbf = staging / "ev.osm.pbf"
        ev_seq = staging / "ev.geojsonseq"
        _run([osmium_bin, "tags-filter", "--overwrite", "-o", str(ev_pbf), str(src),
              "nwr/natural=cave_entrance", "nwr/military", "nwr/historic=fort",
              "nwr/historic=battery", "nwr/man_made=adit", "nwr/building=bunker",
              "nwr/historic=bunker"])
        _run([osmium_bin, "export", "-f", "geojsonseq", "-o", str(ev_seq),
              "--overwrite", str(ev_pbf)])
        ev: dict[str, int] = {}
        for line in ev_seq.read_text(encoding="utf-8").splitlines():
            line = line.strip("\x1e \t\r\n")
            if not line:
                continue
            feat = json.loads(line)
            props = feat.get("properties") or {}
            geom = feat.get("geometry") or {}
            for key in ("natural", "military", "historic", "man_made", "building"):
                val = props.get(key)
                if val:
                    label = f"{key}={val}"
                    ev[label] = ev.get(label, 0) + 1
                    if keep_geometry and geom:
                        out.features.append({
                            "type": "Feature",
                            "geometry": _point_of(geom),
                            "properties": {"kind": label, "name": props.get("name")},
                        })
                    break
        out.underground_evidence = dict(sorted(ev.items(), key=lambda kv: -kv[1]))
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return out


def _point_of(geom: dict) -> dict:
    """A representative point, so a fort polygon and a cave node plot alike."""
    if geom.get("type") == "Point":
        return geom
    coords = geom.get("coordinates") or []
    flat: list[list[float]] = []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            flat.append(c)
        else:
            for sub in c or []:
                walk(sub)

    walk(coords)
    if not flat:
        return {"type": "Point", "coordinates": [0, 0]}
    return {"type": "Point",
            "coordinates": [sum(p[0] for p in flat) / len(flat),
                            sum(p[1] for p in flat) / len(flat)]}
