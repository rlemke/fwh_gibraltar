# SPDX-License-Identifier: Apache-2.0
"""Render the survey as a self-contained page.

No CDN, no tile server, no JavaScript library: the geometry is drawn as inline
SVG. That is the county-atlas precedent and it matters more than usual here,
because the point of the map is the *absence* of something — a page that needs
a basemap to make sense would be showing someone else's data at the moment it
claims a gap.

The projection is a local equirectangular one with a cos(latitude) correction.
At 36°N that is accurate to well under a pixel across a 4 km territory, and it
avoids pulling in a projection dependency for a single map.
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

W, H, PAD = 760, 1180, 28  # Gibraltar is ~1.5 km wide and ~5 km tall: portrait.

STYLE = {
    "road": ("#9aa3ab", 0.9),
    "tunnel": ("#e2492f", 2.6),
}
MARKS = {
    "natural=cave_entrance": ("#2f6fe2", 3.4, "cave entrance"),
    "military=bunker": ("#7a4fd6", 3.0, "bunker"),
    "historic=fort": ("#c8952a", 2.6, "fort / battery"),
}


def _project(features: list[dict]) -> tuple[Any, float, float, float, float]:
    lons, lats = [], []
    for f in features:
        g = f.get("geometry") or {}
        cs = g.get("coordinates") or []
        if g.get("type") == "Point":
            lons.append(cs[0]); lats.append(cs[1])
        else:
            for c in cs:
                lons.append(c[0]); lats.append(c[1])
    if not lons:
        raise ValueError("nothing to draw")
    lon0, lon1 = min(lons), max(lons)
    lat0, lat1 = min(lats), max(lats)
    kx = math.cos(math.radians((lat0 + lat1) / 2))
    sx = (W - 2 * PAD) / max((lon1 - lon0) * kx, 1e-9)
    sy = (H - 2 * PAD) / max(lat1 - lat0, 1e-9)
    s = min(sx, sy)
    ox = PAD + ((W - 2 * PAD) - (lon1 - lon0) * kx * s) / 2
    oy = PAD + ((H - 2 * PAD) - (lat1 - lat0) * s) / 2

    def to_xy(lon: float, lat: float) -> tuple[float, float]:
        return (ox + (lon - lon0) * kx * s, H - oy - (lat - lat0) * s)

    return to_xy, lon0, lat0, s, kx


def render(survey: dict, features: list[dict], out_path: str, *, title: str = "The Hollow Mountain") -> str:
    to_xy, *_ = _project(features)
    layers: dict[str, list[str]] = {"road": [], "tunnel": [], "mark": []}

    for f in features:
        g = f.get("geometry") or {}
        p = f.get("properties") or {}
        kind = p.get("kind", "")
        if g.get("type") == "LineString" and kind in STYLE:
            colour, width = STYLE[kind]
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (to_xy(c[0], c[1]) for c in g["coordinates"]))
            name = html.escape(p.get("name") or "")
            extra = f"<title>{name} — {p.get('metres','')} m</title>" if kind == "tunnel" and name else ""
            layers[kind].append(
                f'<polyline points="{pts}" fill="none" stroke="{colour}" '
                f'stroke-width="{width}" stroke-linecap="round">{extra}</polyline>')
        elif g.get("type") == "Point" and kind in MARKS:
            colour, r, label = MARKS[kind]
            x, y = to_xy(*g["coordinates"])
            name = html.escape(p.get("name") or label)
            layers["mark"].append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{colour}" '
                f'fill-opacity="0.85" stroke="#0b0d10" stroke-width="0.5">'
                f'<title>{name}</title></circle>')

    svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
           f'aria-label="Gibraltar: mapped roads, mapped tunnels, and surface evidence of the '
           f'unmapped tunnel system">'
           + "".join(layers["road"]) + "".join(layers["tunnel"]) + "".join(layers["mark"])
           + "</svg>")

    s = survey
    bar_mapped = 100 * s["tunnel_km"] / s["published_tunnel_km"]
    top = sorted(s["named_tunnels"], key=lambda t: -t["metres"])[:8]
    rows = "".join(
        f"<tr><td>{html.escape(t['name'])}</td><td class='n'>{t['metres']:,} m</td>"
        f"<td class='t'>{html.escape(t['highway'])}</td></tr>" for t in top)
    ev = "".join(
        f"<li><b>{v}</b> {html.escape(k.split('=')[1].replace('_',' '))}</li>"
        for k, v in list(s["underground_evidence"].items())[:6])
    cls = "".join(
        f"<tr><td>{html.escape(k)}</td><td class='n'>{v:,.2f} km</td></tr>"
        for k, v in sorted(s["km_by_class"].items(), key=lambda kv: -kv[1])[:8])

    return _write(out_path, f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Gibraltar in OpenStreetMap</title>
<style>
 :root {{ --bg:#0b0d10; --fg:#e8eaed; --dim:#98a1ab; --line:#20262e;
          --road:#9aa3ab; --tunnel:#e2492f; --cave:#2f6fe2; --bunker:#7a4fd6; --fort:#c8952a; }}
 * {{ box-sizing:border-box }}
 body {{ margin:0; background:var(--bg); color:var(--fg);
        font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
 .wrap {{ max-width:1180px; margin:0 auto; padding:28px 20px 64px; }}
 h1 {{ font-size:1.9rem; margin:0 0 .2em; letter-spacing:-.02em }}
 .sub {{ color:var(--dim); margin:0 0 28px; max-width:62ch }}
 .grid {{ display:grid; grid-template-columns:minmax(320px,1fr) minmax(300px,420px); gap:28px; align-items:start }}
 @media (max-width:820px) {{ .grid {{ grid-template-columns:1fr }} }}
 .card {{ background:#11151a; border:1px solid var(--line); border-radius:10px; padding:18px 20px; margin-bottom:18px }}
 .card h2 {{ font-size:.78rem; text-transform:uppercase; letter-spacing:.09em; color:var(--dim);
             margin:0 0 14px; font-weight:600 }}
 .big {{ font-size:2.5rem; font-weight:700; line-height:1; letter-spacing:-.03em }}
 .big small {{ font-size:.95rem; font-weight:400; color:var(--dim); letter-spacing:0 }}
 .bar {{ height:22px; background:#1b2028; border-radius:4px; overflow:hidden; margin:12px 0 6px; position:relative }}
 .bar i {{ display:block; height:100%; background:var(--tunnel) }}
 .barlab {{ display:flex; justify-content:space-between; font-size:.8rem; color:var(--dim) }}
 table {{ width:100%; border-collapse:collapse; font-size:.88rem }}
 td {{ padding:5px 0; border-bottom:1px solid var(--line) }}
 td.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap }}
 td.t {{ text-align:right; color:var(--dim); font-size:.8rem; padding-left:10px; white-space:nowrap }}
 ul {{ margin:0; padding-left:1.1em }} li {{ margin:.25em 0 }}
 .key {{ display:flex; flex-wrap:wrap; gap:14px; font-size:.82rem; color:var(--dim); margin-top:12px }}
 .key i {{ display:inline-block; width:11px; height:11px; border-radius:2px; margin-right:5px; vertical-align:-1px }}
 a {{ color:#7fb2ff }} .foot {{ color:var(--dim); font-size:.84rem; margin-top:30px; max-width:78ch }}
 .map {{ background:#0e1216; border:1px solid var(--line); border-radius:10px; padding:8px }}
</style></head><body><div class="wrap">
<h1>{html.escape(title)}</h1>
<p class="sub">Gibraltar holds about <b>55&nbsp;km of tunnels</b> inside a {s['area_km2']}&nbsp;km²
rock, cut between 1782 and 1967. Almost all of it is military and sealed. This is what
OpenStreetMap knows about it — and what it does not.</p>
<div class="grid">
  <div class="map">{svg}
    <div class="key" style="padding:6px 10px 2px">
      <span><i style="background:var(--road)"></i>mapped road</span>
      <span><i style="background:var(--tunnel)"></i>mapped tunnel</span>
      <span><i style="background:var(--cave)"></i>cave entrance</span>
      <span><i style="background:var(--bunker)"></i>bunker</span>
      <span><i style="background:var(--fort)"></i>fort / battery</span>
    </div></div>
  <div>
    <div class="card"><h2>The gap</h2>
      <div class="big">{s['mapped_pct']}%<small> of the tunnel system is in OSM</small></div>
      <div class="bar"><i style="width:{bar_mapped:.1f}%"></i></div>
      <div class="barlab"><span>{s['tunnel_km']} km mapped</span><span>{s['unmapped_km']} km not</span></div>
      <p style="color:var(--dim); font-size:.86rem; margin:12px 0 0">
      The missing {s['unmapped_km']} km is not an error. It is classified, sealed, or both —
      the limit of what a public map can hold.</p>
    </div>
    <div class="card"><h2>Two gaps, opposite directions</h2>
      <table>
        <tr><td>tunnels, published</td><td class="n">{s['published_tunnel_km']} km</td></tr>
        <tr><td>tunnels, in OSM</td><td class="n">{s['tunnel_km']} km</td></tr>
        <tr><td>public road, official</td><td class="n">{s['official_road_km']} km</td></tr>
        <tr><td>public road, in OSM</td><td class="n">{s['public_road_km']} km</td></tr>
      </table>
      <p style="color:var(--dim); font-size:.86rem; margin:12px 0 0">
      OSM holds <b>12%</b> of the tunnels and <b>{s['osm_vs_official_roads']}×</b> the official
      road length. Both are definitional, not sloppy: one counts what cannot be surveyed,
      the other counts service ways and both carriageways that no road statistic does.</p>
    </div>
    <div class="card"><h2>Longest mapped tunnels</h2><table>{rows}</table></div>
    <div class="card"><h2>Where the underground surfaces</h2><ul>{ev}</ul></div>
    <div class="card"><h2>Network by class</h2><table>{cls}</table></div>
  </div>
</div>
<p class="foot">Geometry © OpenStreetMap contributors (ODbL), measured from a locally hosted
extract. Lengths are geodesic. Published figures and their sources are listed in
<code>docs/sources.md</code>; the tunnel total is the widely published ~55&nbsp;km (34&nbsp;miles)
and the road total is Gibraltar's official 29&nbsp;km. Generated by
<code>fwh_gibraltar</code>.</p>
</div></body></html>""")


def _write(out_path: str, doc: str) -> str:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc, encoding="utf-8")
    return str(p)


def write_stats(survey: dict, out_path: str) -> str:
    return _write(out_path, json.dumps(survey, indent=2))
