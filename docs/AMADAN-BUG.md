# ~~Open bug: Amadan doesn't render~~ — SOLVED 2026-08-01 (session 22)

> **Resolved.** Amadan renders: correct body mesh, correct clothing, correct weapon, and he
> registers as a real character. The cause was architectural, not a configuration mistake — every
> earlier attempt spawned the character directly and bypassed Conan's camp/territory-spawner system
> entirely. See **[`CAMP-SPAWNER-SYSTEM.md`](CAMP-SPAWNER-SYSTEM.md)** for the real mechanism and
> the runtime build.
>
> The decisive confirmation, after four sessions of it never once appearing: paired
> `SK_human_male_underwear` / `SK_human_male_hair_01` clothing-assembly lines in the log, plus
> **zero** hits for any of the old failure signatures (`No animation instance found`,
> `does not have a valid UID`, `StartEmoteInternal`). He now also turns up in ordinary
> `KillCharacterWithRagdoll` lines — i.e. a real, registered character rather than a ghost actor.
>
> Checkpoints from the working run:
> ```
> MENU_CAMP: SpawnAmadan entry, existing camp owners:  0
> MENU_CAMP: registered spawn point, CampActors now:   1
> MENU_CAMP: spawner BeginPlay, camp owners found:     1
> ```
>
> **Still open, both cosmetic and both understood** — see "Remaining cosmetic gaps" at the end.
>
> The rest of this document is kept as-is: it is the record of what was tried and ruled out, and
> the reasoning that eventually pointed at the camp system. It is no longer a help request.

This was the one real blocker left before the mod is fully "done."

## What Amadan is supposed to be

A fixed, decorative, non-capturable NPC standing beside Amadan's Desk. No AI, no
movement, no combat — a `BeginPlay`-forced `SleepOnGround` idle pose is the intended
final state. He's spawned once at server start (`Menu_ModController::BeginPlay`) and
periodically re-checked/respawned by the sweep timer if killed
(`Menu_ModController::RunSweep`), both via a `SpawnAmadan` function/event.

*(Correction, session 22: an earlier revision of this doc said `SpawnAmadan` had been
removed from the build. It hadn't — a live pull found the event still present, and it is
currently wired into `Menu_ModController::BeginPlay` in the simple
`SpawnActorFromClass` + `SetCharacterSpawnTableID` form.)*

His class (`HumanoidNPC_Character_Amadan`, plain `HumanoidNPCCharacter` subclass) and
his `SpawnDataTable`/`RaceTemplateDataTable`/`EquipmentTemplateDataTable` rows (all
under the `Amadan*` DataTables in `Mods/Menu/Local/`) are already built and — as far as
we can tell from the DataTable content itself — correctly configured, following the
same real shape as base-game named NPCs like Tephra (`HeadHunter_Guard_Elite_Tephra`).

## What actually happens

He spawns successfully (confirmed via a `SpawnSucceeded` delegate on the async spawn
call), but:

- **No visible mesh.** Not even a default/wrong mesh — nothing renders. Equipment
  (specifically a weapon, socket-attached) *does* render and moves correctly, so the
  actor and its skeleton genuinely exist; specifically the base body
  `SkeletalMeshComponent` (`CharacterMesh0`) never gets a mesh assigned.
- **No nameplate.**
- A real native error fires every time, the moment his forced idle emote tries to play:
  ```
  UEmoteController::StartEmoteInternal - No animation instance found on skeletal
  mesh component: CharacterMesh0 on character: Amadan Cnoic when starting emote: 55
  ```
- A second real native error, intermittent: `An attempt to save/load a Smart Object
  failed because its owning actor does not have a valid UID`.
- **Decisive diagnostic**: across a full server session's log, there is not one single
  `SkeletalMeshComponent: Recreating Clothing Actors` line for him — the line every
  other character (player, any other NPC) gets several of. Whatever native system
  triggers mesh/clothing setup on spawn never fires for him, at any point, regardless of
  how long the session runs. This rules out a pure timing/race explanation.

## What's been tried, and ruled out or inconclusive

All of the following were tried, each grounded in a real precedent pulled live from a
base-game asset that does this correctly (not guessed) — **none of them changed the
symptom above**:

1. A `Delay` before the forced-emote call (timing theory) — no change.
2. Spawning via `AsyncSpawnNPCFromWeightedTable` (a `SpawnDataTable`-row-driven async
   spawn, the same node type real spawners like `BP_MercenarySpawnpoint` and
   `NPCTerritorySpawner` use) instead of a synchronous `SpawnActorFromClass` +
   `SetCharacterSpawnTableID` — got past an initial "could not find weighted table"
   error (a real `WeightedSpawnTableRow` row was authored, `AmadanWeight` DataTable),
   `SpawnSucceeded` started firing, but no change in the actual symptom.
3. Following the exact real finalization chain used by `BP_ThrallCage` (a base-game
   spawner for captured thralls) after a successful async spawn: `FinishAsyncTrySpawnNPCFromSpawnTableLowLevel`
   → `ConfigureSpawnedNPC` → `GenerateUniqueID`/`SetUniqueID` → `SetCharacterLayout`
   (a `HasCharacterLayoutInterface` message call — the actual "apply appearance now"
   function, confirmed via a real base-game usage in `DataCmd_SwapGender`). Each of
   these was added, wired correctly (confirmed via re-pulling the pasted graph and
   diffing), and — critically — **`BP_ThrallCage`'s own entry point uses plain
   `AsyncSpawnNPC` (a `SpawnTableID` parameter) rather than the `WeightedTable` variant
   from step 2**, so the entry point was later swapped to match. Still no change.
4. A direct query of the save database's `characters` table (SQLite,
   `ConanSandbox/Saved/Game_0.db`) confirmed Amadan never gets a row there at all — he's
   a live "ghost" actor never registered as a persistent, tracked character, which is
   consistent with (but doesn't fully explain) everything above.

## Real leads not yet tried

0. **★ Strongest current lead (session 22): spawn him through the real camp/territory
   spawner system instead of calling the spawn pipeline directly.** Every attempt above
   hand-rebuilt `NPCTerritorySpawner`'s internals inside `Menu_ModController`, with no
   camp, no spawn point, and no territory spawner. Conan spawns world NPCs through a
   **three-actor system** — `BP_CampOwner` + `BP_ManualSpawnPoint` + `NPCTerritorySpawner`
   — wired together by array membership. The full trace, including the spawn-point cache
   lifecycle and the exact ordering constraint it imposes, is in
   [`CAMP-SPAWNER-SYSTEM.md`](CAMP-SPAWNER-SYSTEM.md); the raw graph pulls backing it are
   in `.ccmod/graphs/campcomp_*_s22.t3d`. Because the connection is plain array
   membership and contains no editor-only registration, this can be built at runtime
   without shipping any map-placed actors. A first attempt at the spawner classes in
   session 21 failed for a now-understood reason: there was no `BP_CampOwner` at all, and
   nothing was ever registered into a camp.

1. **`BP_ThrallCage`'s `ConvertToThrall` self-call** — a bare, zero-parameter self-context
   call, skipped in every attempt above on the assumption it's specific to thrall-capture
   semantics. It may not actually be; it's the one piece of that real, working chain
   never replicated, and worth tracing into its own function body (not just its
   call-site) before ruling it out.
2. **Bypass the whole async/SpawnDataTable registration path entirely.** Go back to a
   plain `SpawnActorFromClass` (which does show a visible weapon/skeleton, just no
   appearance), and self-apply appearance directly via `SetCharacterLayout` called from
   Amadan's own `BeginPlay`, using `Make Character Mesh Layout`/`Make Character Bool
   Parameters`/`Make Character Enum Parameters` constructor nodes wired in by hand
   (remember: `SetCharacterLayout`'s pins don't accept literal defaults, see
   [`TECHNICAL-NOTES.md`](TECHNICAL-NOTES.md)). This sidesteps the native-registration
   mystery instead of continuing to chase it, at the cost of Amadan likely never being a
   "real," fully game-system-registered character (Smart Objects etc. may still not
   work for him).
3. **Reparent as a diagnostic.** `HumanoidNPC_Character_Amadan`'s parent is plain
   `HumanoidNPCCharacter`. Real named/unique NPCs like Tephra instead use a
   purpose-built subclass (`HumanoidNPCCharacter_RelicHunters`). Temporarily reparenting
   Amadan to a similar subclass, purely to see whether mesh/anim application starts
   working, would help isolate whether the plain base class is itself part of the
   problem — never directly tested.

## Amadan's real extracted appearance data

For whoever picks this up, his real appearance values (extracted from the reference
character used to design him) are already on file and don't need re-deriving:

```
MeshLayout:  Helmet=-2, Hair=7, FacialHair=8, Head=4, Forearms=0, Hands=0, UpperBody=0, LowerBody=0, Legs=0, Feet=0
TintLayout:  Skin=4, Hair=9, SecondaryHair=9, FacialHair=10, InnerIrisEyeLeft=4, InnerIrisEyeRight=4,
             MiddleIrisEyeLeft=4, MiddleIrisEyeRight=4, OuterIrisEyeLeft=2, OuterIrisEyeRight=2
TextureLayout: EyebrowTexture=0, EyeTexture=1, LipTexture=0, WarpaintFaceTexture=0, WarpaintBodyTexture=0, WarpaintHandsTexture=0
BoolParams:  IsFemale=false
EnumParams:  Race=Stygian
Gear (EquipmentTemplateDataTable, real ItemTable template IDs): Helmet=51900, Torso=91036, Legs=91038, Feet=91039, MainHand=51812 (Stygian Khopesh)
Dye channels (candidate, not confirmed final): Helmet ch1=100; UpperBody ch1=117,ch2=100,ch3=117; LowerBody ch1=100,ch2=117; Feet ch1=100,ch2=100,ch3=117
```

These are already baked into the `AmadanRace`/`AmadanEquipment` DataTable rows in
`Mods/Menu/Local/`; they're listed here mainly for anyone pursuing lead #2 above, which
needs them supplied directly rather than resolved through the DataTable pipeline.

---

## Remaining cosmetic gaps (session 22)

Neither blocks the mod; both are understood rather than mysterious.

### Dyes don't apply

**Not a bug — structurally impossible through the mechanism being used.**
`EquipmentTemplateDataTable` has exactly nine fields: `MainHand`, `OffHand`, `Helmet`, `Torso`,
`Legs`, `Hands`, `Feet`, `Backpack`, `Durability`. There is no dye, colour, tint, or channel field
of any kind (verified against the real asset, not assumed). An equipment template can say *which*
items an NPC wears, never what colour they are.

The dye-channel values recorded earlier in this document came from a reference thrall's **item
instances in the save DB**, which is per-instance data, not template data. Applying them would mean
dyeing the spawned items at runtime — real work, and it would have to re-apply on every respawn.

Options: ship undyed; or choose template IDs whose base colours already read the way you want.

### He doesn't play his idle emote

The pose is meant to come from the spawn point, not from the character class. `BP_ManualSpawnPoint`
exposes an `EmoteState` (`ECharacterEmotes`) field, and `GetEmoteState` has exactly one consumer in
the whole content tree — `BaseNPC` — so it is read by the NPC base class directly, independent of
the Behavior Tree. That matters because Amadan's `SpawnDataTable` row deliberately uses
`BT_DoNothing`; the separate random-idle path (`BTTaskIdleEmote` → `GetIdleEmoteToPlay`) is
therefore dead for him, and the two mechanisms do not collide.

Cause: `EmoteState` and `IsGuardSpot` were simply never set on `Amadan_ManualSpawnPoint`. Confirmed
by inspecting its `.uasset` — the `SpawnTable` property is serialized there, those two are absent,
and only *overridden* properties get written into a subclass's defaults.

Fix is Class Defaults only, no graph work: `EmoteState` = "Sleep on back" (the display name for
`SleepOnGround`), `IsGuardSpot` = true. If that proves insufficient, the next suspect is
`BT_DoNothing` being too inert for `BaseNPC` to reach the emote call, with `BT_Passive` as the
sibling to try.

This also retires the old `BeginPlay → StartEmote` hook on `HumanoidNPC_Character_Amadan`, which
was the source of the `UEmoteController::StartEmoteInternal - No animation instance found` error
chased across sessions 20 and 21. The spawn point's own field is the supported route.
