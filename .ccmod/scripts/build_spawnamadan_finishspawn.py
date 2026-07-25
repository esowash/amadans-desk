"""Add the missing finalization call to SpawnAmadan: FinishAsyncTrySpawnNPCFromSpawnTableLowLevel
(on BP_AISpawningLibrary), chained between AsyncAction's SpawnSucceeded and our own debug print.

Root cause found via a real live capture of BP_ThrallCage (a base-game spawner that also uses the
async spawn pipeline for full-fledged, properly-registered NPCs): it ALWAYS calls this function
immediately after SpawnSucceeded, feeding it the exact same SpawnedPawn/TargetLayout/
NPCBehaviorParameters the async node's own outputs already provide, plus the SpawnTableID row name.
We never called it - explaining the log's real native errors (no AnimInstance on CharacterMesh0,
Smart Object save/load failing for lack of a valid UID) despite SpawnSucceeded itself firing clean.
Every OTHER optional param on this function (SpawnLocation, RoamRadius_, StaticSpawnPoint_,
TerritoryVolumeSpawner, SpawnerType, SpawnerIndex, bSnapToGround, SpawnPointEntryIndex,
__WorldContext) is left unwired in the real BP_ThrallCage example too, confirmed not guessed.

Node cloned verbatim from that real capture (K2Node_CallFunction_1447 in thrallcage_live_s20.t3d),
only RowName's literal retargeted from BP_ThrallCage's own dynamic variable to a hardcoded "Amadan"
(matching this whole project's SpawnTableID convention), and Input* pins rewired to our own
AsyncAction_0's SpawnedPawn/TargetLayout/NPCBehaviorParameters instead of BP_ThrallCage's variables.
"""
import sys
import copy

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw, output=None):
    pin(n, pn, output=output)._set(k, raw)


raw = open(MOD + r"\.ccmod\graphs\spawnamadan_customevent_live_s20b.t3d", encoding="utf-8-sig").read()
g = parse(raw)

thrallcage_src = parse(open(MOD + r"\.ccmod\graphs\thrallcage_live_s20.t3d", encoding="utf-8-sig").read())
finish_node_src = [n for n in thrallcage_src.nodes if n.name == "K2Node_CallFunction_1447"][0]

template_node = copy.deepcopy(finish_node_src)
for p in template_node.pins:
    p.links = []
template = Graph(nodes=[template_node])

[finish] = instantiate(template, g)
setf(finish, "RowName", "DefaultValue", '"Amadan"')

asyncspawn = [n for n in g.nodes if n.name == "K2Node_AsyncAction_0"][0]
print_ok = [n for n in g.nodes if n.name == "K2Node_CallFunction_21"][0]

# Sever AsyncAction.SpawnSucceeded -> print_ok (direct link) before inserting FinishSpawn between them.
spawn_succeeded = pin(asyncspawn, "SpawnSucceeded", output=True)
print_execute = pin(print_ok, "execute", output=False)
spawn_succeeded.links = [l for l in spawn_succeeded.links if l[0] != print_ok.name]
print_execute.links = [l for l in print_execute.links if l[0] != asyncspawn.name]

connect(asyncspawn, "SpawnSucceeded", finish, "execute")
connect(finish, "then", print_ok, "execute")
connect(asyncspawn, "SpawnedPawn", finish, "InputSpawnedNPC")
connect(asyncspawn, "TargetLayout", finish, "InputLayout")
connect(asyncspawn, "NPCBehaviorParameters", finish, "InputNPCBehaviorParameters")

out_path = MOD + r"\.ccmod\graphs\spawnamadan_finishspawn_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
