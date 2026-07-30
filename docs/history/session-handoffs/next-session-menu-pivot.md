# Session 14 wrap-up: hard pivot from Stocker to Menu (read this first)

**Status: decision made, transplant not yet started. Stop reading other `docs/next-session-*.md`
files for next-step guidance — they're all superseded by this one. Full memory record lives in the
`stocker-menu-pivot` memory (and `stocker-menu-registration`/`stocker-current-state` for the
historical registration investigation this pivot ends).**

## The decision

Stated directly by the user: **"I need to wrap this up in 4 sessions... we've spent more time
fighting the menu popup than we have actually coding the mod logic."**

Effective immediately: **stop debugging Stocker's `ActivateModule`/`DT_UIModuleTable` registration
problem. Move Stocker's actual game logic into the separate `Menu` mod**
(`C:\CEUE5Devkit\UE4\Content\Mods\Menu\`), which has a proven-working interact-opens-a-cursor-modal
UI chain. `Stocker` (`C:\CEUE5Devkit\UE4\Content\Mods\Stocker\`) becomes legacy/reference-only — its
logic gets copied out of it, but it's not being developed further as its own mod. Whether `Menu`
eventually gets renamed/rebranded to ship is an open question, explicitly deferred — doesn't block
the logic transplant.

## Why this was the right call, not giving up early

This session built a second, fully isolated "Menu" test mod (from a fellow modder's video/Discord
tip) to settle whether Stocker's registration approach could ever work. It proved genuinely useful,
then hit a wall that justifies the pivot:

1. **Menu's own menu DOES work** — `Menu_ModController`'s plain regular-timing
   `MergeDataTables(DT_UIModuleTable, AmadanUIModule)` + `BP_PL_Table_Strategy_Amadan`'s
   `ClientInteractableActivate → GetGUIModuleController → ActivateModule("W_AmadanMenu",
   activate=true, force=false)` genuinely opens `W_AmadanMenu` with a working cursor. Confirmed by
   the user directly ("damnit - it worked!!").
2. **Every difference between Menu (works) and Stocker (doesn't) was found and eliminated, one at a
   time, across this session:**
   - `Category`: Modal → Popup (matched)
   - `force`: true → false (matched)
   - Every one of ~30 `AmadanUIModule`/`DT_UIModuleTable` row fields aligned to Menu's row, verified
     via direct clipboard row-copy (only `CloseOnESC` still differs — cosmetic, no plausible
     mechanism for causing a NULL return)
   - Widget renamed to `StockerHouseRules` to match Menu's self-referential row-name convention —
     confirmed the rename didn't leave a dangling `WidgetClass` reference
   - Added a real `IsValid`/`Branch`/print diagnostic to the actual interact-triggered path itself
     (not just the pre-existing decoupled 90s BeginPlay probe), so both paths give unambiguous
     log signal
3. **Result: still `NULL`, on both paths, in a properly-run test.** Session lasted ~155 seconds
   (well past every relevant timing threshold), 3 real desk interacts before the 90s mark, Probe A
   fired right on schedule at 90.2s — this was NOT an incomplete test (an earlier attempt that same
   session genuinely was: game quit at 84.8s, 5s short of Probe A's 90s delay, giving a false
   non-result — don't confuse the two log-checks if reviewing raw logs later).
4. **One flag was flagged but never cleanly isolated: `bRequiresLoadOnStartup`** — `true` on Stocker,
   `false` on Menu (checked directly in both `modinfo.json` files). Every past test of this flag
   (session 11) was confounded by other differences that have since been eliminated. This remains a
   loose thread if anyone ever wants to pick the registration mystery back up — but per the decision
   above, not with this project's remaining session budget.

**Conclusion: the real differentiator, whatever it is, is invisible to every artifact `ccmod`/T3D/
DataTable-row-copy can inspect.** That means it's not a Blueprint-graph-level or DataTable-content
difference — the kind of thing that has no obvious cheap next step. That's what makes this pivot
sound engineering judgment, not a premature bailout: the investigation was run to a real dead end,
not abandoned mid-thread.

## The transplant plan (next session starts here)

Inventory of Stocker's real logic assets (`Stocker/Local/`), what each needs:

| Asset | Plan |
|---|---|
| `S_KeepRule` (struct) | Save-As copy into `Menu/Local` |
| `E_Stocker_Outcome` (enum) | Save-As copy into `Menu/Local` |
| `BPFL_Stocker2` (function library, has `ApplyKeepRule` — the actual move-items logic) | Save-As copy. Preserves the whole function body wholesale, no `ccmod` repaste needed for the algorithm itself. |
| `Stocker_ModController`'s BeginPlay chain (gather `ManagedStations`, pass 1 tidy, pass 2 restock, `KeepRulesV2` iteration, 8s tidy-sweep) | Already captured this session as `.ccmod/graphs/stocker_modcontroller_probe_a_live.t3d` (158 nodes) — reusable directly, no need to re-pull from the DevKit. Needs `KeepRulesV2`/`ManagedStations` variables declared on `Menu_ModController` first (user-side), then retarget+paste, dropping the now-dead Probe A diagnostic branch. |
| `AddKeepRule` | A Function-type member directly on `Stocker_ModController` (not in the library) — needs its own capture+transplant via the paste-only-the-Result-node-plus-hand-wire trick (Function-type members can't have their `FunctionEntry` pasted). Not urgent, can follow the core loop. |
| Production `AmadanItem`/`AmadanRecipe`/`AmadanFeat` | Menu already has its own copies from the sidequest repro — unverified whether these are real production content or placeholder test rows. Check before assuming either way. |
| `BPC_Stocker.uasset`, `BP_BAC_KeepManifest.uasset` | Unexplained — appear nowhere in this project's own memory record. Ask the user what they're for before deciding whether they need to move. |
| `BP_PL_WorkStation_Amadan`, `Stocker/Preload/`, old `StockerHouseRules`-renamed widget (session 13's `W_StockerTestPanel`, has the unsolved `FLXButtonBase` click problem) | **Leave behind.** Superseded/dead ends — see `stocker-placeable-saveas-gotcha` and `stocker-menu-registration` memories. Menu's own `W_AmadanMenu` (stock `Button`, not `FLXButtonBase`) is the one to build the real house-rules UI onto instead. |

**Suggested first concrete step next session:** the three Save-As copies (`S_KeepRule`,
`E_Stocker_Outcome`, `BPFL_Stocker2`) — cheap, no risk, unblocks everything else. Then declare
`KeepRulesV2`/`ManagedStations` on `Menu_ModController` so the captured 158-node BeginPlay graph has
somewhere to paste into.

## Follow-up design pass (same session, after the pivot decision): decompose the giant ModController graph into functions instead of transplanting it as one 158-node monolith

User's framing: "many small graphs are much more approachable than a few large ones," drawing
direct inspiration from `AC_Menu::SaveVariableToMC` (Menu mod) — a tiny, single-purpose function.
Decided to break `Stocker_ModController`'s BeginPlay chain into real Function-type members before
(or as part of) moving it into `Menu_ModController`, rather than pasting the whole 158-node graph
in as one piece.

**Mechanical reality, confirmed before designing anything:** `ccmod` can't run the DevKit's native
"Collapse to Function" (GUI-only). And `K2Node_FunctionEntry`/`K2Node_FunctionResult` still can't be
pasted (same limitation `AddKeepRule`/`InteractableGetUIModuleName` already hit). So each extracted
function is its own small round trip: I find the node boundary + propose a signature → **user
creates the empty Function** (My Blueprint → Functions → `+`, matching that signature — same
asset-creation division of labor as always) → I generate the interior body as paste-ready T3D → user
pastes + does the one Entry/Result hand-wire → I generate the call-site replacement for the
EventGraph.

### Target #1: `AddKeepRule` — DONE, ready to transplant, no extraction needed

It's already a standalone Function-type member on `Stocker_ModController` (not embedded in the
BeginPlay graph). Pulled and captured verbatim as `.ccmod/graphs/stocker_addkeeprule_current.t3d`.
Full signature and body:

```
AddKeepRule(Station: Actor, TemplateID: int, Keep: int, KeepAll: bool)   [void, no FunctionResult]
  Cast Station → BP_Master_Placeables → GetActorUniqueID
    → MakeStruct(S_KeepRule{Container=UniqueID, TemplateID, Keep, KeepAll})
    → Array_Add(KeepRulesV2, NewItem) → print "STOCKER_ADDRULE: rule added"
  [cast fail] → print "STOCKER_ADDRULE: cast to placeable failed"
```

**Next session: as soon as `KeepRulesV2: Array<S_KeepRule>` and the `S_KeepRule` struct exist on
`Menu_ModController`/`Menu/Local` (already planned above), generate the retargeted paste for this —
no further design decisions needed, just mechanical transplant.**

### Targets #2/#3: the two sweeps — signature decided, exact node boundary NOT yet nailed down

**Decision made: Option B — two fully independent functions, not one function sharing a loop.**
Each does its own full gather + filter, even though the current code does both in one pass. The
extra iteration cost is irrelevant (a handful of nearby placeables, not a hot path), and it matches
the "many small graphs" philosophy directly.

**Signature decided:**
```
GatherNearbyBenches(AnchorActor: Actor, Range: float) -> Array<Actor>
GatherNearbyStorageContainers(AnchorActor: Actor, Range: float) -> Array<Actor>
```
Taking `AnchorActor` as a real parameter (not reading a hardcoded actor reference the way the
current code does) is a deliberate, free side benefit: it's the actual fix for the old parked
"single-anchor limitation" in `stocker-open-questions` (today's engine can only see ONE base because
the gather is anchored to one hardcoded actor; a real placeable-facing function taking its own
`AnchorActor` fixes this as a byproduct of the refactor, not a separate effort).

**Confirmed requirement, changes the shape from a pure function: each one MUST still write to the
existing `ManagedStations`/`ManagedContainers` member variables on the ModController**, not just
return a fresh array — the reason: the eventual bench-picker combobox in the real house-rules UI
needs to read `ManagedStations` directly as a variable (same pattern as `W_AmadanMenu`'s `Construct`
reading `Menu_ModController.AmadanText` directly), not receive a value passed around from a
function's return. So the actual shape is **impure**: refresh the member array as a side effect,
probably also return it as a convenience output pin (free, already computed) — not settled which,
low-stakes either way.

**What's NOT done yet: the precise node boundary.** A first `ccmod`-based exec-chain trace of the
158-node graph (script: BFS over exec pins from `ReceiveBeginPlay`, in the transcript above if
picking this up fresh) showed the real control flow is genuinely tangled — nested `ForEachLoop`
macros and `Branch`es, not simple sequential sections the way the print-string landmarks (`STOCKER_3N`/
`3S`) suggested at first glance. Specifically unresolved: does `ManagedStations` get populated as
the **complement bucket of the same branch** that fills the storage-candidate array (what
`stocker-open-questions`' older design note describes — "the gather Branch sorts every in-range
container into two buckets and we discard one"), or from a **separate, later `GetAllActorsOfClass`
call** (`K2Node_CallFunction_10`, which the exec trace shows running right before the `"3S
ManagedStations found"` print, after the storage loop already completed)? **Answering this requires
reading the actual DATA pins** — `ActorClass` filters on each `GetAllActorsOfClass`, and the
`Condition` inputs on the two `IfThenElse` nodes in the first loop (`K2Node_IfThenElse_0`,
`K2Node_IfThenElse_1`) — not just the exec shape, which is as far as this session got.

**Also confirmed and worth remembering when re-tracing:** the `STOCKER_3Q` "rules-v2 seed+restock"
section sits immediately after the real gather/print sections complete, before any of the other dead
spike sections. If re-running the same BFS trace script, `STOCKER_3Q`'s subtree (`K2Node_CallFunction_43`
onward) marks where real gather logic ends and dead spike code begins — useful landmark for isolating
just the two sweeps' nodes without wading through the 3Q/3O/3P/3V/3W dead weight that follows.

### Also confirmed dead, to delete during the transplant (not carry forward as functions)

`STOCKER_3O` (identity spike), `STOCKER_3P` (round-trip check, 14× "OK" prints), `STOCKER_3V`
(friendly-name spike), `STOCKER_3W` (custom-name spike), Probe A's `ActivateModule` diagnostic — all
still wired into live `BeginPlay`, firing every game load for zero production value. **`STOCKER_3Q`
is worse than cosmetic noise — it actively injects 2 hardcoded fake rules into the real `KeepRulesV2`
array every single load** (confirmed firing in this session's own log: `"STOCKER_3Q seeded 2 rules"`).
All five sections should be deleted outright during the transplant, not ported.

**Suggested order for next session, updated:** (1) the three Save-As copies, (2) transplant
`AddKeepRule` (fully ready, zero further design needed), (3) resume the data-pin-level trace of the
gather/branch region to nail the exact `GatherNearbyBenches`/`GatherNearbyStorageContainers` node
boundaries, (4) only then attempt the full BeginPlay transplant, with the five dead spike sections
stripped and the two sweeps as real function calls instead of inline.

## The real house-rules UI — sketched and design-confirmed, not yet built

Same session, after the function-decomposition pass: sketched the actual player-facing panel that
replaces `W_AmadanMenu`'s current `AmadanText`/`SaveVariableToMC` placeholder demo. Mocked as an
HTML wireframe (not committed as an asset — describe layout below for the next session to build as
real UMG).

**Layout, user-specified and confirmed:**
- Top: an On/Off toggle, **default Off**, scoped to **this bench only** — other benches keep their
  own setting independently. Not a mod-wide switch.
- Left column: **Crafting bench** dropdown (populated from `ManagedStations`, see the sweep-function
  plan above) → **Item** field → **Keep** integer input → **Save rule** button.
- Right column, right-justified in the panel: **Saved rules** list box. Each row shows
  `<bench> — <item>: <keep>` with a delete (trash) affordance. Rows are click-to-highlight,
  click-trash-to-delete.
- **Add/delete only — no edit-in-place.** Changing a rule means deleting the old one and saving a
  new one; the list box never loads a row back into the form fields.

**The Item field is NOT a plain dropdown — confirmed as a type-ahead over the FULL `ItemTable`**
(every item in the game, not scoped to the selected bench). Needs, on `Construct`: enumerate all
`ItemTable` row names (`GetDataTableRowNames`, already a known idiom — see `stocker-datatable-workflow`
memory), resolve each to a friendly display name (`Get Name From Template ID`, returns `Text` not
`String` — also an already-solved idiom), build a lookup array once. Then as the player types, filter
that array by substring match and show matches in a small results list; clicking one selects it. This
is a real, somewhat involved widget-side function of its own — worth treating as another one of the
"many small graphs," not folded into `Construct` directly.

**Two real data-model decisions this design forces, neither of which existed as a concern in the
original transplant plan:**

1. **`AddKeepRule` needs upsert semantics, not blind append.** Since the UI only ever adds or
   deletes (never edits), a player changing their mind about a `Keep` value does it by saving a new
   rule for the same bench+item — which means `AddKeepRule` must check `KeepRulesV2` for an existing
   rule matching `(Station, TemplateID)` and **replace** it, not add a second entry. Otherwise
   `ApplyKeepRule` would have two conflicting rules for the same item at the same station with no
   defined resolution order. This changes `AddKeepRule`'s body from the simple "cast → make struct →
   array-add" shape already captured in `stocker_addkeeprule_current.t3d` — the transplant needs this
   dedup logic added, not just a straight port.
2. **The per-bench On/Off toggle doesn't fit anywhere in the current data model.** `S_KeepRule` is
   per-item-per-station, but this flag is a property of the station itself, independent of how many
   item rules exist there. Needs its own small piece of state — likely a `Map<UniqueID, bool>` (or a
   small new struct if more per-station settings show up later) — plus its own tiny get/set functions
   (`SetStationEnabled`/`IsStationEnabled` or similar), same single-purpose-function pattern as
   everything else in this plan. `ApplyKeepRule`'s tidy/restock pass needs a check at the top: skip
   the station entirely if its flag is off, same effect as having zero rules there.

**Updated function-decomposition list for next session (supersedes the shorter one above):**
- `GatherNearbyBenches(AnchorActor, Range) -> Array<Actor>` — writes `ManagedStations`, also the
  dropdown's data source
- `GatherNearbyStorageContainers(AnchorActor, Range) -> Array<Actor>` — writes `ManagedContainers`
- `AddKeepRule(Station, TemplateID, Keep, KeepAll)` — **upsert, not append** (new requirement, body
  needs a rewrite from the captured version, not just a retarget)
- `RemoveKeepRule(Station, TemplateID)` or similar — needed for the list box's delete action, not
  designed yet at all
- `SetStationEnabled(Station, bool)` / `IsStationEnabled(Station) -> bool` — new, not designed yet
- A type-ahead item-search helper for the widget side — new, not designed yet

## Everything captured this session, on disk and reusable

All in `.ccmod/graphs/` (the same `ccmod` workspace was used for both mods' work this
session — Menu's captures are prefixed `menu_`, Stocker's own live-state pulls are prefixed
`stocker_`):

- `menu_amadan_eventgraph_pre.t3d` / `_postfix.t3d` — Menu desk's interact chain, before/after the
  `activate` checkbox fix (3 nodes each: `Event → GetGUIModuleController → ActivateModule`)
- `menu_moddatatableoperations_pre.t3d` — Menu's `ModDataTableOperations` (4 `MergeDataTables` calls,
  `DT_UIModuleTable` first)
- `menu_modcontroller_eventgraph_empty.t3d` — confirms `Menu_ModController`'s `BeginPlay`/`Tick` are
  both disabled and unwired (no hidden timing tricks)
- `menu_w_amadanmenu_widgettree.t3d` / `_eventgraph.t3d` — the working widget's full tree (stock UMG
  `Button`, not `FLXButtonBase`) and logic (Construct reads `AmadanText`, button click saves it)
- `menu_ac_menu_eventgraph.t3d` — `AC_Menu`'s `SaveVariableToMC(Text)`, the Additional-Class-Component
  write-path pattern (unrelated to the registration mystery, but a real pattern worth reusing for the
  eventual real house-rules UI)
- `stocker_amadan_clientinteractableactivate_live.t3d` — the messy 15-node SetTimer-hack graph found
  still live on the real Stocker desk (should have been empty per old notes — wasn't; a reminder to
  verify live DevKit state over trusting session notes)
- `stocker_amadan_clientinteractableactivate_replacement.t3d` / `_with_diag.t3d` — the clean 3-node
  and then 7-node (with `IsValid`/`Branch`/print) replacements actually pasted onto the real Stocker
  desk this session
- `stocker_modcontroller_probe_a_live.t3d` — **the reusable one** — `Stocker_ModController`'s full
  158-node `EventGraph`, live, as of this session. This is the source for the transplant's core-logic
  paste next session.
- `stocker_addkeeprule_current.t3d` — `AddKeepRule`'s full function body, captured verbatim, ready
  to retarget and paste into `Menu_ModController` as soon as its `KeepRulesV2`/`S_KeepRule`
  dependencies exist there.
