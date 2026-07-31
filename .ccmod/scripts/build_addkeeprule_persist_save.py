r"""Add a persistence Save() call to AddKeepRule, right after its one true success terminal.

Full pull+edit+repaste onto the live graph (addkeeprule_live_s19_persist.t3d), per this
project's own rule: never assume an on-disk build script still matches reality after
several rounds of hand-fixes -- verify by tracing the real exec graph first (done this
session, see the print-out in conversation).

Traced structure (exec-only, confirmed): DynamicCast_0.CastFailed -> CallFunction_1
("cast to placeable failed", dead end, a FAILURE path -- no Save() there). The two real
success paths (append via Array_Add when no existing (Station,TemplateID) match is found,
vs. in-place replace via Array_Set when one is) both converge on ONE shared node,
CallFunction_0 ("STOCKER_ADDRULE: rule added") -- IfThenElse_2.then goes through Array_Add
first, IfThenElse_2.else goes straight there. CallFunction_0.then was dangling (unused) --
that is the single correct splice point: it fires exactly once per real successful call,
covering both append and replace.

Real captured precedent used for the new nodes (both pulled this session):
- PersistenceComponent self-context VariableGet: persistence_dragoff_s19.t3d
- Save() call (self = PersistenceComponent, no params): same file
"""
import copy
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])

g = parse(open(MOD + r"\.ccmod\graphs\addkeeprule_live_s19_persist.t3d", encoding="utf-8-sig").read())
persist_src = parse(open(MOD + r"\.ccmod\graphs\persistence_dragoff_s19.t3d", encoding="utf-8-sig").read())


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def add(t):
    return instantiate(t, g)[0]


def clone_from(src_graph, name):
    n = copy.deepcopy(src_graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


successPrint = g.by_name("K2Node_CallFunction_0")  # "STOCKER_ADDRULE: rule added"
assert pin(successPrint, "then", output=True).links == [], "expected this to still be dangling"

persistGet = add(clone_from(persist_src, "K2Node_VariableGet_0"))   # self-context PersistenceComponent get
saveCall = add(clone_from(persist_src, "K2Node_CallFunction_1"))    # Save()

connect(persistGet, "PersistenceComponent", saveCall, "self")
connect_exec(successPrint, saveCall, "then", "execute")

# --- validate --------------------------------------------------------------------------------
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

out = MOD + r"\.ccmod\graphs\addkeeprule_persist_save.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
