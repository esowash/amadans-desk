# Stocker — a Conan Exiles Enhanced mod

A quality-of-life mod for **Conan Exiles Enhanced** (Unreal Engine 5.6.1). **Stocker**
gives you a follower thrall — **"Amadan Cnoic"** — who, *while you are at your base*,
quietly skims **excess crafting materials out of your crafting benches** and files them
into storage that already holds that item type. Enroll a bench once, set your "keep"
levels, and never hand-sort overflow again. Amadan subclasses the base **Bearer thrall**, so
he keeps full carry + follow behavior.

> **Naming.** The **mod** is **Stocker** (`Mods/Stocker/`). The follower thrall inside it is
> **"Amadan Cnoic"** and his bench is **"Amadan's Desk"** (names finalized 2026-07-13). Read
> "Amadan" below as the *thrall*, not the mod.

> **Concept history.** Stocker began (2026-07-08) as a Copper Golem–inspired *container
> sorter*, but that mod already ships polished on the Workshop (**The Porter**), so on
> **2026-07-09** it was reworked into the bench **reclaimer** described above.
> [`docs/design.md`](docs/design.md) is the authoritative design record.

## Status

**Pre-production complete; P1 build in progress.** The Dev Kit toolchain is proven end to
end — a throwaway mod (`ZZTest`) was cooked, paked, and published Hidden to the Steam
Workshop (file id `3761708831`) on 2026-07-10. **P1 (reclaim logic)** is now under active
authoring via the `ccmod` companion tool: source-chest selection is solved; the current
open problem is getting the item **transfer** to persist. See the **▶ RESUME HERE** block
in [`docs/local-test-loop.md`](docs/local-test-loop.md) for live state.

## How it works (design summary)

- **Ambient, while-present.** Conan does no offline processing — an unloaded base freezes,
  benches included — so Stocker is a helper that runs *while you play at base*, not remote
  automation. On return from an adventure, the Desk clears the backlog as you settle in.
- **Opt-in twice, explicitly.** Nothing moves until you both (1) **enroll a bench** and
  (2) **set a "keep" rule** for an item on it. *Keep 200* skims that item down to 200;
  *Keep 0* takes all of it; unlisted items are left alone. A **pause** toggle suspends an
  enrolled bench without wiping its rules.
- **House rules live on Amadan's Desk.** A craftable placeable of ours holds the manifest
  (`Map<BenchUUID → KeepRules>`), keyed by each bench's persistence id — not on the bench
  itself. The Desk subclasses `BP_PL_Crafting_Station` for its inventory UI.
- **Safety rules:** never touch fuel; skip a bench with an active craft queue; don't fight
  the player (skip a bench whose UI is open, plus a ~300 s grace after close); only deposit
  into storage that already holds ≥1 of that item type.
- **Touches no base asset.** The whole mod is pure "insert" — new placeable, recipe, and
  feat merged as data-table rows via the Mod Controller; no base Blueprint overridden and
  no existing data-table row contested, so it conflicts with no other mod.

## Phased build plan

Supersedes the original sorter phasing. Each phase leaves a working, testable mod.

1. **P1 — Reclaim logic** (instant transfer as a test harness): the keep-manifest + the
   four safety rules + deposit-to-matching-storage, on a stationary bench. Provable with
   no AI/pathing.
2. **P2 — Amadan thrall + gate:** subclass Bearer → Amadan; the reclaimer QoL unlocks only once
   you've acquired him (a soft gate that keeps an "Amadan" in your world).
3. **P3 — Cosmetic patrol** (immersion polish): Amadan walks a loop past enrolled benches
   and storage for flavor; the reclaim itself runs on the Desk's timer (P1), not triggered
   by his movement. *(Simplified 2026-07-13 — see [`docs/design.md`](docs/design.md).)*

## Design references

Two existing Workshop mods are study targets — we learn from them, we do not copy assets:

- **Organizer Sorting Chest** — the item-match + deposit rule (file into a container that
  already holds ≥1 of that type). Our **deposit stage**.
  <https://steamcommunity.com/sharedfiles/filedetails/?id=3723101055>
- **Living Settlements** / the base settlement work-AI — `EQS_Work_<Profession>` paths
  thralls to crafting benches by profession. Our **patrol** foundation (P3): repoint "walk
  to your work bench" into "walk to a bench with overflow and skim it."

## Hard constraint

The Conan Exiles Dev Kit is **Blueprint-only — no C++ code changes**. Every mechanic is
built from Conan's existing Blueprint framework; confirm feasibility in the Dev Kit before
committing to a phase.

## Development environment

See [`docs/dev-environment.md`](docs/dev-environment.md). Editing and building happen on
the **build box** (RTX 4060 Ti 16 GB / i7-12700K / 32 GB / Win11) via the UE 5.6.1 Dev
Kit. A secondary machine handles version control and orchestration. The
[`ccmod`](docs/blueprint-authoring.md) companion tool authors Blueprint graphs as T3D
through the clipboard.

## Repo layout

- `Mods/Stocker/` — the mod's UE content (assets land here; binary `.uasset`/`.umap`
  tracked via Git LFS).
- `docs/` — design record, environment runbook, build/test loop, and references.
- `.ccmod/` — the mod's `ccmod` **workspace** brick library and authored T3D graphs
  (Stocker-specific bricks live here, never in the shared `claude-conan-modder` library).
