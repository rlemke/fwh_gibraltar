# FFL examples — `gibraltar`

Complete, compile-checked scenarios against this domain's own facets. Every
fenced `ffl` block below is meant to compile:

```bash
fw ffl compile --check --primary <block>.ffl \
  --library ~/fw_handlers/fwh_gibraltar/src/gibraltar/ffl/gibraltar.ffl
```

The facets in play:

| Namespace | Facet | Returns |
|---|---|---|
| `gibraltar` | `Survey(place, pbf, out_dir)` | `stats_path, place_name, tunnel_km, tunnel_km_distinct, has_denominator, summary, feature_count, stats, features` |
| `gibraltar` | `RenderMap(stats, features, out_dir, title)` | `map_path, feature_count` |
| `gibraltar` | `TunnelSurvey(place, pbf, out_dir, title)` *(workflow)* | `map_path, stats_path, place_name, summary` |

`place` is `"gibraltar"` or `"jersey"` (the registry in
`_gibraltar_tools/places.py`). With `pbf` empty the extract is resolved from
`FW_OSM_LOCAL_EXTRACTS`. There is deliberately no `mapped_pct` return: Jersey
has no published total, so callers branch on `has_denominator` and read
`summary` instead.

---

## 1. The minimal workflow

Survey one place and return the sentence it supports.

```ffl
namespace ex.minimal {
    use gibraltar

    workflow WhatOsmHolds() => (summary: String) andThen {
        s = Survey(place = "gibraltar")
        yield WhatOsmHolds(summary = s.summary)
    }
}
```

## 2. `$`-scoping — survey, then draw

`$` is the block's immediate container, so `$.place` reads the workflow's
parameter. `RenderMap` takes the geometry `Survey` already returned, so there is
no second pass over the extract — and the reference orders it.

```ffl
namespace ex.scoping {
    use gibraltar

    workflow DrawPlace(
        place: String = "jersey",
        out_dir: String = "jersey-out"
    ) => (map_path: String, distinct_km: Double) andThen {
        s = Survey(place = $.place, out_dir = $.out_dir)
        m = RenderMap(stats = s.stats, features = s.features,
                      out_dir = $.out_dir, title = s.place_name)
        yield DrawPlace(map_path = m.map_path, distinct_km = s.tunnel_km_distinct)
    }
}
```

`tunnel_km_distinct` is the shared-bore correction (Jersey's Route du Fort is
one ~250 m bore mapped as three ways); `tunnel_km` is the raw way length.

## 3. `when` — never invent a denominator

Attach the `when` to the step it gates: inside the cases `$` is that step, so
`$.has_denominator` reads `Survey`'s return.

```ffl
namespace ex.branch {
    use gibraltar

    workflow Headline(place: String) => (headline: String, comparable: Boolean) andThen {
        s = Survey(place = $.place) andThen when {
            case $.has_denominator => {
                yield Headline(headline = $.summary, comparable = true)
            }
            case _ => {
                yield Headline(headline = $.summary, comparable = false)
            }
        }
    }
}
```

## 4. `foreach` — both places, aggregated with `+=`

Loop variables are read as `$.<varname>`. `+=` collects one value per
iteration; a bare `=` would keep only the last place.

```ffl
namespace ex.fanout {
    use gibraltar

    workflow AllPlaces(places: Json) => (summaries: Json)
        andThen foreach p in $.places {
            s = Survey(place = $.p, out_dir = "out/" ++ $.p)
            yield AllPlaces(summaries += s.summary)
        }
}
```

## 5. Reusing the composed workflow

`TunnelSurvey` is itself a workflow, so it can be called as a step — this is
how `HollowMountain` and `OccupiedIsland` are built.

```ffl
namespace ex.compose {
    use gibraltar

    workflow BothMaps() => (gibraltar_map: String, jersey_map: String) andThen {
        g = TunnelSurvey(place = "gibraltar", out_dir = "gibraltar-out")
        j = TunnelSurvey(place = "jersey", out_dir = "jersey-out")
        yield BothMaps(gibraltar_map = g.map_path, jersey_map = j.map_path)
    }
}
```

## 6. `after` — ordering an invisible dependency

`fw.file.MakeDir` returns nothing the survey reads, so the compiler cannot see
that the survey depends on it. State the edge with `after`.

```ffl
namespace ex.after {
    use gibraltar

    workflow SurveyInto(out_dir: String) => (stats_path: String) andThen {
        base = fw.file.MakeDir(path = $.out_dir)
        s    = Survey(place = "gibraltar", out_dir = $.out_dir) after base
        yield SurveyInto(stats_path = s.stats_path)
    }
}
```

## 7. `catch` — degrade instead of failing the run

A missing extract fails `Survey`; report that in words rather than failing the
caller.

```ffl
namespace ex.resilient {
    use gibraltar

    workflow TrySurvey(place: String, pbf: String = "") => (summary: String) andThen {
        s = Survey(place = $.place, pbf = $.pbf) catch {
            yield TrySurvey(summary = "no extract available for this place")
        }
        yield TrySurvey(summary = s.summary)
    }
}
```

---

## Syntax cheat sheet

| Want | Write |
|---|---|
| A workflow's own parameter | `$.param` |
| A previous step's return | `step_name.field` (never a bare `step_name`) |
| A `foreach` loop variable | `$.varname` |
| Order behind a directory/cache write | `step = F(…) after producer` |
| Order behind a value | nothing — the reference already orders it |
| Branch | `step = F(…) andThen when { case cond => { … } case _ => { … } }` |
| Fan out | `andThen foreach x in $.xs { … }` |
| Aggregate a fan-out | `yield F(xs += step.field)` |
| String concatenation | `"out/" ++ $.p` |

Workflows, facets and schemas must live inside a `namespace`. Numeric types are
`Int`, `Long`, `Double`; also `String`, `Boolean`, `Json`.
