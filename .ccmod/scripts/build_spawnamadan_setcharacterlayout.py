"""Add the actual missing appearance-application call: SetCharacterLayout (a HasCharacterLayoutInterface
message, K2Node_Message not a plain CallFunction), chained right after
FinishAsyncTrySpawnNPCFromSpawnTableLowLevel, before GenerateUniqueID.

Real signature and precedent found via DataCmd_SwapGender.uasset (a cheat purely about swapping
character appearance) - the interface method's combined `Layout: CharacterLayout` struct pin exists
on the real node (confirmed present even though that specific caller split it into sub-fields
instead) - Split Struct Pin is a pure editor convenience that reconstructs the same single struct at
compile time, so wiring the combined pin directly is functionally identical and far simpler than
replicating 8 broken-out sub-fields we'd have to source via a BreakStruct we don't need.

We already have a real CharacterLayout struct sitting unused on
FinishAsyncTrySpawnNPCFromSpawnTableLowLevel's own CharacterLayout output (fed by TargetLayout
throughout this whole chain but never actually applied to the character until now) - this is very
likely the actual root cause of the persistent invisible-mesh bug: every prior finalization call
passed layout data AROUND but nothing ever called the one function that actually APPLIES it.

self wired from the same NPC output already used for SetUniqueID's actor param. IsServer wired from
a real cloned KismetSystemLibrary::IsServer() call (pure, matching the real example verbatim rather
than hardcoding a literal true/false blind).
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


raw = open(MOD + r"\.ccmod\graphs\spawnamadan_plainasync_live_s20.t3d", encoding="utf-8-sig").read()
g = parse(raw)

swapgender_src = parse(open(MOD + r"\.ccmod\graphs\swapgender_live_s20.t3d", encoding="utf-8-sig").read())
setlayout_src = [n for n in swapgender_src.nodes if n.name == "K2Node_Message_0"][0]
isserver_src = [n for n in swapgender_src.nodes if n.name == "K2Node_CallFunction_46"][0]

setlayout_template = copy.deepcopy(setlayout_src)
for p in setlayout_template.pins:
    p.links = []
[setlayout] = instantiate(Graph(nodes=[setlayout_template]), g)

isserver_template = copy.deepcopy(isserver_src)
for p in isserver_template.pins:
    p.links = []
[isserver] = instantiate(Graph(nodes=[isserver_template]), g)

finish = [n for n in g.nodes if n.name == "K2Node_CallFunction_1447"][0]
generate = [n for n in g.nodes if n.name == "K2Node_CallFunction_324"][0]

finish_then = pin(finish, "then", output=True)
generate_exec = pin(generate, "execute", output=False)
finish_then.links = [l for l in finish_then.links if l[0] != generate.name]
generate_exec.links = [l for l in generate_exec.links if l[0] != finish.name]

connect(finish, "then", setlayout, "execute")
connect(setlayout, "then", generate, "execute")
connect(finish, "NPC", setlayout, "self")
connect(finish, "CharacterLayout", setlayout, "Layout")
connect(isserver, "ReturnValue", setlayout, "IsServer")

out_path = MOD + r"\.ccmod\graphs\spawnamadan_setcharacterlayout_body.t3d"
open(out_path, "w", encoding="utf-8").write(g.render())
print("wrote", out_path, "-", len(g.nodes), "nodes")
