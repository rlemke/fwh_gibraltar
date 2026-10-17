# fwh_gibraltar — Measuring what OpenStreetMap cannot see

Two territories whose underground is far larger than their surface, and which
differ in the one way that decides what a measurement is allowed to say.

| | Gibraltar | Jersey |
|---|---|---|
| area | 6.7 km² | 118.2 km² |
| tunnels, **published** | **55 km** | **no total exists** |
| tunnels, in OSM | 6.06 km | 1.97 km (1.47 km of distinct bore) |
| what can be said | OSM holds **11%** | **nothing can be said** — see below |

Gibraltar is the rare place where OSM's *omission* is bounded: the true length
is published, so the gap can be measured rather than guessed at. Jersey is the
rarer one, where the omission cannot even be sized — the German occupation
destroyed the records before the 1945 surrender, so not even the **number** of
tunnel complexes is known.

```bash
fw ffl run src/gibraltar/ffl/gibraltar.ffl --workflow gibraltar.HollowMountain
fw ffl run src/gibraltar/ffl/gibraltar.ffl --workflow gibraltar.OccupiedIsland
# or, without a runner:
src/gibraltar/tools/survey-gibraltar.sh --place jersey -o out/
```

---

## Gibraltar — *The Hollow Mountain*

| | |
|---|---|
| tunnels, published | **55.00 km** |
| tunnels, in OSM | **6.06 km** |
| **mapped** | **11.0%** |
| not in OSM | 48.90 km |
| public road, official | 29.00 km |
| public road, in OSM | 57.21 km (**1.97×**) |
| mapped tunnel ways | 82 of 2,167 highway ways |
| surface evidence | 84 forts · 28 cave entrances · 27 bunkers |

Figures from the 2026-09-30 extract. An earlier version of this page reported
65.66 km of road (2.26×) and 6.63 km of tunnel from an extract that reached
beyond the territory; the survey counts every way in the extract it is given,
so the extract must be cut to Gibraltar's boundary (clipping today's to the
admin_level=2 land polygon changes nothing).

Longest mapped tunnels: **Kingsway Tunnel (5 ways, 1,037 m combined)**,
Admiralty tunnel 957 m, Dudley Ward Way 693 m, Ragged Staff Magazine 659 m,
Keightley Way 405 m.

### Two gaps, in opposite directions

OSM is *both* far short and far over, and neither is sloppiness — both are
definitional.

- **Tunnels: OSM has 11%.** The missing 49 km is classified, sealed, or both.
- **Roads: OSM has 1.97× the official figure.** Gibraltar's published road
  network is 29 km; OSM maps 57.21 km of public road, and 121.05 km if you count
  service ways. OSM counts both carriageways, estate access and car parks; a
  national road statistic does not.

The second gap explains a claim that would otherwise look wrong. Wikipedia says
the tunnels are *"nearly twice the length of its entire road network"*: 55 ÷ 29 =
**1.90**, so it holds against the official statistic — and fails against OSM,
where the same ratio is 0.84. Same territory, same tunnels, different
denominator.

### Why the gap cannot be closed, and why that is the point

**Operation Tracer.** In 1941–42 a chamber roughly 45 × 16 × 8 feet was cut into
the Rock against the German plan to take Gibraltar. Six volunteers — a leader,
two physicians, three wireless operators — were to be **sealed inside** and
observe the Strait if the Rock fell. It remained a rumour for fifty years: the
[Stay Behind Cave](https://www.ministryforheritage.gi/heritage-and-antiquities/stay-behind-cave-complex-1072)
was found by the Gibraltar Caving Group in **1997**, confirmed by one of its
builders in 1998 and later by the last surviving team member, who died in 2010.

A chamber that took half a century to find, in a territory of 6.7 km², is why 48
km of tunnel is absent from a public map — and why that absence is a finding
rather than a defect.

---

## Jersey — *The Island With No Denominator*

Building the second map is where the method broke, usefully.

Jersey should have been Gibraltar again: an occupied island, tunnelled through
by an army, mapped by volunteers. But Gibraltar's headline needs a published
total to divide by, and **Jersey has none**. The
[Wikipedia article on the Hohlgangsanlage tunnels](https://en.wikipedia.org/wiki/Hohlgangsanlage_tunnels,_Jersey)
says why:

> In all, 19–25 storage tunnels were planned but, due to the almost wholesale
> destruction of primary source material before the surrender, the exact number
> is unknown.

Not the length — the **number**. So this survey returns `None`, and the page
says "unknown". Printing 0%, or dividing by a plausible-looking estimate, would
convert *nobody knows* into a measurement, and the difference between "unmapped"
and "unknowable" is the only thing Jersey has to say that Gibraltar doesn't.

That constraint reaches into the type signature: `mapped_pct` is **not** a return
of the `Survey` facet. A field that cannot exist for some inputs has no business
in a signature that promises it for all of them, so callers get
`has_denominator` and a `summary` sentence instead of a number with a hole in it.

### What is mapped instead

| | |
|---|---|
| tunnel ways, in OSM | **1.97 km** |
| less shared bores | **1.47 km** |
| of which Ho8 | **522 m** |
| bunkers, in OSM | **397** |
| road, in OSM | 946.51 km |
| tunnel per km² | 0.017 (Gibraltar: 0.90) |

**The surface is mapped exhaustively and the underground barely at all.** OSM
holds 325 `military=bunker`, 59 `building=bunker` and 13 `historic=bunker`,
many carrying their German designations — *"631 bunker"*, *"634 bunker -
6-Sch. Mach.Gun"*, *"606 bunker: searchlight"*. Everything you can stand next
to has been recorded. Almost nothing that runs *between* them has.

One complex accounts for a third of the island's mapped tunnel: **Ho8**, the
German Underground Hospital, of which OSM has 522 m of passage. Over **1,000 m**
was excavated there, 33.5 m below the surface, intended for 500 wounded — and it
was one of 19–25 planned, of which only **Ho5** was ever finished. Dug by
Organisation Todt and fortress construction battalions using forced labourers
from North Africa, Russia, Spain and Ukraine.

### A double-count worth recording

Jersey's 1.97 km counts **Route du Fort three times**: a 250.2 m trunk
carriageway plus a 250.4 m footway for each pavement, all through one ~250 m
bore. The survey reports the correction separately (`tunnel_km_distinct`) rather
than silently subtracting it — way length is the reproducible measurement, the
correction is an estimate.

The rule is deliberately narrow: same name, one road-class way, one path-class
way within 15% of its length. A general bbox-overlap heuristic would have
collapsed **Ho8's eight footway tunnels** into a single passage and destroyed
real length; requiring a road in the group means it never fires there. Both
behaviours are pinned by tests.

---

## The maps

Grey is mapped road, red is mapped tunnel, and the dots are where the
underground reaches daylight — cave entrances, bunkers, batteries. On Gibraltar
the red is what 11% looks like. On Jersey the purple is what an exhaustively
mapped surface looks like over an unmapped, unmeasurable underneath.

The canvas follows the data: Gibraltar is 1.5 × 5 km and renders portrait,
Jersey 14 × 8 km and renders landscape.

### Three backgrounds, and only one of them costs a request

**Dark** (default) and **light** are pure CSS over the same inline SVG — no CDN,
no external stylesheet, no JavaScript library. The page opens, renders and reads
with **no network at all**, which matters more than usual here: a map whose
subject is an *absence* should not need someone else's data to be legible.

**Street map** is the one concession, so it is opt-in. Every tile carries
`data-src`, never `src`, and nothing is requested until a reader clicks that
mode. A saved preference restores light but never streets, so a return visit
cannot fetch tiles unasked. In that mode the basemap draws the roads, so ours
drop to 12% opacity and the tunnels take a white casing — the tiles are the
context, the tunnels stay the subject.

That mode is why the projection is **Web Mercator**. It replaced a local
equirectangular projection, which was fine on its own but would have slid the
geometry against the tiles beneath it — a tunnel no longer meeting its portal is
exactly the error a reader notices. A test pins every point to land inside its
own tile at the fraction across it the slippy-map maths predicts (worst
observed error: 1e-15).

Basemap tiles come from openstreetmap.org and are attributed on the page.

## How it runs

Two facets, `gibraltar.Survey` → `gibraltar.RenderMap`, chained by
`TunnelSurvey(place=…)`; `HollowMountain` and `OccupiedIsland` are the two
named entry points. The survey reads a small extract from **this deployment's
own planet split** (`FW_OSM_LOCAL_EXTRACTS`) — 0.8 MB for Gibraltar, 2.3 MB for
Jersey — so there is no Overpass call, no rate limit and no network at
measurement time. Both verified end to end through the runtime.

Lengths are geodesic (`pyproj.Geod`). Gibraltar sits at 36°N, where a degree of
longitude is 0.81 of one at the equator; planar arithmetic would inflate
east-west lengths by about 24%.

**A measurement mistake worth recording**, because it nearly became the
headline: the first Gibraltar pass measured `w/highway` as one number and got
**207.69 km**. On a rock climbed by the Mediterranean Steps, footways, steps and
paths are 66 km of that. Comparing it to a published *road* figure would have
overstated the network sevenfold. Hence the classification, and a test that pins
it. The Route du Fort double-count above is the same error in miniature, caught
the same way.

Adding a place means publishing its ground truth in
[`docs/sources.md`](docs/sources.md) and adding an entry to
`_gibraltar_tools/places.py`. A place with no sourced figures cannot produce a
result — except in Jersey's sense, where the absence is sourced too.

## Tests

```bash
FW_OSM_LOCAL_EXTRACTS=/path/to/extracts python -m pytest tests -q   # 19 tests
```

The classification, the geodesic assumption, the pavement rule, the escaping,
the tile alignment, the fact that **nothing is fetched on load**, and above all
**the refusal to invent a denominator** are pinned. Tests needing a real extract skip themselves without one.

## Licence

Apache-2.0. Map data © OpenStreetMap contributors, ODbL.
