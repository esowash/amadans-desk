# Next-session kickoff prompt — Stocker move primitive, via `ccmod`

Paste the block below into a fresh session on the **build box** to resume.

---

We're continuing the **Stocker** Conan Exiles mod (the "Amadan Cnoic" reclaimer thrall).
Repo: `C:\Users\<user>\amadans-desk`. Start by reading `docs/local-test-loop.md` — the
**▶ RESUME HERE** block at the top is the authoritative state — and my memory files
`stocker-conan-mod` / `stocker-current-state`.

**Where we are.** Build 0.1.5 ("3A") is installed and playtested. The graph on
`Stocker_ModController` (BeginPlay → Delay 8s → `GetAllActorsOfClass(BP_PL_Chest_Medium)`)
now correctly **picks the source chest by content** — it branches on
`GetPopulatedItemCount(chest0) > GetPopulatedItemCount(chest1)` and selects the stocked chest
as source. That part works (playtest-confirmed). **The open problem is the transfer itself:**
`ItemInventory::MoveItemsByTemplateId`, called on the chest's `PlaceableInventory`, **returns 0
and moves nothing** — verified against `Game_0.db`, not just the log — under both
`(quantity=0, bMoveAllAvailable=true)` and `(quantity=999, bMoveAllAvailable=false)`, with no
error logged. It's the function, not the args. Leading hypothesis: `PlaceableInventory` is an
`ItemInventoryReplicateToAll` wrapper whose reads reflect state but whose moves don't hit the
authoritative inventory.

**Use the `ccmod` companion tool this time — not hand-rolled Python.** It's at
`C:\Users\<user>\claude-conan-modder` (CLI `ccmod`, or `python -m ccmod`). Read its
`prompt.md` first. It parses/generates T3D losslessly, mints GUIDs, writes reciprocal
`LinkedTo`, keeps a git-tracked library of captured node "bricks" (shared + per-mod workspace),
bridges the clipboard, and reads `Game_0.db`. Last session I hand-built a one-off generator
(`scratchpad/gen_graph.py`) — don't; drive `ccmod` and give Stocker a `.ccmod/` workspace
library (`cd` into the mod repo, `ccmod init`).

**The experiment to run:** swap the transfer function from `MoveItemsByTemplateId` to
**`MoveAndStackItems`** — the primitive Conan's own Item Distributor (thrall/pet feeding) uses
(`C:\CEUE5Devkit\UE4\Content\Systems\Building\Placeables\ItemDistributor.uasset`; params look
like `(TemplateID, Amount, Source, Target) → Remaining`). It's a method on the **ItemDistributor
component** that `Stocker_ModController` already has (there's a benign startup warning
`Couldn't find native parent component 'Sprite' for 'ItemDistributor'` — sanity-check the
component actually works). Steps:
1. `cd` into the mod repo → `ccmod init`. Capture the `MoveAndStackItems` node with
   `ccmod capture …` (in the DevKit: right-click graph → "Move and Stack Items", uncheck
   Context Sensitive if needed → select → Ctrl+C). Also capture the ItemDistributor component
   getter if not already a brick.
2. Rebuild the graph swapping `MoveItemsByTemplateId` → `MoveAndStackItems` (wire its target to
   the ItemDistributor component getter). **Also add before/after `GetPopulatedItemCount` prints
   on both source AND target**, so the log shows the in-memory effect directly — this
   distinguishes "didn't move" from "moved but didn't persist." Bump the banner to `STOCKER_3B`.
3. Paste into the DevKit graph, compile, save. Verify on disk: grep the **source** uasset
   (`…/Content/Mods/Stocker/Local/Stocker_ModController.uasset`) for the new banner.
4. Build mod. **Cook cache goes stale within the same minute** — before rebuilding, delete
   `UE4/Saved/Mods/_Cooked/<Platform>/ConanSandbox/Content/Mods/Stocker/` (all platforms) and the
   game's `Saved/ExtractedMods/Stocker-Windows.*`. Copy
   `C:\CEUE5Devkit\UE4\Saved\Mods\Stocker\Output\Stocker.pak` →
   `…\Conan Exiles\ConanSandbox\Mods\Stocker.pak`. **Verify the installed pak contains the new
   banner** (`grep -aoE "STOCKER_[0-9][A-Z]" <pak>`) BEFORE asking for a playtest (a stale 2C
   pak wasted a launch last time).
5. Ask the user to playtest: launch → **Continue** the existing save → stand ~20 s → quit.
6. Read `…/ConanSandbox/Saved/Logs/ConanSandbox.log` for the `STOCKER_3B` lines AND cross-check
   `Game_0.db` (chest 36 stocked with template 10001; chest 35 empty; `item_inventory(item_id,
   owner_id, inv_type, template_id, data)`, chests are `inv_type=4`; no sqlite3 CLI, use Python
   stdlib or `ccmod savedb`). Success = 10001 relocates 36→35 and the after-count on the source
   drops.

**Collaboration model:** you structure all the logic and drive the tools (`ccmod`, clipboard,
file/DB inspection); the user is your hands in the DevKit GUI (they'll click/drag and run
Build-mod when told — they don't know the editor) and they run the game for playtests. Guided
direct authoring by their real mouse is reliable; the old unreliability was about computer-use
pixel control.

**Feed learnings back:** update `ccmod`'s `reference/conan-functions.md` — it currently conflates
"Move and Stack Items" with `MoveItemsByTemplateId` and lists the primitive as merely unproven.
Record the refined finding (`MoveItemsByTemplateId` on `PlaceableInventory` is a confirmed no-op
with a non-empty source; whatever `MoveAndStackItems` turns out to do). Commit new shared/
workspace bricks. Commit the mod repo at the next stopping point.

---
