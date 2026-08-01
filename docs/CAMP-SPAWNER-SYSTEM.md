# Conan's camp / NPC-spawner system, traced

**Written session 22.** This is a trace of how the base game actually spawns NPCs into
the world, produced while chasing the Amadan render bug (`AMADAN-BUG.md`). Everything
here was read out of real base-game assets — live `T3D` pulls of the actual graphs, or
identifier extraction from the raw `.uasset` files — not inferred from naming.

The short version: **Conan does not spawn world NPCs by calling a spawn function on an
actor.** It spawns them through a three-actor system that is wired together at map-edit
time by an editor utility. Sessions 19–21 repeatedly tried to call the spawn pipeline
directly and got a character that exists but never renders. This document is the system
those calls were bypassing.

## The three actors

| Actor | Package | Role |
|---|---|---|
| `BP_CampOwner` | `/Game/Systems/Camps/BP_CampOwner` | Near-empty actor. A `Billboard` + a `BP_CampComponent`. Holds the camp's identity and its list of member actors. |
| `BP_ManualSpawnPoint` | `/Game/Systems/AI/Navigation/BP_ManualSpawnPoint` | One spawn location. Carries the spawn-table selector and per-point presentation options. |
| `NPCTerritorySpawner` | `/Game/Systems/Spawning/NPCTerritorySpawner` | The thing that actually spawns NPCs. Owns the whole `AsyncSpawnNPC` chain. |

They are connected by **`CampBlutility`** (`/Game/Systems/Camps/CampBlutility`), an
editor utility Blueprint: select the actors in the level, run
`ConnectTerritorySpawnerWithCamp`. Its functions call only `Array_Add` /
`Array_AddUnique` / `Array_Contains` / `Array_RemoveItem` plus editor-only helpers
(`GetSelectedActors`, `GetAllLevelActors`, `GetEditorSubsystem`).

**That matters: the "connect" step contains no hidden native registration. It writes
plain array membership.** The connection is therefore reproducible at runtime without
the editor utility and without placing actors in a map.

## Division of labour

`BP_CampComponent` **does not spawn NPCs.** Its `SpawnCampActor` spawns camp
*placeables* (props). The component is an activation manager plus a spawn-point
registry — `HasPawnWithinDistance`, `CanClaimSphere`, `GetPlayerPawnRegistry`,
`CampRespawnTime`, `CheckIsCampEssential`, `CampsIgnoreLandclaim`.

All NPC spawning lives on `NPCTerritorySpawner`: `GetCurrentNPCSpawnEntry`,
`GetNextSpawnLocation`, `SampleSpawnPoint`, `AsyncSpawnNPC`,
`AsyncSpawnNPCFromWeightedTable`, `AsyncTrySpawnNPCFromSpawnTableLowLevel`,
`FinishAsyncTrySpawnNPCFromSpawnTableLowLevel`, plus gating
(`IsBlockedByLandClaim`, `IsSuppressed`, `IsFull`, `IsLocationInsideBuildingBlockerVolume`).

The camp's only job in the NPC path is to answer `GetSpawnPoints()`.

## `BP_CampComponent::BeginPlay`

Pulled live; saved as `.ccmod/graphs/campcomp_eventgraph_s22.t3d` (261 nodes).

```
IsServer?
 └ ForEach CampActors → IsValid
     ├ MakeStruct ST_CampActor → Array_Add → CampActorData
     └ CheckIsCampEssential (interface msg) → Array_AddUnique → CampEssentials
                                            → set HasCampEssentials
   Completed:
     GetAllActorsOfClass(<camp system>) → Greater_IntInt (found any?)
       ├ YES → CampSystem = [0] → RegisterCamp(Camp=self)
       │        → GetPlayerPawnRegistry → store
       └ NO  → RetryRegistrationCounter <= N?
                ├ yes → DWLogString → Delay(4s) → loop back to the check
                └ no  → SetCampActiveState(false) → ForEach → K2_DestroyActor
```

Two things worth knowing:

- There is a **4-second retry-poll loop** waiting for the camp system to exist — the
  same shape as this mod's own persistence-poll on `Menu_ModController`.
- If registration never succeeds, the camp **destroys its own camp actors**. A camp that
  comes up too early and exhausts its retries fails silently by self-destructing.

Other event-graph entry points: `InitCamp`, `Camper_Destroyed`, `CheckForLandclaim`,
`DeactivateCamp`, `DeactivatedDueToLandClaim`, `AddTerritorySpawnerReference`.

`InitCamp` (a Custom Event, invoked after registration) iterates the camp actors, binds
each one's `OnDestroyed` delegate, re-checks essentials, and runs `CanClaimSphere`; if
the area is land-claimed it destroys the camp actors, clears the array and fires
`DeactivatedDueToLandClaim`. **It does not touch spawn points.**

`AddTerritorySpawnerReference` is implemented as an **interface Event** whose entire
body is `Array_AddUnique(TerritorySpawners, TerritorySpawner)`. The territory spawner
registers itself with the camp through `I_CampComponentInterface`.

## The spawn-point cache

Two small functions, both pulled live
(`campcomp_getspawnpoints_s22.t3d`, `campcomp_updatecache_s22.t3d`).

`GetSpawnPoints` is 4 nodes, and is a **native interface function** —
`MemberParent = /Script/ConanSandbox.StaticNavigationProviderInterface`, not
`BP_CampComponent`. That is how `NPCTerritorySpawner` reaches its camp, and why a
call-graph search for callers of `GetSpawnPoints` turns up almost nothing.

```
FunctionEntry ──> UpdateCachedWaypointsAndSpawnPoints()  [self-context, no branch]
              ──> FunctionResult: SpawnPoints = CachedSpawnPoints
```

`UpdateCachedWaypointsAndSpawnPoints`:

```
if IsSpawnPointAndWaypointCacheValid? ──> return          ← early-out
else:
  Array_Clear(CachedSpawnPoints); Array_Clear(CachedWaypoints)
  ForEach CampActors:
    Cast → StaticSpawnPoint  ──> Array_AddUnique(CachedSpawnPoints)
      └ CastFailed → Cast → StaticWaypoint ──> Array_AddUnique(CachedWaypoints)
  Completed:
    IsSpawnPointAndWaypointCacheValid? = true
    return
```

Consequences for anyone building on this:

- **The cache is sourced from `CampActors`**, the raw actor array — *not* from
  `CampActorData`, the `ST_CampActor` struct array that `BeginPlay` builds. So adding a
  spawn point needs only an array add; no struct construction, and no need to beat
  `BeginPlay`.
- **Elements are cast to the native classes** `StaticSpawnPoint` / `StaticWaypoint`, not
  to `BP_ManualSpawnPoint_C`. `BP_ManualSpawnPoint` derives from `StaticSpawnPoint`
  (its CDO reference `Default__StaticSpawnPoint` appears in the asset), so subclasses of
  it satisfy the cast.
- **The cache is built once and then frozen.** `IsSpawnPointAndWaypointCacheValid?`
  (the variable name really does end in `?`) is only ever set `true` here, and appears
  nowhere in the 261-node event graph. Anything added to `CampActors` after the first
  `GetSpawnPoints()` call will not be picked up unless something sets that flag back to
  `false`. *Not fully established:* every function graph on `BP_CampComponent` has not
  been enumerated, so there may be an invalidation path not yet found. There is no
  camp-side `AddSpawnPoint` — that function belongs to `NPCTerritorySpawner`, for its
  own internal list.

## `NPCTerritorySpawner` has two modes, and a non-obvious switch between them

Its `BeginPlay` (pulled live, `.ccmod/graphs/npcterritoryspawner_beginplay_real_s21.t3d`):

```
if SpawnFromTriggerEvent            ──> skip
else if (Color == NewEnumerator27)  ──> FindStaticNavigationOverride(Camp)
                                        ──> InitializeSpawners(...)        ← camp mode
     else                           ──> RegisterNPCTerritorySpawner        ← territory-volume mode
EndPlay ──> UnregisterNPCTerritorySpawner + DestroyAllSpawned
```

**`Color` is not cosmetic.** It is typed `/Game/Systems/Spawning/SpawnInputs/TerritoryIdentifyColor`
(White/Blue/Green/Red/Yellow/Cyan/Purple/Pink/Orange) and it selects the code path. Community
tutorials present it as a labelling convention for organising camps — it isn't. If `Color` is not
the camp value, **`Camp` is never read at all**: the spawner registers as a free territory-volume
spawner and any manual spawn points are silently ignored.

The camp value is **Yellow**, read off a real working base-game camp spawner (see reference below).
That is an inference rather than a decoded enum mapping — the literal in the graph is
`NewEnumerator27`, and `TerritoryIdentifyColor`'s `DisplayNameMap` ordering is not recoverable from
the raw asset — but a strong one: `Camp` is only ever read down that branch, and that camp works.

`Camp` itself is a plain object reference to a `BP_CampOwner`, shown in the Details panel under a
category literally named **"Static Navigation Override"**. That name is the missing link in the
whole chain: `BP_CampComponent` implements `StaticNavigationProviderInterface`, which is the
interface `GetSpawnPoints` belongs to. So:

```
spawner.Camp ──> BP_CampOwner ──> BP_CampComponent (implements StaticNavigationProviderInterface)
             ──> GetSpawnPoints() ──> CachedSpawnPoints ──> built from CampActors
```

## Reference camp for diffing configuration

`Content/Maps/ConanSandbox/Gameplay/Camps_NPC/` ships **202 camp sublevels**.
`Camps_NPC_x4_y3.umap` is a small complete one — camp `The_Black_Hand_Camp_092`, with actors
`BP_CampOwner46_32` and `NPCTerritorySpawner41_57`. Opening that sublevel directly loads only that
tile, not the full world-composition map.

Its spawner's real configured values, for mirroring:

| Property | Value |
|---|---|
| `Color` | **Yellow** |
| `Camp` | `BP_CampOwner46` |
| `NPCs` / `Human NPCs` | **both empty** — the spawner carries no NPC entries; spawn tables live on the spawn points |
| `Roam Radius` | 5000.0 |
| `Spawn Underneath Roof` | true |
| `Spawn from Trigger Event` / `Ignore Land Claim` | false |
| `Territory Super Region` / `Sub Region` | Desert / 5 |

It also exposes editor-callable buttons: `UpdateSpawnVolumeForManualSpawnPoints`,
`Release Nav Build Lock`, `Visualize Static Navigation`. The first implies a real `SpawnVolume`
(`BoxComponent`) that is sized at edit time to cover the manual spawn points — relevant to any
runtime build, where nothing performs that step. `GetNextSpawnLocation` does use box extents
(`GetScaledBoxExtent` / `RandomPointInBoundingBox`), and there is also a
`TerritorySpawnVolume` / `TerritorySpawnVolumeRadius`. How much of this gates *camp* mode
specifically was not traced; co-locating the spawner with the spawn point and giving the volume a
generous extent sidesteps the question.

## `BP_ManualSpawnPoint`'s real configuration surface

- `SpawnTable` — a free text/name field matching a `WeightedSpawnTableRow` row's
  `WeightedTableID`. **Not** limited by the `HumanNPCType` / `NPCType` enum.
- `HumanNPCType` / `WildlifeNPCType` — the legacy `NPCHumans` / `NPCs` `UserDefinedEnum`
  path. Superseded; leave unset.
- `EmoteState` (`ECharacterEmotes`) — a per-spawn-point idle pose, applied by the spawn
  system itself. This is the supported way to get a fixed pose; it removes any need for
  a `BeginPlay → StartEmote` hook on the character class.
- `IsGuardSpot` — stand and face the actor's rotation instead of roaming.
- `AllowRespawn`, `DespawnTime`, `DayNightSpawning`, `AIDataTableEntryOverride`,
  `NPCBehavior`.

## Building this at runtime

`BP_CampComponent::BeginPlay` resolves the camp system via
`GetAllActorsOfClass(/Script/ConanSandbox.ConanWorldSettings)` → its `BP_CampSystemComponent` →
`RegisterCamp(self)`. **`ConanWorldSettings` is part of the level and always present**, so a
runtime-spawned camp does find the camp system and register; the "exhaust retries and destroy your
own camp actors" failure branch is not a risk for runtime spawning.

Spawn order matters, because the spawn-point cache is build-once-then-frozen:

```
1. camp owner        (subclass it — GetAllActorsOfClass(BP_CampOwner) would otherwise
                      collide with the 202 base-game camps sharing the world)
2. manual spawn point ──> GetComponentByClass(BP_CampComponent) ──> Array_Add into CampActors
3. territory spawner  LAST, Color = Yellow, and Camp set in its own BeginPlay
                      *before* Parent: BeginPlay (the parent reads Camp immediately)
```

Setting `Camp` from inside a subclass's own `BeginPlay` also avoids depending on the property being
externally writable. `CampActors` is Instance Editable (the Details panel offers an eyedropper for
it), but whether it accepts a write from an unrelated Blueprint is a separate flag and is not
established here.

## Why this matters for the Amadan bug

Sessions 19–21 hand-rebuilt `NPCTerritorySpawner`'s internals inside
`Menu_ModController` — calling `AsyncSpawnNPC` / `AsyncTrySpawnNPCFromSpawnTableLowLevel`
/ `FinishAsync…` directly, with no camp, no spawn point, and no territory spawner. The
character was created but never rendered, and never appeared in the save's `characters`
table.

This system is what those calls were routing around. Building it properly — camp owner,
spawn point registered into `CampActors`, territory spawner registered via the camp
interface — spawns the NPC through the same path every base-game NPC uses.

It also explains the session-21 native-spawner attempt, which was abandoned as "stalled on native
C++" after `Amadan_ManualSpawnPoint` and `Amadan_TerritorySpawner` were spawned at runtime and
produced nothing. Two independent reasons, both now understood: there was no `BP_CampOwner` at all
(so no spawn points were ever registered anywhere), and the spawner's `Color` was left at its
default, which routes `BeginPlay` down `RegisterNPCTerritorySpawner` where `Camp` is never read.
Right actors, wrong mode, missing a third of the system.

One caution against over-reading the evidence: the low-level call's
`TerritoryVolumeSpawner` parameter, which the hand-built version never supplied, is
marked **optional** in its signature. It is a real difference from the native call, but
it is not on its own proof of the cause.
