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

W, PAD = 760, 28
#: Canvas height follows the data. Gibraltar is ~1.5 x 5 km (portrait) and
#: Jersey ~14 x 8 km (landscape); a fixed portrait canvas would leave one of
#: them as a thin band in a field of empty page. Clamped so a pathological
#: bbox cannot produce a 20,000px page.
H_MIN, H_MAX = 420, 1180

STYLE = {
    "road": ("#9aa3ab", 0.9),
    "tunnel": ("#e2492f", 2.6),
}
MARKS = {
    "natural=cave_entrance": ("#2f6fe2", 3.4, "cave entrance"),
    "military=bunker": ("#7a4fd6", 3.0, "bunker"),
    "historic=fort": ("#c8952a", 2.6, "fort / battery"),
    "historic=bunker": ("#7a4fd6", 3.0, "bunker"),
    "building=bunker": ("#7a4fd6", 3.0, "bunker"),
}


def _project(features: list[dict]) -> tuple[Any, int]:
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
    dx = max((lon1 - lon0) * kx, 1e-9)
    dy = max(lat1 - lat0, 1e-9)
    inner = W - 2 * PAD
    H = int(min(H_MAX, max(H_MIN, inner * dy / dx + 2 * PAD)))
    s = min(inner / dx, (H - 2 * PAD) / dy)
    ox = PAD + (inner - dx * s) / 2
    oy = PAD + ((H - 2 * PAD) - dy * s) / 2

    def to_xy(lon: float, lat: float) -> tuple[float, float]:
        return (ox + (lon - lon0) * kx * s, H - oy - (lat - lat0) * s)

    return to_xy, H


def render(survey: dict, features: list[dict], out_path: str, *, title: str | None = None) -> str:
    title = title or survey.get("title") or "The Hollow Mountain"
    to_xy, H = _project(features)
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
           f'aria-label="{html.escape(survey.get("place_name", ""))}: mapped roads, mapped '
           f'tunnels, and the surface evidence of what is not mapped">'
           + "".join(layers["road"]) + "".join(layers["tunnel"]) + "".join(layers["mark"])
           + "</svg>")

    s = survey
    has_denom = s.get("mapped_pct") is not None
    bar_mapped = (100 * s["tunnel_km"] / s["published_tunnel_km"]) if has_denom else 0.0
    top = sorted(s["named_tunnels"], key=lambda t: -t["metres"])[:8]
    rows = "".join(
        f"<tr><td>{html.escape(t['name'])}</td><td class='n'>{t['metres']:,} m</td>"
        f"<td class='t'>{html.escape(t['highway'])}</td></tr>" for t in top)
    # Collapse by the tag VALUE: military=bunker, building=bunker and
    # historic=bunker are one kind of thing recorded by three mappers'
    # conventions, and listing "325 bunker / 59 bunker / 13 bunker" reads as
    # three categories rather than one count of 397.
    by_value: dict[str, int] = {}
    for k, v in s["underground_evidence"].items():
        by_value[k.split("=")[-1].replace("_", " ")] = (
            by_value.get(k.split("=")[-1].replace("_", " "), 0) + v)
    ev = "".join(
        f"<li><b>{v}</b> {html.escape(k)}</li>"
        for k, v in sorted(by_value.items(), key=lambda kv: -kv[1])[:6])
    cls = "".join(
        f"<tr><td>{html.escape(k)}</td><td class='n'>{v:,.2f} km</td></tr>"
        for k, v in sorted(s["km_by_class"].items(), key=lambda kv: -kv[1])[:8])

    if has_denom:
        gap_card = f"""<div class="card"><h2>The gap</h2>
      <div class="big">{s['mapped_pct']}%<small> of the tunnel system is in OSM</small></div>
      <div class="bar"><i style="width:{bar_mapped:.1f}%"></i></div>
      <div class="barlab"><span>{s['tunnel_km']} km mapped</span><span>{s['unmapped_km']} km not</span></div>
      <p style="color:var(--dim); font-size:.86rem; margin:12px 0 0">
      The missing {s['unmapped_km']} km is not an error. It is classified, sealed, or both —
      the limit of what a public map can hold.</p></div>"""
        compare_card = f"""<div class="card"><h2>Two gaps, opposite directions</h2>
      <table>
        <tr><td>tunnels, published</td><td class="n">{s['published_tunnel_km']} km</td></tr>
        <tr><td>tunnels, in OSM</td><td class="n">{s['tunnel_km']} km</td></tr>
        <tr><td>public road, official</td><td class="n">{s['official_road_km']} km</td></tr>
        <tr><td>public road, in OSM</td><td class="n">{s['public_road_km']} km</td></tr>
      </table>
      <p style="color:var(--dim); font-size:.86rem; margin:12px 0 0">
      OSM holds <b>{s['mapped_pct']}%</b> of the tunnels and <b>{s['osm_vs_official_roads']}×</b>
      the official road length. Both are definitional, not sloppy: one counts what cannot be
      surveyed, the other counts service ways and both carriageways that no road statistic
      does.</p></div>"""
    else:
        # No published total exists. Saying "0%" or picking a plausible
        # denominator would turn "unknown" into a number; the absence of a
        # denominator IS this map's subject, so it is stated instead.
        bunkers = sum(v for k, v in s["underground_evidence"].items() if "bunker" in k)
        ho8_m = sum(t["metres"] for t in s["named_tunnels"] if "Ho8" in (t["name"] or ""))
        gap_card = f"""<div class="card"><h2>The denominator</h2>
      <div class="big">unknown<small> — no total was ever published</small></div>
      <p style="color:var(--dim); font-size:.86rem; margin:12px 0 0">
      The occupiers destroyed the records before the surrender, so not even the
      <b>number</b> of tunnel complexes is known: 19–25 were planned. There is no figure
      to measure OpenStreetMap against, and inventing one would be the only way to
      produce a percentage. Every other map of this kind reports what is missing; here
      the size of the missing part is itself missing.</p></div>"""
        compare_card = f"""<div class="card"><h2>What is mapped instead</h2>
      <table>
        <tr><td>tunnel ways, in OSM</td><td class="n">{s['tunnel_km']} km</td></tr>
        <tr><td>&nbsp;&nbsp;less shared bores</td><td class="n">{s['tunnel_km_distinct']} km</td></tr>
        <tr><td>&nbsp;&nbsp;of which Ho8</td><td class="n">{ho8_m:,} m</td></tr>
        <tr><td>bunkers, in OSM</td><td class="n">{bunkers}</td></tr>
        <tr><td>road, in OSM</td><td class="n">{s['road_km']} km</td></tr>
      </table>
      <p style="color:var(--dim); font-size:.86rem; margin:12px 0 0">
      Every fortification you can stand next to is mapped, in German designation order.
      Almost nothing that runs <i>between</i> them is. One complex — Ho8, the underground
      hospital — accounts for {100 * ho8_m / 1000 / max(s['tunnel_km_distinct'], 1e-9):.0f}%
      of it, and Ho8 alone had over 1,000&nbsp;m excavated. Of 19–25 planned, only Ho5 was
      ever finished.</p>
      <p style="color:var(--dim); font-size:.8rem; margin:8px 0 0">
      The two figures differ because Route du Fort's single ~250&nbsp;m bore is three OSM
      ways — a carriageway and a pavement each side. Way length is the reproducible
      measurement; the second line removes that double-count.</p></div>"""

    foot_figures = (
        f"The published tunnel total is {s['published_tunnel_km']}&nbsp;km and the official "
        f"road total {s['official_road_km']}&nbsp;km; both are sourced."
        if has_denom else
        "No published tunnel total exists for this place, so no percentage is given — "
        "see the first panel."
    )
    notes = "".join(f"<li>{html.escape(n)}</li>" for n in s.get("notes", []))
    notes_card = f'<div class="card"><h2>Recorded</h2><ul>{notes}</ul></div>' if notes else ""

    return _write(out_path, f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — {html.escape(s.get('place_name','')) } in OpenStreetMap</title>
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
<p class="sub">{html.escape(s.get('blurb') or '')}</p>
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
    {gap_card}
    {compare_card}
    <div class="card"><h2>Longest mapped tunnels</h2><table>{rows}</table></div>
    <div class="card"><h2>Where the underground surfaces</h2><ul>{ev}</ul></div>
    {notes_card}
    <div class="card"><h2>Network by class</h2><table>{cls}</table></div>
  </div>
</div>
<p class="foot">Geometry © OpenStreetMap contributors (ODbL), measured from a locally hosted
extract. Lengths are geodesic. {foot_figures} Every historical claim on this page is cited in
<code>docs/sources.md</code>. Generated by <code>fwh_gibraltar</code>.</p>
</div></body></html>""")


def _write(out_path: str, doc: str) -> str:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc, encoding="utf-8")
    return str(p)


def write_stats(survey: dict, out_path: str) -> str:
    return _write(out_path, json.dumps(survey, indent=2))
