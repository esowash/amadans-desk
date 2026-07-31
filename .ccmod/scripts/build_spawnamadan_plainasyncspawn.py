"""Swap SpawnAmadan's top-level async spawn call from AsyncSpawnNPCFromWeightedTable (WeightedTableID)
to plain AsyncSpawnNPC (SpawnTableID) - user's catch: every finalization call added since
(FinishAsyncTrySpawnNPCFromSpawnTableLowLevel, ConfigureSpawnedNPC, GenerateUniqueID/SetUniqueID) was
cloned from BP_ThrallCage's own real graph, which itself uses plain AsyncSpawnNPC, not the
WeightedTable variant - a mismatch between our entry point and the finalization chain grafted onto it,
never reconsidered after the original "DataCmd_SpawnNPC_Actor is just a cheat command" objection was
overturned by finding BP_ThrallCage (a real gameplay spawner) using the same plain function.

New async node cloned verbatim from BP_ThrallCage's own real K2Node_AsyncAction_35
(thrallcage_live_s20.t3d) - same pin shape as the WeightedTable version except SpawnTableID (Name)
instead of WeightedTableID, and no material behavioral difference otherwise confirmed. All downstream
wiring (SpawnTransform from MakeTransform, SpawnSucceeded->FinishAsyncTrySpawnNPCFromSpawnTableLowLevel,
SpawnFailed->print_fail, guard's IfThenElse.then->execute) is preserved exactly as before.

The AmadanWeight/WeightedSpawnTableRow merge built earlier is left in place, unused but harmless -
not cleaned up tonight, noted as a future tidy-up.
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


raw = open(MOD + r"\.ccmod\graphs\spawnamadan_uniqueid_live_s20.t3d", encoding="utf-8-sig").read()
g = parse(raw)

thrallcage_src = parse(open(MOD + r"\.ccmod\graphs\thrallcage_live_s20.t3d", encoding="utf-8-sig").read())
new_async_src = [n for n in thrallcage_src.nodes if n.name == "K2Node_AsyncAction_35"][0]

old_async = [n for n in g.nodes if n.name == "K2Node_AsyncAction_0"][0]

# Capture everything the old async node was connected to before removing it.
ite = [n for n in g.nodes if n.name == "K2Node_IfThenElse_0"][0]
maketransform = [n for n in g.nodes if n.name == "K2Node_CallFunction_4"][0]
finish = [n for n in g.nodes if n.name == "K2Node_CallFunction_1447"][0]
print_fail = [n for n in g.nodes if n.name == "K2Node_CallFunction_22"][0]

template_node = copy.deepcopy(new_async_src)
for p in template_node.pins:
    p.links = []
[new_async] = instantiate(Graph(nodes=[template_node]), g)
setf(new_async, "SpawnTableID", "DefaultValue", '"Amadan"')

# Remove the old async node and all its links entirely.
g.nodes = [n for n in g.nodes if n.name != old_async.name]
for n in g.nodes:
    for p in n.pins:
        p.links = [l for l in p.links if l[0] != old_async.name]

connect(ite, "then", new_async, "execute")
connect(maketransform, "ReturnValue", new_async, "SpawnTransform")
connect(new_async, "SpawnSucceeded", finish, "execute")
connect(new_async, "SpawnFailed", print_fail, "execute")
connect(new_async, "SpawnedPawn", finish, "InputSpawnedNPC")
connect(new_async, "TargetLayout", finish, "InputLayout")
connect(new_async, "NPCBehaviorParameters", finish, "InputNPCBehaviorParameters")

out_path = MOD + r"\.ccmod\graphs\spawnamadan_plainasync_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
