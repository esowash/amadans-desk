"""Fix the exec-wiring tangle that happened while hand-adding Array_Set to AddKeepRule
(session 16): working on the REAL pasted-back graph (27 nodes, includes the user's real
Array_Set node), not a fresh template.

Bugs found by pulling and inspecting the actual post-paste state:
1. FunctionEntry.then got disconnected from DynamicCast_0.execute (the cast right after entry)
   and rerouted into the knot instead -- the whole function is currently unreachable from its
   own entry point.
2. Array_Set's own "then" (output) got wired INTO the knot's InputPin, instead of the knot's
   OutputPin feeding Array_Set's "execute" (input).
3. Knot_623.InputPin ended up with 3 incoming links (ite_template.then -- correct; Array_Set.then
   -- wrong; FunctionEntry.then -- wrong) while its OutputPin fed nothing.

Fix: restore FunctionEntry.then -> DynamicCast_0.execute; knot_623.OutputPin -> Array_Set.execute;
Array_Set.then -> the second Set-FoundIndex node's execute; strip the two stray links off the
knot's InputPin so it carries only ite_template.then.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec

MOD = r"<MOD_ROOT>"
SRC = MOD + r"\.ccmod\graphs\menu_addkeeprule_final_check.t3d"

g = parse(open(SRC, encoding="utf-8-sig").read())


def by_name(name):
    n = g.by_name(name)
    assert n, f"missing node {name}"
    return n


def pin(n, name, output=None):
    p = n.pin_by_name(name, output=output)
    assert p, f"{n.name} has no pin {name}"
    return p


entry = by_name("K2Node_FunctionEntry_1")
dyncast = by_name("K2Node_DynamicCast_0")
knot = by_name("K2Node_Knot_623")
array_set = by_name("K2Node_CallArrayFunction_4")
setidx_found = by_name("K2Node_VariableSet_374")

# --- strip the tangled links -------------------------------------------------------------------
pin(entry, "then", output=True).links = []
pin(dyncast, "execute", output=False).links = []
pin(knot, "InputPin", output=False).links = []
pin(knot, "OutputPin", output=True).links = []
pin(array_set, "then", output=True).links = []
pin(array_set, "execute", output=False).links = []
pin(setidx_found, "execute", output=False).links = []

# --- rewire correctly ---------------------------------------------------------------------------
connect_exec(entry, dyncast, "then", "execute")
# re-establish ite_template.then -> knot.InputPin (the ONLY thing that should feed the knot)
ite_template = by_name("K2Node_IfThenElse_1")
connect_exec(ite_template, knot, "then", "InputPin")
connect(knot, "OutputPin", array_set, "execute")
connect_exec(array_set, setidx_found, "then", "execute")

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

out = MOD + r"\.ccmod\graphs\menu_addkeeprule_fixed.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"Fixed AddKeepRule: nodes={len(g.nodes)} wrote={out} problems={len(problems)}")
for pr in problems:
    print("  !", pr)

# --- sanity trace: is DynamicCast_0 reachable from FunctionEntry, and is Array_Set reachable
# from ite_template, and does Array_Set actually lead to setidx_found?
print()
print("entry.then ->", pin(entry, "then", output=True).links)
print("dyncast.execute <-", pin(dyncast, "execute", output=False).links)
print("knot.OutputPin ->", pin(knot, "OutputPin", output=True).links)
print("array_set.execute <-", pin(array_set, "execute", output=False).links)
print("array_set.then ->", pin(array_set, "then", output=True).links)
print("setidx_found.execute <-", pin(setidx_found, "execute", output=False).links)
