# Design notes — Stocker

> **Renamed 2026-07-09.** The **mod** is now called **Stocker** (repo folder
> `Mods/Stocker/`; the short name also keeps Windows paths short — see the handoff in
> [`dev-environment.md`](dev-environment.md)). The **follower thrall NPC** was renamed
> **2026-07-13** to **"Amadan Cnoic,"** and his bench to **"Amadan's Desk"** — see
> [The thrall: identity](#the-thrall-identity). Below, read "Amadan" as the *thrall*, not the
> mod.

> **Concept reworked 2026-07-09.** The original "Copper Golem sorter" (pull items
> from a designated source container, sort into matching storage) already exists as
> a polished Workshop mod, **The Porter** — we are *not* recreating it. Amadan is now a
> QoL **crafting-bench reclaimer**. The earlier sorter research is preserved under
> [Reference findings](#reference-findings) because the mechanics still apply.

## Decision (2026-07-13) — the bench is the prop; the thrall gates it

**The mod's center of gravity is the bench, not the thrall.** The *prop* the player
interacts with — the object Stocker mechanically *is*, and where the whole UI lives — is
**Amadan's Desk**, a crafting-bench placeable (see
[the side-table architecture](#the-side-table-architecture-2026-07-10)). You walk to the
Desk, open its panel, and do everything there: enroll benches, set house rules, pause, read
status. The reclaim engine lives on the bench too (the `StockerItemDistributor` — see
[Item Distributor](#item-distributor--what-it-actually-is-2026-07-10)).

**The thrall stays, but its role is now purely narrative: it gatekeeps the bench.** Earlier
drafts made the thrall the *star* — a copper-golem automaton that walked your goods around.
It is now the **lore key** that unlocks the Desk's utility: there is always an "Amadan" in your
world, and the Desk's house-rules power is inert until you have him. Milder immersion than a
walking automaton, but a cleaner, conflict-free mod whose value concentrates in one
craftable object.

**Consequences (resolved 2026-07-13 unless noted):**
1. **Rename the thrall — DONE.** "Amadan Cnoic"; bench "Amadan's Desk." See
   [The thrall: identity](#the-thrall-identity).
2. **Acquisition & access — DECIDED.** Capture on the Wheel of Pain, then a consumable in his
   inventory grants the Desk recipe. See [Acquisition & access](#acquisition--access).
3. **The bench UI — specified (v1).** The Desk's panel scaffolds the Blueprint/widget
   organization. See [Amadan's Desk — the bench UI](#amadans-desk--the-bench-ui-v1).
4. **Patrol (P3) — SIMPLIFIED.** The Desk does the reclaim on a timer; the thrall's patrol is
   cosmetic only (visits benches/storage for immersion, does not trigger moves).
5. **Naming ripple — applied.** The bench and all thrall references were renamed across the
   docs; UE asset names + display strings to follow when authored on the build box.

---

## Concept — the Bench Reclaimer

"Amadan Cnoic" is a follower thrall that, **while you are at your base**, quietly
skims **excess crafting materials out of your crafting benches** and files them into
storage that already holds that item type. He subclasses the base **Bearer thrall**
(inherits carry + follow), and the whole QoL is **gated** behind acquiring him — so
there is always an "Amadan" character in your world.

## The constraint that shapes everything

Conan does **no offline processing**: when a base chunk is unloaded (no player
nearby), thralls *and* crafting benches freeze — benches even switch off. There is no
real-time simulation of an unattended base, so **"tidy my base while I adventure" is
impossible** for any real-time approach (a placeable "sorter station" would be just
as frozen as a thrall).

*Nuance:* smelting and thrall-breaking **do** persist while unloaded — but via a
**timestamp catch-up** (on reload, advance the queue by elapsed time). That works
only because those are self-contained, time-deterministic queues. Amadan's cleanup
depends on the live state of *other* containers ("which chest already holds this
item?"), so it can't be reduced to a per-bench timestamp — it can only run when the
chunk is loaded.

**Consequence: Amadan is an ambient, while-present helper, not remote automation.**

## The experience

- **Ambient tidy while present** — as you play at base, Amadan patrols benches and files
  overflow into storage. Enroll benches once; never hand-sort overflow again.
- **Welcome-home sweep** — nothing ran while you were away, so on return the patrol
  simply finds the **backlog** left from last session and clears it as you ride in —
  a satisfying "he kept it tidy" moment, for free. (Sits comfortably in the mental
  model players already have from smelting/thrall-breaking persisting.)
- **Emergent division of labor** — you work the *hot* benches; Amadan tidies the
  *settled* ones. You don't step on each other.

## Interaction model — the patrol is core (not polish)

> **Resolved 2026-07-13 — patrol simplified.** The **Desk does the work**: reclaim moves are
> **timer-driven** on the `StockerItemDistributor`, independent of the thrall's location.
> Amadan still runs a **cosmetic patrol** (he visits enrolled benches and storage for
> immersion) but his walking **does not trigger** transfers. This retires the
> "patrol-is-the-mechanism" scope (P3). The rest of this section describes that original
> model, kept for context.

During active play, **instant** item removal is hostile — things vanishing mid-task
read as a glitch and fight your workflow. So the shipping model is a **physical,
paced patrol**: Amadan picks the nearest managed bench with overflow, walks to it, takes
the excess, carries it to matching storage, repeats — one bench at a time, unhurried,
interruptible. **Cadence: a slow timer, idle-benches-only** (validate the feel in
playtest).

This is the **most reusable** behavior in the DevKit: the base settlement AI already
walks thralls to crafting benches (`EQS_Work_<Profession>` finds benches by profession
and paths a thrall to them). "Amadan visits the bench" is that behavior **repointed**
from "work here" to "skim overflow here." Instant transfer survives only as a P1 test
harness.

## House rules — opt-in twice, explicitly

> **Renamed & tightened 2026-07-10.** The manifest is called **"house rules"** in-game.
> It no longer lives on the bench (see [the side-table architecture](#the-side-table-architecture-2026-07-10));
> it lives on **Amadan's Desk**, keyed by bench persistence UUID.

**"Amadan touches nothing until told" is now a designed-in invariant, not an emergent one.**
There are **two explicit gates**, and both must be passed before Amadan moves a single item:

1. **Enroll the bench.** A deliberate act — the bench is assigned to Amadan. An
   un-enrolled bench does not exist to him, no matter what it contains.
2. **Set a Keep rule for an item** on that enrolled bench.

- **Keep 200** → skim that item down to 200, filing the overflow into storage.
- **Keep 0** → "take all of this" (the aggressive case, still opt-in per item).
- **no rule for an item** → untouched. Unlisted items are always left alone; use
  **Keep 0** to have him clear one.
- **no rules at all on an enrolled bench** → nothing moves. Enrollment alone authorises
  nothing.
- **Pause toggle** → one click suspends an enrolled bench *without* wiping its rules
  (handy during a big build); resume to re-enable.

> **Decision (2026-07-10):** enrollment is **explicit, per bench**, not "manage every
> bench in range." It is more legible, and it *is* the opt-in promise — designing around
> it now is cheaper than shoehorning it in later. **This supersedes the earlier
> `no entries at all → the bench is invisible to Amadan` implicit gate**, which made
> enrollment a side effect of setting a rule.

**UI:** the **"Keep Many"** control borrows the **"Craft Many"** quantity-spinner
paradigm — you set *Keep 200* right where you'd set *Craft 200*. It lives in **Amadan's
Desk's own panel**, so no base widget is touched.

## Safety rules (settled)

1. **Skip active crafting** — never touch a bench that has a craft queue.
2. **Never touch fuel** — regardless of any Keep entry.
3. **Don't-fight-me** — skip a bench whose inventory UI is open **right now**, plus a
   **configurable ~300 s grace** after the player closes it (a timestamp stamped on
   close — reliable, not a guess). This covers the *loaded-but-not-yet-queued* window:
   dump mats, close, and you have 5 minutes to start the craft before Amadan would skim.
4. **Deposit target** — file each item into storage that already holds **≥1** of that
   type (the sorting-automaton rule; empty chests never receive).

## The thrall: identity

> Resolved 2026-07-13. Supersedes the earlier thrall-and-gate framing: per the
> [bench-is-the-prop decision](#decision-2026-07-13--the-bench-is-the-prop-the-thrall-gates-it)
> the thrall's job is to **gate the bench**, not to be the mechanism.

Subclass the base **Bearer thrall** (inherits carry + follow for free). The reclaimer
utility **unlocks only once you've acquired him** (see
[Acquisition & access](#acquisition--access)), so an "Amadan" always exists in your world.

**Name — DECIDED: "Amadan Cnoic."** From the Irish *amadán* ("fool") + *cnoic* ("of the
hill") — a faintly folkloric, in-universe name for a wandering trickster-sage. His bench is
**"Amadan's Desk."** These finalize the placeholder names carried until now.

**Rename applied 2026-07-13 across the design docs** ("Amadan" / "Amadan Cnoic" = the thrall;
"Amadan's Desk" = the bench). When the mod's UE assets are authored on the build box, name the assets
and display strings to match. The mod itself stays **Stocker**.

## Acquisition & access

> Resolved 2026-07-13.

**How you get Amadan and unlock his Desk — a standard Conan loop:**
1. **Capture him on the Wheel of Pain.** Amadan is a **named Bearer thrall**; knock him out
   and break him like any thrall. *(Spawn site / encounter: TBD.)*
2. **Loot the knowledge from his inventory.** Once broken, open his inventory and take a
   **consumable item** he carries.
3. **Consume it to learn the recipe.** Consuming that item **grants the Knowledge/Feat** to
   craft **Amadan's Desk** and its house-rules UI.

This "consume → learn a recipe" pattern is well-worn in Conan, so it should have **many
precedents in the asset library** — find an existing grant-on-consume item and model ours on
it. The loop keeps the soft gate intact (no Amadan ⇒ no Desk) using only shipped systems.

**Still to pin (not blockers):** Amadan's spawn location/encounter; the exact
"grant-knowledge-on-consume" asset to model; whether losing the thrall later revokes access
(lean **no** — once learned, the Desk stays craftable, as Conan recipes normally do).

## Amadan's Desk — the bench UI (v1)

This is the surface that will govern the Blueprint/widget organization, so it is specified
before the graphs are built. **First pass — labels and feel to confirm in the editor/playtest.**

The Desk **subclasses `BP_PL_Crafting_Station`**, inheriting the standard bench
inventory-panel frame; its custom panel is a **new row** in `DT_CraftingGUIPanelTable`
(`StockerHouseRules → W_StockerHouseRulesView`) — no base widget overridden (see
[the bench-UI resolution](#-resolved-2026-07-10-amadans-desk-is-a-crafting-bench--contested-surface-drops-to-zero)).

### Screens / states
1. **Overview (default)** — the list of **enrolled benches**. Each row: bench name/type,
   rule count, a live **overflow** indicator (how much is skimmable right now), and a
   **pause** toggle. Empty state: *"No benches enrolled — enroll one to begin."*
2. **Enroll** — an action to **add a bench** to the manifest. (Enroll gesture TBD — see
   below.) Enrolling adds a row but authorizes nothing until a rule is set.
3. **Bench detail** — opened from a row; shows that bench's **item rules** as a list of
   `item → Keep N`. Controls:
   - **Add rule** — pick an item type, set **Keep N** via the **"Keep Many"** spinner (mirrors
     vanilla **"Craft Many"** / `WBP_SelectCraftAmount`). *Keep 0* = "take all"; no rule =
     untouched.
   - **Edit / remove rule.**
   - **Pause this bench** (mirrors the overview toggle).
4. **Safety read-outs (non-editable)** — the [four safety rules](#safety-rules-settled) are
   **fixed, not user config**. Surface them as info so the player understands *why* an item
   wasn't taken (fuel skipped / active craft / grace window / no matching storage).

### Data model behind the UI (the manifest)
`Map<BenchUUID → { Map<TemplateID → KeepN>, bPaused, LastClosedTimestamp }>`, held on the
Desk and persisted via the Persistence Component (see
[the persistence API](#the-persistence-api--the-foreign-key-confirmed-2026-07-10)). The UI
is a **view over this map**: enrolling adds an outer key; adding a rule adds an inner entry.

### UI → Blueprint organization (the scaffolding)
| UI piece | Widget / BP asset | Notes |
|---|---|---|
| Panel root | `W_StockerHouseRulesView` *(new)* | registered by a new `DT_CraftingGUIPanelTable` row — contests nothing |
| Enrolled-bench row | `W_StockerBenchRow` *(new)* | binds to one manifest outer key |
| Item-rule row | `W_StockerRuleRow` *(new)* | binds to one `TemplateID → KeepN` entry |
| Keep-N control | reuse the `WBP_SelectCraftAmount` paradigm | the "Keep Many" spinner |
| Manifest store | `BP_BAC_KeepManifest` *(exists)* on the Desk BP | owns the `Map` + save/load hooks |
| Reclaim engine | `StockerItemDistributor` *(new — subclass `ItemDistributor`)* | reads the manifest, runs `Move and Stack Items` |

Each UI element maps to a small, bindable widget over one slice of the manifest, so the
widget tree and the data model share a shape — which keeps the Blueprint graphs small and
makes the panel the natural spine for organizing the mod's Blueprints.

**To confirm (editor/playtest):** the enroll gesture (walk-up? select from a list of nearby
benches by UUID?); whether item rules are added by picking from the bench's current contents
vs. a searchable item list; the overflow-indicator refresh cadence.

## Phases

- **P1 — Reclaim logic (instant; proves the core):** the Keep-manifest + safety rules +
  deposit-to-matching-storage, applied on a stationary bench with instant transfer.
  The instant transfer is a *test harness*, not the shipping feel — provable with no
  AI/pathing.
- **P2 — Amadan thrall + gate:** subclass Bearer → Amadan; unlock P1 only when he's yours.
- **P3 — Cosmetic patrol (immersion, optional polish):** Amadan walks a loop visiting
  enrolled benches and storage for flavor; the reclaim itself is the Desk's timer (P1), **not**
  triggered by his movement. *(Simplified 2026-07-13.)*

## Decisions (2026-07-09) — the five forks, resolved

- **Enrollment & buffer** → **opt-in, per bench, per item** via the house rules
  (above). Supersedes the earlier opt-out lean. *(Tightened 2026-07-10: enrollment is now
  an **explicit** act, not a side effect of setting the first rule.)*
- **Grace-after-close** → **~300 s, configurable.**
- **Lock/enroll UI** → **"Keep Many"** control on the bench (borrowed from "Craft
  Many") + a **pause** toggle.
- **Patrol cadence** → **slow timer, idle-benches-only** (tentative — confirm the feel
  in playtest).

Feel-tuning to confirm in-game (not blockers): the 300 s grace length and the patrol
cadence/speed.

## DevKit feasibility — inspection findings (2026-07-09)

CLI asset inspection (no building/cooking) confirms the design is buildable via
Conan's standard modding hooks. **Architecture:** crafting benches are
`BP_PL_CraftingStation_*` placeables (Blacksmith `_Metal`, Carpenter `_Wood`,
`_Furnace`, `_Tannery`, `_Mixer`, Wheel of Pain `_WheelOfPain`, …) that gain behavior
from modular **Building Actor Components** (`BP_BAC_*`). All six questions come back
**GO**:

1. **Inject a "Keep" control into the bench UI** — GO. `W_CraftingStationInventoryView`
   is the bench inventory widget; **`WBP_SelectCraftAmount`** is the existing "Craft
   Amount" spinner to model "Keep Many" on; `CraftingGUI` + `DT_CraftingGUIPanelTable`
   drive the panels. *(Editor: confirm the injection method — subclass vs data-driven
   panel.)*
2. **Attach a Keep-manifest component to base benches** — GO, but **not via the Mod
   Controller**. ⚠ *Corrected 2026-07-10 — see [Attach mechanism](#attach-mechanism-settled-2026-07-10).*
   The Mod Controller only merges **data tables**; components are attached by
   **overriding the base Blueprint**.
3. **Bench state (open / inventory-change / craft-queue) BP-readable** — GO.
   `BP_BAC_CraftingStation` (a Blueprint component) holds the inventory + queue.
   *(Editor: confirm the specific queue/change events.)*
4. **Distinguish fuel / input / foreign** — GO, cleanly. **Fuel is its own component,
   `BP_BAC_UsesFuel`**, separate from the crafting inventory — "never touch fuel" =
   skip that component's slots.
5. **Repoint the settlement work-AI (`EQS_Work`)** — GO (Path A viable, from the
   Phase-3 inspection). Its targets *are* these `BP_PL_CraftingStation_*` benches.
6. **Smelt / thrall-break catch-up** — Furnace and Wheel of Pain use the *same*
   `BP_PL_CraftingStation` + `BP_BAC_CraftingStation` architecture, so their
   unloaded-persistence is a mode of the shared component, not special-case code.
   (Only relevant if we ever revisit "while-away.")

**Net:** no blockers; the design maps cleanly onto the game's component system.

---

## Attach mechanism — SETTLED (2026-07-10)

Verified empirically in the editor, not inferred. **`BP_BAC_KeepManifest` now exists**
(`Mods/Stocker/Local/BP_BAC_KeepManifest.uasset`, parent = native
`BuildingMasterActorComponent` — the same base the other `BP_BAC_*` use) and **is
attached to the shared bench parent**, compiling clean.

### The Mod Controller does *not* attach components
`Items/Example_modcontroller` (native parent `ModController`) exposes only
`ItemTable` / `FeatTable` / `RecipesTable` and `MergeDataTables` /
`MergeIntoDataTable` / `ToBeAddedDataTable`. A full-content sweep of every
`Content/*.uasset` for `BuildingActorComponent` returns **one** hit
(`BP_AC_LootSpawner`, itself a component), and `Content/Mods/ModsShared` is **empty**.
There is no class→component mapping table anywhere. The Mod Controller merges data
tables; that is all it does.

### Components are attached by overriding the base Blueprint
Open the base bench, add the component, save. The Dev Kit's `ModDevKitPlatformFile`
**redirects the write into the active mod** — the base install is never modified
(verified: `BP_PL_Crafting_Station.uasset` sha256 and mtime unchanged after saving).

**Two distinct trees inside a mod, and the difference matters:**

| Tree | Holds | Runtime path | Cook dialog type |
|---|---|---|---|
| `Mods/<Mod>/Local/` | new mod-owned assets | `/Game/Mods/<Mod>/<Asset>` | green **(Mod Asset)** |
| `Mods/<Mod>/Content/<original path>` | **overrides of base assets** | the *original* `/Game/…` path | orange **(Base Asset)** |

So our override lives at
`Mods/Stocker/Content/Systems/Building/Placeables/BP_PL_Crafting_Station.uasset`
(1.24 MB — a full copy of the 1.23 MB base), and it references
`/Game/Mods/Stocker/BP_BAC_KeepManifest`. *Base-asset override is a first-class,
Dev-Kit-supported workflow* — it has its own type tag in **Choose Assets For Cook**.

### ⚠ Consequence: the override conflicts with every other bench mod
`BP_PL_Crafting_Station` is the **shared parent** of every bench
(`BP_PL_CraftingStation_Metal`, `_Wood`, `_Furnace`, … all inherit from it, and it in
turn derives from `BP_PlaceableItemContainer` ← native `ConanSandbox.PlaceableBase`).
One override reaches every bench — but it occupies the *original* `/Game/` path, so
Stocker would **conflict with any other mod that overrides `BP_PL_Crafting_Station`**
(last in load order wins). This is the well-known Conan bench-mod conflict.

> **We rejected this. The override was reverted on 2026-07-10** (deleted from
> `Mods/Stocker/Content/`; base bench verified byte-identical). See
> [The side-table architecture](#the-side-table-architecture-2026-07-10) below — the
> mechanism above is documented because it is *how attaching works*, and because a
> single data-table row (option **B**) may still be worth spending.

---

## The side-table architecture (2026-07-10)

**Decision: Stocker touches no base asset.** Instead of altering the bench, we sit
*alongside* it — the database pattern of adding a reference table with a foreign key
when you cannot modify the schema. The base benches are the existing table; our
manifest is a new table keyed on bench identity; the Mod Controller's data-table merge
is the migration that adds it. Three facts from the DevKit make this work:

1. **The foreign key exists** — see [Persistence API](#the-persistence-api--the-foreign-key-confirmed-2026-07-10),
   verified in the Blueprint palette. Conan ships a per-actor persistent `Unique ID`, a
   **world-level index** to resolve it back to an actor, save/load lifecycle events, and
   a `Delete` for cascade cleanup.
2. **The join works.** Cross-inventory transfer is a first-class Blueprint concept, not
   something benches keep private: `BP_ThrallFeedingContainer` has custom events whose
   parameters are literally **`srcInventory`** and **`dstInventory`** object references,
   and it calls `GetPopulatedItemCount`. The bench's `SignalItemAdded` delegate likewise
   carries `item, index, srcInventory, srcIndex`. Precedent: *Organizer Sorting Chest*
   scans nearby containers and moves items with **no base override at all**.
3. **"Insert rows, don't alter schema" is exactly what the Mod Controller does.** Our
   placeable, its recipe, and its feat ship as **new rows** merged into `ItemTable` /
   `RecipesTable` / `FeatTable`. Contested surface: none.

### Amadan's Desk — where the house rules live
Since the manifest can no longer live on the bench, it lives on a craftable placeable of
ours. Conan already has the idiom: the **Officer's Desk** governs settlement work cycles.
"Amadan's Desk" holds `Map<BenchUUID → KeepRules>` plus the pause flag and the
last-closed timestamp. It preserves the soft gate (the desk is inert without Amadan),
gives the P3 patrol a home anchor, and is thematically native.

*FK hygiene:* a destroyed bench leaves a dangling UUID row. Needs a cleanup/cascade
pass — `Delete` on the Persistence Component, gated by `Is Valid ID`. Not a blocker.

> **⚠ Lesson learned (2026-07-12, save-DB gut-check): bind rules to stable container
> identity, never to `GetAllActorsOfClass` enumeration.** While testing, the graph
> discovered target chests by `GetAllActorsOfClass(BP_PL_Chest_Medium)` and blindly grabbed
> the two Medium chests that happened to exist — which turned out to be **~2.6 km from the
> player**, at an old death site, with no relation to the player's actual base. Enumeration
> answers "what exists," not "what the player opted in." The runtime registry the Desk holds
> (`Map<container-UUID → KeepRules>`) is therefore not just storage — it is the **only** correct
> source of which containers Amadan acts on. At apply-time, resolve each registered UUID to its live
> actor (and skip/park the ones not currently loaded); do **not** re-enumerate by class. This
> also means the opt-in flow must capture the container's persistent id at rule-creation time.

#### Art: borrow the Stygian Strategist Table's mesh (2026-07-10)
No new art. The Desk wears the mesh of the **Stygian Strategist Table** — a strategist's
table for a thrall who plans your logistics. Verified in the Dev Kit:

| | Asset |
|---|---|
| Placeable (cosmetic) | `Systems/Building/Placeables/BP_PL_Table_Strategy_Stygian` |
| **Mesh** *(what we take)* | `Items/Placeables/Meshes/SM_A2C2_Stygian_FOBTacticsTable` |
| Material | `Items/Placeables/Materials/FLX/MI_A2C2_Stygian_FOBTacticsTable` |

`BP_PL_Table_Strategy_Stygian` is 37 KB, parents to `BP_Master_Placeables` ← native
`ConanSandbox.PlaceableBase`, and carries **no inventory and no crafting components** —
confirming it is purely decorative. So we do **not** subclass it. Amadan's Desk subclasses
`BP_PL_Crafting_Station` (for the bench UI) and simply **points its static mesh at
`SM_A2C2_Stygian_FOBTacticsTable`**.

> **Reference the mesh; do not copy it.** A `/Game/` reference adds nothing to our
> `.pak`, stays in sync with the base game, and is **not** an override. Copying the
> `.uasset` into `Mods/Stocker/Local/` would needlessly duplicate ~megabytes.

> **Note on the ID.** The wiki lists this item as **19021**, but Dev Kit `ItemTable` row
> `19021` is **"Spider Egg-sac"**. The wiki's numbering does not match the Enhanced
> `ItemTable`; the item was located by name instead. (`ItemTable` row `29112` is
> *"Stygian Schematic (Stygian Strategist Table)"*, the schematic that unlocks it.)
> **Don't trust wiki item IDs against this Dev Kit** — resolve by name or asset path.
> This matters because `Move and Stack Items` takes a **Template ID**.

*Availability:* the same mesh is referenced by `Systems/AI/Purge/FOB/BP_PurgeFOB_WarTable`
— a core Purge asset — so it ships in the base install rather than behind a Battle Pass.
(`A2C2` in the name is only its authoring batch.) Still worth an eyeball in-game.

### The one place the analogy breaks: the bench UI
You cannot add a column to someone else's table, and "Keep Many" wants to live inside the
bench's own panel. But `DT_CraftingGUIPanelTable` maps a panel **name → widget class**
(`CraftingStationInventory → W_CraftingStationInventoryView`), i.e. the bench UI is
**data-driven**. That yields a spectrum of contested surface:

| | Contested surface | Conflicts with | Keep-Many UX |
|---|---|---|---|
| **A. Pure side table** | none | nothing | config lives on Amadan's Desk |
| **B. Re-point one DT row** | 1 row of `DT_CraftingGUIPanelTable` | only mods re-pointing *that panel* | "Keep 200" where you'd set "Craft 200" |
| **C. Override the bench** | `BP_PL_Crafting_Station` (1.2 MB) | **every** bench mod | same as B |

Option **B** subclasses `W_CraftingStationInventoryView` (a *new* asset — no override) and
merges a single row re-pointing the panel. **C is abandoned.**

### ✅ Resolved (2026-07-10): Amadan's Desk *is* a crafting bench — contested surface drops to zero

Player-experience call: *"walking to Amadan's Desk as a crafting bench and using its UI to
establish **house rules** is the most satisfying."* This is not just nicer UX — it
**eliminates the last contested surface**:

- Amadan's Desk **subclasses `BP_PL_Crafting_Station`** → a *new* asset in
  `Mods/Stocker/Local/`, **not** an override. It inherits the bench inventory UI,
  persistence, craft-queue plumbing, and `Is Open` for free.
- Its panel is a **new row key** in `DT_CraftingGUIPanelTable` (e.g.
  `StockerHouseRules → W_StockerHouseRulesView`), merged by the Mod Controller. A brand
  new row contests nothing — we no longer re-point `CraftingStationInventory`.
- The desk ships as new rows in `ItemTable` / `RecipesTable` / `FeatTable`.

So the whole mod is **pure `INSERT`**: not one base asset overridden, not one existing
data-table row contested. Option **B** is no longer needed.

**"House rules"** is the player-facing name for the Keep manifest — the rules you set at
the desk, which Amadan then enforces across the base.

### P3 does not force an override either
Q4 already confirmed Blueprints can `MoveTo` a specific actor and detect arrival
(`FollowerOrders/BT_Order_Move`), so the patrol can walk Amadan to a bench without the bench
hosting a SmartObject slot.

---

## The persistence API — the foreign key, confirmed (2026-07-10)

Verified by searching the Blueprint node palette (context-sensitivity off) inside
`BP_BAC_KeepManifest`. Everything below is a **Blueprint-callable node that already
ships**, under the category **`Dreamworld → Persistence`** ("Dreamworld" is Funcom's
internal engine layer).

> ⚠ **Correction.** An earlier note claimed `BP_PlaceableItemContainer`'s
> `EqualEqual_UUIDUUID` call proved *"the base game compares placeables by UUID."* That
> was over-read. Searching the palette for `Unique ID` returns almost entirely
> **player/owner**-flavoured nodes — `Get Unique ID From Player Info` (Guild),
> `Get Cell Owner as UUniqueID` (Land Claim), `Set Owner Unique ID` (Thrall),
> `Get Character/Controller from Unique Id` (Player Id). The container's `OwnerUniqueID`
> is almost certainly **who owns the chest**, used for `InventorySharingAccess` /
> `EInventoryShareAccess` permission checks — *not* which chest it is. The real
> per-actor key lives on the **Persistence Component**, below. The conclusion survives;
> the evidence for it was wrong.

| What we need (DB term) | The node | Target |
|---|---|---|
| Primary key | **`Get Unique ID`** | Persistence Component |
| Key → row lookup (the **index**) | **`Get Actor By Unique ID`** | **World** Persistence Component |
| Extract the actor part of a key | `Get Actor ID` *(siblings: `Get Player Id`, `Get User ID`)* | Unique ID |
| Mint / validate keys | `Generate Unique ID`, `Make UID`, `Make null ID`, `Is Valid ID` | — |
| Copy / clear | `Copy Unique ID`, `Clear Unique ID` | Persistence Component |
| **Write our row** | `Save actor persistent data`, `Save to database` | Persistence Component |
| **Cascade delete** (orphan cleanup) | `Delete` | Persistence Component |
| Serialize/deserialize hooks | `On Signal Pre Save`, `On Signal Data Loaded` *(+ Bind Event / Assign / Call variants)* | Persistence Component |

Two things this settles:

- **`Unique ID` is a composite key.** `Get Actor ID` / `Get Player Id` / `Get User ID`
  all take a `Unique ID` as target, so it bundles actor + player + user identity.
- **`Get Actor By Unique ID` is a world-level reverse lookup.** A stable, persisted key
  is the *only* thing that node could mean — it is exactly
  `SELECT * FROM actors WHERE id = ?` after a reload.

So Conan doesn't merely permit the side-table design; it ships the primary key, the
index, the write path, the lifecycle hooks, and the cascade delete. Amadan's Desk stores
`Map<UniqueID → KeepEntries>`, writes it on `On Signal Pre Save`, rehydrates on
`On Signal Data Loaded`, and re-resolves each key to a live bench with
`Get Actor By Unique ID`. Orphan rows are swept with `Is Valid ID`.

---

## Palette sweep (2026-07-10) — the Item Distributor system

Same method: node palette, context-sensitivity **off**, hover for the Target class.

### 🎯 Conan already ships the transfer primitive
Spawning the node reveals its exact signature:

```
Move and Stack Items          (Target is Item Distributor)
    Template ID   : int       ← the item type
    Amount        : int       ← how much to move
    Source Inventory  : obj
    Target Inventory  : obj
  → Remaining     : int       ← what did NOT fit
```

This *is* the deposit stage. `Remaining` handles the full-chest case for free, so the
"skim overflow into a chest that already holds ≥1 of this type" rule needs no
hand-rolled stack maths.

### An entire distribution framework exists
Categories found in the palette:

| Category | Nodes |
|---|---|
| `Item Distributor` | **`Move and Stack Items`** |
| `Item Distributor Component` | `Get` / `Set` **`Quantity to Move Per Cycle`** |
| `Item Distributor Interface` | `Distribute Items` |
| `Item Distributor Controller Interface` | `Add Distributor`, `Remove Distributor` |
| `Item Requester` | **`Get Registered Distributors`**, `Compare Requester and Distributor Owner`, `Clean Set Distributor List`, `Get`/`Set Distributor Class`, `On Character Moved Update Distributors` |

This is almost certainly the base-game system for **benches pulling crafting materials
out of nearby containers**. It hands us three things we were about to build ourselves:

1. a **registry of nearby containers** (`Get Registered Distributors`) instead of a
   custom radius scan;
2. a **paced transfer** (`Quantity to Move Per Cycle`) — precisely the "slow cadence"
   the patrol design asks for;
3. the **transfer primitive** itself.

See [Item Distributor — what it actually is](#item-distributor--what-it-actually-is-2026-07-10)
for the verdict.

### ⚠ Two guardrails discovered
- **`Try Get Generic Local Inventory from Actor` is NOT for gameplay.** Its tooltip:
  *"Gets an already spawned generic local inventory on the actor… **Cosmetic. This event
  is only for cosmetic, non-gameplay actions.**"* It returns a client-side
  `GenericLocalOnlyInventory`. Using it to move items would be a non-authoritative bug.
- **Conan is server-authoritative.** `BP_PL_Crafting_Station`'s own graph runs through
  `Switch Has Authority` (Authority / Remote). **The reclaim pass must run on the
  server.**

### Inventory access — the async question, softened
`Load Inventory` is confirmed **async** (*"Target is Load Inventory Call Proxy"*), and
there is an `Is Inventory Loaded` check. But the reclaim may never need a full
enumeration: `Move and Stack Items` takes **inventory object references**, and we only
need *per-item-type counts* (`GetPopulatedItemCount`) to compute overflow and to test the
"already holds ≥1" deposit rule. So the control flow is likely
`Is Inventory Loaded` → (if not) `Load Inventory` → then synchronous counts + moves —
**not** a callback chain around every operation.

---

## Item Distributor — what it actually is (2026-07-10)

**It is Conan's thrall/pet feeding system.** Not a general hauling framework. The proof
is in the assets, all under `Systems/Building/Placeables/`:

- `ItemDistributor` — a **Blueprint** whose native parent is
  **`ConanSandbox.ItemDistributorComponent`** (an `ActorComponent`). It holds
  `AmountToMove`, `ActorsToIgnore`, `Add Any Food Item Inventory to Stock`, does sphere
  traces to find nearby requesters, and reads `BP_ServerSettings`.
- **`ThrallItemDistributor`** and **`PetItemDistributor`** — Blueprint **subclasses** of
  `ItemDistributor`. This is the sanctioned extension point.
- The requester side is diet-specific: `ItemRequester`, `DietItemRequester`,
  `ThrallDietItemRequester`, `PetDietItemRequester`, `ItemStockStruct`.
- `Systems/ItemDistributorController` — an `ActorComponent` with `TickInterval`, a
  `Delay Timer`, and `GlobalDistributeItems`. Its own comment reads:
  *"Added internal timer to check if the thralls need food."*

So a feeding box (the **distributor**) periodically pushes food into nearby thralls and
pets (the **requesters**), on a timer owned by a controller.

### Verdict: reuse the transfer + pacing + scheduling. Do not reuse the discovery.

| Piece | Reuse? | Why |
|---|---|---|
| **`Move and Stack Items`** | ✅ **Yes** | Takes explicit `Source Inventory` / `Target Inventory`, so it moves bench → chest without owning either. `Remaining` handles the full-chest case. This is the deposit stage, done. |
| **Subclassing `ItemDistributor`** | ✅ **Yes** | `ThrallItemDistributor` / `PetItemDistributor` are exactly this. A `StockerItemDistributor` is a **new asset** — no override, no conflict. |
| **`AmountToMove` / `Quantity to Move Per Cycle`** | ✅ **Yes** | The paced-transfer knob our "slow cadence" wants. |
| **`ItemDistributorController` + `Add Distributor`** | ⚠️ **Probably** | A ready-made timer-driven cycle (`GlobalDistributeItems` → `Distribute Items` per registered distributor). *But* its interval is tuned for feeding and reads `BP_ServerSettings`; registering may make other systems treat Amadan's Desk as a feeder. Evaluate before adopting; a private timer is the fallback. |
| **`Get Registered Distributors` / `ItemRequester`** | ❌ **No** | Requester = a thrall/pet **with a diet**, not a storage container. This is *not* nearby-container discovery. We still write our own overlap query for deposit targets. |

**The architectural fit is uncanny.** "A placeable that pushes items into nearby things on
a timer" is precisely the feeding box. Amadan's Desk becomes a `StockerItemDistributor`
whose source is an enrolled bench and whose targets are nearby storage — the same shape,
different cargo. We bypass the built-in requester scan by calling `Move and Stack Items`
with our own source/target.

**What this deletes from P1:** the stack-splitting maths, the partial-fill handling, the
pacing timer, and the "how do I even move an item" question. What remains is genuinely
ours: the house-rules manifest, the four safety rules, and finding deposit targets.

### ✅ The foreign key is real — proven from the save database (2026-07-10)

Instead of a fragile Blueprint probe, the persistence question was answered from the
**ground truth**: Conan's single-player save is a **SQLite database**
(`…\ConanSandbox\Saved\Game_0.db`, with `Game_0_backup_1.db` = the prior save). Reading
it after a playtest:

- **`id` (integer) is the universal persistence primary key.** Every persistent object
  has one: mod controllers `1–17`, world buildables `18–25`, the character `26`.
- **It is the cross-table foreign key.** `actor_position.id`, `properties.object_id`,
  `item_inventory.owner_id`, `buildable_health.object_id`, `character_stats.char_id` all
  reference the same `id`. This *is* the reference-table-with-FK the design wanted — it's
  how the game itself relates inventory, health, and transform to an object.
- **A crafting bench is stored this way.** `properties` row: `object_id=18`,
  `BP_PL_Crafting_Bonfire_C.*` — benches get stable ids in the persistence tables.
- **Stocker persisted correctly.** `mod_controllers` + `actor_position` carry `id=17`,
  class `/Game/Mods/Stocker/Stocker_ModController_C`. Our mod controller is a real,
  saved row.

**Stability across save/load is a relational necessity, not an assumption.** The game
reloads a save by reading these rows *keyed by `id`*. If an object's `id` changed on
reload, its inventory (`owner_id`), health (`object_id`), and transform (`id`) would all
detach — the character would lose their items, buildings their health. The schema's
referential integrity *requires* `id` to be stable, exactly as a primary key must be.

The Blueprint `Get Unique ID` / `Get Actor By Unique ID` API is the runtime face of this
same database. So Amadan's Desk keying its house rules on a bench's persistence id is sound.

### Still to verify (down to two, both low-risk)
1. **Runtime Blueprint round-trip** — that a Blueprint can read a bench's `Unique ID` and
   reverse-resolve it via `Get Actor By Unique ID` at runtime. The DB proves the *object*
   is stably persisted; this confirms the *Blueprint API* surfaces it. Deferred to the P1
   build (where the real graph is authored anyway), now checkable against the DB ground
   truth. *(Optional empirical cross-check: reload the existing save once and diff
   `Game_0.db` vs `Game_0_backup_1.db` — matching ids across the reload boundary is
   direct observation of stability.)*
2. **`Move and Stack Items` is a plain Blueprint function, not an RPC** — so *we* gate the
   reclaim pass behind `Switch Has Authority`. Confirm the controller ticks server-side.

*(The bench `Is Open` visibility question is folded into P1 — the grace-timestamp rule can
key off inventory-change events regardless.)*

The entire mod remains conflict-free — no base asset overridden, no existing data-table
row contested.

## Bench API — the hooks P1 needs (verified from asset name tables, 2026-07-10)

| Need | Hook | Where |
|---|---|---|
| Skip active crafting (rule 1) | `CraftingQueue`, `QueueStarted` / `QueueEmpty`, `SignalCraftingQueueCleared` | `BP_PL_Crafting_Station` |
| Never touch fuel (rule 2) | `AcceptedFuels`, `AcceptedFuelTypes`, `IsConsumingFuel` | `BP_BAC_UsesFuel` |
| Don't-fight-me (rule 3) | **`Is Open`** (bool, exposed on the bench's Class Defaults) | `BP_PL_Crafting_Station` |
| Inventory-changed event | `SignalItemAdded` *(params: `item`, `index`, `srcInventory`, `srcIndex`)* | bench / inventory |
| Deposit (rule 4) | `AddItem`, `AddItemToStack`; `GetPopulatedItemCount` | `BP_Inventory`; `BP_ThrallFeedingContainer` precedent |

### ⚠ Inventory access looks **asynchronous**
`BP_BAC_CraftingStation` reads its inventory via **`LoadInventory`** + a
**`LoadInventoryCallProxy`** + **`LoadInventoryDelegate`**, keyed by an
**`InventoryUID`** (also `ProcessInventoryData`). If that is the only read path, the
reclaim pass **cannot be a synchronous read-then-write function** — it has to be
callback-driven. This is the one thing that could still reshape P1's control flow, and
it should be pinned before the graph is wired.

*(Other bench components seen on the shared parent: `PlaceableInventory`,
`CraftingIngredientsInventory`, `ArtisanRecipeInventory`, `ConanBuildingPersistence`,
`ThrallWorker`.)*

---

## Reference findings

Researched 2026-07-08/09; still valid, reframed for the new concept.

### Deposit rule — from Organizer Sorting Chest (Workshop 3723101055)

Custom placeable that, on insert or a radial trigger, scans containers within a radius
and moves each item into a container **already holding ≥1 of that type** (empty chests
never receive). Modes: whitelist / blacklist / any; a **"Sorting Excluder" item** opts
a chest out; transfer is **instant, no pathing**. → This is exactly our **deposit
stage**. Reusable primitives to find in the DevKit: query nearby placeables, read a
placeable's `PlaceableInventory`, test for an item type, move stacks between two
inventories.

### Pathing — from Living Settlements / the base settlement AI

Crafting bonuses are a **140 m radius aura** (thralls don't slot into stations or walk
to them to "work"). The **visible walking** is a **needs/schedule AI** that seeks
furniture, and — key for us — **`EQS_Work_<Profession>` queries path thralls to
crafting benches** by profession. Living Settlements is now a **base-game** system, so
this AI ships in the DevKit. → This is our **patrol** foundation: repoint "walk to your
work bench" into "walk to a bench with overflow and skim it."

### Container building blocks (official wiki + DevKit inspection)

Crafting benches are **placeable containers**. Base class **`BP_PlaceableItemContainer`**
(a Blueprint; native parent `ConanSandbox.PlaceableBase` via `BP_Master_Placeables`,
13 BP components); inventory lives in a **`PlaceableInventory`** component; storage via
**`BP_BAC_Storage`**; `Item Container Size` sets slot count. Inventory read/transfer is
Blueprint-accessible — see the container confirmation in
[`phase3-ai-inspection.md`](phase3-ai-inspection.md).

### Phase-3 AI decision

The "path to a placed object and interact" primitive is **UE5 SmartObjects**, and the
needs AI is data-driven and Blueprint-extensible. **Not blocked; Path A viable.** Full
Q1–Q6 analysis in [`phase3-ai-inspection.md`](phase3-ai-inspection.md).

### Golem follower framework (design lead worth keeping)

`Characters/Golems/` has `ThrallGolemNPC` + `GolemAIController` + `BT_GolemFollower` +
`BP_GolemGatheringComponent_*` (thralls that autonomously path out and **gather with
tools**). Even with the reworked concept, this remains the closest existing pattern to
"a follower that does autonomous collection work," and taught us the hard constraint
that **thralls only tick when a player is nearby** — the fact that reshaped this whole
design.

## Hard constraint: Blueprint-only

No C++. Every mechanic above must be reachable from Conan's existing Blueprint API;
confirm in the DevKit before committing to a phase.
