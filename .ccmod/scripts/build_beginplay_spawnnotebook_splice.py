"""Splice a SpawnAmadanNotebook() self-call onto Menu_ModController::BeginPlay, chained off
SpawnAmadan()'s own currently-unused `then` pin (not a new ExecutionSequence branch - avoids
touching the sequence node's pin count at all, and matches the project's own "sequential chain is
simpler than adding a branch" preference when a spare `then` pin is already sitting there unused).

The self-call node is cloned from SpawnAmadan's own real, already-compiled K2Node_CallFunction
(same "clone a real example of a same-class self-call" technique this project has used 3+ times -
hand-typed self-call synthesis has never worked here, see stocker-menu-pivot memory session 16).

Uses ccmod's own instantiate()/connect() helpers throughout, not hand-rolled renaming - a first
attempt at hand-rolling the NodeGuid/PinId/Name remap missed that begin_line's Name="..." has to be
kept in sync too (instantiate() does this correctly, confirmed by reading generator.py directly
rather than re-guessing).
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

raw = open(MOD + r"\.ccmod\graphs\menu_beginplay_live_s20.t3d", encoding="utf-8-sig").read()
g = parse(raw)

spawn_amadan = [n for n in g.nodes if n.name == "K2Node_CallFunction_SpawnAmadan_18135A4D"][0]

# Build a standalone 1-node template from SpawnAmadan's real node, stripped of its live links.
template_node = copy.deepcopy(spawn_amadan)
for p in template_node.pins:
    p.links = []
template = Graph(nodes=[template_node])

[new_node] = instantiate(template, g)

# Retarget the FunctionReference from SpawnAmadan -> SpawnAmadanNotebook, keep bSelfContext=True,
# no MemberGuid (per the proven precedent: UE resolves by name when GUID is absent, then self-heals
# the GUID on next save - stocker-menu-pivot session 16 finding).
for i, (kind, text) in enumerate(new_node.body):
    if kind == "raw" and "FunctionReference=" in text:
        new_node.body[i] = (kind, 'FunctionReference=(MemberName="SpawnAmadanNotebook",bSelfContext=True)')
    if kind == "raw" and text.startswith("NodePosY="):
        new_node.body[i] = (kind, "NodePosY=160")

connect(spawn_amadan, "then", new_node, "execute")

out_path = MOD + r"\.ccmod\graphs\menu_beginplay_spawnnotebook_spliced.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes, new node name:", new_node.name)
