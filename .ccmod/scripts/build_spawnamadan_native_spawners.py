"""Rebuild SpawnAmadan's internal body to spawn the REAL native NPC placement actors
(Amadan_ManualSpawnPoint + Amadan_TerritorySpawner, both already configured with
SpawnTable="Amadan" in their own Class Defaults) instead of spawning the character directly.

Rationale (session 21): plain SpawnActorFromClass(HumanoidNPC_Character_Amadan) + a post-hoc
SetCharacterSpawnTableID never triggers the native mesh/clothing-application system - confirmed
decisively via log cross-reference (every other human NPC gets a paired 'Recreating Clothing
Actors' underwear+hair line, Amadan never does, regardless of spawn method). NPCTerritorySpawner's
own real call list uses AsyncSpawnNPCFromWeightedTable + GetRandomSpawnPoint/GetSpawnPoints,
suggesting it scans nearby BP_ManualSpawnPoint actors and drives the actual native spawn-from-table
call itself - the same real pipeline that correctly spawns every other human NPC in the session.
Letting the native classes do the spawning (rather than us calling the low-level async functions
by hand, already tried and failed in session 20 attempts 2-7) is the new hypothesis.

Guard changed to check for an existing Amadan_TerritorySpawner (was HumanoidNPC_Character_Amadan)
so a relaunch doesn't double-spawn the spawner pair. Cast/SetCharacterSpawnTableID dropped entirely
- these are plain Actor spawns, not ConanCharacters, and their behavior is already fully configured
via their own Class Defaults (SpawnTable="Amadan"), no runtime property-setting needed.
"""
import sys, copy, pathlib

CCMOD = str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = str(pathlib.Path(__file__).resolve().parents[2])

SRC_PATH = MOD + r"\.ccmod\graphs\spawnamadan_postpaste_verify_s21.t3d"
src = parse(open(SRC_PATH, encoding="utf-8-sig").read())


def find_by_name(g, name):
    n = next(x for x in g.nodes if x.name == name)
    nn = copy.deepcopy(n)
    for p in nn.pins:
        p.links = []
    return Graph(nodes=[nn])


EVENT_T = find_by_name(src, "K2Node_CustomEvent_0")
GAC_T = find_by_name(src, "K2Node_CallFunction_45")
ARRLEN_T = find_by_name(src, "K2Node_CallArrayFunction_Len")
EQ0_T = find_by_name(src, "K2Node_CallFunction_260")
ITE_T = find_by_name(src, "K2Node_IfThenElse_0")
MAKETRANSFORM_T = find_by_name(src, "K2Node_CallFunction_4")
SPAWN_T = find_by_name(src, "K2Node_SpawnActorFromClass_1")

SPAWNPOINT_PATH = '"/Game/Mods/Menu/Amadan_ManualSpawnPoint.Amadan_ManualSpawnPoint_C"'
SPAWNPOINT_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Amadan_ManualSpawnPoint.Amadan_ManualSpawnPoint_C'"'''
TERRITORY_PATH = '"/Game/Mods/Menu/Amadan_TerritorySpawner.Amadan_TerritorySpawner_C"'
TERRITORY_BGC = '''"/Script/Engine.BlueprintGeneratedClass'/Game/Mods/Menu/Amadan_TerritorySpawner.Amadan_TerritorySpawner_C'"'''

g = Graph()


def add(t):
    return instantiate(t, g)[0]


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


event = add(EVENT_T)
for i, (kind, text) in enumerate(event.body):
    if kind == "raw" and text.strip().startswith("CustomFunctionName="):
        event.body[i] = (kind, 'CustomFunctionName="SpawnAmadan"')

gac = add(GAC_T)
setf(gac, "ActorClass", "DefaultObject", TERRITORY_PATH)
setf(gac, "OutActors", "PinType.PinSubCategoryObject", TERRITORY_BGC, output=True)

arrlen = add(ARRLEN_T)
setf(arrlen, "TargetArray", "PinType.PinSubCategoryObject", TERRITORY_BGC)

eq0 = add(EQ0_T)
ite = add(ITE_T)

maketransform = add(MAKETRANSFORM_T)
# Location pin already carries the real Amadan coordinate verbatim from the cloned source.

spawn_point = add(SPAWN_T)
setf(spawn_point, "Class", "DefaultObject", SPAWNPOINT_PATH)
setf(spawn_point, "CollisionHandlingOverride", "DefaultValue", '"AdjustIfPossibleButAlwaysSpawn"')
setf(spawn_point, "ReturnValue", "PinType.PinSubCategoryObject", SPAWNPOINT_BGC, output=True)

spawn_territory = add(SPAWN_T)
setf(spawn_territory, "Class", "DefaultObject", TERRITORY_PATH)
setf(spawn_territory, "CollisionHandlingOverride", "DefaultValue", '"AdjustIfPossibleButAlwaysSpawn"')
setf(spawn_territory, "ReturnValue", "PinType.PinSubCategoryObject", TERRITORY_BGC, output=True)

# --- exec spine ----------------------------------------------------------
connect_exec(event, gac, "then", "execute")
connect_exec(gac, ite, "then", "execute")
connect_exec(ite, spawn_point, "then", "execute")
connect_exec(spawn_point, spawn_territory, "then", "execute")

# --- data ------------------------------------------------------------------
connect(gac, "OutActors", arrlen, "TargetArray")
connect(arrlen, "ReturnValue", eq0, "A")
connect(eq0, "ReturnValue", ite, "Condition")
connect(maketransform, "ReturnValue", spawn_point, "SpawnTransform")
connect(maketransform, "ReturnValue", spawn_territory, "SpawnTransform")

out_path = MOD + r"\.ccmod\graphs\spawnamadan_native_spawners_s21.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
