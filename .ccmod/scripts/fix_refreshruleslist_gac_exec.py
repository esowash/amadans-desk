r"""Fix RefreshRulesList: GetAllActorsOfClass (K2Node_CallFunction_6) was built with its data
pins wired (OutActors -> GetArrayItem[0] -> ...) but its OWN exec pin was never spliced into the
chain -- a real bug in the original build script, not a wrong-name guess like the others this
session. UE pruned it ("Exec pin is not connected"), so Menu_ModController never actually
resolved, which cascaded into the KeepRulesV2 array read looking unresolved too.

Fix: reroute ClearChildren.then -> GetAllActorsOfClass.execute -> GetAllActorsOfClass.then ->
ForEachLoop.Exec (previously ClearChildren.then went straight to ForEachLoop.Exec, skipping GAC
entirely).

Full pull+edit+repaste of the whole 33-node RefreshRulesList body (no FunctionEntry included,
same discipline as always).
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"
CCMOD = r"<CCMOD_HOME>"
LIB = CCMOD + r"\library"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = db.get_graph(conn, "refreshruleslist_postpaste_broken")
assert row, "run `ccmod pull --save refreshruleslist_postpaste_broken` first"
g = parse(row["t3d"])


def by_name(name):
    n = g.by_name(name)
    assert n, f"missing node {name}"
    return n


gac = by_name("K2Node_CallFunction_6")
clearChildren = by_name("K2Node_CallFunction_1")
feach = by_name("K2Node_MacroInstance_0")

# clear the stale direct ClearChildren->ForEachLoop link on both ends
clearThen = clearChildren.pin_by_name("then", output=True)
feachExec = feach.pin_by_name("Exec", output=False)
clearThen.links = []
feachExec.links = []

connect_exec(clearChildren, gac, "then", "execute")
connect_exec(gac, feach, "then", "Exec")

# --- drop FunctionEntry from the render, same discipline as every other function-graph fix this
# session -- reroute its only link (Entry.then -> ClearChildren, wired directly by the user, no
# knot survived their hand-wire) through a fresh knot for a clean re-hand-wire after paste.
entry = by_name("K2Node_FunctionEntry_0")
entry_then = entry.pin_by_name("then", output=True)
clear_exec = clearChildren.pin_by_name("execute", output=False)
entry_then.links = []
clear_exec.links = []

from ccmod.t3d import parse as _parse


def tmpl_file(path):
    t = _parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")
knot_entry = instantiate(KNOT_T, g)[0]
for pn in ("InputPin", "OutputPin"):
    p = knot_entry.pin_by_name(pn)
    p._set("PinType.PinCategory", '"exec"')
    p._set("PinType.PinSubCategoryObject", "None")
    p._set("PinType.ContainerType", "None")
connect_exec(knot_entry, clearChildren, "OutputPin", "execute")

g.nodes.remove(entry)

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

out = MOD + r"\.ccmod\graphs\amadanmenu_refreshruleslist_fixed.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
print()
print("hand-wire needed after DELETE + REPASTE: Entry.then ->", knot_entry.name)
