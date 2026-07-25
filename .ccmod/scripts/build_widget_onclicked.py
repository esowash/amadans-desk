"""W_StockerTestPanel::SignalClicked body.

Resolves the (hardcoded, for this v1 slice) Furnace and the one-and-only
Stocker_ModController, then calls AddKeepRule(Station=Furnace,
TemplateID=18025 [Dry Wood, literal], Keep=<from the user's existing
Conv_StringToInt chain>, KeepAll=<from the user's existing IsChecked chain>).

Self-contained fragment, no reference to the live SignalClicked bound-event
node or the user's already-built KeepInput/KeepAllCheck read chains -- per
the user's standing feedback (2026-07-18), every hand-wire point is a knot,
not a bare pin, even where there's no fan-out. 3 hand-wires total:
  1. SignalClicked.then           -> knot (exec)
  2. Conv_StringToInt.ReturnValue -> knot (int, feeds AddKeepRule.Keep)
  3. IsChecked.ReturnValue        -> knot (bool, feeds AddKeepRule.KeepAll)
"""
import sys
import copy

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

MOD = r"<MOD_ROOT>"

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)


def load_graph(name):
    row = db.get_graph(conn, name)
    assert row, f"no saved graph '{name}'"
    return parse(row["t3d"])


def load_template(key):
    row = db.get_template(conn, key)
    assert row, f"no template '{key}'"
    graph = parse(row["t3d"])
    assert len(graph.nodes) == 1, f"expected single-node template for '{key}'"
    return tmpl_from(graph, graph.nodes[0].name)


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


g = Graph(nodes=[])


def add(t):
    return instantiate(t, g)[0]


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


def setf(n, pn, k, raw):
    pin(n, pn)._set(k, raw)


def setd(n, pn, v):
    setf(n, pn, "DefaultValue", f'"{v}"')


def bgc(path):
    return f'''"/Script/Engine.BlueprintGeneratedClass'{path}'"'''


# --- templates ---------------------------------------------------------------
seedFix = load_graph("keepall_seed_fix") if db.get_graph(conn, "keepall_seed_fix") else None
if seedFix is None:
    seedFix = parse(open(MOD + r"\.ccmod\graphs\keepall_seed_fix.t3d", encoding="utf-8").read())

FURNACE_GAC_T = tmpl_from(seedFix, "K2Node_CallFunction_14")
ITEM_T = tmpl_from(seedFix, "K2Node_GetArrayItem_2")

MODCONTROLLER_CLASS = "/Game/Mods/Stocker/Stocker_ModController.Stocker_ModController_C"
MODCONTROLLER_GAC_T = copy.deepcopy(FURNACE_GAC_T)
setf(MODCONTROLLER_GAC_T.nodes[0], "ActorClass", "DefaultObject", bgc(MODCONTROLLER_CLASS))
setf(MODCONTROLLER_GAC_T.nodes[0], "OutActors", "PinType.PinSubCategoryObject", bgc(MODCONTROLLER_CLASS))

callGraph = load_graph("stocker/call_addkeeprule")
CALL_ADDRULE_T = tmpl_from(callGraph, callGraph.nodes[0].name)
KNOT_T = load_template("flow/knot")

DRYWOOD_TID = "18025"

# --- build ---------------------------------------------------------------------
gacFurnace = add(FURNACE_GAC_T)
itemFurnace = add(ITEM_T)
connect(gacFurnace, "OutActors", itemFurnace, "Array")

gacMC = add(MODCONTROLLER_GAC_T)
itemMC = add(ITEM_T)
connect(gacMC, "OutActors", itemMC, "Array")

connect_exec(gacFurnace, gacMC, "then", "execute")

call = add(CALL_ADDRULE_T)
connect(itemFurnace, "Output", call, "Station")
connect(itemMC, "Output", call, "self")
setd(call, "TemplateID", DRYWOOD_TID)
connect_exec(gacMC, call, "then", "execute")

# --- 3 knots: the hand-wire landing points --------------------------------------
knotExec = add(KNOT_T)
setf(knotExec, "InputPin", "PinType.PinCategory", '"exec"')
setf(knotExec, "InputPin", "PinType.PinSubCategoryObject", "None")
setf(knotExec, "OutputPin", "PinType.PinCategory", '"exec"')
setf(knotExec, "OutputPin", "PinType.PinSubCategoryObject", "None")
connect_exec(knotExec, gacFurnace, "OutputPin", "execute")

knotKeep = add(KNOT_T)
setf(knotKeep, "InputPin", "PinType.PinCategory", '"int"')
setf(knotKeep, "InputPin", "PinType.PinSubCategoryObject", "None")
setf(knotKeep, "OutputPin", "PinType.PinCategory", '"int"')
setf(knotKeep, "OutputPin", "PinType.PinSubCategoryObject", "None")
connect(knotKeep, "OutputPin", call, "Keep")

knotKeepAll = add(KNOT_T)
setf(knotKeepAll, "InputPin", "PinType.PinCategory", '"bool"')
setf(knotKeepAll, "InputPin", "PinType.PinSubCategoryObject", "None")
setf(knotKeepAll, "OutputPin", "PinType.PinCategory", '"bool"')
setf(knotKeepAll, "OutputPin", "PinType.PinSubCategoryObject", "None")
connect(knotKeepAll, "OutputPin", call, "KeepAll")

# --- layout ----------------------------------------------------------------------
knotExec.set_position(-100, 0)
gacFurnace.set_position(150, 0)
itemFurnace.set_position(500, 0)
gacMC.set_position(150, 200)
itemMC.set_position(500, 200)
call.set_position(850, 100)
knotKeep.set_position(700, 500)
knotKeepAll.set_position(700, 600)

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

wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

dangling = [(n.name, p.name) for n in g.nodes for p in n.pins if not p.links]
print("intentionally dangling (hand-wire landing points + literals):")
for nn, pn in dangling:
    print(f"  {nn}.{pn}")

out = MOD + r"\.ccmod\graphs\widget_onclicked_body.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
