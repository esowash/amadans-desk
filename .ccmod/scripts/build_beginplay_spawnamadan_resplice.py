"""Re-add SpawnAmadan() to Menu_ModController::BeginPlay, chained off SpawnAmadanNotebook's own
dangling `then` pin - the user's manual fix (removing the broken call to the now-deleted Function)
correctly cleaned up the compile error but also dropped the call to SpawnAmadan entirely. Order vs
SpawnAmadanNotebook doesn't matter (no data coupling between the two spawns, confirmed), so this
just appends rather than re-inserting before it.

SpawnAmadan is now a Custom Event (not a Function) - calling it uses the identical K2Node_CallFunction
shape as calling a Function (confirmed via AC_Menu's real SaveVariableToMC caller earlier tonight),
cloned from the same real self-call node used throughout this project, MemberGuid omitted so UE
resolves by name (proven pattern, session 16).
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

raw = open(MOD + r"\.ccmod\graphs\beginplay_postfix_s20.t3d", encoding="utf-8-sig").read()
g = parse(raw)

notebook_call = [n for n in g.nodes if n.name == "K2Node_CallFunction_SpawnAmadan_18135A4D_1"][0]

template_node = copy.deepcopy(notebook_call)
for p in template_node.pins:
    p.links = []
template = Graph(nodes=[template_node])

[new_node] = instantiate(template, g)
for i, (kind, text) in enumerate(new_node.body):
    if kind == "raw" and "FunctionReference=" in text:
        new_node.body[i] = (kind, 'FunctionReference=(MemberName="SpawnAmadan",bSelfContext=True)')
    if kind == "raw" and text.startswith("NodePosY="):
        new_node.body[i] = (kind, "NodePosY=480")

connect(notebook_call, "then", new_node, "execute")

out_path = MOD + r"\.ccmod\graphs\beginplay_spawnamadan_resplice.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes, new node name:", new_node.name)
