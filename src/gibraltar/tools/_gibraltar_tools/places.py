# SPDX-License-Identifier: Apache-2.0
"""The places this survey can measure, and what is published about each.

The method is a comparison against published ground truth, so the registry is
the part that decides what a result can even say. Two places, and they differ in
the way that matters most:

**Gibraltar has a denominator.** ~55 km of tunnel is published, so "OSM holds
12% of it" is a computable statement.

**Jersey does not.** The Germans destroyed the primary records before the May
1945 surrender, so not even the *number* of tunnel complexes is known — Wikipedia
gives "19–25 storage tunnels were planned but, due to the almost wholesale
destruction of primary source material before the surrender, the exact number is
unknown." No total length has ever been published.

That is not a gap in the research; it is the finding. A percentage would require
inventing the denominator, so for Jersey this module reports ``None`` and the
renderer says so rather than quietly picking a number. An unknown ground truth is
a different epistemic situation from a known-but-unmapped one, and the output
should not flatten them together.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Place:
    key: str
    name: str
    title: str
    area_km2: float
    #: Published total tunnel length in km, or None when no total exists.
    tunnel_km_published: float | None
    #: Official public-road length in km, for the second comparison.
    road_km_official: float | None
    blurb: str
    #: Shown beside the numbers; each claim here is cited in docs/sources.md.
    notes: list[str] = field(default_factory=list)

    @property
    def has_denominator(self) -> bool:
        return self.tunnel_km_published is not None


PLACES: dict[str, Place] = {
    "gibraltar": Place(
        key="gibraltar",
        name="Gibraltar",
        title="The Hollow Mountain",
        area_km2=6.7,
        tunnel_km_published=55.0,
        road_km_official=29.0,
        blurb=(
            "Gibraltar holds about 55 km of tunnels inside a 6.7 km² rock, cut "
            "between 1782 and 1967. Almost all of it is military and sealed. "
            "This is what OpenStreetMap knows about it — and what it does not."
        ),
        notes=[
            "Tunnelling ran 1782–99, 1933–38, 1939–45 and 1956–68.",
            "Excavation peaked in 1942 at over 35,000 cubic yards; the spoil "
            "extended the airfield.",
            "The Stay Behind Cave, cut in 1941–42 for six men to be sealed "
            "inside, stayed a rumour until 1997.",
        ],
    ),
    "jersey": Place(
        key="jersey",
        name="Jersey",
        title="The Island With No Denominator",
        area_km2=118.2,
        # No total was ever published — see the module docstring. This is the
        # point of the Jersey map, not a missing constant.
        tunnel_km_published=None,
        road_km_official=None,
        blurb=(
            "Between 1941 and May 1945 the German occupation drove tunnel "
            "complexes into Jersey with forced labour. Nobody knows how much. "
            "The records were destroyed before the surrender, so unlike "
            "Gibraltar there is no total to measure OpenStreetMap against."
        ),
        notes=[
            "19–25 storage tunnels were planned; the exact number is unknown "
            "because primary sources were destroyed before the surrender.",
            "Only one complex, Ho5, was ever completed.",
            "Ho8 alone — later the German Underground Hospital — had over "
            "1,000 m excavated, 33.5 m below the surface, for 500 wounded.",
            "Dug by Organisation Todt, fortress construction battalions and a "
            "specialist mining battalion, using forced labourers from North "
            "Africa, Russia, Spain and Ukraine.",
        ],
    ),
}


def get(key: str) -> Place:
    try:
        return PLACES[key.strip().lower()]
    except KeyError:
        raise KeyError(
            f"unknown place {key!r}. Known: {', '.join(sorted(PLACES))}. "
            "Adding one means publishing its ground truth in docs/sources.md — "
            "the survey is a comparison, so a place without sourced figures "
            "cannot produce a result."
        ) from None
