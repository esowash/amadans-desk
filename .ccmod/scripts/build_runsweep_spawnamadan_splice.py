"""Splice a SpawnAmadan() self-call onto Menu_ModController::RunSweep, chained off
RestockManagedStations' currently-unused `then` pin (the dangling end of RunSweep's thin
TidyManagedStations->RestockManagedStations orchestrator chain).

Purpose: periodic respawn. SpawnAmadan's own guard (GetAllActorsOfClass count == 0) already makes
it safe/idempotent to call repeatedly - it only actually spawns when no Amadan currently exists.
Piggybacking on RunSweep's existing 300s repeating timer means Amadan comes back within 5 minutes
of being killed, with zero new timer infrastructure. User's explicit call: periodic respawn, not
invulnerability - scope is Amadan only, not the notebook (wasn't asked for, notebook isn't a normal
combat target).

Clone technique identical to the BeginPlay splice: pull SpawnAmadan's own real self-call node
(from the just-edited BeginPlay capture) via instantiate(), no retargeting needed this time since
we want the SAME function, not a different one.
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

runsweep_raw = open(MOD + r"\.ccmod\graphs\runsweep_live_s20.t3d", encoding="utf-8-sig").read()
g = parse(runsweep_raw)

beginplay_raw = open(MOD + r"\.ccmod\graphs\menu_beginplay_spawnnotebook_spliced.t3d", encoding="utf-8-sig").read()
bp = parse(beginplay_raw)
spawn_amadan_src = [n for n in bp.nodes if n.name == "K2Node_CallFunction_SpawnAmadan_18135A4D"][0]

template_node = copy.deepcopy(spawn_amadan_src)
for p in template_node.pins:
    p.links = []
template = Graph(nodes=[template_node])

[new_node] = instantiate(template, g)
for i, (kind, text) in enumerate(new_node.body):
    if kind == "raw" and text.startswith("NodePosY="):
        new_node.body[i] = (kind, "NodePosY=320")

restock = [n for n in g.nodes if n.name == "K2Node_CallFunction_3"][0]
connect(restock, "then", new_node, "execute")

out_path = MOD + r"\.ccmod\graphs\runsweep_spawnamadan_spliced.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes, new node name:", new_node.name)
