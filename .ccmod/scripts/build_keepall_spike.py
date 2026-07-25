"""KeepAll spike: splice one early-exit Branch into the LIVE ApplyKeepRule body.

Small, self-contained delta -- NOT a full pull-edit-repaste (stocker-full-graph-edits
says that rule is for edits that reach into an existing graph's own nodes; this one
only touches 2 existing exec links, both by exact known PinId, no eyeballing needed).

THE EDIT: right after the IsValid check (K2Node_IfThenElse_0), insert a new Branch
gated on the (now real, user-added) `KeepAll` function input. If true, skip straight
to a NEW literal Return (Moved=0, Outcome=NoExcess -- reusing the existing enum value,
no new enum entry needed for the spike). If false, fall through into the ORIGINAL
excess/deficit chain exactly as before (K2Node_IfThenElse_1), untouched.

Chosen topology deliberately avoids ALL fan-in/fan-out ambiguity from past sessions
(see stocker-full-graph-edits + gotcha #12 lineage):
  - the new Branch gets its OWN dedicated FunctionResult (not a second wire into the
    existing NoExcess terminus), so no exec-input-pin fan-in is needed via GUI drag.
  - IfThenElse_0.then currently goes straight to IfThenElse_1.execute (single link).
    The user's first hand-wire (IfThenElse_0.then -> new Branch.execute) is a normal
    single-source drag; per the known UE quirk (re-dragging FROM an already-linked
    OUTPUT pin replaces rather than adds), this one drag both connects the new node
    AND detaches the old direct wire for free -- no separate "unwire" step needed.
  - the user's second hand-wire (new Branch.else -> IfThenElse_1.execute) is then a
    clean single connection, since the old incoming link on IfThenElse_1.execute is
    already gone after hand-wire 1.

Function entry nodes can't be pasted (established gotcha), so the new Branch's
Condition is fed through a KNOT (bool-typed) with its InputPin left open -- the
user's third and final hand-wire is Entry.KeepAll -> this Knot.InputPin. This mirrors
exactly how build_3m_function.py originally wired Station/TemplateID/Keep/Candidates.

Three hand-wires total after paste, all simple single-source-single-target drags by
exact pin name -- no node-identification-by-eye, no fan-out/fan-in risk.
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
base = parse(row[0])
print("base (reference only, not repasted) nodes:", len(base.nodes))


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


# --- verify the two splice points look exactly as expected -------------------
ifte0 = base.by_name("K2Node_IfThenElse_0")
ifte1 = base.by_name("K2Node_IfThenElse_1")
entry = base.by_name("K2Node_FunctionEntry_0")
assert pin(ifte0, "then").links == [("K2Node_IfThenElse_1", pin(ifte1, "execute").pin_id)], \
    "IfThenElse_0.then no longer points straight at IfThenElse_1.execute -- re-check topology"
assert pin(ifte1, "execute").links == [("K2Node_IfThenElse_0", pin(ifte0, "then").pin_id)], \
    "IfThenElse_1.execute has more than the one expected incoming link"
keepall_pin = pin(entry, "KeepAll")
assert keepall_pin.category == "bool" and not keepall_pin.links, \
    "entry's KeepAll pin missing, wrong type, or already wired -- re-check the signature edit"
print("splice points verified: IfThenElse_0.then -> IfThenElse_1.execute (only link); "
      "entry.KeepAll present, bool, unwired")

# --- templates -----------------------------------------------------------------
BRANCH_T = tmpl_from(base, "K2Node_IfThenElse_0")
RESULT_T = tmpl_from(base, "K2Node_FunctionResult_5")   # the existing NoExcess terminus shape
KNOT_T = tmpl_file(LIB + r"\flow\knot.t3d")

g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


branch = add(BRANCH_T)
result = add(RESULT_T)
knot = add(KNOT_T)

# type the knot bool (mirrors build_3m_function.py's kStation/kTemplate typing)
for pn in ("InputPin", "OutputPin"):
    setf(knot, pn, "PinType.PinCategory", '"bool"')
    setf(knot, pn, "PinType.PinSubCategoryObject", "None")

# result: reuse the NoExcess terminus shape verbatim (Moved=0, Outcome=NewEnumerator0)
setd(result, "Moved", "0")
setd(result, "Outcome", "NewEnumerator0")

# --- wiring within the new delta only ------------------------------------------
connect(knot, "OutputPin", branch, "Condition")
connect_exec(branch, result, "then", "execute")
# branch.execute, branch.else, knot.InputPin all left OPEN -- the 3 hand-wires.

# --- layout: tuck the new nodes just below IfThenElse_0/_1, out of the way ----
branch.set_position(1552, 1450)
result.set_position(1552, 1600)
knot.set_position(1350, 1450)

# --- validate (internal to the delta only) --------------------------------------
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

assert not [n for n in g.nodes if "FunctionEntry" in n.class_path], "entry must NOT be pasted"

out = MOD + r"\.ccmod\graphs\keepall_spike_delta.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
