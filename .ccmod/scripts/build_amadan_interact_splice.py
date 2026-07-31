"""Hook W_StockerTestPanel to the real desk's interact event instead of the
abandoned always-visible-on-BeginPlay approach.

Base: the freshly-added, still-mostly-empty InteractableActivate override on
BP_PL_WorkStation_Amadan (pulled as 'stocker/amadan_interactableactivate_raw')
-- 2 nodes, UE auto-wired the Event straight into a Parent-function call so
the default interact behavior (whatever BP_Master_Placeables does) is
preserved. CallParentFunction.then is dangling; that's the splice point.

New chain, reusing the exact node shapes proven end-to-end in
modcontroller_input_mode_splice.t3d (playtest-confirmed, 2026-07-18):
  CallParentFunction.then -> CreateWidget(W_StockerTestPanel) -> AddToViewport
  -> Set bShowMouseCursor(true) -> SetInputMode_UIOnlyEx
GetPlayerController is PURE (no exec pins) and fans out by data to all three
consumers that need a PlayerController -- pure-node fan-out is fine, only
EXEC fan-out is restricted in this DevKit (see stocker-exec-fanout-gotcha).

No hand-wires needed: both existing nodes were fully captured, so this is a
complete in-code edit, not a splice into an opaque live graph -- the user
selects-all + deletes the 2 old nodes and pastes this whole corrected
fragment back in one shot (same full-graph-edit process, just on a small
graph this time).
"""
import sys
import copy

import os, pathlib
CCMOD = os.environ.get("CCMOD_HOME") or str(pathlib.Path(__file__).resolve().parents[3] / "claude-conan-modder")
sys.path.insert(0, CCMOD)
from ccmod import db
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph
from ccmod.workspace import Workspace

import pathlib
MOD = str(pathlib.Path(__file__).resolve().parents[2])

ws = Workspace.resolve()
conn = db.connect(ws.cache_db)


def load_graph(name):
    row = db.get_graph(conn, name)
    assert row, f"no saved graph '{name}'"
    return parse(row["t3d"])


def load_file(path):
    return parse(open(path, encoding="utf-8").read())


def tmpl_from(graph, name):
    n = copy.deepcopy(graph.by_name(name))
    for p in n.pins:
        p.links = []
    return Graph(nodes=[n])


def pin(n, name):
    p = n.pin_by_name(name)
    assert p, f"{n.name} has no pin {name}"
    return p


# --- base: the real 2-node override, pulled from the DevKit -------------------
g = load_graph("stocker/amadan_interactableactivate_raw")
assert len(g.nodes) == 2, f"expected 2 nodes, got {len(g.nodes)}"

event = g.by_name("K2Node_Event_0")
callParent = g.by_name("K2Node_CallParentFunction_0")
assert pin(callParent, "then").links == [], "expected CallParentFunction.then dangling"

# --- templates, lifted from the proven input-mode-splice graph ----------------
src = load_file(MOD + r"\.ccmod\graphs\modcontroller_input_mode_splice.t3d")

CREATEWIDGET_T = tmpl_from(src, "K2Node_CreateWidget_0")
ADDTOVIEWPORT_T = tmpl_from(src, "K2Node_CallFunction_238")
SETSHOWMOUSE_T = tmpl_from(src, "K2Node_VariableSet_0")
SETINPUTMODE_T = tmpl_from(src, "K2Node_CallFunction_417")
GETPC_T = tmpl_from(src, "K2Node_CallFunction_239")


def add(t):
    return instantiate(t, g)[0]


createWidget = add(CREATEWIDGET_T)
addToViewport = add(ADDTOVIEWPORT_T)
setShowMouse = add(SETSHOWMOUSE_T)
setInputMode = add(SETINPUTMODE_T)
getPC = add(GETPC_T)

# --- exec chain: CallParentFunction.then is a single dangling pin, plain connect ---
connect_exec(callParent, createWidget, "then", "execute")
connect_exec(createWidget, addToViewport, "then", "execute")
connect_exec(addToViewport, setShowMouse, "then", "execute")
connect_exec(setShowMouse, setInputMode, "then", "execute")

# --- data: GetPlayerController is pure, fans out by data to 3 consumers -----------
connect(getPC, "ReturnValue", createWidget, "OwningPlayer")
connect(getPC, "ReturnValue", setShowMouse, "self")
connect(getPC, "ReturnValue", setInputMode, "PlayerController")

connect(createWidget, "ReturnValue", addToViewport, "self")
connect(createWidget, "ReturnValue", setInputMode, "InWidgetToFocus")

# --- layout --------------------------------------------------------------------
event.set_position(0, 0)
callParent.set_position(350, 0)
createWidget.set_position(700, 0)
addToViewport.set_position(1050, 0)
setShowMouse.set_position(1400, 0)
setInputMode.set_position(1750, 0)
getPC.set_position(700, 300)

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

for nn, pn in [(callParent.name, "then"), (createWidget.name, "execute"),
               (createWidget.name, "then"), (addToViewport.name, "execute"),
               (addToViewport.name, "then"), (setShowMouse.name, "execute"),
               (setShowMouse.name, "then"), (setInputMode.name, "execute")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

dangling = [(n.name, p.name) for n in g.nodes for p in n.pins if not p.links]
print("intentionally dangling (event params + literals + chain end):")
for nn, pn in dangling:
    print(f"  {nn}.{pn}")

out = MOD + r"\.ccmod\graphs\amadan_interact_splice.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
