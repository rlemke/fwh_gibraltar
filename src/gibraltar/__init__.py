# SPDX-License-Identifier: Apache-2.0
"""fwh_gibraltar — the Hollow Mountain: measuring what OpenStreetMap cannot see.

Gibraltar holds roughly 55 km of tunnels inside a 6.7 km² rock, cut between 1782
and 1967. Almost all of it is military and sealed, so OSM cannot hold it — and
because the true length is published, the omission can be *measured* instead of
guessed at. Most OSM analysis renders what the map contains; this renders what
it is missing, in the one place where the missing part is bounded and known.
"""

from __future__ import annotations

from pathlib import Path

from facetwork.domains import DomainPackage

from .handlers import register_all_registry_handlers

domain = DomainPackage(
    name="gibraltar",
    ffl_dir=Path(__file__).parent / "ffl",
    register_handlers=register_all_registry_handlers,
)
