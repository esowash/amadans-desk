"""Rebuild the full ActivateModule-based interact chain onto the freshly
re-added InteractableActivate override (the original got lost when a stray
ModDataTableOperations paste landed in the desk's EventGraph instead -- this
is a clean restart on a fresh 2-node capture, not a delta).

Drops the auto-wired Parent call (this time pointing at BP_PlaceableItemContainer's
implementation -- doesn't matter which ancestor, same mechanism as before) and
builds: Event.then -> STOCKER_INTERACT begin -> GetGUIModuleController ->
ActivateModule("StockerHouseRules") -> STOCKER_INTERACT done. Same idiom
verified this session off BP_PL_Sign_Master's real interact handler.
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


# --- base: the fresh 2-node capture ---------------------------------------------
g = load_graph("stocker/amadan_interactableactivate_fresh2")
assert len(g.nodes) == 2, f"expected 2 nodes, got {len(g.nodes)}"

event = g.by_name("K2Node_Event_7")
callParent = g.by_name("K2Node_CallParentFunction_3")
assert pin(event, "then").links == [
    (callParent.name, pin(callParent, "execute").pin_id)]

# --- drop the Parent call: clear its remaining data-pin links first ------------
for p in callParent.pins:
    for (lnn, lp) in p.links:
        other = g.by_name(lnn).pin_by_id(lp)
        if other is not None:
            other.links = [lk for lk in other.links if lk != (callParent.name, p.pin_id)]
    p.links = []
event.pin_by_name("then").links = []
g.nodes = [n for n in g.nodes if n.name != callParent.name]

# --- templates -------------------------------------------------------------------
mcSrc = parse(open(MOD + r"\.ccmod\graphs\modcontroller_anchor_repointed.t3d", encoding="utf-8").read())
PRINT_T = tmpl_from(mcSrc, "K2Node_CallFunction_21")

signSrc = parse(open(MOD + r"\.ccmod\graphs\signmaster_activatemodule_idiom.t3d", encoding="utf-8").read())
GETGUI_T = tmpl_from(signSrc, "K2Node_CallFunction_4")
ACTIVATE_T = tmpl_from(signSrc, "K2Node_CallFunction_5")

printBegin = add(PRINT_T, g)
printDone = add(PRINT_T, g)
pin(printBegin, "InString")._set("DefaultValue", '"STOCKER_INTERACT begin (desk widget hookup)"')
pin(printDone, "InString")._set("DefaultValue", '"STOCKER_INTERACT done (ActivateModule)"')

getGui = add(GETGUI_T, g)
activate = add(ACTIVATE_T, g)
connect(getGui, "ReturnValue", activate, "self")
pin(activate, "moduleName")._set("DefaultValue", '"StockerHouseRules"')

# --- exec chain --------------------------------------------------------------------
connect_exec(event, printBegin, "then", "execute")
connect_exec(printBegin, activate, "then", "execute")
connect_exec(activate, printDone, "then", "execute")

# --- layout ----------------------------------------------------------------------
event.set_position(0, 0)
printBegin.set_position(400, 0)
getGui.set_position(750, -200)
activate.set_position(1100, 0)
printDone.set_position(1550, 0)

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

for nn, pn in [(event.name, "then"), (printBegin.name, "then"),
               (activate.name, "execute"), (activate.name, "then"),
               (printDone.name, "execute")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\amadan_interact_final.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"nodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
