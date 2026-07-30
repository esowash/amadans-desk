# Authoring Blueprints reliably (the T3D clipboard method)

**Problem.** Wiring Blueprint graphs over computer-use (remote desktop control) is
unreliable: pins are a few pixels wide, and drag-off-pin operations frequently grab the
node body instead. A moderately complex graph is not practically hand-wireable this way.

**Solution — Blueprint nodes round-trip through the clipboard as text (UE "T3D").**
Verified end-to-end 2026-07-10:

- **Read:** select nodes in the graph → `Ctrl+C` → **PowerShell `Get-Clipboard -Raw`**
  returns the full text. No `clipboardRead` computer-use grant needed.
- **Write:** **PowerShell `Set-Clipboard`** the text → click the graph → `Ctrl+V` →
  the whole node network instantiates, **fully wired**.

### The format
Each node is a block:
```
Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_0"
   ...node props (FunctionReference, NodePosX=, NodePosY=, NodeGuid=)...
   CustomProperties Pin (PinId=<GUID>,PinName="...",Direction="EGPD_Input|Output",
       PinType.PinCategory="exec|object|...",..., LinkedTo=(<OtherNodeName> <OtherPinId>,), ...)
   ...more pins...
End Object
```
- **Nodes** are identified by `Name="..."`; **pins** by `PinId=<GUID>`.
- **Connections** are `LinkedTo=(<TargetNodeName> <TargetPinId>,)` — present on **both**
  ends of a wire.
- **Layout** is `NodePosX=` / `NodePosY=`.

### The reliable authoring workflow
1. **Capture reference blocks from ground truth.** Drop each node type you need once (via
   the graph right-click menu — reliable), `Ctrl+C`, `Get-Clipboard` to read its exact
   T3D (all the `PinType.*` boilerplate is captured correctly this way, not hand-written).
2. **Assemble in a script:** give each node a unique `Name`, mint fresh `PinId` GUIDs,
   wire by writing matching `LinkedTo` on both pins, set `NodePosX/Y`.
3. **`Set-Clipboard` the assembled text → click graph → `Ctrl+V`.** Compile.

### Gotchas
- Pasting a **duplicate event** (e.g. a second `Event BeginPlay`) makes UE **substitute a
  `CustomEvent`** and warn "one or more copied nodes were substituted during paste." So
  don't paste event nodes that already exist — paste the *body* and wire it to the
  existing event, or include the event only when the graph doesn't already have one.
- `Get-Component-by-Class` etc. keep their `Component Class` in the node props; capture a
  correctly-configured reference and reuse it.
- Still use menus/dropdowns/clipboard-paste-into-fields for non-graph work (creating the
  asset, parent class, components, variables) — those are reliable over computer-use.

### Python is NOT the answer here
The Dev Kit ships `Engine/Plugins/Experimental/PythonScriptPlugin` (disabled by default)
+ a Python 3 interpreter, but UE's `unreal` Python API is weak at exactly the hard part —
constructing K2 event-graph node networks. It's fine for assets/variables/defaults, not
graph wiring. T3D paste is the better lever and needs no plugin enable/restart.

---

# P1 build plan (the reclaim core)

**Goal (from [`design.md`](design.md)):** prove the reclaim *mechanic* — read a bench's
inventory, compute overflow past a Keep-N rule, and move it into storage that already
holds ≥1 of that item — with **instant transfer, stationary, no AI** (explicitly a test
harness, not shipping feel).

### Where to build P1 v1: on the Mod Controller (the proven harness)
`Stocker_ModController` already loads server-side, ticks, and prints to the log (v1
proved this end-to-end). Build the reclaim core here first with **hardcoded enrollment**
(a test item + Keep-N), before adding Amadan's Desk and real enrollment. This isolates the
mechanic from the UI/enrollment surface.

### The graph (authored via T3D paste)
Server-only (`Switch Has Authority`), on the existing loop:
1. `Get All Actors Of Class` → `BP_PlaceableItemContainer` (or the crafting-station class).
2. `For Each` bench:
   - **Safety:** skip if craft queue active (`CraftingQueue`/`QueueStarted`); skip fuel
     slots (`BP_BAC_UsesFuel`); skip recently-opened (`Is Open` + grace timestamp).
   - Read count of the test item; if `> KeepN`, compute `excess`.
   - Find a nearby storage container that already holds ≥1 of the item (overlap query).
   - **`Move and Stack Items`** (Item Distributor): Template ID = item, Amount = excess,
     Source = bench inventory, Target = storage inventory. Log `Remaining`.
3. `Print String` each action for the log.

### After v1 proves the mechanic
- Author **Amadan's Desk** (subclass `BP_PL_Crafting_Station`, mesh
  `SM_A2C2_Stygian_FOBTacticsTable`) and move the manifest there:
  `Map<benchUniqueId → KeepRules>` + pause + close-timestamp.
- Real **explicit enrollment** (two gates: enroll bench, then set a Keep rule).
- "Keep Many" UI in the Desk's own panel (new `DT_CraftingGUIPanelTable` row).

### Verify each iteration via the local test loop
Build → overwrite `…/Conan Exiles/ConanSandbox/Mods/Stocker.pak` → launch (Stocker
already enabled) → read `LogBlueprintUserMessages` in the game log, and cross-check
transfers against the save DB (`Game_0.db`). See [`local-test-loop.md`](local-test-loop.md).
