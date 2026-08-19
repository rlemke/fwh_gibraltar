# SPDX-License-Identifier: Apache-2.0
"""Tests for the Hollow Mountain survey.

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

from gibraltar.tools._gibraltar_tools import render as rmod
from gibraltar.tools._gibraltar_tools import survey as smod

HAS_OSMIUM = shutil.which("osmium") is not None
EXTRACT = next(
    (p for root in os.environ.get("FW_OSM_LOCAL_EXTRACTS", "").split(":") if root.strip()
     for p in [Path(root) / "europe/gibraltar-latest.osm.pbf"] if p.exists()),
    None,
)
needs_extract = pytest.mark.skipif(
    not (HAS_OSMIUM and EXTRACT), reason="no osmium or no local Gibraltar extract")


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
    s = smod.survey(str(EXTRACT))
    d = s.as_dict()
    assert 5.0 < d["tunnel_km"] < 9.0, d["tunnel_km"]
    assert 8.0 < d["mapped_pct"] < 20.0, "the gap is the finding; it should be large"
    assert 55.0 < d["public_road_km"] < 80.0
    assert d["osm_vs_official_roads"] > 1.5, "OSM maps far more road than the official figure"
    assert any("cave_entrance" in k for k in d["underground_evidence"])
    assert any(t["name"] == "Admiralty tunnel" for t in d["named_tunnels"])
