# SPDX-License-Identifier: Apache-2.0
"""Tests for the tunnel survey.

The arithmetic and the refusals are pure and always run. The tests that need a
real extract skip themselves, so a host without the local planet split still
gets a green suite.

What is pinned hardest is the CLASSIFICATION, because the headline comparison
depends on it: `w/highway` is not "roads", and adding footways and steps to a
road total would overstate Gibraltar's network sevenfold against the published
29 km. That mistake was made once here before the split existed.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from gibraltar.tools._gibraltar_tools import places as pmod
from gibraltar.tools._gibraltar_tools import render as rmod
from gibraltar.tools._gibraltar_tools import survey as smod

HAS_OSMIUM = shutil.which("osmium") is not None
def _extract(rel: str) -> Path | None:
    for root in os.environ.get("FW_OSM_LOCAL_EXTRACTS", "").split(":"):
        if root.strip() and (p := Path(root) / rel).exists():
            return p
    return None


EXTRACT = _extract("europe/gibraltar-latest.osm.pbf")
JERSEY = _extract("europe/jersey-latest.osm.pbf")
needs_extract = pytest.mark.skipif(
    not (HAS_OSMIUM and EXTRACT), reason="no osmium or no local Gibraltar extract")
needs_jersey = pytest.mark.skipif(
    not (HAS_OSMIUM and JERSEY), reason="no osmium or no local Jersey extract")


# --- classification: the thing the headline depends on ----------------------


def test_paths_are_not_roads():
    """Footways, steps and paths must never land in the road total: Gibraltar is
    climbed by the Mediterranean Steps, and counting them as road would put the
    network at ~207 km against a published 29 km."""
    assert "footway" not in smod.ROAD_VALUES
    assert "steps" not in smod.ROAD_VALUES
    assert "path" not in smod.ROAD_VALUES
    assert smod.PATH_VALUES.isdisjoint(smod.ROAD_VALUES)


def test_public_road_excludes_service():
    """`service` is car parks and estate access — 75 km of it here, which no road
    statistic counts. The like-for-like against the official 29 km excludes it."""
    s = smod.Survey(km_by_class={"primary": 8.47, "residential": 20.18, "service": 75.25,
                                 "footway": 37.27})
    assert s.public_road_km == pytest.approx(28.65)
    assert "service" in smod.ROAD_VALUES, "service is still a road, just not a public one"


def test_mapped_fraction_is_against_the_published_total():
    s = smod.Survey(tunnel_km=6.63)
    assert s.mapped_fraction == pytest.approx(6.63 / 55.0)
    assert s.as_dict()["mapped_pct"] == pytest.approx(12.1, abs=0.2)
    assert s.as_dict()["unmapped_km"] == pytest.approx(48.4, abs=0.1)


def test_lengths_are_geodesic_not_planar():
    """A degree of longitude at 36°N is ~0.81 of one at the equator. Treating
    degrees as planar would inflate east-west lengths by ~24%."""
    east_west = smod._geodesic_km([[-5.35, 36.14], [-5.34, 36.14]])
    north_south = smod._geodesic_km([[-5.35, 36.14], [-5.35, 36.15]])
    assert east_west < north_south
    assert east_west / north_south == pytest.approx(0.808, abs=0.01)


# --- the missing denominator ------------------------------------------------


def test_jersey_has_no_denominator_and_does_not_invent_one():
    """The load-bearing invariant of this project.

    Jersey's records were destroyed before the 1945 surrender, so no total
    tunnel length was ever published. `mapped_fraction` must be None, not 0.0:
    a zero would read as "nothing is mapped", when what is true is "nobody knows
    how much there is to map". Those are different claims and the output must
    not flatten them together.
    """
    j = pmod.get("jersey")
    assert j.tunnel_km_published is None
    assert j.has_denominator is False

    s = smod.Survey(place=j, tunnel_km=1.97)
    assert s.mapped_fraction is None
    d = s.as_dict()
    assert d["mapped_pct"] is None
    assert d["unmapped_km"] is None
    assert d["tunnel_km"] == 1.97, "the measurement itself is still reported"


def test_gibraltar_still_has_one():
    g = pmod.get("gibraltar")
    assert g.has_denominator and g.tunnel_km_published == 55.0
    assert smod.Survey(place=g, tunnel_km=6.63).as_dict()["mapped_pct"] == pytest.approx(12.1, abs=0.2)


def test_the_page_never_prints_a_percentage_without_a_denominator(tmp_path):
    """The renderer branches on this, so the branch is pinned: a Jersey page
    must not carry a "% of the tunnel system" claim anywhere."""
    stats = smod.Survey(place=pmod.get("jersey"), tunnel_km=1.97,
                        km_by_class={"residential": 300.0}).as_dict()
    feats = [{"type": "Feature", "properties": {"kind": "tunnel", "name": "Tunnels Ho8",
                                                "metres": 148},
              "geometry": {"type": "LineString", "coordinates": [[-2.15, 49.21], [-2.14, 49.21]]}}]
    doc = Path(rmod.render(stats, feats, str(tmp_path / "j.html"))).read_text()
    assert "% of the tunnel system" not in doc
    assert "unknown" in doc and "no total was ever published" in doc


def test_an_unknown_place_says_what_is_missing():
    with pytest.raises(KeyError, match="gibraltar, jersey"):
        pmod.get("atlantis")


# --- double counting --------------------------------------------------------


def test_a_road_tunnels_pavements_are_counted_as_one_bore():
    """Route du Fort is a ~250 m bore mapped as three ways — a trunk carriageway
    and a footway for each pavement. Summing way length triples it."""
    s = smod.Survey(place=pmod.get("jersey"), tunnel_km=0.751, tunnels=[
        {"name": "Route du Fort", "metres": 250, "highway": "trunk"},
        {"name": "Route du Fort", "metres": 250, "highway": "footway"},
        {"name": "Route du Fort", "metres": 250, "highway": "footway"},
    ])
    assert s.pavement_duplicate_km == pytest.approx(0.5)
    assert s.as_dict()["tunnel_km_distinct"] == pytest.approx(0.25, abs=0.01)


def test_a_branching_footway_network_is_left_alone():
    """Ho8 is eight footway tunnels with no road among them — a real branching
    complex. A bbox-overlap rule would have collapsed it to one passage; this
    rule requires a road-class way in the group, so it does not fire."""
    s = smod.Survey(place=pmod.get("jersey"), tunnel_km=0.521, tunnels=[
        {"name": "Tunnels Ho8", "metres": m, "highway": "footway"}
        for m in (148, 128, 89, 56, 50, 33, 18)
    ])
    assert s.pavement_duplicate_km == 0.0
    assert s.as_dict()["tunnel_km_distinct"] == pytest.approx(0.52)  # as_dict rounds to 2dp


def test_a_dissimilar_footway_is_not_a_pavement():
    """A 20 m footway beside a 250 m road tunnel is a separate thing, not that
    tunnel's pavement — the length test is what keeps the rule narrow."""
    s = smod.Survey(place=pmod.get("jersey"), tunnels=[
        {"name": "X", "metres": 250, "highway": "trunk"},
        {"name": "X", "metres": 20, "highway": "footway"},
    ])
    assert s.pavement_duplicate_km == 0.0


def test_a_missing_extract_is_refused():
    with pytest.raises(smod.SurveyError, match="no such extract"):
        smod.survey("/nowhere/gibraltar.osm.pbf")


# --- rendering --------------------------------------------------------------


def test_representative_point_of_a_polygon():
    poly = {"type": "Polygon", "coordinates": [[[-5.35, 36.14], [-5.34, 36.14],
                                                [-5.34, 36.15], [-5.35, 36.15]]]}
    pt = smod._point_of(poly)
    assert pt["type"] == "Point"
    assert -5.35 <= pt["coordinates"][0] <= -5.34


def test_render_is_self_contained(tmp_path):
    """No CDN, no tile server: the subject is an absence, and a page that needed
    someone else's basemap to be legible would undercut the claim."""
    stats = smod.Survey(tunnel_km=6.63, km_by_class={"primary": 8.47}).as_dict()
    feats = [
        {"type": "Feature", "properties": {"kind": "road", "highway": "primary"},
         "geometry": {"type": "LineString", "coordinates": [[-5.35, 36.14], [-5.34, 36.15]]}},
        {"type": "Feature", "properties": {"kind": "tunnel", "name": "Admiralty tunnel",
                                           "metres": 957},
         "geometry": {"type": "LineString", "coordinates": [[-5.35, 36.13], [-5.35, 36.14]]}},
        {"type": "Feature", "properties": {"kind": "natural=cave_entrance", "name": "St Michael's"},
         "geometry": {"type": "Point", "coordinates": [-5.344, 36.13]}},
    ]
    out = rmod.render(stats, feats, str(tmp_path / "m.html"))
    doc = Path(out).read_text()
    for bad in ("http://", "https://cdn", "<script", "src="):
        assert bad not in doc, f"page reaches outside itself: {bad}"
    assert "<polyline" in doc and "<circle" in doc
    assert "Admiralty tunnel" in doc


def test_render_escapes_names(tmp_path):
    feats = [{"type": "Feature",
              "properties": {"kind": "tunnel", "name": "<script>x</script>", "metres": 1},
              "geometry": {"type": "LineString", "coordinates": [[-5.35, 36.14], [-5.34, 36.15]]}}]
    out = rmod.render(smod.Survey().as_dict(), feats, str(tmp_path / "m.html"))
    doc = Path(out).read_text()
    assert "<script>x</script>" not in doc and "&lt;script&gt;" in doc


# --- against the real extract ----------------------------------------------


@needs_extract
def test_the_real_survey_reproduces_the_published_comparison():
    s = smod.survey(str(EXTRACT), place=pmod.get("gibraltar"))
    d = s.as_dict()
    assert 5.0 < d["tunnel_km"] < 9.0, d["tunnel_km"]
    assert 8.0 < d["mapped_pct"] < 20.0, "the gap is the finding; it should be large"
    assert 55.0 < d["public_road_km"] < 80.0
    assert d["osm_vs_official_roads"] > 1.5, "OSM maps far more road than the official figure"
    assert any("cave_entrance" in k for k in d["underground_evidence"])
    assert any(t["name"] == "Admiralty tunnel" for t in d["named_tunnels"])


@needs_jersey
def test_the_real_jersey_survey_measures_without_a_denominator():
    """The surface is mapped exhaustively and the underground barely at all —
    which is the whole finding, and it survives the real extract."""
    d = smod.survey(str(JERSEY), place=pmod.get("jersey"), keep_geometry=False).as_dict()
    assert d["mapped_pct"] is None and d["published_tunnel_km"] is None
    assert 1.0 < d["tunnel_km"] < 4.0, d["tunnel_km"]
    assert d["tunnel_km_distinct"] < d["tunnel_km"], "Route du Fort's pavements"
    bunkers = sum(v for k, v in d["underground_evidence"].items() if "bunker" in k)
    assert bunkers > 200, f"Jersey's bunkers are mapped in force; got {bunkers}"
    assert any("Ho8" in (t["name"] or "") for t in d["named_tunnels"]), \
        "the German Underground Hospital is the one complex OSM holds"
