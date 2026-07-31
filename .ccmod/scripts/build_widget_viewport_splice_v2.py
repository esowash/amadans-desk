"""Fix: this DevKit rejects exec-output fan-out (BeginPlay.then -> 2 targets
failed to compile: "Replace existing output connections", a fatal error).
Insert an explicit Sequence node instead -- one exec in, N exec outs, each
with exactly one connection, which is the standard way to fire multiple
chains from one event when direct fan-out isn't supported.

Base: the LIVE graph as it stands after the failed compile attempt (pulled
as 'stocker/modcontroller_compile_fail_check') -- CreateWidget/AddToViewport/
GetPlayerController are already correctly wired to each other; only
BeginPlay's connection needs to change.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace
import copy

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)


def load_graph(name):
    row = db.get_graph(conn, name)
    assert row, f"no saved graph '{name}'"
    return parse(row["t3d"])


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


g = load_graph("stocker/modcontroller_compile_fail_check")
print("base graph nodes:", len(g.nodes))

beginPlay = g.by_name("K2Node_Event_0")
gatherChain = g.by_name("K2Node_CallFunction_25")   # the original then-destination
createWidget = g.by_name("K2Node_CreateWidget_0")

seqSrc = load_graph("stocker/sequence_node")
SEQ_T = tmpl_from(seqSrc, "K2Node_ExecutionSequence_0")
seq = instantiate(SEQ_T, g)[0]

# --- clear the bad fan-out, wire through Sequence instead ---------------------
bp_then = beginPlay.pin_by_name("then")
gather_exec = gatherChain.pin_by_name("execute")
cw_exec = createWidget.pin_by_name("execute")
seq_exec = seq.pin_by_name("execute")
seq_then0 = seq.pin_by_name("then_0")
seq_then1 = seq.pin_by_name("then_1")

bp_then.links = [(seq.name, seq_exec.pin_id)]
seq_exec.links = [(beginPlay.name, bp_then.pin_id)]

gather_exec.links = [(seq.name, seq_then0.pin_id)]
seq_then0.links = [(gatherChain.name, gather_exec.pin_id)]

cw_exec.links = [(seq.name, seq_then1.pin_id)]
seq_then1.links = [(createWidget.name, cw_exec.pin_id)]

# --- layout --------------------------------------------------------------------
seq.set_position(1900, 1550)

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

# each of these pins must have EXACTLY one link now (single-connection constraint
# this DevKit enforces even on exec outputs)
for nn, pn in [(beginPlay.name, "then"), (gatherChain.name, "execute"), (createWidget.name, "execute"),
               (seq.name, "execute"), (seq.name, "then_0"), (seq.name, "then_1")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

out = MOD + r"\.ccmod\graphs\modcontroller_widget_viewport_splice_v2.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
