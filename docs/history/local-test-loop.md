# Local mod test loop + the persistence probe

---

## ▶ RESUME HERE (next session start) — updated 2026-07-12 (session 3)

**Source-selection is SOLVED. The write no-op is the open problem — and it is NOT the transfer
function.** Build **"3B"** is authored, cooked, installed, and playtested (this session was driven
entirely through `ccmod`: the `.ccmod/` workspace, the captured `MoveAndStackItems` brick, and a
Python T3D edit of the full graph → single clipboard paste). The graph picks the source chest
**by content** and that works. Session 3 swapped `MoveItemsByTemplateId` → **`MoveAndStackItems`**
(on the ItemDistributor component; the getter returns a valid object — no Accessed-None). Result:
**`Remaining=0`, moved nothing, `Game_0.db` unchanged** — identical to `MoveItemsByTemplateId`.
**Two independent transfer functions fail identically, so the suspect is now the inventory object,
not the function.** `PlaceableInventory` is a read proxy (reads reflect state, writes don't
persist).

**⚠ CONFOUND FOUND (2026-07-12 save-DB gut-check): the "no-op" chests were ~2.6 km from the
player.** Both no-op tests targeted Medium chests 35/36, which sit at `(-55760, 253050)` next to a
corpse — **~260,000 units from the player** at `(-96181, -3681)`. So the write may have failed
because the target actors were **streamed-out / not the authoritative loaded instance**, not
because `PlaceableInventory` is unwritable. The read-proxy conclusion is **not yet safe** — retest
in the loaded player chunk before trusting it.

**TESTING SCOPE — from now on, use ONLY the player-chunk containers (owner ids 56–59), all ~400–650
units from the player:**
| owner | actor | contents (template ×qty) |
|---|---|---|
| 58 | `BP_PL_Chest_Large` | `12515` ×400 |
| 59 | `BP_PL_Chest_Large` | `11501` ×2 · `18061` ×500 |
| 57 | `BP_PL_CraftingStation_Metal` | `11501` ×1000 · `18061` ×500 |
| 56 | `BP_PL_CraftingStation_Wood` | `10005` ×2 · `10011` ×1002 · `12515` ×200 |

Do **not** target `BP_PL_Chest_Medium` (35/36) anymore — they're the far/stale pair.

**THE NEXT LEVER (Bug 2), reframed: prove a move persists in the player chunk first.**
- **3C test:** target the two **Large** chests (58/59) — `GetAllActorsOfClass(BP_PL_Chest_Large)`
  returns exactly those two, both loaded — pick source by content, move a template the fuller
  chest actually holds (e.g. `18061`), verify `Game_0.db` changes. If it persists ⇒ root cause was
  **distance/streaming**, and we have a working move. If it still no-ops ⇒ it really is the
  inventory object/authority, and the next levers below apply.
- If still failing on loaded chests: inspect `BP_PlaceableItemContainer` for a non-proxy inventory
  accessor (real `ItemContainer`/`Inventory` vs. replicated `PlaceableInventory`); study the game's
  own "transfer all" server path; check authority (`Stocker_ModController` may lack authority to
  mutate a placed container; graph has no `Switch Has Authority` gate).

<details><summary>superseded session-2 note (function-swap hypothesis — now disproven)</summary>

**Source-selection is SOLVED. The open problem is the transfer function itself.** Build
**0.1.5 (increment "3A")** is authored, cooked, installed, and playtested. The graph now
picks the source chest **by content** (not by array index), and that works. But the actual
item move **still transfers nothing** — and we've now ruled out the argument tuning, so the
next move is to change the *function*.

**Use `ccmod` next session.** A companion tool — `claude-conan-modder` (CLI `ccmod`) at
`C:\Users\<user>\claude-conan-modder` — was built specifically to do this T3D authoring
without hand-rolled Python. It parses/generates T3D losslessly, mints GUIDs, writes reciprocal
`LinkedTo`, has a git-tracked **library of captured node "bricks"** (shared + per-mod), a
clipboard bridge, and a read-only `Game_0.db` reader. This session hand-built a one-off
generator (`scratchpad/gen_graph.py`) instead — **the next session should drive `ccmod`.** See
its `README.md` / `prompt.md`. The Stocker mod should grow a `.ccmod/` workspace library.

**The 3A graph** (`Stocker_ModController`, server harness, on BeginPlay → Delay 8s):
`GetAllActorsOfClass(BP_PL_Chest_Medium)` → `arr[0]`,`arr[1]` → read each chest's
`PlaceableInventory` → `GetPopulatedItemCount` of each → **Branch on `cnt0 > cnt1`**: the
fuller chest is Source, the other is Target → `ItemInventory::MoveItemsByTemplateId(self=src,
templateID=10001, quantity=999, bMoveAllAvailable=false, targetInventory=tgt)` → print the
returned count. (Two symmetric branches so it's order-independent.)

**What the playtests proved (2026-07-12):**
- **Selection works.** Log shows `STOCKER_3A src=chest0 (moving 10001 -> chest1)` — the branch
  correctly identified the stocked chest (36, holding template 10001) as source. `GetPopulated
  ItemCount` reads are reliable (they drive the branch).
- **The move is a no-op.** `MoveItemsByTemplateId` returned **0** and `Game_0.db` was
  **unchanged** (chest 36 still holds 10001/10011/13015; chest 35 still empty) under BOTH
  arg combos tried: `(quantity=0, bMoveAllAvailable=true)` and `(quantity=999,
  bMoveAllAvailable=false)`. No error/warning in the log at the move's frame. So the params
  aren't the problem — the function itself isn't transferring.
- **Leading hypothesis:** `PlaceableInventory` returns an `ItemInventoryReplicateToAll`
  wrapper. Reads reflect state, but `MoveItemsByTemplateId` on that wrapper may not touch the
  authoritative inventory (or doesn't mark persistence dirty). Reads work; writes don't.

**THE FIX to try next — switch the transfer function to `MoveAndStackItems`.** This is the
primitive Conan's own **Item Distributor** (thrall/pet feeding system) uses in production —
`UE4/Content/Systems/Building/Placeables/ItemDistributor.uasset` references it 42× with a
`Remaining` return; params look like `(TemplateID, Amount, Source, Target) → Remaining`. It is
a method on the **ItemDistributor component**, which `Stocker_ModController` already has (note
the benign startup warning `Couldn't find native parent component 'Sprite' for 'ItemDistributor'`
— verify the component is actually functional). We were about to **capture its exact node
signature** (right-click graph → "Move and Stack Items", uncheck Context Sensitive if needed →
copy) when this session paused. Next session: capture it (via `ccmod capture`), swap it in for
`MoveItemsByTemplateId`, wire its target to the ItemDistributor component getter, and add
before/after `GetPopulatedItemCount` prints on **both** src and tgt so the log shows the
in-memory effect directly (distinguishes "didn't move" from "moved but didn't persist").

</details>

**Env facts pinned this session** (still current):
- **Cook cache can go stale within the same minute.** A save + Build-mod in the same minute
  produced a pak with the *old* graph (incremental cook skipped the change). Fix: delete
  `UE4/Saved/Mods/_Cooked/<Platform>/ConanSandbox/Content/Mods/Stocker/` (all platforms) AND
  the game's `Saved/ExtractedMods/Stocker-Windows.*` before rebuilding. **Always verify the
  installed pak** contains the new banner (`grep -aoE "STOCKER_[0-9][A-Z]" <pak>`) *before*
  playtesting — caught a stale 2C pak that wasted a launch.
- Source uasset:
  `/c/CEUE5Devkit/UE4/Content/Mods/Stocker/Local/Stocker_ModController.uasset`.
  Built pak: `/c/CEUE5Devkit/UE4/Saved/Mods/Stocker/Output/Stocker.pak` →
  install to `…/Conan Exiles/ConanSandbox/Mods/Stocker.pak`.
- `Game_0.db` has no sqlite3 CLI; read it with Python stdlib. `item_inventory(item_id,
  owner_id, inv_type, template_id, data)`; chests are `inv_type=4`. Chest 35 empty, chest 36
  stocked (10001/10011/13015). Snapshots in the session scratchpad (`before.db`, `after*.db`).

**Authoring reminder:** direct GUI node-wiring by a real-moused human (guided step-by-step) is
reliable; the earlier unreliability was about *computer-use pixel control*. T3D paste (now via
`ccmod`) is the low-friction path. Verify a save by grepping printable strings in the **source**
uasset (cooked = bytecode). Cook time is variable (2–6 min).

---

Fast iteration path that skips the Steam Workshop: build the mod, drop the pak into
the game's own `Mods` folder, point `modlist.txt` at it, launch normally. Established
2026-07-10 for the persistence test.

## The loop (what Claude does)

1. **Build** in the Dev Kit — Mod Info → *Build mod*. Produces
   `C:\CEUE5Devkit\UE4\Saved\Mods\Stocker\Output\Stocker.pak` (a self-contained,
   single-file pak — the same shape a Steam subscription delivers; e.g. Workshop mods
   appear as one `Emberlight.pak`).
2. **Install** — copy that pak to
   `…\steamapps\common\Conan Exiles\ConanSandbox\Mods\Stocker.pak`.
3. **Activate** — **do NOT pre-write `modlist.txt`.** ⚠️ *Corrected 2026-07-10 after the
   first run.* The game discovers mods **two ways at once**: it **auto-scans `Mods\`**
   *and* it reads `modlist.txt`. Pre-seeding `modlist.txt` with an absolute path made the
   game see the same pak twice (once via the scan as a forward-slash path, once via the
   list as a backslash path) and list **two identical "Stocker" mods** in the menu.
   - **Correct loop:** drop the pak in `Mods\`, leave `modlist.txt` empty, and **enable
     Stocker once in the in-game Mods menu**. The game writes the single canonical entry
     itself. On later rebuilds you just overwrite `Mods\Stocker.pak` — it stays enabled,
     and the hash-keyed `Saved\ExtractedMods\` cache re-extracts automatically when the
     content changes.
   - `-modlist=<file>` is the CLI escape hatch; `RequestRestartWithDefaultModlist`
     recovers if a mod wedges the game.
4. **Read the result** — `…\ConanSandbox\Saved\Logs\ConanSandbox.log`. Blueprint
   `Print String` output lands under **`LogBlueprintUserMessages`** (confirmed present in
   this Shipping build; `Print to Log` defaults true).

### Facts pinned this session
- Game is `ConanSandbox-Win64-Shipping.exe`, but `Print String` **survives** — the base
  game's own Blueprints log via `LogBlueprintUserMessages`.
- **The Dev Kit's *Build mod* rewrites `modinfo.json` on every build**, resetting
  `bRequiresLoadOnStartup` to `false` (the panel field isn't exposed). So the packed flag
  is `false` for now. Mod Controllers are auto-discovered and instantiated when their pak
  mounts (every Funcom DLC in the log loads via `AddActiveModControllerClass` regardless),
  so this *probably* doesn't block the probe — but it is **suspect #1** if the banner
  never appears.
- Mods do **not** need a `.sig` file (Workshop mods ship the bare `.pak`).
- BattlEye is present but gates online play only; single-player is unaffected.
- Mods **alter the save** — always test in a throwaway single-player world.

## The probe (v1 — pipeline validation) — ✅ PASSED 2026-07-10

`Stocker_ModController` (parent = native `ModController`) with the minimal graph:

```
Event BeginPlay → Print String "STOCKER_PROBE: ModController BeginPlay reached"
```

**Result — the whole pipeline works.** From the game log (first run):
```
LogModManager: Mounting mod pak file: …\Mods\Stocker.pak
LogModManager: AddActiveModControllerClass: … (all DLC + ours)
LogBlueprintUserMessages: [Stocker_ModController_C_2147477000] STOCKER_PROBE: ModController BeginPlay reached
```
Confirmed:
- A locally-installed pak mounts and the Mod Controller is discovered + instantiated.
- **`Print String` reaches the log in the Shipping game** (`LogBlueprintUserMessages`).
- **`bRequiresLoadOnStartup=false` did NOT block it** — that worry is retired. Mod
  Controllers load on pak-mount regardless.
- The banner fired **once** despite the double-mount duplicate above (mount deduped by
  hash), so double-listing didn't double-run — but it's cleaned up for v2 anyway.

The harness is proven; the v2 probe (the real persistence read) builds on solid ground.

## The v2 probe (persistence read — to be built after v1 passes)

On the server, on a slow timer after load: `Get All Actors Of Class`
(`BP_PlaceableItemContainer`) → for each, read its Persistence Component **`Get Unique
ID`** → `ToText`; feed that UID back through **`Get Actor By Unique ID`** (World
Persistence Component) and confirm it resolves to the same actor; `Print String` the
name, location, UID, and round-trip result. The round-trip is the half that matters — a
stable key we cannot resolve back to an actor is useless.

---

## ✅ PLAYTEST CHECKLIST — v1 (pipeline validation)

**Goal:** confirm the Stocker mod loads locally and the probe prints to the log. ~5 min.
No building or chest-placing needed for v1.

1. **Launch Conan Exiles** normally from Steam. At the main menu you *may* see a mod
   warning / "continue with mods" prompt — **accept it**. (If a "modlist reset" dialog
   appears, do **not** reset.)
   - *If the mod does not appear active at all in the menu's mod list*, note that and stop
     — the modlist path or pak location is wrong, and that's the finding.
2. **Start a NEW single-player game** (throwaway — mods alter saves). Any map. Let it load
   to where your character is standing in the world.
3. Once you're **in the world**, wait ~15 seconds, then **quit to desktop** (or back to
   menu). You don't need to *do* anything — the probe fires on load.
4. **Tell Claude "done."** Claude reads the log and looks for
   `STOCKER_PROBE: ModController BeginPlay reached`.

**What each outcome means (Claude will interpret):**
- **Banner present** → harness proven; Claude builds the v2 persistence probe next.
- **Mod loads but no banner** → `bRequiresLoadOnStartup` (or Controller instantiation) is
  the culprit; Claude has the fix.
- **Mod won't activate in the menu** → modlist format / pak-registration issue; Claude
  adjusts and rebuilds.

> Optional but helpful: if it's trivial, **place a single wooden chest** somewhere before
> you quit. It costs nothing for v1 and gives v2 a ready-made test object next round.
