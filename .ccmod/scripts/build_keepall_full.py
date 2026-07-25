"""KeepAll spike, take 2: full pull-edit-repaste of ApplyKeepRule (stocker-full-graph-edits).

The delta-paste + 3-hand-wire plan (build_keepall_spike.py) turned out unnavigable --
this function's Branch nodes are visually stacked with no distinguishing label, so
"drag from IfThenElse_0's True pin" is not something the user can actually find in
the GUI. Falling back to the established process: edit the WHOLE graph in code, hand
back one paste-ready replacement. User will select-all + delete the existing graph
contents (the FunctionEntry node can't be deleted, so it survives) then paste this,
then re-hand-wire the entry's 5 output pins (Station, TemplateID, Keep, Candidates,
KeepAll) into their knots -- same one-drag-per-pin idiom as the original 3M build,
just done 5 times instead of once, since a full repaste re-creates all 4 pre-existing
knots too (their old links-to-entry can't be part of the pasted text either, per the
"entry can't be pasted" rule -- ANY node's dangling reference to it must be redone by
hand, not just the new one).

THE EDIT ITSELF is unchanged from the spike: one Branch right after the IsValid
check, gated on the new `KeepAll` input. True -> a dedicated new Return (Moved=0,
Outcome=NoExcess, reusing the existing enum value). False -> falls through into the
ORIGINAL excess/deficit chain (K2Node_IfThenElse_1) exactly as before, untouched.
"""
import sys

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"
LIB = CCMOD + r"\library"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)
row = conn.execute("SELECT t3d FROM graphs WHERE name=?", ("applykeeprule_keepall_pull",)).fetchone()
assert row, "run `ccmod pull --save applykeeprule_keepall_pull` first"
g = parse(row[0])
print("pulled nodes:", len(g.nodes))


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


def setd(n, pn, v):
    setf(n, pn, "DefaultValue", f'"{v}"')


def tmpl_from(graph, name):
    import copy
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def tmpl_file(path):
    t = parse(open(path, encoding="utf-8-sig").read())
    for n in t.nodes:
        for p in n.pins:
            p.links = []
    return t


def add(t):
    return instantiate(t, g)[0]


# --- identify fixed anchors, same checks as the spike --------------------------
ifte0 = g.by_name("K2Node_IfThenElse_0")
ifte1 = g.by_name("K2Node_IfThenElse_1")
entry = g.by_name("K2Node_FunctionEntry_0")
assert pin(ifte0, "then").links == [("K2Node_IfThenElse_1", pin(ifte1, "execute").pin_id)], \
    "IfThenElse_0.then no longer points straight at IfThenElse_1.execute -- re-check topology"
assert pin(ifte1, "execute").links == [("K2Node_IfThenElse_0", pin(ifte0, "then").pin_id)], \
    "IfThenElse_1.execute has more than the one expected incoming link"
keepall_pin = pin(entry, "KeepAll")
assert keepall_pin.category == "bool" and not keepall_pin.links, \
    "entry's KeepAll pin missing, wrong type, or already wired -- re-check the signature edit"
print("splice points verified")

# --- templates (derived from THIS graph, before we mutate it) ------------------
BRANCH_T = tmpl_from(g, "K2Node_IfThenElse_0")
RESULT_T = tmpl_from(g, "K2Node_FunctionResult_5")
KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")

branch = add(BRANCH_T)
result = add(RESULT_T)
knot = add(KNOT_T)

for pn in ("InputPin", "OutputPin"):
    setf(knot, pn, "PinType.PinCategory", '"bool"')
    setf(knot, pn, "PinType.PinSubCategoryObject", "None")

setd(result, "Moved", "0")
setd(result, "Outcome", "NewEnumerator0")

connect(knot, "OutputPin", branch, "Condition")
connect_exec(branch, result, "then", "execute")
# knot.InputPin left open -- one of the 5 entry hand-wires.

# --- rewire the two existing exec links -----------------------------------------
pin(ifte0, "then").links = []
pin(ifte1, "execute").links = []
connect_exec(ifte0, branch, "then", "execute")
connect_exec(branch, ifte1, "else", "execute")

branch.set_position(1552, 1450)
result.set_position(1552, 1600)
knot.set_position(1350, 1450)

# --- exclude the entry node from the paste (established, unavoidable) ----------
g.nodes = [n for n in g.nodes if n.name != "K2Node_FunctionEntry_0"]

# --- validate --------------------------------------------------------------------
# Links pointing at the excluded entry are EXPECTED (5 of them: Station, TemplateID,
# Keep, Candidates, KeepAll knots) -- those are exactly the hand-wires the user redoes.
problems = []
names = {n.name for n in g.nodes}
entry_dangling = 0
for n in g.nodes:
    for p in n.pins:
        for (lnn, lp) in p.links:
            if lnn == "K2Node_FunctionEntry_0":
                entry_dangling += 1
                continue
            if lnn not in names:
                problems.append(f"{n.name}.{p.name} -> missing {lnn}")
                continue
            other = g.by_name(lnn).pin_by_id(lp)
            if other is None:
                problems.append(f"{n.name}.{p.name} -> {lnn} missing pin {lp}")
                continue
            if (n.name, p.pin_id) not in other.links:
                problems.append(f"non-reciprocal: {n.name}.{p.name} -> {lnn}.{other.name}")

assert entry_dangling == 5, f"expected exactly 5 dangling links to entry (the 5 hand-wires), got {entry_dangling}"
assert not [n for n in g.nodes if "FunctionEntry" in n.class_path], "entry must NOT be pasted"

out = MOD + r"\.ccmod\graphs\keepall_full.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"dangling links to entry (expected hand-wires): {entry_dangling}")
print(f"other problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
