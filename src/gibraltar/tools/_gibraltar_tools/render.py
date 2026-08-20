# SPDX-License-Identifier: Apache-2.0
"""Render the survey as a page that stands on its own data.

No CDN, no external stylesheet, no JavaScript library: the geometry is inline
SVG. That is the county-atlas precedent and it matters more than usual here,
because the point of the map is the *absence* of something — a page that needed
someone else's basemap to make sense would be leaning on external data at the
moment it claims a gap.

Three backgrounds: **dark** (default), **light**, and **street map**. The first
two are pure CSS over the same inline geometry, so the page opens, renders and
reads with no network at all. The third lays XYZ tiles behind the SVG — and is
the one concession, so it is opt-in: every tile carries `data-src`, never `src`,
and nothing is requested until a reader clicks it. A saved preference restores
light but never streets, so a return visit cannot fetch tiles unasked.

The projection is **Web Mercator**, which the tiles require. It replaced a local
equirectangular projection when the basemap was added; over a 5-14 km territory
the two are visually identical, but a mismatch would slide the geometry against
the tiles and stop a tunnel meeting its portal.
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

#: Strokes and fills are CSS variables, not literals, so the dark / light /
#: street palettes reach the geometry itself. A hex here would leave the map
#: unchanged while its chrome switched — the mismatch would look like a bug.
STYLE = {
    "road": ("var(--road)", 0.9),
    "tunnel": ("var(--tunnel)", 2.6),
}
MARKS = {
    "natural=cave_entrance": ("var(--cave)", 3.4, "cave entrance"),
    "military=bunker": ("var(--bunker)", 3.0, "bunker"),
    "historic=fort": ("var(--fort)", 2.6, "fort / battery"),
    "historic=bunker": ("var(--bunker)", 3.0, "bunker"),
    "building=bunker": ("var(--bunker)", 3.0, "bunker"),
}


TOGGLE_SCRIPT = """<script>
// The whole toggle. Dark and light are pure CSS; "streets" additionally
// promotes each tile's data-src to src, ONCE. Until someone asks for it, this
// page has made no network request of any kind — which is the property that
// lets a map about an absence stand on its own data.
(function () {
  var body = document.body, tilesLoaded = false;
  var buttons = [].slice.call(document.querySelectorAll('.modes button'));
  function loadTiles() {
    if (tilesLoaded) return;
    tilesLoaded = true;
    [].forEach.call(document.querySelectorAll('#tiles img[data-src]'), function (img) {
      img.src = img.getAttribute('data-src');
      img.removeAttribute('data-src');
    });
  }
  function set(mode) {
    body.classList.remove('light', 'streets');
    if (mode !== 'dark') body.classList.add(mode);
    if (mode === 'streets') loadTiles();
    buttons.forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.mode === mode));
    });
    try { localStorage.setItem('fwh-gibraltar-mode', mode); } catch (e) {}
  }
  buttons.forEach(function (b) {
    b.addEventListener('click', function () { set(b.dataset.mode); });
  });
  var saved;
  try { saved = localStorage.getItem('fwh-gibraltar-mode'); } catch (e) {}
  // A remembered "streets" would fetch tiles before the reader asked on THIS
  // visit, so a saved preference restores the chrome but not the basemap.
  if (saved === 'light') set('light');
})();
</script>"""


def _merc(lon: float, lat: float) -> tuple[float, float]:
    """Web Mercator, in world units where the whole globe is 0..1.

    This replaced a local equirectangular projection when the street-basemap
    mode was added. The two are visually indistinguishable over a 5-14 km
    territory, but XYZ tiles ARE Web Mercator, so anything else would leave the
    geometry sliding against the tiles under it — the one error a reader would
    actually notice, because a tunnel would stop meeting its portal.
    """
    x = lon / 360.0 + 0.5
    sin = math.sin(math.radians(lat))
    y = 0.5 - math.log((1 + sin) / (1 - sin)) / (4 * math.pi)
    return x, y


def _project(features: list[dict]) -> tuple[Any, int, dict]:
    """Fit the features to the canvas, and describe the tile grid that covers it.

    Returns ``(to_xy, height, tiles)`` where `tiles` carries everything the page
    needs to lay a basemap behind the SVG in the SAME coordinate space.
    """
    xs, ys = [], []
    for f in features:
        g = f.get("geometry") or {}
        cs = g.get("coordinates") or []
        pts = [cs] if g.get("type") == "Point" else cs
        for c in pts:
            x, y = _merc(c[0], c[1])
            xs.append(x); ys.append(y)
    if not xs:
        raise ValueError("nothing to draw")
    mx0, mx1 = min(xs), max(xs)
    my0, my1 = min(ys), max(ys)
    dx = max(mx1 - mx0, 1e-12)
    dy = max(my1 - my0, 1e-12)

    inner = W - 2 * PAD
    H = int(min(H_MAX, max(H_MIN, inner * dy / dx + 2 * PAD)))
    s = min(inner / dx, (H - 2 * PAD) / dy)  # canvas px per world unit
    ox = PAD + (inner - dx * s) / 2
    oy = PAD + ((H - 2 * PAD) - dy * s) / 2

    def to_xy(lon: float, lat: float) -> tuple[float, float]:
        x, y = _merc(lon, lat)
        return (ox + (x - mx0) * s, oy + (y - my0) * s)

    # Pick the zoom whose tiles land nearest their native 256 px, so the
    # basemap is neither blurry nor needlessly heavy.
    z = max(0, min(19, round(math.log2(max(s, 1) / 256.0))))
    n = 2 ** z
    span = s / n  # canvas px per tile at this zoom
    tiles = {
        "z": z,
        "size": round(span, 3),
        "x0": int(mx0 * n), "x1": int(mx1 * n),
        "y0": int(my0 * n), "y1": int(my1 * n),
        "ox": ox, "oy": oy, "mx0": mx0, "my0": my0, "s": s, "n": n,
    }
    return to_xy, H, tiles


def _tile_layer(t: dict, H: int) -> tuple[str, int]:
    """Absolutely-positioned tile <img>s in the SVG's own coordinate space.

    Every tile carries ``data-src``, never ``src``. Nothing is requested until
    the reader chooses the street basemap, so the page still opens, renders and
    reads with no network at all — which is the property the dark and light
    modes are there to keep.

    Positions are percentages so the layer tracks the SVG as it scales to the
    viewport. Horizontal ones resolve against the container's width and
    vertical ones against its HEIGHT, so they are divided by W and H
    respectively — the container is given the viewBox's aspect ratio, which is
    what makes the two agree.
    """
    imgs = []
    for ty in range(t["y0"], t["y1"] + 1):
        for tx in range(t["x0"], t["x1"] + 1):
            left = t["ox"] + (tx / t["n"] - t["mx0"]) * t["s"]
            top = t["oy"] + (ty / t["n"] - t["my0"]) * t["s"]
            imgs.append(
                f'<img alt="" loading="lazy" data-src="https://tile.openstreetmap.org/'
                f'{t["z"]}/{tx}/{ty}.png" style="left:{100 * left / W:.4f}%;'
                f'top:{100 * top / H:.4f}%;width:{100 * t["size"] / W:.4f}%;'
                f'height:{100 * t["size"] / H:.4f}%">')
    return "".join(imgs), len(imgs)


def render(survey: dict, features: list[dict], out_path: str, *, title: str | None = None) -> str:
    title = title or survey.get("title") or "The Hollow Mountain"
    to_xy, H, tiles = _project(features)
    tile_html, tile_count = _tile_layer(tiles, H)
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
                f'fill-opacity="0.85" stroke="var(--mapbg)" stroke-width="0.5">'
                f'<title>{name}</title></circle>')

    # Grouped so the street-basemap mode can dim our roads (the tiles already
    # draw them) without touching the tunnels and marks, which are the subject.
    svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
           f'aria-label="{html.escape(survey.get("place_name", ""))}: mapped roads, mapped '
           f'tunnels, and the surface evidence of what is not mapped">'
           f'<g class="roads">{"".join(layers["road"])}</g>'
           f'<g class="tunnels">{"".join(layers["tunnel"])}</g>'
           f'<g class="marks">{"".join(layers["mark"])}</g>'
           "</svg>")

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
 /* Dark is the default and needs no class, so a reader with JS disabled gets
    the page as designed rather than an unstyled one. */
 :root {{ --bg:#0b0d10; --fg:#e8eaed; --dim:#98a1ab; --line:#20262e; --card:#11151a;
          --mapbg:#0e1216; --bar:#1b2028; --link:#7fb2ff;
          --road:#9aa3ab; --tunnel:#e2492f; --cave:#2f6fe2; --bunker:#7a4fd6; --fort:#c8952a; }}
 body.light {{ --bg:#f7f6f3; --fg:#16191d; --dim:#5c646d; --line:#dcd8d1; --card:#fffefb;
               --mapbg:#fffefb; --bar:#e6e2db; --link:#0b57d0;
               --road:#b3bac1; --tunnel:#c62d12; --cave:#1b4fbf; --bunker:#5b32b8; --fort:#a06f0d; }}
 /* Street mode keeps the light chrome but hands the map itself to the tiles. */
 body.streets {{ --bg:#f7f6f3; --fg:#16191d; --dim:#5c646d; --line:#dcd8d1; --card:#fffefb;
                 --mapbg:#e8e3dc; --bar:#e6e2db; --link:#0b57d0;
                 --road:#9aa3ab; --tunnel:#d61f00; --cave:#123fae; --bunker:#4c22b0; --fort:#8a5d00; }}
 * {{ box-sizing:border-box }}
 body {{ margin:0; background:var(--bg); color:var(--fg);
        font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
 .wrap {{ max-width:1180px; margin:0 auto; padding:28px 20px 64px; }}
 h1 {{ font-size:1.9rem; margin:0 0 .2em; letter-spacing:-.02em }}
 .sub {{ color:var(--dim); margin:0 0 28px; max-width:62ch }}
 .grid {{ display:grid; grid-template-columns:minmax(320px,1fr) minmax(300px,420px); gap:28px; align-items:start }}
 @media (max-width:820px) {{ .grid {{ grid-template-columns:1fr }} }}
 .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px 20px; margin-bottom:18px }}
 .card h2 {{ font-size:.78rem; text-transform:uppercase; letter-spacing:.09em; color:var(--dim);
             margin:0 0 14px; font-weight:600 }}
 .big {{ font-size:2.5rem; font-weight:700; line-height:1; letter-spacing:-.03em }}
 .big small {{ font-size:.95rem; font-weight:400; color:var(--dim); letter-spacing:0 }}
 .bar {{ height:22px; background:var(--bar); border-radius:4px; overflow:hidden; margin:12px 0 6px; position:relative }}
 .bar i {{ display:block; height:100%; background:var(--tunnel) }}
 .barlab {{ display:flex; justify-content:space-between; font-size:.8rem; color:var(--dim) }}
 table {{ width:100%; border-collapse:collapse; font-size:.88rem }}
 td {{ padding:5px 0; border-bottom:1px solid var(--line) }}
 td.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap }}
 td.t {{ text-align:right; color:var(--dim); font-size:.8rem; padding-left:10px; white-space:nowrap }}
 ul {{ margin:0; padding-left:1.1em }} li {{ margin:.25em 0 }}
 .key {{ display:flex; flex-wrap:wrap; gap:14px; font-size:.82rem; color:var(--dim); margin-top:12px }}
 .key i {{ display:inline-block; width:11px; height:11px; border-radius:2px; margin-right:5px; vertical-align:-1px }}
 a {{ color:var(--link) }} .foot {{ color:var(--dim); font-size:.84rem; margin-top:30px; max-width:78ch }}
 .map {{ background:var(--mapbg); border:1px solid var(--line); border-radius:10px; padding:8px }}
 /* The stage carries the viewBox's aspect ratio, which is what lets the tile
    layer's percentage positions agree with the SVG's own coordinates. */
 .stage {{ position:relative; width:100%; aspect-ratio:{W} / {H}; }}
 .stage svg {{ position:absolute; inset:0; width:100%; height:100% }}
 #tiles {{ position:absolute; inset:0; overflow:hidden; border-radius:4px; display:none }}
 #tiles img {{ position:absolute; display:block }}
 body.streets #tiles {{ display:block }}
 /* The basemap already draws the roads, so ours would only muddy it; the
    tunnels get a casing instead, to stay legible over street colours. */
 body.streets .roads {{ opacity:.12 }}
 body.streets .tunnels {{ filter:drop-shadow(0 0 2px #fff) drop-shadow(0 0 1px #fff) }}
 body.streets .marks {{ filter:drop-shadow(0 0 1.5px #fff) }}
 .modes {{ display:flex; gap:2px; margin:0 0 10px; background:var(--bar);
           border-radius:8px; padding:3px; width:fit-content }}
 .modes button {{ font:inherit; font-size:.82rem; color:var(--dim); background:none; border:0;
                  padding:5px 12px; border-radius:6px; cursor:pointer }}
 .modes button[aria-pressed="true"] {{ background:var(--card); color:var(--fg); font-weight:600 }}
 .tileattr {{ display:none; font-size:.74rem; color:var(--dim); padding:6px 10px 0 }}
 body.streets .tileattr {{ display:block }}
</style></head><body><div class="wrap">
<h1>{html.escape(title)}</h1>
<p class="sub">{html.escape(s.get('blurb') or '')}</p>
<div class="grid">
  <div class="map">
    <div class="modes" role="group" aria-label="Background">
      <button type="button" data-mode="dark" aria-pressed="true">Dark</button>
      <button type="button" data-mode="light" aria-pressed="false">Light</button>
      <button type="button" data-mode="streets" aria-pressed="false">Street map</button>
    </div>
    <div class="stage"><div id="tiles">{tile_html}</div>{svg}</div>
    <div class="key" style="padding:6px 10px 2px">
      <span><i style="background:var(--road)"></i>mapped road</span>
      <span><i style="background:var(--tunnel)"></i>mapped tunnel</span>
      <span><i style="background:var(--cave)"></i>cave entrance</span>
      <span><i style="background:var(--bunker)"></i>bunker</span>
      <span><i style="background:var(--fort)"></i>fort / battery</span>
    </div>
    <p class="tileattr">Basemap tiles &copy; <a href="https://www.openstreetmap.org/copyright"
      >OpenStreetMap</a> contributors, served by openstreetmap.org. The dark and light
      modes need no network; only this one fetches anything.</p>
  </div>
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
</div>
{TOGGLE_SCRIPT}
</body></html>""")


def _write(out_path: str, doc: str) -> str:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc, encoding="utf-8")
    return str(p)


def write_stats(survey: dict, out_path: str) -> str:
    return _write(out_path, json.dumps(survey, indent=2))
