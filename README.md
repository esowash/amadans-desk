# Amadan's Desk

A quality-of-life mod for **Conan Exiles Enhanced** (Unreal Engine 5.6.1, DevKit 1.3.2).

Amadan's Desk is a placeable crafting-bench "strategy table" that quietly skims excess
crafting materials out of your other benches and files them into nearby storage that
already holds that item type. Set a house rule — furnaces always keep 500 coal, the
blacksmith bench keeps 200 Star Metal for repairs, etc. — and never hand-sort overflow
again. It's designed to be compatible with other crafting-table mods, because all the
rules live on the Desk itself, not on the benches it tidies.

A companion notebook placeable, found beside the Desk, grants the Feat that unlocks it —
read it once and Amadan's Desk becomes craftable.

## Current status

**The sweep engine, house-rules UI, notebook, and persistence are all built and
playtest-confirmed working.** You can enroll benches, set/edit/delete keep rules
(including "keep all"), search items by name with live type-ahead, and the whole rule
set survives a server restart.

**Amadan himself — the NPC standing by the Desk — does not work yet, and this is the
main thing we'd love help with.** He's meant to be a fixed, decorative NPC (not
capturable, no AI, just standing there for flavor and to gatekeep the Desk narratively),
async-spawned from `Menu_ModController`'s `BeginPlay`/`RunSweep`. He currently fails to
render at all — invisible, no nameplate, no working animation instance — despite
spawning successfully and being a real, named, registered character by every check we've
tried. **See [`docs/AMADAN-BUG.md`](docs/AMADAN-BUG.md) for the full writeup**: exactly
what's been tried, what the real native error messages say, and where the investigation
currently stands. The relevant Blueprint logic (`SpawnAmadan`) was removed from this
build so the rest of the mod ships clean — if you want to pick up the appearance bug,
you're starting from a blank page on that one function specifically, informed by
everything in that doc.

## Repo layout

- **`Mods/Menu/`** — the actual DevKit mod source, structured exactly as the Conan
  Exiles DevKit organizes it. Drop this folder into your own DevKit's `Content/Mods/`
  to open it directly. `Local/` holds all our custom Blueprints, DataTables, structs,
  and widgets (all named `Amadan*`/`Menu_*`/`W_*`/`BP_*`).
- **`.ccmod/graphs/`** — captured Blueprint node graphs in Unreal's clipboard text
  format ("T3D"). These are real, live-pulled captures from the DevKit — proof of what
  each function's wiring actually is, not just source-of-truth prose.
- **`.ccmod/scripts/`** — Python build scripts that assemble and validate those graphs
  programmatically (via a small companion tool, see [`docs/TECHNICAL-NOTES.md`](docs/TECHNICAL-NOTES.md)),
  rather than hand-wiring everything by dragging pins in the DevKit UI.

## Getting oriented

- [`docs/TECHNICAL-NOTES.md`](docs/TECHNICAL-NOTES.md) — how the Blueprint graphs in
  `.ccmod/` were actually built (the clipboard/T3D authoring method), useful context for
  reading or extending anything in `.ccmod/graphs`.
- [`docs/AMADAN-BUG.md`](docs/AMADAN-BUG.md) — the open NPC-spawn/appearance bug, written
  up in detail for anyone who wants to take a swing at it.

## License / use

Source assets and scripts here are shared for collaboration on this specific mod. The
mod itself targets Conan Exiles Enhanced (Funcom) and depends on base-game content
referenced by path, not redistributed here.
