"""No visible menu at all this time, but STOCKER_INTERACT begin/done both
fired repeatedly (~30 times over 11s) with zero errors in the log -- and
ActivateModule's ReturnValue was never checked, just discarded. The most
likely explanation: the "StockerHouseRules" row isn't actually resolving at
runtime (merge didn't take, or the row name doesn't exactly match after the
Export-JSON-rename-Reimport dance) -- ActivateModule looks up a module by
Name and, going by the total silence in the log, most likely just returns
None on an unknown name rather than erroring loudly.

Add an IsValid branch on ActivateModule's ReturnValue so the NEXT playtest's
log tells us definitively whether the row resolved, instead of guessing
again. IsValid/Branch node shapes lifted from the existing ModController
graph (K2Node_CallFunction_22-style IsValid, K2Node_IfThenElse-style Branch)
-- same PrintString template as everything else this session.

Base: amadan_interact_final.t3d (5 nodes, currently live on the desk).
Splice point: ActivateModule.then, currently -> STOCKER_INTERACT done
directly; insert IsValid+Branch between them, both branches converging back
into the same done print.
"""
import sys
import copy

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def add(t, g):
    return instantiate(t, g)[0]


g = parse(open(MOD + r"\.ccmod\graphs\amadan_interact_final.t3d", encoding="utf-8").read())
print("base graph nodes:", len(g.nodes))

activate = g.by_name("K2Node_CallFunction_5")
printDone = g.by_name("K2Node_CallFunction_22")

activate_then = pin(activate, "then")
assert activate_then.links == [(printDone.name, pin(printDone, "execute").pin_id)]

# --- templates -------------------------------------------------------------------
src = parse(open(MOD + r"\.ccmod\graphs\modcontroller_anchor_repointed.t3d", encoding="utf-8").read())
ISVALID_T = tmpl_from(src, "K2Node_CallFunction_22")
BRANCH_T = tmpl_from(src, "K2Node_IfThenElse_0")
PRINT_T = tmpl_from(src, "K2Node_CallFunction_21")

isValid = add(ISVALID_T, g)
branch = add(BRANCH_T, g)
printOk = add(PRINT_T, g)
printFail = add(PRINT_T, g)

pin(printOk, "InString")._set(
    "DefaultValue", '"STOCKER_INTERACT ActivateModule OK (valid WindowRoot)"')
pin(printFail, "InString")._set(
    "DefaultValue", '"STOCKER_INTERACT ActivateModule FAILED (ReturnValue None -- row not resolving)"')

connect(activate, "ReturnValue", isValid, "Object")

# --- rewire: ActivateModule.then -> Branch(IsValid) -> {OK,Fail} -> printDone --
activate_then.links = []
printDone.pin_by_name("execute").links = []

connect_exec(activate, branch, "then", "execute")
connect(isValid, "ReturnValue", branch, "Condition")
connect_exec(branch, printOk, "then", "execute")
connect_exec(branch, printFail, "else", "execute")
connect_exec(printOk, printDone, "then", "execute")
connect_exec(printFail, printDone, "then", "execute")

# --- layout ----------------------------------------------------------------------
isValid.set_position(1350, -300)
branch.set_position(1550, -150)
printOk.set_position(1900, -300)
printFail.set_position(1900, 0)
printDone.set_position(2300, -150)

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

for nn, pn in [(activate.name, "then"), (branch.name, "then"), (branch.name, "else"),
               (printOk.name, "then"), (printFail.name, "then")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

p = pin(printDone, "execute")
if len(p.links) != 2:
    problems.append(f"printDone.execute has {len(p.links)} incoming links, expected 2 (converging branches)")

out = MOD + r"\.ccmod\graphs\amadan_interact_diagnose.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
