# Historical docs — the pre-Desk era

These documents are the development record from **before this repo existed**. They come from
the project's original private repo, which ran from 2026-07-08 through session 14 on
2026-07-21. `amadans-desk` was created on 2026-07-25 as the public snapshot of the finished
MVP, and development continued here.

**They are preserved for context, not as current guidance.** Read them for *why* decisions
were made and what was already ruled out — not for what to do next. For current state see the
top-level [`README.md`](../../README.md); for what's next see [`ROADMAP.md`](../ROADMAP.md).

## Where the mod actually came from

Worth knowing before reading `design.md`, because the early pages describe a different mod.

The project started as an item-sorting follower — a Conan take on Minecraft's copper golem,
pulling items from a source chest and filing them into storage that already held that item
type. That concept was **abandoned once it became clear a Workshop mod already did it well.**

The pivot is what produced Amadan's Desk: the interesting problem wasn't a walking sorter, it
was *overflow* — crafting benches silently accumulating materials you have to hand-sort. So
the centre of gravity moved from the follower to the **bench**, and the mod became a
house-rules reclaimer: opt in a bench, set a keep-count per item, and let excess file itself
into nearby storage that already holds it.

The NPC survived the pivot in a reduced, deliberate role — **Amadan Cnoic** is a narrative
gate, not a mechanism. You acquire him to unlock the Desk; the Desk does the work on a timer.
That's why the shipped mod's sweep engine has nothing to do with the NPC, and why him not
rendering (see [`AMADAN-BUG.md`](../AMADAN-BUG.md)) doesn't stop the mod working.

## What's here, and how stale each one is

| Doc | Status |
|---|---|
| `design.md` | The design's full evolution, including the copper-golem origin, the pivot above, and the reasoning behind the bench-is-the-prop decision. Largely realised in the shipped mod. |
| `local-test-loop.md` | Build → copy `.pak` → `modlist.txt` → read `LogBlueprintUserMessages`. **Still accurate and still useful.** |
| `blueprint-authoring.md` | Early T3D/clipboard authoring notes. Superseded by [`TECHNICAL-NOTES.md`](../TECHNICAL-NOTES.md), which is more complete and more correct. |
| `dev-environment.md` | DevKit install, the ModPak "code 28" fix, the build pipeline. Machine-specific to the original dev box. |
| `phase3-ai-inspection.md` | Early feasibility inspection of Conan's crafting-station and thrall assets. |
| `original-repo-README.md` | The predecessor repo's README as it stood at the end. |

Note that these docs call the mod **`Stocker`** throughout — that was its working name before
it became Amadan's Desk. The DevKit mod folder in this repo is named `Menu`, which was in turn
a throwaway test-mod name that stuck. All three names refer to the same mod.

## `session-handoffs/`

Per-session "read this first" notes, each written to hand off to the next session. **All of
them are superseded.** The most useful one historically is `next-session-menu-pivot.md`
(session 14) — it records the decision to stop debugging the `ActivateModule` /
`DT_UIModuleTable` registration problem and move the mod's logic into the working `Menu` mod
instead. That second pivot is what produced this repo.

Note that these handoffs describe planned work in the future tense that has **since been
completed** — the transplant, the house-rules UI, the item type-ahead, and persistence all
shipped in the MVP. Don't mistake their to-do lists for open work.

## The one thread deliberately left parked

Session 14 never cleanly isolated `bRequiresLoadOnStartup` (`true` on the old Stocker mod,
`false` on Menu) as a possible cause of the registration failure — every earlier test of it was
confounded by other differences that were later eliminated. The decision was to stop chasing it
and stay pivoted to Menu. It is **parked on purpose, not forgotten.**
