# fwh_gibraltar — The Hollow Mountain

**Measuring what OpenStreetMap cannot see.**

Gibraltar holds roughly **55 km of tunnels inside a 6.7 km² rock**, cut between
1782 and 1967. Almost all of it is military and sealed, so a public map cannot
hold it. Because the true length is *published*, the omission can be **measured**
rather than guessed at.

That inverts the usual shape of an OSM project. Every other map in this fleet
renders what OSM contains. This one renders what it is missing — in the one
territory small enough, and documented enough, for the missing part to be
bounded.

```bash
fw ffl run src/gibraltar/ffl/gibraltar.ffl --workflow gibraltar.HollowMountain
# or, without a runner:
tools/survey-gibraltar.sh -o out/
```

## The result

| | |
|---|---|
| tunnels, published | **55.00 km** |
| tunnels, in OSM | **6.63 km** |
| **mapped** | **12.0%** |
| not in OSM | 48.40 km |
| public road, official | 29.00 km |
| public road, in OSM | 65.66 km (**2.26×**) |
| mapped tunnel ways | 107 of 2,565 highway ways |
| surface evidence | 84 forts · 28 cave entrances · 19 bunkers |

Longest mapped tunnels: **Admiralty tunnel 957 m**, Dudley Ward Way 693 m,
Ragged Staff Magazine 659 m, Keightley Way 405 m, Kingsway Tunnel (3 ways,
997 m combined).

## Two gaps, in opposite directions

The interesting part is that OSM is *both* far short and far over, and neither
is sloppiness — both are definitional.

- **Tunnels: OSM has 12%.** The missing 48 km is classified, sealed, or both.
- **Roads: OSM has 2.26× the official figure.** Gibraltar's published road
  network is 29 km; OSM maps 65.66 km of public road, and 140.91 km if you count
  service ways. OSM counts both carriageways, estate access and car parks; a
  national road statistic does not.

The second gap explains a claim that would otherwise look wrong. Wikipedia says
the tunnels are *"nearly twice the length of its entire road network"*: 55 ÷ 29 =
**1.90**, so it holds against the official statistic — and fails against OSM,
where the same ratio is 0.84. Same territory, same tunnels, different
denominator.

**A measurement mistake worth recording**, because it nearly became the headline:
the first pass measured `w/highway` as one number and got **207.69 km**. On a
rock climbed by the Mediterranean Steps, footways, steps and paths are 66 km of
that. Comparing it to a published *road* figure would have overstated the
network sevenfold. Hence the classification, and a test that pins it.

## Why the gap cannot be closed, and why that is the point

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

Full citations, with what each figure supports: **[docs/sources.md](docs/sources.md)**.

## The map

`hollow-mountain.html` is **self-contained** — inline SVG, no CDN, no tile
server, no JavaScript library. That is deliberate: the subject is an *absence*,
and a page that needed someone else's basemap to be legible would be leaning on
external data at the moment it claims a gap. It works offline, forever.

Grey is mapped road, red is mapped tunnel, and the dots are where the
underground reaches daylight — cave entrances, bunkers, batteries. The red is
what 12% looks like.

## How it runs

Two facets, `gibraltar.Survey` → `gibraltar.RenderMap`, chained by
`HollowMountain`. The survey reads a **1 MB extract from this deployment's own
planet split** (`FW_OSM_LOCAL_EXTRACTS`), so there is no Overpass call, no rate
limit and no network at measurement time. Verified end to end through the
runtime: survey 0.2s, render 0.3s, 1,775 features drawn.

Lengths are geodesic (`pyproj.Geod`). Gibraltar sits at 36°N, where a degree of
longitude is 0.81 of one at the equator; planar arithmetic would inflate
east-west lengths by about 24%.

## Tests

```bash
FW_OSM_LOCAL_EXTRACTS=/path/to/extracts python -m pytest tests -q   # 9 tests
```

The classification, the geodesic assumption, the escaping and the
self-containment are pinned. The test that needs a real extract skips itself
without one.

## Licence

Apache-2.0. Map data © OpenStreetMap contributors, ODbL.
