# Sources

Every published figure this project compares OSM against, and where it comes
from. The whole result is a comparison, so a wrong number here is a wrong
result — each entry says exactly what it supports.

Two places, and they are not symmetrical. **Gibraltar has a published tunnel
total**, so the omission can be stated as a percentage. **Jersey does not** —
and the reason it does not is itself sourced below, because that absence is the
Jersey map's entire subject.

Links were retrieved 2026-08-19 (Gibraltar) and 2026-08-20 (Jersey).

---

# Gibraltar

## The tunnel total — 55 km / 34 miles

| | |
|---|---|
| used for | `TUNNEL_KM_PUBLISHED = 55.0`, the denominator of the 12% figure |
| source | [Tunnels of Gibraltar — Wikipedia](https://en.wikipedia.org/wiki/Tunnels_of_Gibraltar) |
| quote | "Gibraltar has around 34 miles (55 km) of tunnels" within an area of only 2.6 square miles |

Corroborated by [War History Online](https://www.warhistoryonline.com/world-war-ii/rock-of-gibraltar-tunnels.html)
and [gibraltar.com's WWII tunnels page](https://gibraltar.com/en/travel/see-and-do/history-and-heritage/world-war-2-tunnels.php),
which give 34 miles / ~52 km. **Sources disagree between 52 and 55 km**; this
project uses 55 and the difference (~5%) is smaller than the gap being reported,
so it does not change the conclusion.

## The road total — 29 km / 18 miles

| | |
|---|---|
| used for | `ROAD_KM_OFFICIAL = 29.0`, and the claim that OSM holds 2.26× it |
| figure | 29 km (18 mi) of roads, as of 2007 — the smallest road network on the continent |

This is the number the well-known comparison rests on. Wikipedia states the
tunnels are *"nearly twice the length of its entire road network"*, and 55 ÷ 29 =
**1.90**, so the claim is consistent with the official statistic. It is **not**
consistent with OSM, which maps 65.66 km of public road (and 140.91 km including
service ways) — see the README for why both are correct.

## The tunnelling itself

- **[Great Siege Tunnels — Wikipedia](https://en.wikipedia.org/wiki/Great_Siege_Tunnels)** ·
  [Visit Gibraltar (official tourist board)](https://www.visitgibraltar.gi/see-and-do/the-great-siege-tunnels) —
  the 1782–99 galleries, hand-cut during the Great Siege; roughly 300 m of gun
  galleries, a tiny fraction of the modern system.
- **[Tunnels of Gibraltar — Wikipedia](https://en.wikipedia.org/wiki/Tunnels_of_Gibraltar)** —
  the four periods: **1782–99**, **1933–38**, **1939–45** (the intensive phase),
  **1956–68**. Named complexes: Great North Road, Foss Way, Molesend Way (the
  final tunnel, completed 1967), Admiralty Tunnel, Keightley Way, Dudley Ward
  Way, AROW Street, Fordham's Accommodation, Williams Way.
- Royal Engineers tunnelling companies, with a large Canadian contribution, dug
  night and day; excavation **peaked in 1942 at over 35,000 cubic yards**, and
  the spoil was used to extend the airfield
  ([War History Online](https://www.warhistoryonline.com/world-war-ii/rock-of-gibraltar-tunnels.html)).
  The runway that now crosses Winston Churchill Avenue is, in part, the inside
  of the Rock.

## Operation Tracer and the Stay Behind Cave

The clearest illustration of why the gap cannot be closed from OSM.

- **[Stay Behind Cave complex — Gibraltar Ministry for Heritage](https://www.ministryforheritage.gi/heritage-and-antiquities/stay-behind-cave-complex-1072)** (official)
- **[Operation Tracer — Wikipedia](https://en.wikipedia.org/wiki/Operation_Tracer)**
- [Atlas Obscura](https://www.atlasobscura.com/places/secret-chamber-in-rock-of-gibraltar) ·
  [War History Online](https://www.warhistoryonline.com/world-war-ii/operation-tracer.html)

Built 1941–42 against the German plan to take Gibraltar (*Operation Felix*), the
chamber measured about 45 × 16 × 8 feet. Six volunteers — a leader, two
physicians and three wireless operators — were to be **sealed inside** and
observe the Strait if the Rock fell. It stayed a rumour for fifty years: the
chambers were found by the **Gibraltar Caving Group in 1997**, confirmed by one
of the builders in 1998 and later by the last surviving member of the team, a
physician who died in 2010.

A chamber that took half a century to find, in a territory 6.7 km² in size, is
the reason 48 km of tunnel is missing from a public map — and the reason that
absence is the finding rather than a defect.

## The map data

OpenStreetMap contributors, ODbL. Read from a **locally hosted extract**
(`europe/gibraltar-latest.osm.pbf`, 1 MB) produced by this deployment's own
planet split — no Overpass call, no rate limit, no upstream dependency at
measurement time.

---

# Jersey

## The missing total — why there is no percentage

| | |
|---|---|
| used for | `tunnel_km_published = None`, and the refusal to print a percentage |
| source | [Hohlgangsanlage tunnels, Jersey — Wikipedia](https://en.wikipedia.org/wiki/Hohlgangsanlage_tunnels,_Jersey) |
| quote | "In all, 19–25 storage tunnels were planned but, due to the almost wholesale destruction of primary source material before the surrender, the exact number is unknown" |

That sentence is the finding. No source consulted gives a combined length for
Jersey's tunnels, and none gives per-site lengths except in passing (Ho12: "only
about 60 yards of rubble had been excavated"). A percentage would require
choosing a denominator that nobody has published, so the survey reports `None`
and the page says "unknown".

This is a different situation from Gibraltar's, where the ground truth is known
and the map is merely short of it. Here the size of the gap is not
merely unmeasured but **unrecoverable**, because the records were destroyed on
purpose in 1945.

## The tunnels themselves

- **[Hohlgangsanlage tunnels, Jersey — Wikipedia](https://en.wikipedia.org/wiki/Hohlgangsanlage_tunnels,_Jersey)**
  — *Hohlgangsanlage* ("cave passage installation"), abbreviated **Ho** and
  numbered Ho1 upward. Construction began in 1941 following Hitler's October
  1941 order to fortify the Channel Islands, and stopped at the surrender on
  **9 May 1945**. Only **Ho5** was ever completed.
- **Ho8**, later the **German Underground Hospital** (today Jersey War
  Tunnels) — over **1,000 m (1,100 yd)** excavated, **33.5 m** below the
  surface, intended for **500** wounded. This is the one complex OSM holds in
  any detail, and it accounts for roughly a third of the island's mapped tunnel.
- Dug by fortress construction battalions, a specialist mining company
  (4/Gesteinsbohr-Kompanie of Bataillon 77), the Reichsarbeitsdienst and
  **Organisation Todt**, using **forced labourers** — French North Africans,
  Russians, Spaniards and Ukrainians. Around **5,000** were involved in the Ho8
  works.

## The occupation and its fortifications

- **[German occupation of the Channel Islands — Wikipedia](https://en.wikipedia.org/wiki/German_occupation_of_the_Channel_Islands)**
  — the only British territory occupied by Nazi Germany, from 1 July 1940 to
  9 May 1945. The islands were fortified far beyond their strategic worth as
  part of the **Atlantic Wall**.
- **[Jersey War Tunnels](https://www.jerseywartunnels.com/)** (the Ho8 site
  museum) and **[Channel Islands Occupation Society (Jersey)](https://www.ciosjersey.org.uk/)**,
  which restores and opens bunkers — the surface fortifications that OSM maps so
  thoroughly.

## The figures used

| | |
|---|---|
| area | 118.2 km² |
| tunnel total | **none published** — see above |
| road total | none used; Jersey's map makes no OSM-vs-official road claim |

Jersey's page deliberately omits the road comparison that Gibraltar's makes. An
official road figure was not established from a source of the same quality, and
a comparison is only worth as much as its denominator.

## The map data

OpenStreetMap contributors, ODbL. Read from a **locally hosted extract**
(`europe/jersey-latest.osm.pbf`, 2.3 MB) produced by this deployment's own
planet split — no Overpass call, no rate limit, no upstream dependency at
measurement time.

The optional street-basemap mode fetches XYZ tiles from
**openstreetmap.org**, attributed on the page per the
[copyright terms](https://www.openstreetmap.org/copyright). Nothing is requested
unless a reader selects that mode; the dark and light backgrounds use no network.

## A measurement caveat, recorded

OSM's 1.97 km of Jersey tunnel way includes **Route du Fort three times**: a
250.2 m trunk carriageway plus a 250.4 m footway for each pavement, all through
one ~250 m bore. The survey reports that separately (`tunnel_km_distinct`,
1.47 km) rather than silently subtracting it, because way length is the
reproducible measurement and the correction is an estimate. Ho8's eight footway
tunnels are **not** treated this way — they are a genuine branching complex with
no road among them.
