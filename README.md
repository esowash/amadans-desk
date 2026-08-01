# Amadan's Desk

A quality-of-life mod for **Conan Exiles Enhanced** (Unreal Engine 5.6.1, DevKit 1.3.2).

Amadan's Desk is a placeable crafting-bench "strategy table" that quietly skims excess
crafting materials out of your other benches and files them into nearby storage that
already holds that item type. Set a house rule — furnaces always keep 500 coal, the
blacksmith bench keeps 200 Star Metal for repairs, etc. — and never hand-sort overflow
again. It's designed to be compatible with other crafting-table mods, because all the
rules live on the Desk itself, not on the benches it tidies.

A companion notebook placeable grants the Feat that unlocks it —
read it once and Amadan's Desk becomes craftable.

## Current status

**The sweep engine, house-rules UI, notebook, and persistence are all built and
playtest-confirmed working.** You can enroll benches, set/edit/delete keep rules
(including "keep all"), search items by name with live type-ahead, and the whole rule
set survives a server restart.

**Amadan himself now works too, as of 2026-08-01.** He was the long-standing open bug on
this repo — a fixed, decorative NPC who spawned successfully but never rendered:
invisible, no nameplate, no animation instance, despite being a real registered character
by every check available. He now renders with the correct body, clothing and weapon, holds
his idle pose, and registers properly in the world.

The cause was architectural rather than a misconfiguration, which is why it survived so
many attempts: **Conan doesn't spawn world NPCs by calling a spawn function on an actor.**
It uses a three-actor system — a camp owner, a manual spawn point, and a territory spawner
— wired together by array membership, and every earlier attempt bypassed it and called the
underlying spawn pipeline directly. Standing that system up at runtime fixed it on the
first playtest.

Two things made it findable, and both are written up here in case they help anyone else
working against this DevKit:

- **[`docs/CAMP-SPAWNER-SYSTEM.md`](docs/CAMP-SPAWNER-SYSTEM.md)** — the camp/NPC-spawner
  system traced end to end from real base-game graphs, including the spawn-point cache and
  its ordering constraint, and the non-obvious detail that a territory spawner's `Color`
  property *selects a code path* rather than being a cosmetic label.
- **[`docs/AMADAN-BUG.md`](docs/AMADAN-BUG.md)** — kept as the record of what was tried and
  ruled out over four sessions. It's no longer a help request, but the reasoning is what
  eventually pointed at the camp system.

Remaining known gap: dyes on his gear don't apply, because `EquipmentTemplateDataTable`
has no dye/colour field at all — an equipment template can say *which* items an NPC wears,
never what colour they are.

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
- [`docs/CAMP-SPAWNER-SYSTEM.md`](docs/CAMP-SPAWNER-SYSTEM.md) — how Conan actually spawns
  world NPCs (the camp / manual spawn point / territory spawner trio), traced from real
  base-game graphs. Read this before touching NPC spawning in a Conan mod.
- [`docs/AMADAN-BUG.md`](docs/AMADAN-BUG.md) — the NPC-spawn/appearance bug, now solved.
  Kept as a record of what was tried and ruled out.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — what shipped, and what's queued next.

## License / use

Source assets and scripts here are shared for collaboration on this specific mod. The
mod itself targets Conan Exiles Enhanced (Funcom) and depends on base-game content
referenced by path, not redistributed here.
