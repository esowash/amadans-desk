# Phase 3 AI inspection checklist

**Purpose:** Phase 3 (a thrall that autonomously paths between containers and
deposits items) is the project's biggest unknown. Before investing in Phase 1/2
polish, spend one Dev Kit session answering a single question:

> Can we make a follower path to a specific placed container and run an
> interaction there **from Blueprints**, by extending the base-game needs/schedule
> AI (**Path A**) — or must we build our own AIController + Behavior Tree
> (**Path B**)?

This checklist makes that session efficient. It is written against Conan naming
*conventions*; exact asset names/paths must be discovered in the Enhanced Dev Kit
(UE 5.6.1). Record what you actually find — correct this doc as you go.

## How to search the content browser

Use the Content Browser search + filters. Useful queries:

- `BT_` — Behavior Trees. `BB_` — Blackboards.
- `Follower`, `Thrall`, `Bearer`, `Companion`, `NPC`, `Human`
- `Need`, `Schedule`, `Job`, `Task`, `Officer`, `LivingSettlement`, `Settlement`
- `AIController`, `BTTask_`, `BTService_`, `BTDecorator_`
- `BP_Placeable_Item_Container`, `BP_BAC_Storage`, `PlaceableInventory`

Turn on **"Show Engine Content"** and **"Show Plugin/Developer Content"** in the
content browser view options, or base-game assets may be hidden.

## Assets to locate (and what to capture about each)

For every asset below, note: exact path, **parent class**, and whether it is a
**Blueprint** (extendable) or a **C++/native** class (icon + parent tells you;
native = we can subclass but can't edit internals).

1. **The follower/thrall character** — the pawn class our thrall derives from.
   Find the **Bearer** variant specifically (Phase 2 subclasses it). Capture its
   class hierarchy up to the human NPC base.
2. **The thrall AIController** — the controller that possesses the follower pawn
   and runs its Behavior Tree.
3. **The follower Behavior Tree + Blackboard** — the actual BT the thrall runs
   (follow / guard / return-home, plus the Living Settlements needs branches).
4. **The needs/schedule system** — component(s) and data that drive
   "seek campfire/chair/bench, eat, rest, socialize." Look for a Needs component,
   a schedule/timetable asset, and the **Officer's Desk** placeable that governs
   work cycles.
5. **The "seek a placeable and interact" task** — the BT task/service that finds a
   furniture target, paths to it, and plays the sit/eat/rest interaction. **This
   is the single most important asset** — it is the primitive we want to
   repoint at containers.
6. **Navigation** — confirm the world has a nav mesh followers use, and note the
   move node in use (`MoveTo` / `MoveToLocation` / `EQS` queries).
7. **Container inventory access** — on `BP_Placeable_Item_Container` /
   `PlaceableInventory`, the functions to (a) enumerate contents, (b) test for an
   item type, (c) add/remove/transfer a stack. (Shared with Phase 1.)

## Questions to answer (the actual decision)

- **Q1.** Is the follower Behavior Tree a **Blueprint asset we can subclass /
  extend**, or is it locked? Can we add a new branch/subtree to it via a child
  or an override?
- **Q2.** Is the **needs/schedule system Blueprint-exposed** enough to register a
  **custom "need"/task** (e.g. "deliver items") that competes with eat/rest? Or
  are needs a fixed C++ enum with no extension point?
- **Q3.** Can the "seek placeable + interact" BT task be **retargeted at an
  arbitrary actor** (our source/target containers) rather than only furniture
  need-targets?
- **Q4.** Can Blueprints command a follower to **`MoveTo` a specific actor**
  location and detect arrival? (Confirms Path B is viable even if A isn't.)
- **Q5.** Can Blueprints **read another placeable's inventory and transfer a
  stack** at runtime? (Gates the deposit action for either path.)
- **Q6.** Does the deposit/carry interplay with **Bearer inventory** (Phase 2)
  cleanly, or do follow-mode and errand-mode conflict? (Likely need a mode
  toggle.)

## Decision output

Write the result at the bottom of this file (and to memory):

- **Path A viable** if Q1–Q3 are yes: extend the needs/schedule AI with a custom
  delivery task. Least work, most "native."
- **Path B** if Q1–Q3 are no but Q4–Q5 are yes: build a custom **AIController +
  Behavior Tree + Blackboard** running our own seek → path → deposit loop on the
  nav mesh.
- **Blocked** if Q4 *or* Q5 is no: the core mechanic isn't reachable from
  Blueprints — reassess scope (e.g. fall back to a stationary Phase 1 sorter and
  drop the walking) before building anything.

## Findings (Dev Kit inspection, build box, 2026-07-09)

Inspected in **Conan Exiles Devkit 1001 (1.3.0)** / UE 5.6.1. Method: full disk
inventory of uncooked `Content/*.uasset` (every `.uasset` = a Blueprint/data
asset; native C++ classes have no `.uasset`), plus opening pivotal Blueprints in
the editor to read parent classes (via the Content Browser asset tooltip:
`Parent Class` / `Native Parent Class`).

### Decision: **PATH A is viable — NOT blocked.**

The reusable "path to a placed object and interact" primitive is **UE5
SmartObjects**, and Conan's Living Settlements needs AI is built entirely on it.
The cleanest implementation is a **SmartObject-based extension of the Settlement
needs AI**; a custom AIController + Behavior Tree (**Path B**) is a solid,
lower-dependency fallback. Q4 and Q5 (the "Blocked" gates) are both **yes**.

### Asset map (exact paths, all under `/Game` = `…/UE4/Content`)

**Follower / thrall AI (`Systems/AI/NewAI/`)** — all Blueprints:
- Controllers: `HumanAIController` (humans/thralls), `GolemAIController`,
  `CreatureAIController` (base). Interfaces in `Systems/AI/AI_Controllers/`
  (`BP_AIControllerInterface`, `BP_AIControllerCharacterInterface`).
- State Behavior Trees: `BT_Orders`, `BT_Fighting`, `BT_Passive`,
  `BT_Disengaged`, `BT_Leashing`, `BT_GolemFollower`.
- **Follower command subtrees** `Systems/AI/NewAI/FollowerOrders/`:
  `BT_Order_Move`, `BT_Order_Return`, `BT_Order_Defend`, `BT_Order_Flee`,
  `BT_Order_Wait`. Blackboards: `BB_FollowAndGather`, `BB_Simple`.

**Needs / schedule = "Living Settlements" (`Systems/AI/Settlement/`)**:
- `BT_SettlementAgent` (top-level agent BT) → `BT_FulfillNeeds`
  (+ `BTDecorators/BTD_HasSmartObjectForNeed`, `BTTasks/BTD_FulfillingMostImportantNeed`,
  `BTTasks/BTT_UpdateNeeds`).
- Needs component: `Needs/BP_AC_AINeeds` — **Blueprint**, native parent
  `ConanSandbox.AINeedsComponent` (C++). BP-editable effect logic uses nodes
  **Apply buff / Set Blackboard Value / Change Behavior Tree / Inject Behavior
  Subtree / Apply need modifier**. Interface `Needs/I_AINeedsInterface`.
- **Data-driven**: `NeedsTable`, `NeedsProfileTable`, `NeedFulfillmentsTable`,
  `NeedsEnumProvider`, `NeedsEnumTable`; structs `S_NeedFulfillment(Profile)`,
  `S_NeedCurve`; per-profile importance/time-of-day curves.
- **Targeting via EQS**: `Needs/NeedQueries/EQS_Need_Hunger/Sleep/Rest_Basic`,
  `EQS_Work_<Profession>` (Blacksmith, Cook, Tanner, Taskmaster, …).
- **Fulfilled via SmartObject slots**: `Settlement/SmartObjects/SOS_Eat_Base`,
  `SOS_Sleep_Base`, `SOS_Work_<Profession>`.
- Nav: `NavArea_AmbientLifeAccessibleDoor`, `NavQueryFilter_SettlementAgent`.

**SmartObject system = the seek-and-interact primitive (`Systems/SmartObject/`)**:
- Slots: `Slots/SOS_Sit_Chair`, `SOS_Sit_Eat`, `SOS_Sit_Read`, `SOS_Sit_Drink_Tavern`,
  `SOS_SimpleAnim`, `SOS_SimpleEmote`.
- **Functions (BP logic that runs *on use*)**: `Functions/SOF_AffectNeed`,
  `SOF_AnimOnce`, `SOF_PlayMultipleAnim`, `SOF_EquipHeldWeapon`, … ← this is the
  hook where a **deposit** action would live (author `SOF_DepositItem`).
- Conditions `Conditions/SOC_SeatIsEmpty`; approach EQS `EQS_AroundSmartObject*`,
  `EQS_FrontOf/BehindSmartObject`; `BP_AC_SlotProxy`; `ScanSmartObjects`.
- BT: `Systems/AI/NewAI/SmartObjects/BT_UseSmartObject` + `BPI_SmartObject`.

**Golem follower framework (`Characters/Golems/`)** — see reframing note below:
- Pawns: `GolemNPC` (base), **`ThrallGolemNPC`** (owned follower golem).
  Controller `GolemAIController`, behavior `BT_GolemFollower`.
- Components: `BPGolemPartInventory`, `BPWorkorderInventory`,
  `BPGolemAppearanceComponent`; **`AttributeComponents/BP_GolemGatheringComponent_hatchetT4`
  / `_PickT4` / `_SicleT4` / `_SkinT4`** (autonomous resource gathering with tools;
  golem `A_golem_harvesting_chop/crop/mine/skin_loop` anims exist).
- `BP_Ritual_CreateFollowerGolem`; interfaces `I_GolemNPC`, `I_GolemPartInventory`.

**Bearer thrall (Phase 2 target)**:
- Pawns `Characters/NPCs/Humanoid/HumanoidNPCCharacter_RelicHunters_BearerT1..T4`;
  carry item `Items/BearerCrates/BPGameItemBearerCrate_T1..T4`; data
  `Systems/Loot/New/Professions/DT_NPC_Bearer_T1..T4`.

**Container = source/target (`Systems/Building/Placeables/`)**:
- **`BP_PlaceableItemContainer`** — Blueprint; parent `BP_Master_Placeables` (BP)
  ← native `ConanSandbox.PlaceableBase`; **13 Blueprint components** (inventory/
  storage are BP components). `BP_ThrallFeedingContainer` is precedent for a
  thrall depositing into a placed container. Also `BP_FeedingContainer`,
  `BP_LootContainer`, `BP_DebugItemContainer`.

### Q1–Q6

- **Q1 (follower BT a BP we can subclass/extend?) — YES.** The follower AI is a
  set of BP Behavior Trees + BP AIControllers (native-parented). BTs aren't
  "subclassed" but are freely cloned/edited, and a custom/child AIController can
  run our own BT. Nothing is locked.
- **Q2 (needs system BP-exposed enough for a custom need?) — YES (native base).**
  `BP_AC_AINeeds` is a Blueprint over native `AINeedsComponent`; effects are
  authored in BP (blackboard writes + **BT subtree injection**), and needs are
  data-table + EQS + SmartObject-slot driven. A custom "deliver/sort" need = new
  data rows + an EQS query + a SmartObject slot + a BP effect. *Only unknown:*
  whether `NeedsEnumProvider`/`NeedsEnumTable` accepts a brand-new enum value
  from a mod — settle with a small build test; architecture is built for it.
- **Q3 (retarget seek-placeable+interact at an arbitrary actor?) — YES,** via
  SmartObjects. Any actor can host SmartObject slots; `BT_UseSmartObject` +
  `EQS_AroundSmartObject` do approach+use; `SOF_*` functions run BP logic on use.
- **Q4 (BP MoveTo a specific actor + detect arrival?) — YES.**
  `FollowerOrders/BT_Order_Move`/`BT_Order_Return` are BP BTs that move a follower
  to a location and detect arrival; golem gathering paths to nodes. Navmesh +
  `NavQueryFilter_SettlementAgent` present. **Path B is viable.**
- **Q5 (BP read another placeable's inventory + transfer a stack?) — YES (high
  confidence).** `BP_PlaceableItemContainer` is a BP with BP inventory components;
  the item/inventory system is BP-exposed game-wide; `BP_ThrallFeedingContainer`
  precedent. Exact transfer node to be pinned at build time — architecturally open.
- **Q6 (deposit/carry vs Bearer follow — mode conflict?) — Design, not a blocker.**
  Follower "orders" already model exclusive modes (Move/Return/Defend/Wait), so a
  **Follow ↔ Sort mode toggle** fits the pattern. Golems already carry (part +
  workorder inventories) while doing autonomous work.

### Recommended build path

1. **Preferred (Path A / SmartObject):** define a custom **need** ("Sort/Deliver"),
   an **EQS** that finds our target-container SmartObjects, a **SmartObject slot**
   on the containers, and a **`SOF_DepositItem`** function that does the transfer.
   Reuse `BT_FulfillNeeds` / `BT_UseSmartObject` for the seek→path→interact loop.
2. **Fallback (Path B):** child a BP AIController + author a Behavior Tree +
   Blackboard modeled on `FollowerOrders/BT_Order_Move` running our own
   source→target→deposit loop on the navmesh.

### Golem-as-base — considered and dropped (superseded 2026-07-13)

An earlier draft here floated basing the follower on the **Golem** worker
(`ThrallGolemNPC` + `GolemAIController` + `BT_GolemFollower` + a
`BP_GolemGatheringComponent`-style component) instead of the Bearer thrall, on the
reasoning that it was "on-theme, since our concept is literally a copper golem." **Dropped —
the premise was never sound, and the concept has since moved past it:**

- **Bad analogy.** Conan's golems are stone/animated-construct servitors — a wholly
  different fiction from Minecraft's Copper Golem. The "on-theme" match was superficial.
- **No behavior left to justify it.** The mod is now a bench **reclaimer** and the thrall
  (**Amadan Cnoic**) is a **pure narrative gate** — a Bearer subclass for carry + follow,
  with the reclaim engine on Amadan's Desk and only a cosmetic patrol (see
  [`design.md`](design.md)). There is no autonomous resource-gathering to model on a golem.

**Base class: Bearer thrall.** The `BT_Order_*` / SmartObject findings above still stand as
generic DevKit facts for the cosmetic patrol; they no longer imply a golem base.
