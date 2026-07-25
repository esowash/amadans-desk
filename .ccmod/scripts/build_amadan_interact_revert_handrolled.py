"""Revert from the ActivateModule dead end (confirmed blocked by DT_UIModuleTable
being cached ~17s before our mod controller activates -- not fixable from a
Blueprint-only mod) back to the hand-rolled chain, which got 2 of 3 problems
solved (panel visible, camera-lock via IgnoreMoveInput/IgnoreLookInput) with
only mouse-cursor-visibility left open.

Base: amadan_interact_diagnose.t3d (9 nodes, currently live on the desk --
Event + STOCKER_INTERACT begin, then GetGUIModuleController/ActivateModule/
IsValid/Branch/printOk/printFail/printDone). Keep Event + begin print, drop
everything else, splice in the known-good hand-rolled chain from
amadan_interact_ignoreinput.t3d (CreateWidget -> AddToViewport ->
SetShowMouseCursor -> SetInputMode_UIOnlyEx -> SetIgnoreMoveInput ->
SetIgnoreLookInput), ending on a fresh STOCKER_INTERACT done print.
"""
import sys
import copy

CCMOD = r"<CCMOD_HOME>"
sys.path.insert(0, CCMOD)
from ccmod.t3d import parse, connect, connect_exec
from ccmod.t3d.generator import instantiate
from ccmod.t3d.model import Graph

MOD = r"<MOD_ROOT>"


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


# --- base: the current live desk graph (ActivateModule + diagnostics) ---------
g = parse(open(MOD + r"\.ccmod\graphs\amadan_interact_diagnose.t3d", encoding="utf-8").read())
print("base graph nodes:", len(g.nodes))

event = g.by_name("K2Node_Event_7")
printBegin = g.by_name("K2Node_CallFunction_21")

keep = {event.name, printBegin.name}
dropped = [n for n in g.nodes if n.name not in keep]
print(f"dropping {len(dropped)} ActivateModule/diagnostic nodes:")
for n in dropped:
    print("  -", n.name)

begin_then = pin(printBegin, "then")
old_head_name = begin_then.links[0][0]
old_head = g.by_name(old_head_name)
old_head.pin_by_name("execute").links = []
begin_then.links = []

g.nodes = [n for n in g.nodes if n.name in keep]

# --- templates, lifted from the last known-good hand-rolled build --------------
src = parse(open(MOD + r"\.ccmod\graphs\amadan_interact_ignoreinput.t3d", encoding="utf-8").read())
CREATEWIDGET_T = tmpl_from(src, "K2Node_CreateWidget_0")
ADDTOVIEWPORT_T = tmpl_from(src, "K2Node_CallFunction_238")
SETSHOWMOUSE_T = tmpl_from(src, "K2Node_VariableSet_0")
SETINPUTMODE_T = tmpl_from(src, "K2Node_CallFunction_417")
GETPC_T = tmpl_from(src, "K2Node_CallFunction_239")
IGNOREMOVE_T = tmpl_from(src, "K2Node_CallFunction_8")
IGNORELOOK_T = tmpl_from(src, "K2Node_CallFunction_9")
PRINT_T = tmpl_from(src, "K2Node_CallFunction_21")  # STOCKER_INTERACT begin, reused as a bare template

createWidget = add(CREATEWIDGET_T, g)
addToViewport = add(ADDTOVIEWPORT_T, g)
setShowMouse = add(SETSHOWMOUSE_T, g)
setInputMode = add(SETINPUTMODE_T, g)
getPC = add(GETPC_T, g)
ignoreMove = add(IGNOREMOVE_T, g)
ignoreLook = add(IGNORELOOK_T, g)
printDone = add(PRINT_T, g)
pin(printDone, "InString")._set("DefaultValue", '"STOCKER_INTERACT done (hand-rolled, reverted from ActivateModule)"')

# --- exec chain --------------------------------------------------------------------
connect_exec(printBegin, createWidget, "then", "execute")
connect_exec(createWidget, addToViewport, "then", "execute")
connect_exec(addToViewport, setShowMouse, "then", "execute")
connect_exec(setShowMouse, setInputMode, "then", "execute")
connect_exec(setInputMode, ignoreMove, "then", "execute")
connect_exec(ignoreMove, ignoreLook, "then", "execute")
connect_exec(ignoreLook, printDone, "then", "execute")

# --- data: GetPlayerController (pure) fans out to every consumer that needs it ---
connect(getPC, "ReturnValue", createWidget, "OwningPlayer")
connect(getPC, "ReturnValue", setShowMouse, "self")
connect(getPC, "ReturnValue", setInputMode, "PlayerController")
connect(getPC, "ReturnValue", ignoreMove, "self")
connect(getPC, "ReturnValue", ignoreLook, "self")

connect(createWidget, "ReturnValue", addToViewport, "self")
connect(createWidget, "ReturnValue", setInputMode, "InWidgetToFocus")

pin(ignoreMove, "bNewMoveInput")._set("DefaultValue", '"true"')
pin(ignoreLook, "bNewLookInput")._set("DefaultValue", '"true"')
pin(addToViewport, "ZOrder")._set("DefaultValue", '"1000"')

# --- layout ----------------------------------------------------------------------
createWidget.set_position(700, 0)
addToViewport.set_position(1050, 0)
setShowMouse.set_position(1400, 0)
setInputMode.set_position(1750, 0)
ignoreMove.set_position(2100, 0)
ignoreLook.set_position(2450, 0)
printDone.set_position(2800, 0)
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

for nn, pn in [(printBegin.name, "then"), (createWidget.name, "execute"),
               (createWidget.name, "then"), (addToViewport.name, "execute"),
               (addToViewport.name, "then"), (setShowMouse.name, "execute"),
               (setShowMouse.name, "then"), (setInputMode.name, "execute"),
               (setInputMode.name, "then"), (ignoreMove.name, "execute"),
               (ignoreMove.name, "then"), (ignoreLook.name, "execute"),
               (ignoreLook.name, "then"), (printDone.name, "execute")]:
    p = g.by_name(nn).pin_by_name(pn)
    if len(p.links) != 1:
        problems.append(f"{nn}.{pn} has {len(p.links)} links, expected exactly 1")

wilds = [(n.name, p.name) for n in g.nodes for p in n.pins
         if p._get("PinType.PinCategory") == '"wildcard"']
assert not wilds, f"unresolved wildcards: {wilds}"

out = MOD + r"\.ccmod\graphs\amadan_interact_reverted.t3d"
open(out, "w", encoding="utf-8").write(g.render())
print(f"\nnodes: {len(g.nodes)}   wrote: {out}")
print(f"problems: {len(problems)}")
for pr in problems:
    print("  !", pr)
