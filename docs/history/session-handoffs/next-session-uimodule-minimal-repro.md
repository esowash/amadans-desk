# UIModule minimal repro — sidequest handoff (pick up in a fresh context)

**Status: planned, unstarted. Written 2026-07-20 (session 13, tail end) after a fellow modder's video
appeared to contradict this project's own repeated test results. This is a SIDEQUEST — it does not
replace the base-`DT_UIModuleTable`-override plan in `stocker-menu-registration` (memory), it exists to
either confirm that plan is still necessary or find a cheaper alternative before committing to it.**

Read this whole doc before touching anything — it's short. The point is to settle one specific factual
disagreement with a clean, isolated test, not to re-litigate anything else about the mod.

---

## 1. The disagreement this resolves

This project (Stocker) has tested "merge a row into `DT_UIModuleTable` so `ActivateModule` can find a
custom module" **three times, all NULL**:

1. **Session 11** — the *first* attempt: regular `Stocker_ModController` → `ModDataTableOperations` →
   `MergeDataTables(UIModuleTable, AmadanUIModule)`. `ActivateModule("StockerHouseRules")` returned
   NULL. Diagnosed via log timestamps: the merge runs at ModController activation (~22s into load),
   ~22s *after* `GUIModuleController` already read+cached `DT_UIModuleTable`.
2. **Session 12** — built a SECOND, separate `Preload` ModController specifically to activate earlier
   than the regular one, to try to beat that timing. Also NULL, twice.
3. **Session 13 (this session, Probe A)** — re-tested the exact same Preload mechanism a third time.
   NULL again. **Also got direct native-engine confirmation**, not just inferred timing: a
   `LogAsyncObjectFinder: Error: ... DT_UIModuleTable ... should have been loaded at this point!` line
   fires at frame 0, *before* `LoadMap: /Game/Maps/Startup` even begins — earlier than any map load,
   let alone any ModController activation.

Full detail on all three: `stocker-current-state` memory (session 12 entry + session 13 part 2 entry).

**Then, later in session 13**, the user got a tip from a fellow modder online (Discord) plus two
screenshots from a video the modder shared:

- **Screenshot 1**: `Event Client Interactable Activate` → `Get GUIModule Controller` → `Activate
  Module(Target=<controller>, Module Name="DemoWidget", Activate=true, Force=false)`. A `Parent: Client
  Interactable Activate` node sits in the graph but is NOT wired into the exec chain (not called) —
  same choice this project already made.
- **Screenshot 2**: inside the ModController, `Mod Data Table Operations` → `Merge Data
  Tables(Target=self, Merge Into Data Table=UIModuleTable, To Be Added Data Table=DemoUIModule)`.

**This is the SAME mechanism as this project's session-11 attempt** (regular ModController merge, not
even the more-aggressive Preload variant) — and per this project's own repeated testing plus the
frame-0 engine-log evidence, it should not work. The modder's claim ("we are adding the line to the
UIModule table CORRECTLY") directly conflicts with that. Neither side has been proven wrong yet — this
doc is the test that settles it.

## 2. What NOT to do

- **Do not conclude either side is right without running the test below.** The frame-0 log evidence is
  concrete; the modder's claim is unverified secondhand information. Don't defer to authority in
  either direction.
- **Do not fold this into Stocker's existing `AmadanUIModule`/`StockerHouseRules` naming or logic.**
  The whole point is an isolated, minimal, apples-to-apples reproduction — new table, new widget, new
  module name, so a result can't be blamed on some Stocker-specific mistake.
- **Do not re-litigate the cursor-revert investigation.** That's a separate, already-exhausted thread
  (three independent decoupling attempts, all failed identically — see `stocker-current-state` session
  13 part 3). This sidequest is purely about registration/`ActivateModule`, not the mouse-capture bug.

## 3. The plan

**Two new assets (user creates in the DevKit — asset creation is the user's side of this project's
established division of labor, not something `ccmod`/clipboard can do):**

1. `W_DemoWidget` — a plain `UserWidget`, no real content needed (a single Text block is plenty). Just
   needs to exist so a render can be observed.
2. `DemoUIModule` — a DataTable asset, same row struct as the existing `AmadanUIModule`
   (`ConanSandbox.UIModuleTableRow` = `WidgetClass` + `Category`), ONE row keyed `DemoWidget`,
   `WidgetClass = W_DemoWidget_C`, `Category = Modal`. This is a repeat of a known process — see
   `stocker-datatable-workflow` memory for how `AmadanUIModule` was built the same way.

Both live wherever the rest of Stocker's mod-local assets live:
`C:\CEUE5Devkit\UE4\Content\Mods\Stocker\Local\`.

**Two Blueprint pieces (Claude generates as T3D once the assets above exist, since the graphs need to
reference real asset paths that don't exist yet):**

1. A SECOND, independent `MergeDataTables(Target=self, Merge Into Data Table=UIModuleTable, To Be
   Added Data Table=DemoUIModule)` call added to `Stocker_ModController`'s `ModDataTableOperations`
   function — alongside the existing `AmadanUIModule` merge, not replacing it. Reuses the
   already-proven-reliable regular ModController activation timing; only the table/row content is new.
2. A fresh diagnostic chain on `BP_PL_Table_Strategy_Amadan`'s `ClientInteractableActivate` (currently
   EMPTY — the old hand-rolled open-chain was deleted session 13 part 2/3, and `ClientInteractableActivate`
   hasn't held anything since). Recreate screenshot 1 node-for-node: `Event → Get GUIModule Controller →
   Activate Module(ModuleName="DemoWidget", Activate=true, Force=false) → IsValid → Branch → print
   VALID/NULL`. No Parent call, matching the video's disconnected one. This can safely coexist with the
   existing `InteractableGetUIModuleName` override (returns `"StockerHouseRules"`, currently inert since
   unregistered) — they're independent dispatch paths, already confirmed to both fire without conflict
   earlier this session.

**Test plan:** cook, deploy, cold-boot, interact with the desk EARLY (do not wait — timing is not what's
being tested here; if anything, an early interact is a *harder*, more honest test given everything
already found about frame-0 reads). Read the log for the new `STOCKER_DEMOMODULE_VALID`/`_NULL` prints
(or whatever the diagnostic ends up labeled — keep it distinct from `STOCKER_ACTMOD_*`, which was
Probe A's labeling for `StockerHouseRules`, to avoid confusing the two in the log).

## 4. Expected outcomes and what they mean

| Result | Diagnosis |
|---|---|
| NULL | Fourth independent confirmation, now with zero Stocker-specific baggage to argue about. The modder's claim doesn't hold up under a faithful reproduction — go back to them with this result and ask whether their own demo was actually tested from a cold boot with an early interact, or only observed after the world had been running a while. Commit to the base-`DT_UIModuleTable`-override plan (`stocker-menu-registration` memory) without further hesitation. |
| VALID + `W_DemoWidget` renders | A real, meaningful difference exists between this repro and Stocker's own setup. Next step: diff the two merge calls and both ModControllers node-for-node (`ccmod pull` both, compare) to find what's actually different — do NOT assume "just do what the demo did" transfers automatically to `AmadanUIModule`/`StockerHouseRules` until the actual differing factor is identified. |
| VALID but nothing renders | Registration works, rendering doesn't — likely the same `WindowRoot`-parentage question already flagged for `W_StockerTestPanel` (`stocker-current-state`, Probe B section): `ActivateModule`'s return pin is typed `WindowRoot`, and a plain `UserWidget` may not satisfy that. Try reparenting `W_DemoWidget` to `MouseBlockWindowBase` before concluding anything deeper is wrong. |

## 5. Context this sidequest assumes (read if picking this up cold)

- `stocker-conan-mod` memory — repo location, build machine, test loop, `ccmod` workflow.
- `stocker-current-state` memory (session 13 part 2 + part 3) — the full registration-disproven
  history and the exhausted cursor-revert thread, so this sidequest isn't confused with either.
- `stocker-menu-registration` memory — the base-table-override plan this sidequest is trying to avoid
  or confirm the necessity of.
- `stocker-open-questions` memory — has a "KICKOFF NOTE" pointing at the same external tip this doc
  addresses; this doc supersedes that pointer once it exists.
