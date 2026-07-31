r"""Fix RemoveKeepRule: swap the broken 'Array_RemoveIndex' call (not a real function -- every
pin orphaned, confirmed via a live pull) for the REAL function, 'Array_Remove', confirmed by
having the user hand-add the actual "Remove Index" node via GUI right-click search and pulling
it (array_remove_index_real, session 18). Real shape: MemberName="Array_Remove",
IndexToRemove:int (my original guess for the PARAM name was actually already correct -- only
the function name itself was wrong).

Full pull+edit+repaste of the whole RemoveKeepRule body (menu_removekeeprule_v2_postpaste, 9
nodes including the live FunctionEntry) -- but per this project's hard-learned rule (gotcha #22,
[[stocker-test-loop-gotchas]]: pasting a synthesized FunctionEntry into a function graph
silently drops the function's custom parameter pins), FunctionEntry is EXCLUDED from the
re-render. Every link that touched Entry gets rerouted through knots instead, for a fresh
hand-wire after paste -- same discipline as the original build.

Also fixes a second, separate gap found during this pull: the user's hand-wire wired
Entry.Index directly to IsValidIndex.IndexToTest (bypassing the intended knot entirely) and
never wired anything into IndexToRemove at all -- Array_Remove's index input was never
connected to begin with, on top of the wrong function name. Both problems share the same fix:
route Index through ONE knot feeding BOTH consumers, so a single hand-wire covers it.
"""
import sys

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.workspace import Workspace

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])
LIB = CCMOD + r"\library"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)

row = db.get_graph(conn, "menu_removekeeprule_v2_postpaste")
assert row, "run `ccmod pull --save menu_removekeeprule_v2_postpaste` first"
g = parse(row["t3d"])

real_row = db.get_graph(conn, "array_remove_index_real")
assert real_row, "run `ccmod pull --save array_remove_index_real` first"
real_g = parse(real_row["t3d"])


def by_name(name):
    n = g.by_name(name)
    assert n, f"missing node {name}"
    return n


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


def add(t):
    return instantiate(t, g)[0]


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")


def type_knot(n, category, subcat_obj="None", container="None"):
    for pn in ("InputPin", "OutputPin"):
        setp = n.pin_by_name(pn)
        setp._set("PinType.PinCategory", f'"{category}"')
        setp._set("PinType.PinSubCategoryObject", subcat_obj)
        setp._set("PinType.ContainerType", container)


old_call = by_name("K2Node_CallArrayFunction_2")
ite = by_name("K2Node_IfThenElse_0")
print_removed = by_name("K2Node_CallFunction_0")
keeprules_get2 = by_name("K2Node_VariableGet_51")
isvalid_call = by_name("K2Node_CallArrayFunction_12")
entry = by_name("K2Node_FunctionEntry_0")

# --- swap in the real Array_Remove node ---------------------------------------------------------
from ccmod.t3d.model import Graph
import copy

real_node = copy.deepcopy(real_g.by_name("K2Node_CallArrayFunction_4"))
for p in real_node.pins:
    p.links = []
new_call = add(Graph(nodes=[real_node]))
new_call.set_position(720, -176)

# clear the OLD node's stale backward-links on its partners before rewiring to the new node
pin(ite, "then", output=True).links = []
pin(print_removed, "execute", output=False).links = []
pin(keeprules_get2, "KeepRulesV2", output=True).links = []

connect_exec(ite, new_call, "then", "execute")
connect_exec(new_call, print_removed, "then", "execute")
connect(keeprules_get2, "KeepRulesV2", new_call, "TargetArray")

g.nodes.remove(old_call)

# --- knot for Index, feeding BOTH IsValidIndex and the new Array_Remove --------------------------
knot_index = add(KNOT_T)
type_knot(knot_index, "int")
knot_index.set_position(200, 0)

# clear the old direct Entry->IsValidIndex link on both ends, reroute through the knot
idx_pin = pin(isvalid_call, "IndexToTest")
idx_pin.links = []
connect(knot_index, "InputPin", isvalid_call, "IndexToTest")
connect(knot_index, "InputPin", new_call, "IndexToRemove")

# --- clear the exec knot's link to Entry (Entry itself is being dropped) ------------------------
knot_exec = by_name("K2Node_Knot_623")
inpin = pin(knot_exec, "InputPin")
inpin.links = []

# --- drop FunctionEntry from the render -----------------------------------------------------------
g.nodes.remove(entry)

# --- validate ------------------------------------------------------------------------------------
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

out = MOD + r"\.ccmod\graphs\menu_removekeeprule_v3_fixed.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
print()
print("hand-wires needed after DELETE + REPASTE (from the REAL FunctionEntry):")
print(f"  Entry.then  -> {knot_exec.name}.InputPin")
print(f"  Entry.Index -> {knot_index.name}.InputPin")
