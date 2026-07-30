# Roadmap: post-MVP

**Written 2026-07-30 (a planning machine, planning session — no DevKit on this machine, so this is
design and sequencing only, nothing built).**

The MVP shipped and was submitted to the modding contest. The sweep engine, house-rules
UI, notebook/Feat unlock, and persistence are all live and playtest-confirmed. This doc
sequences what comes next.

## Priority call: multi-desk before Amadan

Two open items compete for the next few sessions:

1. **Global state / multi-desk** — the MVP keeps its rules and managed-station arrays on
   `Menu_ModController`, which is a **single instance per server**. Any player with two
   bases and two Desks gets one shared rule set: both Desks show and edit the same rules,
   and the sweep has one anchor. This is a correctness bug that affects real players of a
   published mod.
2. **Amadan doesn't render** (`AMADAN-BUG.md`) — cosmetic and narrative. He's a decorative
   gate-keeping NPC; the mod's actual function doesn't depend on him.

**Multi-desk goes first.** It's player-facing correctness on a shipped mod; the render bug
is polish on a feature that is currently absent rather than broken. `AMADAN-BUG.md` is also
public and written as a help-request, so outside help may arrive on it in parallel at no
cost to this schedule.

---

## The multi-desk problem, stated precisely

`S_KeepRule` is already `{Container (station UniqueID), TemplateID, Keep, KeepAll}` — so
rules are already scoped **per bench** (that was the 3U "ruled anywhere = protected
everywhere" fix). What's missing is scoping **per Desk**. Every Desk reads and writes the
same `KeepRulesV2` array on the one ModController.

### Decision 1: where does per-Desk state actually live?

| | Option A — state on the Desk | Option B — central, keyed by Desk |
|---|---|---|
| Shape | `KeepRulesV2`/`ManagedStations`/`ManagedContainers` become member variables on `BP_PL_Table_Strategy_Amadan` | Arrays stay on `Menu_ModController`; add a `Desk` (UniqueID) field to `S_KeepRule` and filter by it |
| Ownership | Clean — each Desk literally owns its data | Indirect — one array, partitioned by key |
| Persistence risk | **Unproven.** Does Conan's persistence save arbitrary Blueprint variables on a mod's placeable subclass? Never tested in this project. | **Low.** ModController persistence is already proven working in the MVP. |
| Size of change | Larger — moves storage, sweep anchoring, and UI read/write | Smaller — S_KeepRule gains a field; reads gain a filter |

**Do not pick until the persistence question is answered.** It is a small, decisive spike:
add a throwaway variable to the Desk placeable, set it, save/quit/reload, print it. If mod
placeable variables persist, Option A is the better design and is what we want. If they
don't, Option B delivers identical player-visible behaviour on a persistence mechanism
that already works, and is the correct call rather than a compromise.

### Decision 2: overlap — prevent, or resolve?

Two Desks whose sweep ranges overlap could both claim the same bench.

- **Prevent placement** (stated preference): block placing a Desk within ~2× sweep range of
  another. Needs a Conan placement-validation hook — which one is not yet identified.
  **Gap: this cannot fix existing saves.** Anyone who already placed two Desks close
  together under the MVP keeps that state; placement rules only apply at build time.
- **Nearest-Desk-wins** (worth weighing): each bench is owned by whichever Desk is closest.
  Overlap becomes harmless instead of forbidden, no placement hook is needed, and existing
  saves are handled for free.

These aren't exclusive — nearest-wins as the resolution rule, with an optional placement
warning, gets both the clean UX and the robustness. Recommend deciding this before building,
since it determines whether a placement hook needs researching at all.

### Decision 3: migration for existing players

The mod is published. Players have rules stored in the current global array. Moving to
per-Desk scoping needs an explicit answer:

- **Migrate** — on first load after the update, assign all existing rules to the nearest (or
  only) Desk.
- **Reset** — rules are cleared, called out loudly in the release notes.

Either is defensible; silently losing a player's configured house rules without saying so is
not. Decide deliberately.

### Consequence that applies under every option: the UI needs Desk context

`W_AmadanMenu` currently has no idea which Desk opened it. The interact chain is
`BP_PL_Table_Strategy_Amadan::ClientInteractableActivate → GetGUIModuleController →
ActivateModule("W_AmadanMenu")` — no Desk reference is passed.

The fix reuses a pattern already proven in this mod: `AC_Menu::SaveVariableToMC` writes to
the ModController and `W_AmadanMenu::Construct` reads it back directly. So — on interact,
write `Self` into a `ActiveDesk` variable on the ModController *before* calling
`ActivateModule`; the widget reads `ActiveDesk` on `Construct` and scopes everything to it.
This is required under both Option A and Option B.

---

## Session plan

### Session 15 — lock the architecture (spike + decide, build nothing)

- **Spike:** does a Blueprint variable on the Desk placeable survive save/quit/reload?
  Decides Option A vs B and gates everything downstream.
- **Trace:** confirm how the shipped sweep actually anchors. Session 14 designed
  `GatherNearbyBenches(AnchorActor, Range)` with a real `AnchorActor` parameter specifically
  to fix the "single anchor / one base only" limitation — whether that parameterised form
  actually shipped in the MVP or is still hardcoded to one actor is **not determinable from
  the repo alone** and needs a look at the live graphs.
- **Decide:** storage shape, overlap strategy, migration policy.

Exit: architecture locked and written down. No assets touched.

### Session 16 — Desk-scoped data model

- Implement the chosen storage shape.
- Add `ActiveDesk` to the interact → widget path.
- Scope all rule reads/writes to the active Desk.
- **Playtest with ONE desk. Gate: no behavioural regression from the shipped MVP.** This
  matters more than it sounds — the refactor touches proven, working, published code, and
  single-desk parity is the proof it stayed working.

### Session 17 — multi-desk behaviour

- Two Desks, disjoint rule sets, independent sweeps.
- Implement the chosen ownership rule.
- Implement the chosen migration path.
- Playtest: two Desks far apart, then deliberately close together.

### Session 18 — UI refinement + release

- UI refinement pass (the second item on the polish list).
- Version bump + release notes — standing project rule, every build.
- Workshop update.
- **Check first: does updating the Workshop item during contest judging cause a problem?**
  Unknown, and worth confirming before pushing a breaking release.

### Sessions 19+ — the Amadan render bug

Resume `AMADAN-BUG.md`. Suggested ordering, which differs from that doc's own emphasis:

1. **Lead #3 (reparent diagnostic) first** — one property change, zero graph authoring.
   The decisive evidence is that `Recreating Clothing Actors` *never* fires for him, meaning
   some native setup path never runs at all. The parent class (`HumanoidNPCCharacter`, where
   real named NPCs like Tephra use a purpose-built subclass) is exactly the kind of native
   difference that is invisible to every DataTable/T3D check already exhausted — the same
   shape of cause that consumed sessions 11–14 on the registration mystery. Test it cheaply
   rather than assuming.
2. **Lead #1 (trace `ConvertToThrall`'s body)** — the one piece of `BP_ThrallCage`'s working
   chain never replicated, skipped on an unverified assumption.
3. **Lead #2 (bypass registration, self-apply `SetCharacterLayout`) last** — it's the most
   concrete but also the largest build, and it carries a stated permanent cost: Amadan never
   becomes a real registered character, so Smart Objects and anything else keyed off that
   registration stay broken. Pay that knowingly after the cheap diagnostics, not by default.

The absent `characters` row and the "owning actor does not have a valid UID" Smart Object
error are the same fact reported twice — he is never registered. Prefer finding the
registration trigger over routing around it.

---

## Cross-cutting: bank the tooling knowledge

`claude-conan-modder` (the `ccmod` tool repo) has had **no commits since 2026-07-16**, while
this mod learned a great deal that is mod-agnostic and belongs there. `docs/TECHNICAL-NOTES.md`
in this repo documents, and ccmod's own `reference/authoring-workflow.md` does not:

- `K2Node_FunctionEntry` cannot be pasted; function bodies need one hand-wire at a knot.
- Latent/async nodes cannot live in a plain Function — only Event Graphs.
- `K2Node_Message` takes no literal pin defaults, and pasting one reproducibly crashes this
  DevKit build (`EXCEPTION_ACCESS_VIOLATION` in `BlueprintGraph.dll`).
- Same-class self-calls don't survive synthesis; clone a real one and retarget `MemberName`.
- Cloning one node template twice can leave a stale `ExportPath` that Unreal mis-imports.

These are tool-level facts any future Conan mod would need. Backport them.

## Cross-cutting: keep memory current

The project's persistent notes holds nothing on this project after 2026-07-13. Sessions 15–21, the contest
submission, the entire Amadan bug, and this roadmap were all invisible to it. A session
starting cold from memory alone gets a two-week-stale picture and will make wrong statements
about project state — this has already happened once. **Store a state anchor at the end of
each working session**, not just at milestones.
