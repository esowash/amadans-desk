# Menu-on-interact fix — handoff for the next session

**Status: diagnosed, unimplemented. Written 2026-07-19 after a full-day investigation (sessions 10–11 + a
post-session audit). This doc supersedes the "base-table override" plan in the
`stocker-menu-registration` memory — that plan is obsolete, do not execute it.**

Read this whole doc before touching anything. The fix itself is ~2 nodes. Everything else here exists so
you don't re-open settled questions or re-run dead experiments.

---

## 1. Goal (unchanged since session 9)

Interacting with the mod's placed table (**`BP_PL_Table_Strategy_Amadan`**, actor id **91** in the save DB)
must open **`W_StockerTestPanel`** as a modal with a working mouse cursor, so the Save/Stock buttons can be
clicked. Blueprint-only, no C++. All assets live in `C:\CEUE5Devkit\UE4\Content\Mods\Stocker\Local\`.

## 2. What is already built and proven — do NOT rebuild or re-test

1. **Module registration timing is SOLVED.** `Preload/Stocker_Preload.uasset` is a second ModController
   whose `ModDataTableOperations` runs `MergeDataTables(AmadanUIModule → DT_UIModuleTable)`. Log-proven
   ordering (ConanSandbox.log, 2026-07-19 18:17 run):
   - `22:17:50.067 [frame 0]` — `AddActiveModControllerClass: Stocker_Preload_C`
   - `22:17:50.550 [frame 0]` — GUIModuleController loads `DT_UIModuleTable` (the one-and-only read)
   The merge runs **~0.5 s before** the read that doomed every session-10/11 attempt. Keep the preload
   controller and `bRequiresLoadOnStartup: true` exactly as they are.
2. **The merged row is well-formed.** `AmadanUIModule` row `StockerHouseRules` →
   `W_StockerTestPanel_C`, `Category=Modal`, native row struct `/Script/ConanSandbox.UIModuleTableRow`.
3. **The panel itself works.** In the 18:17 run it was opened by a ModController BeginPlay+20s delay
   (the "simpletest" graph) and a real click registered (`STOCKER_STOCKBUTTON_CLICKED` in the log).
4. **`ActivateModule` works from an interact context** for a registered module (session 11:
   `ActivateModule("ContainerInfo")` returned a valid WindowRoot from the desk's interact).

## 3. The problem, precisely

The table's menu-open is currently wired to an override of **`ClientInteractableActivate`**
(interface event on `ConanSandbox.InteractableInterface`) which calls
`GetGUIModuleController → ActivateModule("StockerHouseRules")`. **That event never fires.** Zero
`STOCKER_PRELOADTEST` prints in all five playtest logs from 2026-07-19. Evidence it never will:

- Zero of ~15,700 shipped assets implement or call `ClientInteractableActivate` (checked via
  `ccmod api`). It exists only in the native interface header.
- A dev comment inside `BP_Master_Placeables` on `InteractableActivate`: *"this is a server side function
  call. The connection between the interface and controller is implementable in FunCombat_PlayerController
  BP."* The real interact chain lives in `FunCombat_PlayerController`:
  range/line-of-sight checks → `InteractableDefaultAction` → **`GUIModuleController_Activate`** (async
  call-proxy), plus `CloseInteractionActorGUIModule` for teardown.

**The native pattern is declarative, not imperative.** A non-crafting placeable never opens its own menu.
It answers the question "what module am I?" via **`InteractableGetUIModuleName`** (a Function-type
interface override returning an FName), and native code does everything else — open, modal, cursor, focus,
close. `BP_PlaceableItemContainer` does exactly this: a 2-node override returning `"ContainerInfo"`.

**Historical trap, already resolved — do not re-litigate:** session 11 tested this exact override and it
was "ignored." That test ran on the OLD desk (`BP_PL_WorkStation_Amadan`, a crafting-station base), and
crafting stations bypass `InteractableGetUIModuleName` via their native `CraftingStationInterface`. The
NEW table is a `BP_Master_Placeables` child — the class family (containers/signs/maproom) where the
override IS honored. The old negative result does not transfer.

## 4. The fix

On **`BP_PL_Table_Strategy_Amadan`**:

1. **Delete** the `ClientInteractableActivate` event override and its whole chain (the
   `STOCKER_PRELOADTEST` prints, `GetGUIModuleController`, `ActivateModule`, `IsValid`).
2. **Add** an override of **`InteractableGetUIModuleName`** returning FName **`StockerHouseRules`**.
   - It's a Function-type interface member: use the **Override dropdown next to Functions in My
     Blueprint** (search the exact name). Do NOT browse the Interfaces category — it lists a different,
     similarly-named interface (known trap, session 10).
   - The idiom is already captured: `chalkcircle_getuimodulename.t3d` and
     `container_getuimodulename.t3d` in `.ccmod/graphs/` (Entry → Result returning a literal FName).
     Function entry/result nodes can't be pasted — this is small enough that the user builds it by hand
     in the DevKit: override the function, type the literal into the Return node. Two nodes, one literal.

## 5. Test plan (one cook, two independent probes)

**Probe A — registration + rendering, no interact dependency.** Edit the ModController "simpletest"
delay chain (currently `CreateWidget/AddToViewport/SetInputMode_UIOnlyEx`): replace the body after the
Delay with `GetGUIModuleController → ActivateModule("StockerHouseRules", activate=true, force=false)` →
`IsValid` → two distinct PrintStrings (e.g. `STOCKER_ACTMOD_VALID` / `STOCKER_ACTMOD_NULL`). Keep the
prints label-only — never combine a literal default with a data wire on the same pin (gotcha #13).

**Probe B — the native interact path.** The `InteractableGetUIModuleName` override from §4. No prints
possible (pure function) — its proof is visual: interact with the placed table (actor 91) and the panel
opens as a native modal with a cursor.

Cook + install + launch per `docs/local-test-loop.md`, and read the gates in the
`stocker-test-loop-gotchas` memory first. Log:
`C:\Program Files (x86)\Steam\steamapps\common\Conan Exiles\ConanSandbox\Saved\Logs\ConanSandbox.log`.

Expected outcomes and what they mean:

| Probe A | Probe B | Diagnosis |
|---|---|---|
| VALID + panel renders | menu opens on E | **Done.** Bank it, clean up (§7). |
| VALID + panel renders | nothing on E | Registration fine; interact dispatch is the gap → §6.2 |
| VALID but nothing renders / NULL | — | Row found but widget rejected or merge failed → §6.1 |

## 6. Fallbacks, in order — only if a probe fails

1. **Row found but no render (or NULL despite the preload merge):** every widget registered in the base
   `DT_UIModuleTable` has a native Conan parent (`WindowRoot`, `SignTextInputBase`, `WritableNoteBase`,
   `DyeWindow`, `InteractionPromptWidgetBase`). `W_StockerTestPanel` is a plain `UMG.UserWidget` child,
   and `ActivateModule`'s return pin is typed `WindowRoot`. Fix: **reparent** `W_StockerTestPanel`
   (Class Settings → Parent Class) to a `WindowRoot`-derived base — try `MouseBlockWindowBase` first —
   then re-cook. Do not go back to debugging timing; timing is proven solved.
2. **No response to E on the table:** check `InteractableDefaultAction` and
   `InteractableActivateDisabled` overrides on `BP_Master_Placeables` (pull them with ccmod) to see what
   gates the prompt, and mirror what a container/sign does. Note: a dev comment says callers deliberately
   test activation-disabled outside `InteractableActivateDisabled`, so read the caller too.
3. **Merge itself suspect:** add a `GetDataTableRowNames(DT_UIModuleTable)` + print to the simpletest
   chain to dump the live table at runtime and confirm `StockerHouseRules` is present.

## 7. After it works

- Re-wire panel close: native teardown (`CloseInteractionActorGUIModule`) should handle walk-away/ESC —
  verify before adding any close-button logic beyond `RemoveFromParent`.
- Delete the now-dead hand-rolled input-mode/cursor code in `W_StockerTestPanel`'s Construct and the
  simpletest scaffolding from the ModController.
- Update the memory files: `stocker-menu-registration` ("merge can't win" is DISPROVEN by the Preload
  controller), `stocker-current-state`, `stocker-open-questions` (cursor fork is resolved). The
  session-10 "cursor unfixable by hand" conclusion is also disproven (click registered from timer-opened
  panel) but moot.
- Commit findings + graphs per project convention.

## 8. Hard "do not" list

- Do NOT execute the old plan of overriding the base `DT_UIModuleTable` asset. Obsolete.
- Do NOT hand-roll `CreateWidget/AddToViewport/SetInputMode/ShowMouseCursor` for this menu.
- Do NOT wire menu logic into `InteractableActivate`/`ClientInteractableActivate` overrides.
- Do NOT re-base the placeable again. `BP_Master_Placeables` via `BP_PL_Table_Strategy_Amadan` is correct.
- Do NOT trust `ccmod api` absence-of-evidence for properties/getters (known indexing gap) — but its
  "zero implementers" finding for `ClientInteractableActivate` was cross-checked and stands.
