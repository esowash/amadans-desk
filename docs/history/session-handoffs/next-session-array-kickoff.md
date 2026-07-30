# Kickoff — Stocker next steps (after 3N)

> Rewritten 2026-07-16 after build 3N succeeded. Open this first next session.

## ★★★ 3N PASSED — thrash fixed. Candidates are storage-only.

Restock (3M) made benches reachable as both a tidy *destination* and a restock *source*, so two
benches with rules for the same item could ping-pong it every run. 3N closes that.

**The discriminator is the game's own:** chests carry a **`BP_BAC_Storage`** component; crafting
benches do not. Verified by grepping the shipped uassets — `Chest_Large`/`Chest_Medium` have it;
`CraftingStation_Wood` has none; `CraftingStation_Metal` has only `BP_BAC_TurnLightOnOff`;
`WorkStation_Artisan` has none. That beats a class allowlist we'd have to maintain as new chests ship.

**The fix went in the CALLER, not the function.** Both the tidy destination and the restock source are
drawn from `Candidates`, so filtering the gather makes benches unreachable in **both** directions at
once. `ApplyKeepRule` was untouched:

    ForEach c in GAC(BP_PlaceableItemContainer):
        c.GetDistanceTo(desk) < 3000                      ?
        IsValid(GetComponentByClass(c, BP_BAC_Storage))   ?    <- the whole fix
            -> Array Add -> ManagedContainers

`ManagedContainers` now means "storage in range", which is what it should always have meant. Altars
and forges drop out for free.

    STOCKER_3N storage candidates kept:
    2                                     <- was 3 benches + 2 chests; 3G counted 17 with altars/phantoms
    BP_PL_Chest_Medium_C_...
    BP_PL_Chest_Large_C_...
    --- pass1 tidy unruled ---
    10005 Bark        NoDestination  0
    16021 ShapedWood  NoDestination  0    <- THE CURE
    16002 IronReinf   NoDestination  0
    --- pass2 reconcile rules ---
    10011 keep=200    NoDestination  0
    12515 keep=300    NoExcess       0

**Save diff: empty.** Every rule satisfied or orphaned, as predicted.

**The test was a deliberate trap.** The world couldn't thrash on its own — no item sat in two benches,
so a filter would have passed while proving nothing. So we *created* the pathology: Shaped Wood moved
into the Artisan bench (Wood station 8, Artisan 7, no storage holding any). Without the filter the
Artisan qualifies and the 8 get `Moved` **into a bench**; with it, `NoDestination`. Different
outcomes, so the run discriminated. It read `NoDestination`, and the DB confirms 8/7 untouched.

Worth noting: this is the second design change `ApplyKeepRule` absorbed without modification
(opt-in→opt-out was the first). Filtering the input turned out to be the whole cure.

## 3M — tidy AND restock (prerequisite, same session)

`ApplyKeepRule` v2 makes a bench hold exactly `Keep` of an item, in **both** directions: excess goes
to storage, a deficit gets pulled back out. Six termini: `NoExcess` / `Moved` / `NoDestination` /
`InvalidInput` / **`Restocked`** / **`NoSource`**.

    STOCKER_3M --- pass1 tidy unruled (bench contents) ---
    10005  NoDestination  0        <- Bark
    16021  NoDestination  0        <- Shaped Wood
    16002  NoDestination  0        <- Iron Reinforcement
                                   <- Wood ABSENT: correctly skipped as ruled
    STOCKER_3M --- pass2 reconcile rules (tidy or restock) ---
    10011  keep=200  NoDestination  0
    12515  keep=300  Restocked      300     <- pulled from chest 59

**The entire save diff:**

    owner 56  WoodStation  LayeredSilk    0 -> 300   (+300)
    owner 59  LargeChest   LayeredSilk  600 -> 300   (-300)

Conserved 600→600. Wood untouched at 731. Unruled orphans untouched.

**A perfect mirror of 3L**: that build moved the Silk OUT because no rule protected it; 3M pulled 300
BACK because a rule now asks for it. Same item, same two containers. The only thing that changed
between them was one entry typed into a Details panel.

## ★ The forced asymmetry (3M's design insight)

**Restock cannot iterate bench contents.** An item the bench has ZERO of doesn't appear in its
`ItemList` — the absence *is* the deficit. So:

- **Tidy iterates the BENCH** — opt-out: everything present that no rule protects
- **Restock iterates the RULES** (`Map_Keys`) — you can only restock what a rule asks for.
  "Restock everything unruled" is meaningless.

Two passes, each item handled exactly **once**: pass 1 uses `Map_Find`'s **`bFound`** to *skip* ruled
items, which pass 2 then reconciles in whichever direction they need.

Worth remembering *why* this mattered: bolting restock onto 3L's single loop would have silently done
nothing and looked like a working build. And the proof it worked is an **absence** — Wood appearing
exactly once, in pass 2. Had the `bFound` polarity been inverted, pass 1 would have tried Wood with
`keep=0` and *still* orphaned, so the outcome would have looked identical.

**Also confirmed:** `bMoveAllAvailable=true` = "move UP TO quantity" in **both** directions — it
restocked exactly 300, not the chest's whole 600. And `Map_Keys` is IMPURE (exec pins), unlike
`Map_Find`.

## 3L — opt-out tidying (prerequisite, same session)

The first graph that names **no item at all**. It asks the bench what's inside, asks the `KeepRules`
map what to keep, and files away the rest. The only place an item id appears is the map, as data.

    STOCKER_3L begin (opt-out tidy of the Wood station)
    5                                   <- items enumerated off the bench
    10011  keep=200  NoDestination  0   <- Wood; the MAP lookup resolved
    10005  keep=0    NoDestination  0   <- Bark
    16021  keep=0    NoDestination  0   <- Shaped Wood
    12515  keep=0    Moved          200 <- Layered Silk -> chest 59
    16002  keep=0    NoDestination  0   <- Iron Reinforcement

**The entire save diff:**

    owner 56  WoodStation  LayeredSilk  200 -> 0    (-200)
    owner 59  LargeChest   LayeredSilk  400 -> 600  (+200)

Silk conserved 600→600. Wood untouched at 731. All three orphans untouched.

**`keep=200` on Wood is the line that mattered.** A failed map lookup would give `keep=0`, try to move
all 731, and *still* orphan — an identical outcome from a broken lookup. Only the printed `keep`
separates "the rules table works" from luck. Print the thing that discriminates, not just the result.

**Three things proven at once:** enumeration (`ItemInventory.ItemList` → `Array<GameItem>` →
`GameItem.TemplateID`); the rules table as **data** (a `Map<int,int>` member edited in the Details
panel, not graph literals); and opt-out **with no conditional** — `Map_Find` returns 0 for an absent
key, and 0 *is* "keep nothing". `ApplyKeepRule` was unchanged throughout.

## ★ Two things that look like functions and aren't

`GetItemList` and `GetTemplateId` are **native member VariableGets**, not calls:

- `ItemInventory.ItemList` → Array of `/Script/ConanSandbox.GameItem`
- `GameItem.TemplateID` → int

The ccmod api index lists their *getter* names from the name table, so they never appear as
`CallFunction`s in any EventGraph — three pulls were wasted hunting them. **The api index reads the
whole asset** (function graphs, macros, variable names) **while Ctrl+A only copies the graph you're
standing in.** It is good for *"does this exist and who uses it"*, useless for *"where can I copy it
from"*. Same trap hit `Subtract_IntInt` and `IsValid`. **Find nodes by dragging off a typed pin with
Context Sensitive ON** — that asks the type what it really offers, and it has never once been wrong.

## 3K — the reusable mover (prerequisite, same session)

`BPFL_Stocker2::ApplyKeepRule(Station, TemplateID, Keep, Candidates) -> (Moved, Outcome)` — a static
Blueprint Function Library function — was called three times from the ModController with different
parameters. Each took a different path to a different terminus. All three as predicted:

    STOCKER_3K begin (3 house rules via BPFL_Stocker2)
    STOCKER_3K rule1 IronBar@Blacksmith keep20 ->      NoExcess        0
    STOCKER_3K rule2 StarMetal@Blacksmith keep20 ->      Moved          480   (log label said HardenedSteel; id 18061 is Star Metal Bar)
    STOCKER_3K rule3 Wood@WoodStation keep200 ->       NoDestination   0

**The save diff against the baseline was ONLY:**

    owner 57  HardenedSteelBar  500 -> 20   (-480)
    owner 65  HardenedSteelBar  500 -> 980  (+480)

Nothing else in any container changed. So `NoExcess` is genuinely inert, `Moved` is exactly
conservative, and **the orphan path moved nothing** (Wood still 731) — the failure mode that would
have undermined the whole terminus design. The ModController no longer moves anything itself: it
gathers candidates and calls a function.

**Everything is now directly observed working:** find (3G), scope (3H), collect (3H), read (3G),
select (3I), move (3I), and parameterised via a reusable function with four termini (3K).

## The mover

    ApplyKeepRule(Station: Actor, TemplateID: int, Keep: int,
                  Candidates: Array<BP_PlaceableItemContainer>)
        -> Moved: int, Outcome: E_Stocker_Outcome

    InvalidInput   - station's inventory didn't resolve      (untested; safest path)
    NoExcess       - station at or under Keep                (3K)
    Moved          - excess moved to the first holder        (3K)
    NoDestination  - excess exists, nothing else holds it    (3K) <- ORPHAN

Destination is automatic: first candidate already holding >0 of the item, excluding the source
itself. The orphan path is structurally incapable of moving anything — the move node exists only
inside the found-destination branch. `Moved` vs expected also reveals partial moves, so no fifth
state is needed.

Live assets: **`BPFL_Stocker2`** (function library), `E_Stocker_Outcome` (enum), `ManagedContainers`
(member array on `Stocker_ModController`). The first attempt, **`BPFL_Stocker`, is broken** — an
Object Blueprint, not a library. Delete it if still present.

## ★ Next: persistent identity — the answer already exists and is unused

`GetUniqueID` is called by **BP_BAC_CraftingStation**, **BP_BAC_Storage** and
**BP_Master_Placeables** — the exact components on our benches and chests. `GetActorByUniqueID` does
the reverse lookup (used by `BP_PL_ThrallTrade_Master`, which we've mined before), and
`EqualEqual_UniqueIDUniqueID` compares them. So the shipped game's own answer to "remember this
placeable and find it again later" is a **UniqueID ↔ Actor round-trip** — a first-class Blueprint
concept, not something to synthesize from the save DB.

**This is the missing piece of the design lesson** we banked six sessions ago: bind rules to stable
container identity, never to enumeration.

**NOT YET SPIKED.** Verify a UniqueID survives a relaunch before designing on it. It's cheap and it
decides the schema, so do it first.

## The rules schema (agreed, not yet built)

With UniqueID it's **one flat array**, not the "complicated set of tables" we expected:

    S_KeepRule { Container: UniqueID, TemplateID: int, Keep: int }

"Several rules per bench" = several entries sharing a `Container`. Filter, don't nest. Execution
resolves via `GetActorByUniqueID`, which means **the GAC + range scan from 3H stops being the
execution path** and becomes only the *enrollment* path — the UI's "pick a bench in range" list.

`TemplateID` stays an **int**, deliberately. The whole Conan item API speaks int template ids
(`AddItemTemplate`, `HasItemByTemplateID`, `FindItemByTemplateID`, `GetNumberOfItemsByTemplate`,
`MoveItemsByTemplateId`), so a table handle would be unwrapped back to an int on entry and would weld
the mover to one table asset. The ItemTable's row keys ARE the template ids, so a handle carries no
extra safety either. That richness belongs in the UI layer, which has **`GetDataTableRowNames`** (198
uses) to populate the item picker and **`GetNameFromTemplateID`** (10 uses) to label it "Iron Bar".

## Semantics: OPT-OUT (user, 2026-07-16)

**House rules describe what should be KEPT in the bench at all times** — arrow materials, repair
stock, parts for quick replacements. **Everything else gets tidied away into storage.** This matches
`docs/design.md`'s original framing of Stocker as "a reclaimer that skims excess materials off
benches".

**The rules don't change shape — only the default does.** Opt-out is exactly:

    for every item in the bench:
        keep = that item's rule Keep, or 0 if no rule names it
        ApplyKeepRule(station, template, keep, candidates)

So **`ApplyKeepRule` is UNCHANGED** — same signature, same four termini. An unruled item is just a
rule with `keep=0` that nobody had to type.

### The one missing primitive: bench enumeration

"What's actually in this bench?" — deferred since 3G. The API has it, none captured yet:

- **`GetItemList`** (11 uses) → the item objects
- **`GetItemAtSlot`** (38) + **`GetPopulatedItemCount`** (33, already used in 3B/3D) → index-based
- **`GetTemplateId`** (3) → template id off an item object

**Hazard:** don't enumerate item OBJECTS while moving items out from under the iteration — they may
go invalid. **Two passes:** collect template ids first, then act on the id list. A function's LOCAL
variables make this easy (locals are made in the UI, like member vars). **Duplicates self-handle:**
`MoveItemsByTemplateId` works by template, not by stack, so a second stack of the same template hits
`NoExcess` on the second call.

### ★ Consequence: NoDestination becomes the COMMON case

A working bench accumulates bark, twine, seeds and half-finished parts that no chest has ever held.
Applied to the real Wood station (2026-07-16):

| Item | Rule | Keep | Excess | Destination | Outcome |
|---|---|---|---|---|---|
| Wood 731 | yes | 200 | 531 | none | **NoDestination** |
| Layered Silk 200 | no | 0 | 200 | chest 59 (400) | **Moved** |
| Bark 2 | no | 0 | 2 | none | **NoDestination** |
| Shaped Wood 15 | no | 0 | 15 | none | **NoDestination** |
| Iron Reinforcement 5 | no | 0 | 5 | none | **NoDestination** |

**Four of five orphan.** Under opt-in this was a rare edge case; under opt-out it's the normal
outcome and the mod's main activity. The orphan design is therefore load-bearing, not a nicety — and
it's why `NoDestination` being a real logged terminus rather than a silent skip matters.

## ★ Pinned: smelters / multi-station — and why it's blocked

**Smelters need tidying too, and the class naming won't help you:**
`BP_PL_CraftingStation_Furnace`, `_Bloomery`, `_Kiln` **are** named CraftingStation;
`BP_PL_Forge`, `BP_PL_FirstMenForge`, `BP_PL_Forge_Anvil` are **not**. A per-class pass needs a list
that rots and still misses modded stations.

**Use the complement of 3N's storage filter — it's already computed.** The gather Branch sorts every
in-range container into two buckets; we discard one:

    Branch( IsValid(GetComponentByClass(c, BP_BAC_Storage)) )
        true  -> ManagedContainers   (chests -- candidates)           [3N does this]
        false -> ManagedStations     (benches/furnaces/forges/kilns)  [one extra Array Add]

Naming-agnostic — it asks the game "are you storage?" instead of "are you on my list?". None of the
furnace/forge/kiln classes carry `BP_BAC_Storage`, so they all land correctly on the false side.

**⚠ But it's blocked, and the reason reorders the queue.** The complement also sweeps up **altars**
(which hold offerings placed deliberately), **beds**, and **the desk itself**. Tidying an empty one is a
no-op — nothing in its `ItemList`. **But pass 2 iterates RULES, not contents.** With a *global*
`KeepRules`, `{10011: 200}` applied to a bed reads "0 Wood, deficit 200, a chest has Wood" →
**restock 200 Wood into your bed**, and into every altar.

**Multi-station is blocked on PER-BENCH rules, not on finding stations.** `KeepRules` must key on
*which* container — exactly what the UniqueID spike is for. **The smelter riff and the identity spike
are the same task.** Don't build the complement until rules are per-station.

## ★ Order of work (user, end of session 6)

**"Concentrate on Identity, then the table UI and thrall."**

1. **★ IDENTITY — start here.** Spike whether `GetUniqueID` survives a relaunch: print each
   container's id, quit, relaunch, compare; then check `GetActorByUniqueID` round-trips. Small, and
   **it gates everything** — per-station rules, multi-station, and the UI's "pick a bench" list.
   Descoped from 3L on purpose: it returns an unfamiliar struct and printing it needs an unverified
   conversion (`Conv_UUIDToText` exists, but so do BOTH `EqualEqual_UUIDUUID` and
   `EqualEqual_UniqueIDUniqueID`, so UUID and UniqueID may differ). Its own small cook.
2. **THE TABLE UI** — Amadan's Desk. The real unknown: **UMG widget hierarchies are NOT graph nodes**,
   so the T3D pipeline doesn't reach them and it's unknown how much must be hand-built. Pieces found:
   `GetDataTableRowNames` (198 uses) for the item picker, `inventory/get_name_from_template_id` to
   label it (**returns Text, not String**).
3. **THE THRALL** — Amadan Cnoic, the follower the mod is named for. Undesigned. Groundwork from the
   api harvest: `GetThrallComponent`, `SpawnThrall`, `RunBehaviorTree`, `GetFollowingThralls`,
   `SmartObjectSlotComponent`.

Later: **orphans** (mechanism solved, two questions PINNED — see below), **multi-station/smelters**
(blocked on Identity), **the repeating timer** (still single-shot off BeginPlay + Delay(8s)).

`docs/design.md` is authoritative for house rules.

## Testing

**Reset the world from the baseline, never by hand.** `Saved\Game_0_stocker_baseline.db`
(sha `eb29fc82…`) — game closed, copy over `Game_0.db`, verify the sha. It encodes the three-terminus
matrix above. The game rotates its own `Game_0_backup_1..8.db` every save, so never park a reference
snapshot there.

**The matrix is one stack away from breaking:** rule 3 is an orphan only because nothing else in
range holds Wood. A single Wood in Medium chest 65 turns it into `Moved 531`. That happened once,
via a save reset. **Always re-derive the expected matrix from the DB — never predict from memory.**

**The save-DB quantity reader has a bug.** "Stack qty = the uint32 before the `16 00 00 00` marker"
is NOT universal — it reported **2 where the truth was 1**, twice. Reliable stacks are 131-byte blobs
laid out `03 00 00 00 | 01 00 00 00 | <qty uint32> | 16 00 00 00` (verified 1000/500/981/731/20). The
odd one was 123 bytes, where the pre-marker bytes are the *template id*, not that header. **Prefer
the mod's own `GetNumberOfItemsByTemplate` printouts for small stacks.**

## Standing gotchas

- **★ Blueprint Function Libraries cannot be created via Blueprint Class → All Classes.** That only
  picks a *parent* and silently gives an Object Blueprint whose functions aren't static; the call
  node then errors *"this blueprint (self) is not a X, therefore Target must have a connection."* The
  asset **type is fixed at creation** — you cannot reparent (BPFL won't appear in the dropdown).
  Correct: **Right-click → Blueprints → Blueprint Function Library**. **Tells of a real one:** the
  entry node has a `__WorldContext` pin, and the call node's `self` is `bHidden=True` with
  `DefaultObject` = the library CDO. Verify the asset's *type*, not its name:
  `grep -aoc BlueprintFunctionLibrary <the uasset>`.
- **★ A Blueprint (user-defined) enum's entries are really `NewEnumeratorN`** — your labels are
  DISPLAY names. Setting an enum pin's DefaultValue to the label fails to compile. Native enums
  differ, which is why `inventoryType="PlaceableInventory"` always worked. Print with
  `K2Node_GetEnumeratorNameAsString` ("Enum to String") for friendly labels.
- **★ Function entry nodes cannot be pasted OR deleted.** UE rejects an incoming one ("one node
  couldn't be pasted") and silently drops every link that referenced it. Generate the body without
  an entry and hand-wire its pins; route fan-outs through **knot** nodes so it's one drag per pin.
- **★ Never leave a captured wildcard pin unresolved** — type it in the build script. UE resolves
  wildcards at paste time from whichever link it processes first, which is a race. Cost 3I a compile.
- **★ Palette searches: Context Sensitive ON, and drag off the target pin.** Global searches gave us
  `IsValid_InstancedStruct` (takes a struct) and a Universal Object Locator `ToString`.
- **T3D paste resolves object refs with `FindObject`, not `LoadObject`** — a class whose asset isn't
  already loaded **silently pastes as null**. Load referenced assets first, or set the dropdown by
  hand. Verify with `grep -aoc "<ClassName>" <the uasset>` — class names survive as ASCII in the
  *source* uasset, but not in the cooked pak.
- **The DevKit has no `Content/DLC`** — DLC classes cannot be referenced from a mod at all. Verify
  any class path against `C:\CEUE5Devkit\UE4\Content\...` before building on it.
- **SAVE must fully land BEFORE Build mod.** Cost a whole playtest on 3E.
- **Install `Output/Stocker.pak`** (~486 KB, combined), NOT `Staged/Stocker-Windows.pak` (~155 KB
  IoStore split, whose banner lives in the `.ucas`).
- **Gate on `sha256sum` of the installed pak == the build output.** The banner is not sufficient when
  iterating within one build letter — old-3H and new-3H both print `STOCKER_3H`.
- **Mods only mount if ENABLED in the in-game Mods menu.** Gate every playtest on the log showing
  `Mounting mod pak file:` AND `AddActiveModControllerClass: /Game/Mods/Stocker/...`.
- **Relaunch after replacing the pak** — mods mount at startup. Check the game isn't already running.
- Member variables, enums, function signatures are made in the DevKit UI; nodes come via clipboard.

## Handy references

- Test items (decoded from the real `Items/ItemTable.uasset` — find `ItemTable_<id>_Name`, the display
  name is the printable string just before it): Iron Bar **11501**, Wood **10011**, Layered Silk
  **12515**, **Star Metal Bar 18061** (NOT "Hardened Steel Bar" — an earlier note claimed that from a
  community DB and was wrong; the id was always right, only the label). Also present: Bark 10005,
  Iron Reinforcement 16002, Shaped Wood 16021, Twine 14174, Seeds 13015, Leavening Agent 18001.
  At runtime `GetNameFromTemplateID` does this properly.
- Actors: 56 Wood station, 57 Metal station (Blacksmith), 59 Large chest, 65 Medium chest, 68 Artisan
  workstation (empty), **69 Stygian table = desk anchor** (unique, 0 inventory), 26 player.
- Build scripts `.ccmod/scripts/build_3{e,f,g,h,i,j_function,k}.py`; graphs `.ccmod/graphs/`.
- Bricks: shared in `claude-conan-modder/library/`; mod-specific in `.ccmod/library/stocker/`.

## ★★ The orphan plan — SOLVED mechanism, unblocked (2026-07-16)

**The plan:** orphans get dumped into **specialist storage containers** — (1) **DLC boxes first**
("if the player paid for a special box, honour that commitment"); (2) then any specialist box; (3) any
left over, **fail safe: don't move at all** (today's `NoDestination`). Not built; discovery mostly done.

### The mechanism: `ItemInventory.BlackWhiteList`

Captured as `inventory/get_blackwhitelist`. Ground truth from the node:

    VariableReference=(MemberParent="/Script/ConanSandbox.ItemInventory",
                       MemberName="BlackWhiteList")
        self           (in)  -> ItemInventory
        BlackWhiteList (out) -> cat="int", ContainerType=Array      ARRAY OF INT

1. **It's on `ItemInventory`**, not the chest actor — we already hold that via `GetInventoryByType`.
   No cast, no subclass, no class reference.
2. **`Array<int>` of TEMPLATE IDS** — the currency `ApplyKeepRule` already speaks.
3. **★ The DLC problem evaporates.** `BP_PL_Special_Chest_*` are absent from the DevKit and
   unreferenceable — but we never name them. We ask their inventory what it accepts.

**A specialist chest has NO logic** — `api asset BP_PL_Chest_Medium_Wood` -> **calls (0)**. It's a
plain `BP_PL_Chest_Medium` plus a material plus a BlackWhiteList value; they share one mesh. Pure config.

Decoded from the shipped uassets:

| Box | list |
|---|---|
| Wood (6) | Wood, Dry Wood, Branch, Bark, Shaped Wood, Insulated Wood |
| Stone (14) — the "ores box" | Stone, Silver/Goldstone, Ironstone, Corrupted Stone, Brimstone, Star Metal Ore, Obsidian, Black Ice, Coal, Crystal, R/B/G Crystal |
| Metalworking (17) | the ores + Iron/Steel/Gold/Silver/Star Metal/**Hardened Steel** Bar, Eldarium, Decaying Eldarium, Khari Steel, Composite Obsidian |
| plain `Chest_Medium` | **none** — empty = accepts anything |

**⚠ The decoder is a heuristic, not a parser.** It scans for a length-prefixed int run whose entries
all resolve to real ItemTable rows. It **failed on Plants/Hides/BloodCrystals** and produced **garbage
for the Icebox** (True Names + Potions). Don't trust those rows — irrelevant to the build, since at
runtime we read the real property. The decode only existed to learn the shape.

Corroboration it threw off: **`18062` = Hardened Steel Bar**, so `18061` = Star Metal Bar is right and
the old note was off by exactly one id.

**Every specialist chest carries `BP_BAC_Storage`**, so 3N's storage filter already accepts them.

`BlackWhiteList` is used by everything that restricts its contents — the six specialist chests, the
icebox, feeding containers, campfires, compost, the dismantler, animal pens. One shared concept.

### ⚠ PINNED BY THE USER — do not pursue until we start building the orphan function

1. **Allow-list or deny-list?** The name permits either and **no companion flag was found** (not in the
   chest assets; the api knows no `bIsBlackList`/`bWhiteList`). Evidence says ALLOW — the Wood box
   lists wood — but that's inference. **Cheap test: try putting an Iron Bar into the Wood box in-game.
   If it refuses, it's an allow-list.** Verify before building on it.
2. **★ Identifying a box as DLC at runtime, without its class** — unsolved, and exactly what pass 1
   needs. `GetDisplayName` gives `<ClassName>_<instanceId>`, so a substring test for `Special_Chest`
   would work but is brittle. No marker property found.
3. **Do DLC and base boxes have identical lists?** If so, only the DLC preference distinguishes them —
   i.e. question 2.

### How it would slot in

`NoDestination` is the hook and that path can't move anything, so extending it is additive. Likely
shape: pass a **different candidate list** (boxes whose BlackWhiteList contains the orphan's template
id) rather than touching `ApplyKeepRule`. Needs `Array_Contains` (not captured yet).
**The function has now absorbed THREE design changes untouched — opt-in->opt-out, the thrash fix, and
this — every time by filtering its input. Try that first.**

## ⚠⚠ The save baseline is now DESTRUCTIVE — do not restore it

`Saved\Game_0_stocker_baseline.db` (sha `eb29fc82…`) was taken at 18:17, **before** the specialist-box
laboratory was placed. **Restoring it would DELETE 14 actors**: all six base-game
`BP_PL_Chest_Medium_*` boxes (ids 70–75), all five DLC `BP_PL_Special_Chest_*` boxes (76–80), both
furnaces (81, 82), and the Icebox (84). Same for `Game_0_pre3{L,M,N}.db` — fine as diff references,
dangerous as restore points.

**Before using a reset baseline again: re-take one from a settled save (game CLOSED), verify it
contains actors 70–84, and only then treat it as the reset point.** Probably just delete the old one.

The reason a baseline exists still holds: a save reset once silently put 1 Wood back into Medium chest
65, which would have turned an orphan test into a move test that proved nothing. **Always re-derive
the expected matrix from the DB before predicting a result — never from memory.**

## The lab that's now placed (enumerated 2026-07-16 20:36, game was RUNNING — re-check when settled)

In range of the desk (actor 69): **2 furnaces** (81 `CraftingStation_Furnace`, 82 `_Furnace2`) ·
**6 base-game specialist boxes** (70–75: `Chest_Medium_` Wood/Stone/Hides/Plants/Metalworking/
BloodCrystals) · **5 DLC specialist boxes** (76–80: `Special_Chest_` Wood/Hides/Stone/Plants/
Bloodcrystals) · **1 icebox with contents** (84) · plus the bed (64), the desk (69), and
`BP_Shop_LostDungeon_Foundation` (55, not a container). All eleven specialist boxes are **empty**,
which is ideal — nothing to pollute a test.

Working actors: 56 Wood station, 57 Blacksmith, 68 Artisan bench (holds 7 Shaped Wood from the 3N
trap), 59 Large chest, 65 Medium chest.
