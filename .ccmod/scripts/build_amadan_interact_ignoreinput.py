"""Splice SetIgnoreMoveInput/SetIgnoreLookInput into the chain, right after
Set Input Mode UI Only -- panel now shows (crafting menu removed last build)
but the player kept moving/looking around underneath it, meaning UI Only
input mode alone doesn't stop Conan's own movement/look handling. Both new
calls were captured live off the same GetPlayerController pin already in the
graph (Context Sensitive search, per this project's standing "verify via a
real pin" discipline -- not hand-authored), landing on Engine.Controller
(SetIgnoreMoveInput/SetIgnoreLookInput are AController members, Player
Controller IS-A Controller, no cast needed).

Base: stocker/amadan_interact_with_ignoreinput (10 nodes: the 8-node
no-craftmenu graph from last build, plus these 2 fresh unconnected captures).
Both new nodes' `self` are already wired to the same GetPlayerController
node the rest of the chain already shares -- only the exec chain and the two
bool defaults need setting.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect_exec
from ccmod.workspace import Workspace

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = db.get_graph(conn, "stocker/amadan_interact_with_ignoreinput")
assert row, "graph not found in cache -- re-pull from clipboard"
g = parse(row["t3d"])
print("base graph nodes:", len(g.nodes))

setInputMode = g.by_name("K2Node_CallFunction_417")
printDone = g.by_name("K2Node_CallFunction_22")
ignoreMove = g.by_name("K2Node_CallFunction_8")
ignoreLook = g.by_name("K2Node_CallFunction_9")

sim_then = setInputMode.pin_by_name("then")
assert sim_then.links == [(printDone.name, printDone.pin_by_name("execute").pin_id)], \
    f"unexpected pre-state on SetInputMode.then: {sim_then.links}"

# --- rewire: SetInputMode.then -> IgnoreMove -> IgnoreLook -> printDone ---------
sim_then.links = []
printDone.pin_by_name("execute").links = []

connect_exec(setInputMode, ignoreMove, "then", "execute")
connect_exec(ignoreMove, ignoreLook, "then", "execute")
connect_exec(ignoreLook, printDone, "then", "execute")

ignoreMove.pin_by_name("bNewMoveInput")._set("DefaultValue", '"true"')
ignoreLook.pin_by_name("bNewLookInput")._set("DefaultValue", '"true"')

# --- layout: nudge the two new nodes into the chain's flow ---------------------
ignoreMove.set_position(2400, 0)
ignoreLook.set_position(2750, 0)

# --- validate --------------------------------------------------------------------
problems = []
names = {n.name for n in g.nodes}
for n in g.nodes:
    for p in n.pins:
        for (lnn, lp) in p.links:
            if lnn not in names:
                problems.append(f"{n.name}.{p.name} -> missing {lnn}")
                continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None:
                problems.append(f"{n.name}.{p.name} -> {lnn} missing pin {lp}")
                continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {lnn}.{other.name}")

for nn, pn in [(setInputMode.name, "then"), (ignoreMove.name, "execute"),
               (ignoreMove.name, "then"), (ignoreLook.name, "execute"),
               (ignoreLook.name, "then"), (printDone.name, "execute")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

out = MOD + r"\.ccmod\graphs\amadan_interact_ignoreinput.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
