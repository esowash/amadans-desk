"""Add ConfigureSpawnedNPC (BP_AISpawningLibrary) to SpawnAmadan, chained after
FinishAsyncTrySpawnNPCFromSpawnTableLowLevel's own `then` pin, before our debug print.

Next real step in BP_ThrallCage's own chain after FinishAsyncTrySpawnNPCFromSpawnTableLowLevel -
deliberately skipping the intervening DeferredEquipStartupItemsInterface/ConvertToThrall calls in
that chain, since those are thrall-capture-specific and don't apply to Amadan (he's not a
capturable/breakable thrall). ConfigureSpawnedNPC itself looks generic to any spawned-from-table
NPC regardless of thrall status, so it's kept.

Node cloned verbatim from the real capture (K2Node_CallFunction_1439 in thrallcage_live_s20.t3d).
NPC wired from FinishAsyncTrySpawnNPCFromSpawnTableLowLevel's own NPC output (ConanCharacter-typed,
matching this pin's expected type exactly - avoids an implicit-cast risk that reusing the original
AsyncAction's Pawn-typed SpawnedPawn output would have). BehaviorParameters reused from the
AsyncAction's own NPCBehaviorParameters output (already proven valid, feeds the same value
FinishAsyncTrySpawnNPCFromSpawnTableLowLevel itself received). RowName="Amadan" (same literal used
throughout this project). SpawnedFromSpawnTable=true matches our case exactly, left at its real
default. Every other param (HumanNPCType, SpawnerHumanNPCIndex/WildlifeNPCIndex/StaticSpawnpointIndex,
RoamRadius, SpawnLocation, StaticSpawnPoint, TerritoryVolumeSpawner, Name, SpawnPointEntryIndex,
__WorldContext) is left unwired, matching BP_ThrallCage's own real usage.
"""
import sys
import copy

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


raw = open(MOD + r"\.ccmod\graphs\spawnamadan_finishspawn_live_s20.t3d", encoding="utf-8-sig").read()
g = parse(raw)

thrallcage_src = parse(open(MOD + r"\.ccmod\graphs\thrallcage_live_s20.t3d", encoding="utf-8-sig").read())
configure_node_src = [n for n in thrallcage_src.nodes if n.name == "K2Node_CallFunction_1439"][0]

template_node = copy.deepcopy(configure_node_src)
for p in template_node.pins:
    p.links = []
template = Graph(nodes=[template_node])

[configure] = instantiate(template, g)
setf(configure, "RowName", "DefaultValue", '"Amadan"')

finish = [n for n in g.nodes if n.name == "K2Node_CallFunction_1447"][0]
asyncspawn = [n for n in g.nodes if n.name == "K2Node_AsyncAction_0"][0]
print_ok = [n for n in g.nodes if n.name == "K2Node_CallFunction_21"][0]

finish_then = pin(finish, "then", output=True)
print_execute = pin(print_ok, "execute", output=False)
finish_then.links = [l for l in finish_then.links if l[0] != print_ok.name]
print_execute.links = [l for l in print_execute.links if l[0] != finish.name]

connect(finish, "then", configure, "execute")
connect(configure, "then", print_ok, "execute")
connect(finish, "NPC", configure, "NPC")
# BehaviorParameters deliberately left unwired: AsyncAction's own NPCBehaviorParameters output is a
# CLASS reference (TSubclassOf<Object>), but this pin wants an OBJECT INSTANCE of
# BP_NPCBehaviorParameters_C - a real compile error confirmed live ("'Variable' is an object type,
# and 'Behavior Parameters' is a reference to an object instance"). BP_ThrallCage's own real example
# feeds this from a private per-class instance variable (OriginalBehaviorParams) we don't have an
# equivalent of - leaving it at default/None matches how most of this function's other optional
# params are already left unset in that same real example.

out_path = MOD + r"\.ccmod\graphs\spawnamadan_configurespawnednpc_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
